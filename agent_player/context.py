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
from agent_player.llm import AgentLLM, ModelReply, Message
from agent_player.notebook import Notebook
from agent_player.observation import observation_as_text
from agent_player.control import AgentController
from agent_player.tools import ToolSpec


class TokenLimitReached(Exception):
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
- Bevor du etwas Riskantes oder Unumkehrbares tust (z. B. etwas zünden, zerstören oder hergeben), speichere mit
  'spielstand_speichern' und schreibe dir in der 'notiz' eine Warnung für dein späteres Ich.
- Handle selbstständig; du kannst niemanden um Hilfe bitten. Schreibe kurz, was du denkst, und rufe dann ein Werkzeug auf.
"""


@dataclass
class RoundEntry:
    """Eine Zeile im kurzen Verlauf."""
    round_number: int
    move: str
    why: str
    result: str

    def as_text(self) -> str:
        short = " ".join(self.result.split())[:140]
        return f"Runde {self.round_number}: {self.move} – {self.why} → {short or '(kein Ergebnistext)'}"


@dataclass
class AgentContext:
    """Alles, was die Schleife über das Spiel und sich selbst weiß. Anbindung nach außen nur über
    drei Funktionen – so läuft dieselbe Schleife mit der echten Engine und mit einer Fake-Welt."""
    llm: AgentLLM
    controller: AgentController
    get_view: Callable[[], dict]                         # liefert, was der Browser anzeigt (session["state"])
    run_move: Callable[[dict], Awaitable[list[dict]]]  # schickt einen Zug durch den Rundenpfad
    report: Callable[[dict], Awaitable[None]]                 # Nachricht an Browser + Spur
    notebook: Notebook = field(default_factory=Notebook)
    history: list[RoundEntry] = field(default_factory=list)
    lessons: str = ""              # Inhalt von Experience.md (aus früheren Spielen), steht im System-Prompt
    save_memo: str = ""                # Notiz aus dem geladenen Spielstand (einmal prominent im Prompt)
    save: Callable[[str], str] | None = None   # speichert Spielstand + Agentenzustand; Rückgabe: Meldung
    tip: str = ""                   # Zuschauer-Hinweis (Testhilfe), wird einmal in den Prompt übernommen
    last_result: str = ""
    npc_messages: list[str] = field(default_factory=list)
    round_number: int = 0
    step: int = 0
    calls_round: int = 0
    tokens_round: int = 0
    tokens_total: int = 0
    model_calls: int = 0
    places: set = field(default_factory=set)

    def system_prompt(self) -> str:
        """System-Prompt, ggf. mit den Erfahrungen aus früheren Spielen (Experience.md)."""
        if not self.lessons.strip():
            return SYSTEM_PROMPT
        return (SYSTEM_PROMPT + "\n=== ERFAHRUNGEN AUS FRÜHEREN SPIELEN (Experience.md) ===\n"
                "Das ist dein Wissen aus früheren Partien. Nutze es, aber prüfe, ob es zur aktuellen Lage passt.\n\n"
                + self.lessons + "\n")

    def new_round(self) -> None:
        view = self.get_view()
        self.round_number = view.get("round", self.round_number)
        self.places.add(view.get("player", {}).get("location", "?"))
        self.calls_round = 0
        self.tokens_round = 0

    async def ask_model(self, messages: list[Message], tools: list[ToolSpec]) -> ModelReply:
        """Fragt das Modell, verbucht Tokens und zeigt den Freitext des Modells (nur echten Text!)."""
        dprint(dl.AGENT, f"Modell wird gefragt ({len(messages)} Nachrichten, {len(tools)} Werkzeuge) ...")
        response = await self.llm.ask(self.system_prompt(), messages, tools)
        dprint(dl.AGENT, f"Modell antwortet: {len(response.calls)} Aufruf(e) {[a.name for a in response.calls]}, "
                         f"{response.tokens_in + response.tokens_out} Tokens, Text: {response.text[:80]!r}")
        used = response.tokens_in + response.tokens_out
        self.tokens_round += used
        self.tokens_total += used
        self.model_calls += 1
        if response.text:
            await self.report({"type": "agent_event", "kind": "text", "tool": "Modell", "args": {},
                              "result": response.text, "round": self.round_number, "step": self.step})
        await self.send_status()
        if config.MAX_TOKENS_TOTAL and self.tokens_total >= config.MAX_TOKENS_TOTAL:
            raise TokenLimitReached()
        return response

    async def send_status(self) -> None:
        await self.report({"type": "agent_status", "state": self.controller.state, "round": self.round_number,
                          "step": self.step, "tempo_ms": self.controller.tempo_ms,
                          "calls_round": self.calls_round, "calls_limit": config.MAX_CALLS_PER_ROUND,
                          "tokens_round": self.tokens_round, "tokens_total": self.tokens_total,
                          "model_calls": self.model_calls, "model": self.llm.model})


def remember_tip(ctx: AgentContext, text: str) -> None:
    """Nimmt einen Tipp von außen auf: einmal prominent im Prompt UND dauerhaft im Notizbuch.

    LERNPUNKT: Was nur in EINER Runde im Prompt steht, ist in der nächsten vergessen (der Prompt wird jede Runde
    frisch gebaut). Damit ein Tipp wirkt, muss er ins Gedächtnis des Agenten – das Notizbuch. Der Eintrag
    erscheint auch in Gesprächen, denn `chat_message` zeigt das Notizbuch ebenfalls."""
    ctx.tip = text
    ctx.notebook.write(f"TIPP VON AUSSEN (Runde {ctx.round_number}, von einem Zuschauer): {text}")


def round_message(ctx: AgentContext) -> Message:
    """Baut die erste Nachricht einer Runde: Lage + Notizbuch + kurzer Verlauf (siehe Modul-Doku)."""
    situation = observation_as_text(ctx.get_view(), ctx.last_result, ctx.npc_messages)
    history = [e.as_text() for e in ctx.history[-config.HISTORY_ROUNDS:]]
    text = (f"=== AKTUELLE LAGE ===\n{situation}\n\n"
            f"=== DEIN NOTIZBUCH ===\n{ctx.notebook.read()}\n\n"
            f"=== DEINE LETZTEN ZÜGE ===\n" + ("\n".join(history) if history else "(noch keine)") + "\n\n")
    if ctx.save_memo:
        text += f"=== ERINNERUNG AUS DEM SPIELSTAND (eine Notiz von dir selbst) ===\n{ctx.save_memo}\n\n"
        ctx.save_memo = ""
    if ctx.tip:
        # LERNPUNKT: ein Hinweis von außen ist ein bewusster Eingriff ("human in the loop"): Er steht als
        # eigener, klar gekennzeichneter Abschnitt im Prompt und wird nur EINMAL verwendet.
        text += (f"=== TIPP VON EINEM ZUSCHAUER ===\n{ctx.tip}\n"
                 "Der Tipp kommt von jemandem, der das Spiel kennt. Prüfe ihn und folge ihm, solange du keinen "
                 "konkreten Gegengrund hast. Er steht jetzt auch in deinem Notizbuch.\n\n")
        ctx.tip = ""
    text += "Was tust du in dieser Runde?"
    return Message.from_user(text)


def chat_message(ctx: AgentContext, partner: str, chat: list[dict]) -> Message:
    """Erste Nachricht eines Gesprächs: Lage + Notizbuch + bisheriger Gesprächsverlauf.

    `chat` hat dasselbe Format wie im Browser-Modal: {"zombiemessage": ...} = der Partner (auch beim Hund),
    {"playermessage": ...} = der Agent."""
    situation = observation_as_text(ctx.get_view(), ctx.last_result, ctx.npc_messages)
    history = []
    for line in chat:
        for role, text in line.items():
            history.append(f"{partner if role == 'zombiemessage' else 'Du'}: {text}")
    text = (f"=== AKTUELLE LAGE ===\n{situation}\n\n"
            f"=== DEIN NOTIZBUCH ===\n{ctx.notebook.read()}\n\n"
            f"=== GESPRÄCH MIT {partner.upper()} BISHER ===\n" + ("\n".join(history) if history else "(noch nichts gesagt)") + "\n\n"
            f"Du führst gerade ein Gespräch mit {partner}. Jetzt stehen dir nur 'sage' und 'gespraech_beenden' zur Verfügung "
            f"(keine Spielzüge). Höchstens {config.MAX_CHAT_EXCHANGES} Wortwechsel. Beende das Gespräch, wenn nichts mehr zu "
            "besprechen ist, und fasse dabei zusammen, was du dir merken willst.")
    return Message.from_user(text)


def pin_message(ctx: AgentContext) -> Message:
    """Erste Nachricht, wenn das PIN-Pad offen ist: Lage + Notizbuch + die Regeln des Pads (wie beim Menschen)."""
    situation = observation_as_text(ctx.get_view(), ctx.last_result, ctx.npc_messages)
    text = (f"=== AKTUELLE LAGE ===\n{situation}\n\n"
            f"=== DEIN NOTIZBUCH ===\n{ctx.notebook.read()}\n\n"
            "Du hast die EC-Karte in den Geldautomaten gesteckt. Auf dem Bildschirm steht: 'Bitte Geheimzahl eingeben.' "
            "Die Geheimzahl hat vier Ziffern. Das Pad lässt sich nur durch Eingabe von vier Ziffern verlassen. "
            "Ist die Zahl falsch, musst du die Karte erneut einstecken (das kostet eine weitere Spielrunde). "
            "Du kannst dein Notizbuch lesen und die Zahl mit 'pin_eingeben' eintippen.")
    return Message.from_user(text)
