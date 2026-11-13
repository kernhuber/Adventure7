"""Das PIN-Pad des Geldautomaten, bedient vom Agenten.

LERNPUNKT: Der Server kennt die PIN nur als MD5-Hash (die Engine reicht den Hash an den "Dialog" weiter,
im Browser prüft pinpad.js dann die Eingabe dagegen). Hier prüft der Server selbst – nach denselben Regeln:
vier Ziffern eintippen, ein Versuch pro Karteneinsatz. Die Zahl selbst steht nirgends im Prompt; der Agent
muss sie im Spiel gefunden und in sein Notizbuch geschrieben haben (guter Test fürs Notizbuch!).
"""
import hashlib

from utils import dprint, dl
from agent_player import config
from agent_player.context import AgentContext, pin_message
from agent_player.llm import ToolResult, Message
from agent_player.tools import PIN_TOOLS

MAX_MODEL_CALLS = 6      # Sicherung: das Pad darf den Agenten nicht endlos beschäftigen


async def solve_pinpad(ctx: AgentContext, expected_hash: str) -> str:
    """Lässt den Agenten die PIN eingeben. Rückgabe wie beim Browser-Pad: "OK" oder "FAIL"."""
    messages = [pin_message(ctx)]
    for _ in range(MAX_MODEL_CALLS):
        response = await ctx.ask_model(messages, PIN_TOOLS)
        messages.append(Message.from_model(response))
        results = []
        for call in response.calls:
            await ctx.controller.before_step()
            ctx.step += 1
            if call.name == "notizbuch_lesen":
                text = ctx.notebook.read()
                await _show(ctx, "free", "notizbuch_lesen", {}, text)
                results.append(ToolResult(call.name, text))
            elif call.name == "pin_eingeben":
                digits = str(call.args.get("ziffern", "")).strip()
                if not (digits.isdigit() and len(digits) == 4):
                    error = "Die Geheimzahl besteht aus genau vier Ziffern."
                    await _show(ctx, "error", "pin_eingeben", {"ziffern": digits}, error)
                    results.append(ToolResult(call.name, "FEHLER: " + error))
                    continue
                correct = hashlib.md5(digits.encode()).hexdigest() == expected_hash
                await _show(ctx, "pin", "pin_eingeben", {"ziffern": digits},
                             "Die Zahl stimmt!" if correct else "Die Zahl ist falsch.")
                dprint(dl.AGENT, f"🔐 PIN eingegeben: {digits} -> {'OK' if correct else 'FAIL'}")
                return "OK" if correct else "FAIL"            # ein Versuch pro Karteneinsatz, wie beim Menschen
            else:
                results.append(ToolResult(call.name, "FEHLER: Am PIN-Pad gibt es nur 'notizbuch_lesen' und 'pin_eingeben'."))
        if response.calls:
            messages.append(Message.tool_results(results))
        else:
            messages.append(Message.from_user(config.NUDGE_PIN_NO_TOOL))
    return "FAIL"


async def _show(ctx: AgentContext, kind: str, tool: str, args: dict, text: str) -> None:
    await ctx.report({"type": "agent_event", "kind": kind, "tool": tool, "args": args, "result": text,
                     "round": ctx.round_number, "step": ctx.step})
