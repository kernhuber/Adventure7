"""Kontext des Agenten: der Prompt je Runde und der Zustand, den die Schleife braucht.

LERNPUNKT (bewusste Entscheidung gegen einen endlos wachsenden Chat):
Jede Runde baut den Prompt FRISCH auf: System-Prompt + aktuelle Beobachtung + Notizbuch +
kurzer Verlauf der letzten Runden. Innerhalb einer Runde wächst der Kontext mit den
Werkzeugergebnissen; nach dem Zug wird er verworfen. Warum?
  - Kosten: ein Chat über 100 Runden würde bei jedem Aufruf ALLES erneut mitschicken.
  - Fokus: das Modell soll auf die aktuelle Lage schauen, nicht in alten Szenen versinken.
  - Es zwingt den Agenten, Wichtiges ins Notizbuch zu schreiben – wie der Zombie (`notes`).
Preis: Was nicht im Notizbuch oder im kurzen Verlauf steht, ist vergessen.
"""
from dataclasses import dataclass, field
from typing import Awaitable, Callable

from utils import dprint, dl
from agent_player import config
from agent_player.llm import AgentLLM, Antwort, Nachricht
from agent_player.notebook import Notizbuch
from agent_player.observation import beobachtung_als_text
from agent_player.control import AgentSteuerung
from agent_player.tools import Werkzeug


class TokenLimitErreicht(Exception):
    """Das konfigurierte Tokenlimit für das ganze Spiel ist erreicht."""


# Was der Agent über sein Ziel weiß – nur das, was auch ein Spieler zu Beginn liest. Kein Lösungswissen!
SYSTEM_PROMPT = """Du spielst ein deutschsprachiges Text-Adventure. Deine Spielfigur heißt Agent.

Die Ausgangslage, wie sie jeder Spieler liest: Du radelst als Bote mit deinem Fahrrad unter sengender Sonne
durch eine endlose Wüste. Bei dir hast du einen Umschlag, den du an ein Ziel bringen musst. Erreicht der Umschlag
das Ziel nicht, geht die Welt unter. Plötzlich reißt deine Fahrradkette – das Fahrrad funktioniert ohne sie nicht
mehr. Du bist an einem Ort gestrandet, an dem es Rettung geben könnte.

So funktioniert das Spiel für dich:
- Du hast zwei Arten von Werkzeugen. FREIE AKTIONEN (Lage lesen, Inventar, Notizbuch, Spielstand speichern) kosten keine Spielzeit.
  ZÜGE (gehen, nehmen, anwenden, untersuchen, …) kosten genau eine Spielrunde; danach handeln andere Figuren,
  und dein Durst nimmt zu. Ein Zug beendet deine Runde.
- Jede Runde: bei Bedarf freie Aktionen, dann genau EINEN Zug. Jeder Zug braucht ein 'warum' (ein Satz).
- Verwende Namen genau so, wie sie in der Lage stehen (Objekte hier, Begehbare Wege, Inventar).
- Ein Fehler (z. B. ein unbekannter Name) kostet keine Runde – du siehst die Fehlermeldung und versuchst es neu.
- Wenn dein Durst-Zähler 0 erreicht, verdurstest du, und das Spiel ist verloren.
- WICHTIG: In jeder Runde siehst du nur die aktuelle Lage, dein Notizbuch und eine kurze Liste deiner letzten Züge.
  Alles andere vergisst du. Schreibe deshalb Wichtiges (Zahlen, Codes, Hinweise, Ideen, was du schon probiert hast,
  wo etwas liegt) ins Notizbuch.
- Handle selbstständig; du kannst niemanden um Hilfe bitten. Schreibe kurz, was du denkst, und rufe dann ein Werkzeug auf.
"""


@dataclass
class RundenEintrag:
    """Eine Zeile im kurzen Verlauf."""
    runde: int
    zug: str
    warum: str
    ergebnis: str

    def als_text(self) -> str:
        kurz = " ".join(self.ergebnis.split())[:140]
        return f"Runde {self.runde}: {self.zug} – {self.warum} → {kurz or '(kein Ergebnistext)'}"


