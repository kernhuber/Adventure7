"""Die INNERE Schleife des Agenten – das Lehrstück dieses Pakets.

Zwei verschachtelte Schleifen:
  außen: die Spielrunden (runner.py) – das Spiel schreitet Zug für Zug fort
  innen: DIESE Datei – in einer Runde fragt der Agent das Modell, führt Werkzeuge aus, sieht die
         Ergebnisse und fragt erneut, bis er einen Zug macht.
Eine Agentenschleife ist im Kern genau das: Modell fragen -> Werkzeug ausführen -> Ergebnis zurückgeben
-> wiederholen. Alles andere in diesem Paket ist Zubehör.
"""
from dataclasses import dataclass

from agent_player import config
from agent_player.context import AgentContext, RoundEntry, round_message
from agent_player.llm import ToolCall, ToolResult, Message
from agent_player.observation import observation_as_text, evaluate_events
from agent_player.tools import FREE_ACTIONS, MOVES, FREE_NAMES, MOVE_NAMES, prepare_move


@dataclass
class RoundResult:
    move: str
    why: str
    result: str
    neutral: bool = False      # True, wenn das Aufruflimit zu einem Ersatzzug geführt hat


async def play_round(ctx: AgentContext) -> RoundResult:
    """Eine Spielrunde des Agenten: so lange Werkzeuge nutzen, bis er einen Zug macht."""
    ctx.new_round()
    # LERNPUNKT: frischer Kontext je Runde (siehe context.py) – der Verlauf der Runde lebt nur in `nachrichten`.
    messages = [round_message(ctx)]
    tools = FREE_ACTIONS + MOVES
    while ctx.calls_round < config.MAX_CALLS_PER_ROUND:
        response = await ctx.ask_model(messages, tools)              # 1. Modell fragen
        messages.append(Message.from_model(response))
        if not response.calls:                                               # Modell hat nur geredet
            ctx.calls_round += 1
            messages.append(Message.from_user(config.NUDGE_NO_TOOL))
            continue
        results = []
        for call in response.calls:
            await ctx.controller.before_step()                                 # Pause / Einzelschritt / Tempo
            ctx.calls_round += 1
            ctx.step += 1
            result, was_move = await run_tool(ctx, call)        # 2. Werkzeug ausführen
            results.append(result)
            await ctx.send_status()
            if was_move:                                                       # ein Zug beendet die Runde,
                return RoundResult(call.name, str(call.args.get("warum", "")), result.text)  # der Kontext wird verworfen
        messages.append(Message.tool_results(results))         # 3. Ergebnis zurück ans Modell, dann von vorn
    return await force_move(ctx, messages)                               # Limit erreicht


# ---------------------------------------------------------------------------------------
# Hilfsfunktionen (bewusst außerhalb der Schleife, damit diese lesbar bleibt)
# ---------------------------------------------------------------------------------------
async def run_tool(ctx: AgentContext, call: ToolCall) -> tuple[ToolResult, bool]:
    """Führt ein Werkzeug aus. Rückgabe: (Ergebnis fürs Modell, wurde ein Zug ausgeführt?)."""
    if call.name in FREE_NAMES:
        text = run_free_action(ctx, call)
        await ctx.report({"type": "agent_event", "kind": "free", "tool": call.name, "args": call.args,
                         "result": text, "round": ctx.round_number, "step": ctx.step})
        if call.name == "notizbuch_schreiben":
            await ctx.report({"type": "agent_notebook", "text": ctx.notebook.read()})
        return ToolResult(call.name, text), False
    if call.name in MOVE_NAMES:
        if not str(call.args.get("warum", "")).strip():
            return await _error(ctx, call, "Jeder Zug braucht das Argument 'warum' (ein Satz).")
        function_call, error = prepare_move(call.name, call.args, ctx.get_view())
        if function_call is None:
            return await _error(ctx, call, error)
        return await execute_move(ctx, call, function_call)
    return await _error(ctx, call, f"Unbekanntes Werkzeug '{call.name}'.")


