"""Das PIN-Pad des Geldautomaten, bedient vom Agenten.

LERNPUNKT: Der Server kennt die PIN nur als MD5-Hash (die Engine reicht den Hash an den "Dialog" weiter,
im Browser prüft pinpad.js dann die Eingabe dagegen). Hier prüft der Server selbst – nach denselben Regeln:
vier Ziffern eintippen, ein Versuch pro Karteneinsatz. Die Zahl selbst steht nirgends im Prompt; der Agent
muss sie im Spiel gefunden und in sein Notizbuch geschrieben haben (guter Test fürs Notizbuch!).
"""
import hashlib

from utils import dprint, dl
from agent_player.context import AgentKontext, pin_nachricht
from agent_player.llm import AufrufErgebnis, Nachricht
from agent_player.tools import PIN_WERKZEUGE

MAX_MODELLAUFRUFE = 6      # Sicherung: das Pad darf den Agenten nicht endlos beschäftigen


async def loese_pinpad(ctx: AgentKontext, erwarteter_hash: str) -> str:
    """Lässt den Agenten die PIN eingeben. Rückgabe wie beim Browser-Pad: "OK" oder "FAIL"."""
    nachrichten = [pin_nachricht(ctx)]
    for _ in range(MAX_MODELLAUFRUFE):
        antwort = await ctx.frage_modell(nachrichten, PIN_WERKZEUGE)
        nachrichten.append(Nachricht.vom_modell(antwort))
        ergebnisse = []
        for aufruf in antwort.aufrufe:
            await ctx.steuerung.vor_schritt()
            ctx.schritt += 1
            if aufruf.name == "notizbuch_lesen":
                text = ctx.notizbuch.lesen()
                await _zeige(ctx, "free", "notizbuch_lesen", {}, text)
                ergebnisse.append(AufrufErgebnis(aufruf.name, text))
            elif aufruf.name == "pin_eingeben":
                ziffern = str(aufruf.args.get("ziffern", "")).strip()
                if not (ziffern.isdigit() and len(ziffern) == 4):
                    fehler = "Die Geheimzahl besteht aus genau vier Ziffern."
                    await _zeige(ctx, "error", "pin_eingeben", {"ziffern": ziffern}, fehler)
                    ergebnisse.append(AufrufErgebnis(aufruf.name, "FEHLER: " + fehler))
                    continue
                richtig = hashlib.md5(ziffern.encode()).hexdigest() == erwarteter_hash
                await _zeige(ctx, "pin", "pin_eingeben", {"ziffern": ziffern},
                             "Die Zahl stimmt!" if richtig else "Die Zahl ist falsch.")
                dprint(dl.AGENT, f"🔐 PIN eingegeben: {ziffern} -> {'OK' if richtig else 'FAIL'}")
                return "OK" if richtig else "FAIL"            # ein Versuch pro Karteneinsatz, wie beim Menschen
            else:
                ergebnisse.append(AufrufErgebnis(aufruf.name, "FEHLER: Am PIN-Pad gibt es nur 'notizbuch_lesen' und 'pin_eingeben'."))
        if antwort.aufrufe:
            nachrichten.append(Nachricht.werkzeug_ergebnisse(ergebnisse))
        else:
            nachrichten.append(Nachricht.vom_nutzer("Rufe 'pin_eingeben' mit vier Ziffern auf."))
    return "FAIL"


async def _zeige(ctx: AgentKontext, art: str, werkzeug: str, args: dict, text: str) -> None:
    await ctx.melde({"type": "agent_event", "kind": art, "tool": werkzeug, "args": args, "result": text,
                     "round": ctx.runde, "step": ctx.schritt})