@dataclass
class AgentKontext:
    """Alles, was die Schleife über das Spiel und sich selbst weiß. Anbindung nach außen nur über
    drei Funktionen – so läuft dieselbe Schleife mit der echten Engine und mit einer Fake-Welt."""
    llm: AgentLLM
    steuerung: AgentSteuerung
    hole_ansicht: Callable[[], dict]                         # liefert, was der Browser anzeigt (session["state"])
    fuehre_zug_aus: Callable[[dict], Awaitable[list[dict]]]  # schickt einen Zug durch den Rundenpfad
    melde: Callable[[dict], Awaitable[None]]                 # Nachricht an Browser + Spur
    notizbuch: Notizbuch = field(default_factory=Notizbuch)
    verlauf: list[RundenEintrag] = field(default_factory=list)
    erinnerung: str = ""                # Notiz aus dem geladenen Spielstand (einmal prominent im Prompt)
    speichere: Callable[[str], str] | None = None   # speichert Spielstand + Agentenzustand; Rückgabe: Meldung
    hinweis: str = ""                   # Zuschauer-Hinweis (Testhilfe), wird einmal in den Prompt übernommen
    letztes_ergebnis: str = ""
    npc_meldungen: list[str] = field(default_factory=list)
    runde: int = 0
    schritt: int = 0
    aufrufe_runde: int = 0
    tokens_runde: int = 0
    tokens_gesamt: int = 0
    modellaufrufe: int = 0
    orte: set = field(default_factory=set)

    def neue_runde(self) -> None:
        ansicht = self.hole_ansicht()
        self.runde = ansicht.get("round", self.runde)
        self.orte.add(ansicht.get("player", {}).get("location", "?"))
        self.aufrufe_runde = 0
        self.tokens_runde = 0

    async def frage_modell(self, nachrichten: list[Nachricht], werkzeuge: list[Werkzeug]) -> Antwort:
        """Fragt das Modell, verbucht Tokens und zeigt den Freitext des Modells (nur echten Text!)."""
        dprint(dl.AGENT, f"Modell wird gefragt ({len(nachrichten)} Nachrichten, {len(werkzeuge)} Werkzeuge) ...")
        antwort = await self.llm.frage(SYSTEM_PROMPT, nachrichten, werkzeuge)
        dprint(dl.AGENT, f"Modell antwortet: {len(antwort.aufrufe)} Aufruf(e) {[a.name for a in antwort.aufrufe]}, "
                         f"{antwort.tokens_ein + antwort.tokens_aus} Tokens, Text: {antwort.text[:80]!r}")
        verbrauch = antwort.tokens_ein + antwort.tokens_aus
        self.tokens_runde += verbrauch
        self.tokens_gesamt += verbrauch
        self.modellaufrufe += 1
        if antwort.text:
            await self.melde({"type": "agent_event", "kind": "text", "tool": "Modell", "args": {},
                              "result": antwort.text, "round": self.runde, "step": self.schritt})
        await self.sende_status()
        if config.MAX_TOKENS_GESAMT and self.tokens_gesamt >= config.MAX_TOKENS_GESAMT:
            raise TokenLimitErreicht()
        return antwort

    async def sende_status(self) -> None:
        await self.melde({"type": "agent_status", "state": self.steuerung.zustand, "round": self.runde,
                          "step": self.schritt, "tempo_ms": self.steuerung.tempo_ms,
                          "calls_round": self.aufrufe_runde, "calls_limit": config.MAX_AUFRUFE_PRO_RUNDE,
                          "tokens_round": self.tokens_runde, "tokens_total": self.tokens_gesamt,
                          "model_calls": self.modellaufrufe, "model": self.llm.modell})