async def execute_move(ctx: AgentContext, call: ToolCall, function_call: dict) -> tuple[ToolResult, bool]:
    """Schickt einen Zug durch den normalen Rundenpfad (derselbe wie beim Menschen)."""
    events = await ctx.run_move(function_call)
    a = evaluate_events(events)
    if a.error:                                   # Systemfehler der Engine: kostet keine Runde
        return await _error(ctx, call, a.text or "Die Engine hat den Zug abgelehnt.")
    ctx.last_result, ctx.npc_messages = a.text, a.npc_messages
    why = str(call.args.get("warum", ""))
    ctx.history.append(RoundEntry(ctx.round_number, f"{call.name} {_args_text(call)}", why, a.text))
    display = a.text + ("\n" if a.text and a.npc_messages else "") + "\n".join(f"⚠ {m}" for m in a.npc_messages)
    await ctx.report({"type": "agent_event", "kind": "move", "tool": call.name, "args": _without_why(call.args),
                     "warum": why, "result": display, "round": ctx.round_number, "step": ctx.step})
    return ToolResult(call.name, a.text), True


async def force_move(ctx: AgentContext, messages: list[Message]) -> RoundResult:
    """Aufruflimit erreicht: Agent auffordern, jetzt zu ziehen; sonst neutraler Zug (wird protokolliert)."""
    messages.append(Message.from_user(config.NUDGE_FORCE_MOVE.format(max_calls=config.MAX_CALLS_PER_ROUND)))
    response = await ctx.ask_model(messages, MOVES)
    for call in response.calls:
        if call.name not in MOVE_NAMES:               # jetzt zählen nur noch Züge
            continue
        await ctx.controller.before_step()
        ctx.step += 1
        result, was_move = await run_tool(ctx, call)
        if was_move:
            return RoundResult(call.name, str(call.args.get("warum", "")), result.text)
    neutral = ToolCall("umsehen", {"warum": "Limit erreicht – neutraler Ersatzzug"})
    ctx.step += 1
    result, _ = await execute_move(ctx, neutral, {"function_call": {"name": "umsehen", "args": {}}})
    return RoundResult("umsehen", neutral.args["warum"], result.text, neutral=True)


def run_free_action(ctx: AgentContext, call: ToolCall) -> str:
    """Freie Aktionen: lesen/schreiben nur im eigenen Gedächtnis bzw. in der Beobachtung – die Welt bleibt unberührt."""
    view = ctx.get_view()
    if call.name == "situation_lesen":
        return observation_as_text(view, ctx.last_result, ctx.npc_messages)
    if call.name == "inventar_ansehen":
        return "Inventar: " + (", ".join(view.get("player", {}).get("inventory", [])) or "leer")
    if call.name == "notizbuch_lesen":
        return ctx.notebook.read()
    if call.name == "notizbuch_schreiben":
        ctx.notebook.write(str(call.args.get("text", "")))
        return "Notiert."
    if call.name == "spielstand_speichern":
        if ctx.save is None:
            return "Speichern ist hier nicht möglich."
        return ctx.save(str(call.args.get("notiz", "")))
    # was_weiss_ich_ueber: nur Notizbuch und eigener Verlauf, NIE die Spielwelt
    term = str(call.args.get("begriff", "")).strip().lower()
    found = [e for e in ctx.notebook.entries if term in e.lower()]
    found += [e.as_text() for e in ctx.history if term in e.as_text().lower()]
    return "\n".join(found) if term and found else f"Zu '{term}' steht nichts in deinem Notizbuch oder Verlauf."


async def _error(ctx: AgentContext, call: ToolCall, text: str) -> tuple[ToolResult, bool]:
    """Fehler als Werkzeugergebnis: verständlich, und ohne dass eine Runde vergeht."""
    await ctx.report({"type": "agent_event", "kind": "error", "tool": call.name, "args": _without_why(call.args),
                     "warum": str(call.args.get("warum", "")), "result": text, "round": ctx.round_number, "step": ctx.step})
    return ToolResult(call.name, f"FEHLER (keine Runde verbraucht): {text}"), False


def _without_why(args: dict) -> dict:
    return {k: v for k, v in args.items() if k != "warum"}


def _args_text(call: ToolCall) -> str:
    return " ".join(str(v) for v in _without_why(call.args).values())
