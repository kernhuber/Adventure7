"""Die Gesprächsschleife des Agenten (Baustein B).

Sie hat denselben Aufbau wie die Rundenschleife in loop.py – Modell fragen, Werkzeug ausführen, Ergebnis
zurückgeben, wiederholen – nur mit anderen Werkzeugen: `sage` und `gespraech_beenden`.

LERNPUNKT: Hier verhandeln ZWEI Modelle miteinander. Der Agent (Gemini mit Werkzeugen) spricht mit dem
Zombie bzw. Hund (ein anderer, unabhängiger Prompt in npc_zombie_state.py / npc_dog_state.py). Das NPC-seitige
Verhalten ist unverändert: Wir liefern nur den Text, den sonst ein Mensch tippen würde.
"""
from typing import Awaitable, Callable

from utils import dprint, dl
from agent_player import config
from agent_player.context import AgentContext, chat_message
from agent_player.llm import ToolResult, Message
from agent_player.tools import CHAT_TOOLS

# npc_reply(chat) -> Antworttext des Partners;  zeige(sprecher, text) -> Anzeige im Chat-Modal
NpcReply = Callable[[list[dict]], Awaitable[str]]
ShowFn = Callable[[str, str], Awaitable[None]]


async def run_conversation(ctx: AgentContext, partner: str, npc_reply: NpcReply, show: ShowFn,
                           npc_start: str = "", agent_start: str = "") -> list[dict]:
    """Führt ein Gespräch bis es endet. Rückgabe: der Gesprächsverlauf (Format wie im Browser-Modal)."""
    dprint(dl.AGENT, f"💬 Gespräch mit {partner} beginnt (NPC-Eröffnung: {npc_start!r}, Agent-Eröffnung: {agent_start!r})")
    chat: list[dict] = []
    if npc_start:                                                        # der NPC hat das Gespräch eröffnet
        chat.append({"zombiemessage": npc_start})
    exchanges = 0
    if agent_start:                                                      # der Agent hat eröffnet (ansprechen mit erster Nachricht)
        await _say(ctx, partner, agent_start, chat, npc_reply, show)
        exchanges += 1
    messages = [chat_message(ctx, partner, chat)]
    summary, partner_ended = "", False
    attempts = 0                                                         # Sicherung gegen endlose Fehlaufrufe
    while (exchanges < config.MAX_CHAT_EXCHANGES and attempts < 2 * config.MAX_CHAT_EXCHANGES + 2
           and not summary and not partner_ended):
        attempts += 1
        response = await ctx.ask_model(messages, CHAT_TOOLS)    # 1. Modell fragen
        messages.append(Message.from_model(response))
        if not response.calls:
            exchanges += 1
            messages.append(Message.from_user(config.NUDGE_CHAT_NO_TOOL))
            continue
        results = []
        for call in response.calls:
            dprint(dl.AGENT, f"💬 Chat: warte auf Freigabe für '{call.name}' (laufend={ctx.controller.running})")
            await ctx.controller.before_step()                            # Pause / Einzelschritt gilt auch im Chat
            ctx.step += 1
            if call.name == "sage":                                    # 2. Werkzeug ausführen
                reply = await _say(ctx, partner, str(call.args.get("text", "")), chat, npc_reply, show)
                exchanges += 1
                partner_ended = reply.strip().lower() == "quit"        # so beendet ein NPC das Gespräch
                results.append(ToolResult("sage", f"{partner} beendet das Gespräch." if partner_ended
                                                 else f'{partner} antwortet: "{reply}"'))
            elif call.name == "gespraech_beenden":
                summary = str(call.args.get("zusammenfassung", "")).strip() or "(keine Zusammenfassung)"
                break
            else:
                results.append(ToolResult(call.name, "FEHLER: Im Gespräch gibt es nur 'sage' und 'gespraech_beenden'."))
            if partner_ended:
                break
        while len(results) < len(response.calls):                    # jeder Aufruf braucht ein Ergebnis (Gemini verlangt das)
            results.append(ToolResult(response.calls[len(results)].name, "Nicht ausgeführt."))
        messages.append(Message.tool_results(results))    # 3. Ergebnis zurück, dann von vorn
    if not summary:                                              # Limit oder Partner hat beendet
        summary = await _wrap_up(ctx, partner, messages, partner_ended)
    await _write_to_notebook(ctx, partner, summary)
    dprint(dl.AGENT, f"💬 Gespräch mit {partner} beendet: {summary[:80]!r}")
    return chat


async def _say(ctx: AgentContext, partner: str, text: str, chat: list[dict],
                npc_reply: NpcReply, show: ShowFn) -> str:
    """Der Agent spricht, der Partner antwortet; beides erscheint im Chat-Modal und im Panel."""
    text = text.strip() or "..."
    chat.append({"playermessage": text})
    await show("agent", text)
    reply = (await npc_reply(chat)).strip() or "(schweigt)"
    chat.append({"zombiemessage": reply})
    await show("npc", reply)
    await ctx.report({"type": "agent_event", "kind": "chat", "tool": "sage", "args": {},
                     "result": f"Agent: {text}\n{partner}: {reply}", "round": ctx.round_number, "step": ctx.step})
    return reply


async def _wrap_up(ctx: AgentContext, partner: str, messages: list[Message], partner_ended: bool) -> str:
    """Gespräch zu Ende, ohne dass der Agent es selbst beendet hat: einmal nach der Zusammenfassung fragen."""
    reason = (config.CHAT_REASON_PARTNER_ENDED.format(partner=partner) if partner_ended
              else config.CHAT_REASON_LIMIT)
    messages.append(Message.from_user(config.PROMPT_CHAT_WRAP_UP.format(reason=reason)))
    response = await ctx.ask_model(messages, [CHAT_TOOLS[1]])
    for call in response.calls:
        if call.name == "gespraech_beenden":
            return str(call.args.get("zusammenfassung", "")).strip() or "(keine Zusammenfassung)"
    return f"({reason})"


async def _write_to_notebook(ctx: AgentContext, partner: str, summary: str) -> None:
    ctx.notebook.write(f"Gespräch mit {partner} (Runde {ctx.round_number}): {summary}")
    await ctx.report({"type": "agent_event", "kind": "chat", "tool": "gespraech_beenden", "args": {},
                     "result": f"Zusammenfassung fürs Notizbuch: {summary}", "round": ctx.round_number, "step": ctx.step})
    await ctx.report({"type": "agent_notebook", "text": ctx.notebook.read()})
