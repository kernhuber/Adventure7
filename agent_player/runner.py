"""Die ÄUSSERE Schleife des Agenten: Zug für Zug durch den normalen Rundenpfad.

LERNPUNKT (zwei verschachtelte Schleifen): Das Spiel kennt Runden – das ist die äußere
Schleife, hier in `_play_agent`. Pro Runde läuft darin die innere Denkschleife des Agenten
(`loop.play_round`). Der Skript-Spieler (`_play_script`) ersetzt das Denken durch eine feste Liste.

Wer spielt, bestimmt die URL: ?mode=agent (Gemini), &player=fake (Fake-Modell, kostenlos),
&player=skript (feste Befehlsliste aus Meilenstein 1).

LERNPUNKT (kein zweiter Regelpfad): `run_move` legt den Zug in dieselbe Befehlswarteschlange
wie ein geparster Menschenbefehl und ruft `handle_command` auf. Durst, Rundenwechsel, NPC-Züge
und Game Over laufen daher exakt wie bei einem Menschen.
"""
import asyncio
import json
import time
import traceback

from utils import dprint, dl
from agent_player import config, context, experience, savestate
from agent_player.context import AgentContext, TokenLimitReached
from agent_player.control import AgentController, AgentStopped
from agent_player.loop import play_round
from agent_player.observation import evaluate_events
from agent_player.script_player import SCRIPT
from agent_player.trace import Trace