def runden_nachricht(ctx: AgentKontext) -> Nachricht:
    """Baut die erste Nachricht einer Runde: Lage + Notizbuch + kurzer Verlauf (siehe Modul-Doku)."""
    lage = beobachtung_als_text(ctx.hole_ansicht(), ctx.letztes_ergebnis, ctx.npc_meldungen)
    verlauf = [e.als_text() for e in ctx.verlauf[-config.VERLAUF_RUNDEN:]]
    text = (f"=== AKTUELLE LAGE ===\n{lage}\n\n"
            f"=== DEIN NOTIZBUCH ===\n{ctx.notizbuch.lesen()}\n\n"
            f"=== DEINE LETZTEN ZÜGE ===\n" + ("\n".join(verlauf) if verlauf else "(noch keine)") + "\n\n")
    if ctx.erinnerung:
        text += f"=== ERINNERUNG AUS DEM SPIELSTAND (eine Notiz von dir selbst) ===\n{ctx.erinnerung}\n\n"
        ctx.erinnerung = ""
    if ctx.hinweis:
        # LERNPUNKT: ein Hinweis von außen ist ein bewusster Eingriff ("human in the loop"): Er steht als
        # eigener, klar gekennzeichneter Abschnitt im Prompt und wird nur EINMAL verwendet.
        text += f"=== HINWEIS EINES ZUSCHAUERS (du darfst ihm folgen) ===\n{ctx.hinweis}\n\n"
        ctx.hinweis = ""
    text += "Was tust du in dieser Runde?"
    return Nachricht.vom_nutzer(text)


def chat_nachricht(ctx: AgentKontext, partner: str, chat: list[dict]) -> Nachricht:
    """Erste Nachricht eines Gesprächs: Lage + Notizbuch + bisheriger Gesprächsverlauf.

    `chat` hat dasselbe Format wie im Browser-Modal: {"zombiemessage": ...} = der Partner (auch beim Hund),
    {"playermessage": ...} = der Agent."""
    lage = beobachtung_als_text(ctx.hole_ansicht(), ctx.letztes_ergebnis, ctx.npc_meldungen)
    verlauf = []
    for zeile in chat:
        for rolle, text in zeile.items():
            verlauf.append(f"{partner if rolle == 'zombiemessage' else 'Du'}: {text}")
    text = (f"=== AKTUELLE LAGE ===\n{lage}\n\n"
            f"=== DEIN NOTIZBUCH ===\n{ctx.notizbuch.lesen()}\n\n"
            f"=== GESPRÄCH MIT {partner.upper()} BISHER ===\n" + ("\n".join(verlauf) if verlauf else "(noch nichts gesagt)") + "\n\n"
            f"Du führst gerade ein Gespräch mit {partner}. Jetzt stehen dir nur 'sage' und 'gespraech_beenden' zur Verfügung "
            f"(keine Spielzüge). Höchstens {config.MAX_CHAT_WORTWECHSEL} Wortwechsel. Beende das Gespräch, wenn nichts mehr zu "
            "besprechen ist, und fasse dabei zusammen, was du dir merken willst.")
    return Nachricht.vom_nutzer(text)


def pin_nachricht(ctx: AgentKontext) -> Nachricht:
    """Erste Nachricht, wenn das PIN-Pad offen ist: Lage + Notizbuch + die Regeln des Pads (wie beim Menschen)."""
    lage = beobachtung_als_text(ctx.hole_ansicht(), ctx.letztes_ergebnis, ctx.npc_meldungen)
    text = (f"=== AKTUELLE LAGE ===\n{lage}\n\n"
            f"=== DEIN NOTIZBUCH ===\n{ctx.notizbuch.lesen()}\n\n"
            "Du hast die EC-Karte in den Geldautomaten gesteckt. Auf dem Bildschirm steht: 'Bitte Geheimzahl eingeben.' "
            "Die Geheimzahl hat vier Ziffern. Das Pad lässt sich nur durch Eingabe von vier Ziffern verlassen. "
            "Ist die Zahl falsch, musst du die Karte erneut einstecken (das kostet eine weitere Spielrunde). "
            "Du kannst dein Notizbuch lesen und die Zahl mit 'pin_eingeben' eintippen.")
    return Nachricht.vom_nutzer(text)
