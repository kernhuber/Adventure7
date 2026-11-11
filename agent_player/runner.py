"""Die ÄUSSERE Schleife des Agenten: Zug für Zug durch den normalen Rundenpfad.

LERNPUNKT (zwei verschachtelte Schleifen): Das Spiel kennt Runden – das ist die äußere
Schleife, hier in `_spiele_agent`. Pro Runde läuft darin die innere Denkschleife des Agenten
(`loop.spiele_runde`). Der Skript-Spieler (`_spiele_skript`) ersetzt das Denken durch eine feste Liste.

Wer spielt, bestimmt die URL: ?mode=agent (Gemini), &player=fake (Fake-Modell, kostenlos),
&player=skript (feste Befehlsliste aus Meilenstein 1).

LERNPUNKT (kein zweiter Regelpfad): `fuehre_zug_aus` legt den Zug in dieselbe Befehlswarteschlange
wie ein geparster Menschenbefehl und ruft `handle_command` auf. Durst, Rundenwechsel, NPC-Züge
und Game Over laufen daher exakt wie bei einem Menschen.
"""
import asyncio
import json
import time
import traceback

from utils import dprint, dl
from agent_player import config, spielstand
from agent_player.context import AgentKontext, TokenLimitErreicht
from agent_player.control import AgentSteuerung, AgentGestoppt
from agent_player.loop import spiele_runde
from agent_player.observation import ereignisse_auswerten
from agent_player.skript_spieler import SKRIPT
from agent_player.trace import Spur