class AgentRunner:
    def __init__(self, server, websocket, session: dict, session_id: str, player: str = "llm", agent_state: dict | None = None,
                 tip: str = ""):
        self.server = server          # WebAdventureServer (hat handle_command)
        self.ws = websocket
        self.session = session
        self.session_id = session_id
        self.player = player         # "llm" | "fake" | "skript"
        self.ctx: AgentContext | None = None
        self.agent_state = agent_state   # aus einem geladenen Spielstand (bereits geprüft), sonst None
        self.in_move = False                  # True, solange ein Zug in der Engine läuft (dann nicht speichern)
        self._tip_text = tip      # Hinweis (z. B. &tipp= aus der URL), der vor dem Start des Agenten kam
        self.trace: Trace | None = None
        self.controller = AgentController(config.START_TEMPO_MS)
        self.controller.on_wait = self._send_status
        self.task: asyncio.Task | None = None
        self.round_number = 0
        self.step = 0
        self.outcome: str | None = None   # None | "finished" | "game_over"

    # --- Kommandos aus dem Browser -------------------------------------------
    async def handle_control_command(self, data: dict) -> None:
        action = data.get("action", "")
        if action == "save":                       # Zuschauer speichert Spiel + Agentenzustand
            await self._send({"type": "info", "message": "💾 " + self.save(str(data.get("name", "")))})
            return
        if action == "slots":                      # Liste der Spielstände fürs Lade-Fenster des Panels
            await self._send({"type": "agent_slots", "slots": savestate.list_saves()})
            return
        if action == "hint":                       # Testhilfe: Zuschauer gibt dem Agenten einen Hinweis
            await self._tip(str(data.get("text", "")).strip())
            return
        self.controller.command(action, data.get("delay_ms"))
        if action in ("start", "resume", "step", "round") and self.task is None:
            self.task = asyncio.create_task(self._play_script() if self.player == "skript" else self._play_agent())
        await self._send_status()

    async def _tip(self, text: str) -> None:
        """Merkt einen Zuschauer-Hinweis für die NÄCHSTE Runde vor (protokolliert, damit man es in der Spur sieht)."""
        if not text:
            return
        self._tip_text = text
        if self.ctx is not None:
            context.remember_tip(self.ctx, text)
            await self._report({"type": "agent_notebook", "text": self.ctx.notebook.read()})
        await self._report({"type": "agent_event", "kind": "text", "tool": "Zuschauer-Hinweis", "args": {},
                           "result": f"{text}\n(gilt ab der nächsten Runde)", "round": self.round_number, "step": self.step})

    def save(self, name: str, note: str = "") -> str:
        """Speichert Spielstand + Agentenzustand. Rückgabe: Meldung (Erfolg oder Grund, warum es nicht ging)."""
        if self.in_move:
            return "Gerade läuft ein Zug – bitte gleich noch einmal versuchen."
        name = savestate.safe_name(name) or time.strftime("agent_%Y%m%d_%H%M%S")
        try:
            savestate.save_game(self.session["game"], self.ctx, name, note)
        except Exception as e:
            dprint(dl.AGENT, f"❌ Speichern fehlgeschlagen: {e}")
            return f"Speichern fehlgeschlagen: {e}"
        suffix = "" if self.ctx is not None else " (ohne Agentenzustand – der Agent hat noch nicht gestartet)"
        return f"Spielstand '{name}' gespeichert{suffix}."

    def _save_for_agent(self, note: str) -> str:
        """Die freie Aktion 'spielstand_speichern' des Agenten: automatischer Name, seine Notiz kommt mit."""
        return self.save(f"agent_runde{self.ctx.round_number}_{time.strftime('%H%M%S')}", note)

    def close(self) -> None:
        """Beim Trennen des Browsers aufräumen."""
        self.controller.command("stop")
        if self.task is not None:
            self.task.cancel()

    # --- Äußere Schleife ------------------------------------------------------
    async def _play_script(self) -> None:
        game = self.session["game"]
        try:
            for step in SCRIPT:
                await self.controller.before_step()
                self.round_number = game.time
                self.step += 1
                events = await self.run_move(step.as_function_call())
                await self._show_move(step.verb, step.args, step.why, events)
                self.controller.move_finished()
                if game.game_over:
                    self.outcome = "game_over"
                    break
            else:
                self.outcome = "finished"
        except (AgentStopped, asyncio.CancelledError):
            pass
        except Exception as e:
            dprint(dl.AGENT, f"❌ Agent abgestürzt: {e}")
            traceback.print_exc()
            dprint(dl.AGENT, traceback.format_exc())      # auch ins Debug-Log (stderr sieht man nicht immer)
            await self._send({"type": "agent_event", "kind": "error", "tool": "-", "args": {},
                               "result": f"Interner Fehler im Agenten: {e}", "round": self.round_number, "step": self.step})
        await self._send_status()

    async def _play_agent(self) -> None:
        """Die äußere Schleife mit echtem Agenten: Runde für Runde, bis das Spiel oder ein Limit endet."""
        game = self.session["game"]
        self.trace = Trace()
        outcome = "abgebrochen"
        try:
            ctx = AgentContext(self._create_llm(), self.controller, lambda: self.session["state"],
                               self.run_move, self._report)
            self.ctx = ctx
            self.controller.on_wait = ctx.send_status      # Panel zeigt, wenn der Agent auf eine Freigabe wartet
            ctx.save = self._save_for_agent
            if config.EXPERIENCE_ACTIVE and self.player == "llm":      # Wissen aus früheren Spielen
                ctx.lessons = experience.read()
                if ctx.lessons:
                    await self._report({"type": "agent_event", "kind": "exp", "tool": "Experience.md", "args": {},
                                       "result": f"Erfahrungen aus früheren Spielen geladen ({len(ctx.lessons)} Zeichen).",
                                       "round": 0, "step": 0})
            if self._tip_text:
                await self._report({"type": "agent_event", "kind": "text", "tool": "Zuschauer-Hinweis", "args": {},
                                   "result": f"{self._tip_text}\n(gilt ab der ersten Runde)", "round": 0, "step": 0})
            if self.agent_state:                            # aus einem Spielstand: Gedächtnis zurückspielen
                savestate.import_state(ctx, self.agent_state)
                await self._report({"type": "agent_notebook", "text": ctx.notebook.read()})
            if self._tip_text:
                context.remember_tip(ctx, self._tip_text)
                await self._report({"type": "agent_notebook", "text": ctx.notebook.read()})
            # Gespräche (Zombie/Hund) führt der Agent selbst: AgentDialogs braucht dafür den Kontext.
            if self.session.get("web_dialogs") is not None:
                self.session["web_dialogs"].ctx = ctx
            for _ in range(config.MAX_ROUNDS):
                await play_round(ctx)                         # innere Schleife (loop.py)
                self.controller.move_finished()
                if game.game_over:
                    outcome = "gewonnen" if game.game_won else "verloren"
                    break
            else:
                outcome = "abgebrochen (Rundenlimit)"
        except (AgentStopped, asyncio.CancelledError):
            outcome = "abgebrochen (gestoppt)"
        except TokenLimitReached:
            outcome = "abgebrochen (Tokenlimit)"
        except Exception as e:
            dprint(dl.AGENT, f"❌ Agent abgestürzt: {e}")
            traceback.print_exc()
            dprint(dl.AGENT, traceback.format_exc())      # auch ins Debug-Log (stderr sieht man nicht immer)
            outcome = f"abgebrochen (Fehler: {e})"
            await self._report({"type": "agent_event", "kind": "error", "tool": "-", "args": {},
                               "result": f"Interner Fehler im Agenten: {e}", "round": self.round_number, "step": self.step})
        # Nach einem echten Spielende (oder Rundenlimit): Resümee in Experience.md, wie ein Mensch sich etwas merkt.
        if (self.ctx is not None and config.EXPERIENCE_ACTIVE and self.player == "llm"
                and outcome in ("gewonnen", "verloren", "abgebrochen (Rundenlimit)")):
            try:
                await experience.write_summary(self.ctx, outcome)
            except Exception as e:
                dprint(dl.AGENT, f"❌ Resümee fehlgeschlagen: {e}")
                dprint(dl.AGENT, traceback.format_exc())
        await self._finish(outcome)

    def _create_llm(self):
        """Wählt das Modell. Import erst hier, damit das Google-SDK nur bei Bedarf geladen wird."""
        if self.player == "fake":
            from agent_player.fake_llm import FakeAgentLLM, DEMO_REPLIES
            return FakeAgentLLM(DEMO_REPLIES)
        from agent_player.llm import GeminiAgentLLM
        return GeminiAgentLLM(config.AGENT_MODEL)

    async def _finish(self, outcome: str) -> None:
        """Zusammenfassung an Browser und Spur; letzter Status."""
        ctx = self.ctx
        if ctx is not None:
            self.round_number, self.step = ctx.round_number, ctx.step
        self.outcome = "finished"
        summary = {
            "type": "agent_summary", "ergebnis": outcome, "runden": ctx.round_number if ctx else 0,
            "aufrufe": ctx.step if ctx else 0, "modellaufrufe": ctx.model_calls if ctx else 0,
            "tokens": ctx.tokens_total if ctx else 0, "orte": sorted(ctx.places) if ctx else [],
            "letzter_ort": self.session["state"].get("player", {}).get("location", "?"),
            "trace_datei": self.trace.file_path if self.trace else None,
        }
        await self._report(summary)
        await self._send_status()

    async def _report(self, message: dict) -> None:
        """Nachricht an den Browser UND (außer Statusmeldungen) in die JSONL-Spur."""
        await self._send(message)
        if self.trace is not None and message.get("type") != "agent_status":
            self.trace.write(message)

    # --- Ein Zug durch den normalen Rundenpfad --------------------------------
    async def run_move(self, function_call: dict) -> list[dict]:
        """Führt einen Zug aus und gibt alle Nachrichten zurück, die der Browser dabei bekam.

        session["tap"] sammelt (siehe CommandEngineMixin._send) eine Kopie jeder gesendeten
        command_result-/npc_actions-Nachricht: genau das, was auch ein Mensch zu sehen bekäme."""
        self.session["tap"] = []
        self.session["cmd_q"].append(function_call)
        self.in_move = True
        try:
            await self.server.handle_command(self.ws, {"command": ""})
            return self.session["tap"]
        finally:
            self.session["tap"] = None
            self.in_move = False

    async def _show_move(self, verb: str, args: dict, why: str, events: list[dict]) -> None:
        a = evaluate_events(events)
        text = a.text + ("\n" if a.text and a.npc_messages else "") + "\n".join(f"⚠ {m}" for m in a.npc_messages)
        error = a.error
        await self._send({"type": "agent_event", "kind": "error" if error else "move", "tool": verb,
                           "args": args, "warum": why, "result": text,
                           "round": self.round_number, "step": self.step})
        dprint(dl.AGENT, f"Runde {self.round_number}: {verb} {args} -> {text[:80]!r}")

    # --- Senden ----------------------------------------------------------------
    async def _send_status(self) -> None:
        state = self.controller.state
        if self.outcome:
            state = self.outcome
        await self._send({"type": "agent_status", "state": state, "round": self.round_number,
                           "step": self.step, "tempo_ms": self.controller.tempo_ms})

    async def _send(self, message: dict) -> None:
        try:
            await self.ws.send(json.dumps(message))
        except Exception as e:
            dprint(dl.AGENT, f"⚠️  Senden an Browser fehlgeschlagen: {e}")

