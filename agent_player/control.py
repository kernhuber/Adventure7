"""Steuerung des Agenten: Start, Pause, Einzelschritt, Runde, Stopp, Tempo.

LERNPUNKT: Der Agent läuft als eigener asyncio-Task neben der WebSocket-Empfangsschleife.
Die Schleife ruft vor JEDEM Schritt `await steuerung.vor_schritt()`; erst wenn die
Steuerung "weiter" sagt, geht es los. So kann man pausieren und einzeln durchschalten,
ohne dass der Server blockiert (kein Thread, kein Lock – nur `await`).
"""
import asyncio


class AgentGestoppt(Exception):
    """Wird in `vor_schritt` geworfen, wenn der Zuschauer 'Stopp' gedrückt hat."""


class AgentSteuerung:
    def __init__(self, tempo_ms: int = 800):
        self.laufend = False              # True = Schritte laufen ohne weiteres Klicken
        self.freie_schritte = 0           # >0 = so viele Einzelschritte sind noch erlaubt
        self.runde_frei = False           # True = bis zum nächsten Zug durchlaufen
        self.gestoppt = False
        self.tempo_ms = tempo_ms
        self._wecker = asyncio.Event()    # weckt vor_schritt, wenn sich etwas geändert hat
        self.wartet = False               # True, solange vor_schritt auf eine Freigabe wartet (Anzeige im Panel)
        self.bei_warten = None            # optional: async Funktion, die den Status an den Browser schickt

    # --- Kommandos aus dem Browser --------------------------------------------
    def kommando(self, aktion: str, tempo_ms: int | None = None) -> None:
        """Setzt eine Aktion des Zuschauers um ('start', 'pause', 'resume', 'step', 'round', 'stop')."""
        if tempo_ms is not None:
            self.tempo_ms = max(0, int(tempo_ms))
        if aktion in ("start", "resume"):
            self.laufend = True
        elif aktion == "pause":
            self.laufend = False
            self.runde_frei = False
        elif aktion == "step":
            self.laufend = False
            self.freie_schritte += 1
        elif aktion == "round":
            self.laufend = False
            self.runde_frei = True
        elif aktion == "stop":
            self.gestoppt = True
        self._wecker.set()

    # --- Aufrufe aus der Agentenschleife --------------------------------------
    async def vor_schritt(self) -> None:
        """Wartet, bis der nächste Schritt erlaubt ist (und hält dann das eingestellte Tempo ein)."""
        while True:
            if self.gestoppt:
                raise AgentGestoppt()
            if self.laufend or self.runde_frei:
                break
            if self.freie_schritte > 0:
                self.freie_schritte -= 1
                break
            self._wecker.clear()
            self.wartet = True
            if self.bei_warten is not None:
                await self.bei_warten()   # Panel zeigt "wartet auf Freigabe"
            await self._wecker.wait()
            self.wartet = False
        if self.laufend and self.tempo_ms:
            await asyncio.sleep(self.tempo_ms / 1000)

    def zug_beendet(self) -> None:
        """Nach einem Spielzug endet ein 'Runde'-Durchlauf; danach wird pausiert."""
        self.runde_frei = False

    @property
    def zustand(self) -> str:
        if self.gestoppt:
            return "stopped"
        if self.wartet:
            return "waiting"
        if self.laufend or self.runde_frei:
            return "running"
        return "paused"
