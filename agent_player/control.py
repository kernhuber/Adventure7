"""Steuerung des Agenten: Start, Pause, Einzelschritt, Runde, Stopp, Tempo.

LERNPUNKT: Der Agent läuft als eigener asyncio-Task neben der WebSocket-Empfangsschleife.
Die Schleife ruft vor JEDEM Schritt `await steuerung.before_step()`; erst wenn die
Steuerung "weiter" sagt, geht es los. So kann man pausieren und einzeln durchschalten,
ohne dass der Server blockiert (kein Thread, kein Lock – nur `await`).
"""
import asyncio


class AgentStopped(Exception):
    """Wird in `before_step` geworfen, wenn der Zuschauer 'Stopp' gedrückt hat."""


class AgentController:
    def __init__(self, tempo_ms: int = 800):
        self.running = False              # True = Schritte laufen ohne weiteres Klicken
        self.free_steps = 0           # >0 = so viele Einzelschritte sind noch erlaubt
        self.round_free = False           # True = bis zum nächsten Zug durchlaufen
        self.stopped = False
        self.tempo_ms = tempo_ms
        self._wakeup = asyncio.Event()    # weckt before_step, wenn sich etwas geändert hat
        self.waiting = False               # True, solange before_step auf eine Freigabe wartet (Anzeige im Panel)
        self.on_wait = None            # optional: async Funktion, die den Status an den Browser schickt

    # --- Kommandos aus dem Browser --------------------------------------------
    def command(self, action: str, tempo_ms: int | None = None) -> None:
        """Setzt eine Aktion des Zuschauers um ('start', 'pause', 'resume', 'step', 'round', 'stop')."""
        if tempo_ms is not None:
            self.tempo_ms = max(0, int(tempo_ms))
        if action in ("start", "resume"):
            self.running = True
        elif action == "pause":
            self.running = False
            self.round_free = False
        elif action == "step":
            self.running = False
            self.free_steps += 1
        elif action == "round":
            self.running = False
            self.round_free = True
        elif action == "stop":
            self.stopped = True
        self._wakeup.set()

    # --- Aufrufe aus der Agentenschleife --------------------------------------
    async def before_step(self) -> None:
        """Wartet, bis der nächste Schritt erlaubt ist (und hält dann das eingestellte Tempo ein)."""
        while True:
            if self.stopped:
                raise AgentStopped()
            if self.running or self.round_free:
                break
            if self.free_steps > 0:
                self.free_steps -= 1
                break
            self._wakeup.clear()
            self.waiting = True
            if self.on_wait is not None:
                await self.on_wait()   # Panel zeigt "wartet auf Freigabe"
            await self._wakeup.wait()
            self.waiting = False
        if self.running and self.tempo_ms:
            await asyncio.sleep(self.tempo_ms / 1000)

    def move_finished(self) -> None:
        """Nach einem Spielzug endet ein 'Runde'-Durchlauf; danach wird pausiert."""
        self.round_free = False

    @property
    def state(self) -> str:
        if self.stopped:
            return "stopped"
        if self.waiting:
            return "waiting"
        if self.running or self.round_free:
            return "running"
        return "paused"