class AgentRunner:
    def __init__(self, server, websocket, session: dict, session_id: str, spieler: str = "llm", agent_zustand: dict | None = None):
        self.server = server          # WebAdventureServer (hat handle_command)
        self.ws = websocket
        self.session = session
        self.session_id = session_id
        self.spieler = spieler         # "llm" | "fake" | "skript"
        self.ctx: AgentKontext | None = None
        self.agent_zustand = agent_zustand   # aus einem geladenen Spielstand (bereits geprüft), sonst None
        self.in_zug = False                  # True, solange ein Zug in der Engine läuft (dann nicht speichern)
        self._hinweis_text = ""        # Hinweis, der kam, bevor der Agent gestartet wurde
        self.spur: Spur | None = None
        self.steuerung = AgentSteuerung(config.START_TEMPO_MS)
        self.steuerung.bei_warten = self._sende_status
        self.task: asyncio.Task | None = None
        self.runde = 0
        self.schritt = 0
        self.ende: str | None = None   # None | "finished" | "game_over"

    # --- Kommandos aus dem Browser -------------------------------------------
    async def behandle_kommando(self, data: dict) -> None:
        aktion = data.get("action", "")
        if aktion == "save":                       # Zuschauer speichert Spiel + Agentenzustand
            await self._sende({"type": "info", "message": "💾 " + self.speichere(str(data.get("name", "")))})
            return
        if aktion == "slots":                      # Liste der Spielstände fürs Lade-Fenster des Panels
            await self._sende({"type": "agent_slots", "slots": spielstand.auflisten()})
            return
        if aktion == "hint":                       # Testhilfe: Zuschauer gibt dem Agenten einen Hinweis
            await self._hinweis(str(data.get("text", "")).strip())
            return
        self.steuerung.kommando(aktion, data.get("delay_ms"))
        if aktion in ("start", "resume", "step", "round") and self.task is None:
            self.task = asyncio.create_task(self._spiele_skript() if self.spieler == "skript" else self._spiele_agent())
        await self._sende_status()

    async def _hinweis(self, text: str) -> None:
        """Merkt einen Zuschauer-Hinweis für die NÄCHSTE Runde vor (protokolliert, damit man es in der Spur sieht)."""
        if not text:
            return
        self._hinweis_text = text
        if self.ctx is not None:
            self.ctx.hinweis = text
        await self._melde({"type": "agent_event", "kind": "text", "tool": "Zuschauer-Hinweis", "args": {},
                           "result": f"{text}\n(gilt ab der nächsten Runde)", "round": self.runde, "step": self.schritt})

    def speichere(self, name: str, notiz: str = "") -> str:
        """Speichert Spielstand + Agentenzustand. Rückgabe: Meldung (Erfolg oder Grund, warum es nicht ging)."""
        if self.in_zug:
            return "Gerade läuft ein Zug – bitte gleich noch einmal versuchen."
        name = spielstand.sicherer_name(name) or time.strftime("agent_%Y%m%d_%H%M%S")
        try:
            spielstand.speichern(self.session["game"], self.ctx, name, notiz)
        except Exception as e:
            dprint(dl.AGENT, f"❌ Speichern fehlgeschlagen: {e}")
            return f"Speichern fehlgeschlagen: {e}"
        zusatz = "" if self.ctx is not None else " (ohne Agentenzustand – der Agent hat noch nicht gestartet)"
        return f"Spielstand '{name}' gespeichert{zusatz}."

    def _speichere_fuer_agent(self, notiz: str) -> str:
        """Die freie Aktion 'spielstand_speichern' des Agenten: automatischer Name, seine Notiz kommt mit."""
        return self.speichere(f"agent_runde{self.ctx.runde}_{time.strftime('%H%M%S')}", notiz)

    def beenden(self) -> None:
        """Beim Trennen des Browsers aufräumen."""
        self.steuerung.kommando("stop")
        if self.task is not None:
            self.task.cancel()

    # --- Äußere Schleife ------------------------------------------------------
    async def _spiele_skript(self) -> None:
        game = self.session["game"]
        try:
            for schritt in SKRIPT:
                await self.steuerung.vor_schritt()
                self.runde = game.time
                self.schritt += 1
                ereignisse = await self.fuehre_zug_aus(schritt.als_function_call())
                await self._zeige_zug(schritt.verb, schritt.args, schritt.warum, ereignisse)
                self.steuerung.zug_beendet()
                if game.game_over:
                    self.ende = "game_over"
                    break
            else:
                self.ende = "finished"
        except (AgentGestoppt, asyncio.CancelledError):
            pass
        except Exception as e:
            dprint(dl.AGENT, f"❌ Agent abgestürzt: {e}")
            traceback.print_exc()
            dprint(dl.AGENT, traceback.format_exc())      # auch ins Debug-Log (stderr sieht man nicht immer)
            await self._sende({"type": "agent_event", "kind": "error", "tool": "-", "args": {},
                               "result": f"Interner Fehler im Agenten: {e}", "round": self.runde, "step": self.schritt})
        await self._sende_status()

    async def _spiele_agent(self) -> None:
        """Die äußere Schleife mit echtem Agenten: Runde für Runde, bis das Spiel oder ein Limit endet."""
        game = self.session["game"]
        self.spur = Spur()
        ende = "abgebrochen"
        try:
            ctx = AgentKontext(self._erzeuge_llm(), self.steuerung, lambda: self.session["state"],
                               self.fuehre_zug_aus, self._melde)
            self.ctx = ctx
            self.steuerung.bei_warten = ctx.sende_status      # Panel zeigt, wenn der Agent auf eine Freigabe wartet
            ctx.speichere = self._speichere_fuer_agent
            if self.agent_zustand:                            # aus einem Spielstand: Gedächtnis zurückspielen
                spielstand.importieren(ctx, self.agent_zustand)
                await self._melde({"type": "agent_notebook", "text": ctx.notizbuch.lesen()})
            ctx.hinweis = self._hinweis_text
            # Gespräche (Zombie/Hund) führt der Agent selbst: AgentDialogs braucht dafür den Kontext.
            if self.session.get("web_dialogs") is not None:
                self.session["web_dialogs"].ctx = ctx
            for _ in range(config.MAX_RUNDEN):
                await spiele_runde(ctx)                         # innere Schleife (loop.py)
                self.steuerung.zug_beendet()
                if game.game_over:
                    ende = "gewonnen" if game.game_won else "verloren"
                    break
            else:
                ende = "abgebrochen (Rundenlimit)"
        except (AgentGestoppt, asyncio.CancelledError):
            ende = "abgebrochen (gestoppt)"
        except TokenLimitErreicht:
            ende = "abgebrochen (Tokenlimit)"
        except Exception as e:
            dprint(dl.AGENT, f"❌ Agent abgestürzt: {e}")
            traceback.print_exc()
            dprint(dl.AGENT, traceback.format_exc())      # auch ins Debug-Log (stderr sieht man nicht immer)
            ende = f"abgebrochen (Fehler: {e})"
            await self._melde({"type": "agent_event", "kind": "error", "tool": "-", "args": {},
                               "result": f"Interner Fehler im Agenten: {e}", "round": self.runde, "step": self.schritt})
        await self._beende(ende)

    def _erzeuge_llm(self):
        """Wählt das Modell. Import erst hier, damit das Google-SDK nur bei Bedarf geladen wird."""
        if self.spieler == "fake":
            from agent_player.fake_llm import FakeAgentLLM, DEMO_ANTWORTEN
            return FakeAgentLLM(DEMO_ANTWORTEN)
        from agent_player.llm import GeminiAgentLLM
        return GeminiAgentLLM(config.AGENT_MODELL)

    async def _beende(self, ende: str) -> None:
        """Zusammenfassung an Browser und Spur; letzter Status."""
        ctx = self.ctx
        if ctx is not None:
            self.runde, self.schritt = ctx.runde, ctx.schritt
        self.ende = "finished"
        zusammenfassung = {
            "type": "agent_summary", "ergebnis": ende, "runden": ctx.runde if ctx else 0,
            "aufrufe": ctx.schritt if ctx else 0, "modellaufrufe": ctx.modellaufrufe if ctx else 0,
            "tokens": ctx.tokens_gesamt if ctx else 0, "orte": sorted(ctx.orte) if ctx else [],
            "letzter_ort": self.session["state"].get("player", {}).get("location", "?"),
            "trace_datei": self.spur.pfad if self.spur else None,
        }
        await self._melde(zusammenfassung)
        await self._sende_status()

    async def _melde(self, nachricht: dict) -> None:
        """Nachricht an den Browser UND (außer Statusmeldungen) in die JSONL-Spur."""
        await self._sende(nachricht)
        if self.spur is not None and nachricht.get("type") != "agent_status":
            self.spur.schreibe(nachricht)

    # --- Ein Zug durch den normalen Rundenpfad --------------------------------
    async def fuehre_zug_aus(self, function_call: dict) -> list[dict]:
        """Führt einen Zug aus und gibt alle Nachrichten zurück, die der Browser dabei bekam.

        session["tap"] sammelt (siehe CommandEngineMixin._send) eine Kopie jeder gesendeten
        command_result-/npc_actions-Nachricht: genau das, was auch ein Mensch zu sehen bekäme."""
        self.session["tap"] = []
        self.session["cmd_q"].append(function_call)
        self.in_zug = True
        try:
            await self.server.handle_command(self.ws, {"command": ""})
            return self.session["tap"]
        finally:
            self.session["tap"] = None
            self.in_zug = False

    async def _zeige_zug(self, verb: str, args: dict, warum: str, ereignisse: list[dict]) -> None:
        a = ereignisse_auswerten(ereignisse)
        text = a.text + ("\n" if a.text and a.npc_meldungen else "") + "\n".join(f"⚠ {m}" for m in a.npc_meldungen)
        fehler = a.fehler
        await self._sende({"type": "agent_event", "kind": "error" if fehler else "move", "tool": verb,
                           "args": args, "warum": warum, "result": text,
                           "round": self.runde, "step": self.schritt})
        dprint(dl.AGENT, f"Runde {self.runde}: {verb} {args} -> {text[:80]!r}")

    # --- Senden ----------------------------------------------------------------
    async def _sende_status(self) -> None:
        zustand = self.steuerung.zustand
        if self.ende:
            zustand = self.ende
        await self._sende({"type": "agent_status", "state": zustand, "round": self.runde,
                           "step": self.schritt, "tempo_ms": self.steuerung.tempo_ms})

    async def _sende(self, nachricht: dict) -> None:
        try:
            await self.ws.send(json.dumps(nachricht))
        except Exception as e:
            dprint(dl.AGENT, f"⚠️  Senden an Browser fehlgeschlagen: {e}")

