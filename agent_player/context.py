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
            return config.SYSTEM_PROMPT
        return config.SYSTEM_PROMPT + config.PROMPT_LESSONS.format(lessons=self.lessons)

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
    """Baut die erste Nachricht einer Runde: Lage + Notizbuch + kurzer Verlauf (siehe Modul-Doku).
    Die Texte stehen in config.py (PROMPT_ROUND, ...)."""
    situation = observation_as_text(ctx.get_view(), ctx.last_result, ctx.npc_messages)
    history = [e.as_text() for e in ctx.history[-config.HISTORY_ROUNDS:]]
    text = config.PROMPT_ROUND.format(situation=situation, notebook=ctx.notebook.read(),
                                      history="\n".join(history) if history else config.PROMPT_NO_HISTORY)
    if ctx.save_memo:
        text += config.PROMPT_ROUND_MEMO.format(memo=ctx.save_memo)
        ctx.save_memo = ""
    if ctx.tip:
        # LERNPUNKT: ein Hinweis von außen ist ein bewusster Eingriff ("human in the loop"): Er steht als
        # eigener, klar gekennzeichneter Abschnitt im Prompt und wird nur EINMAL verwendet.
        text += config.PROMPT_ROUND_TIP.format(tip=ctx.tip)
        ctx.tip = ""
    text += config.PROMPT_ROUND_QUESTION
    return Message.from_user(text)


def chat_message(ctx: AgentContext, partner: str, chat: list[dict]) -> Message:
    """Erste Nachricht eines Gesprächs: Lage + Notizbuch + bisheriger Gesprächsverlauf (Text: config.PROMPT_CHAT).

    `chat` hat dasselbe Format wie im Browser-Modal: {"zombiemessage": ...} = der Partner (auch beim Hund),
    {"playermessage": ...} = der Agent."""
    situation = observation_as_text(ctx.get_view(), ctx.last_result, ctx.npc_messages)
    conversation = []
    for line in chat:
        for role, text in line.items():
            conversation.append(f"{partner if role == 'zombiemessage' else config.PROMPT_CHAT_YOU}: {text}")
    text = config.PROMPT_CHAT.format(
        situation=situation, notebook=ctx.notebook.read(), partner=partner, partner_upper=partner.upper(),
        conversation="\n".join(conversation) if conversation else config.PROMPT_CHAT_NOTHING_SAID,
        max_exchanges=config.MAX_CHAT_EXCHANGES)
    return Message.from_user(text)


def pin_message(ctx: AgentContext) -> Message:
    """Erste Nachricht, wenn das PIN-Pad offen ist: Lage + Notizbuch + die Regeln des Pads (Text: config.PROMPT_PIN)."""
    situation = observation_as_text(ctx.get_view(), ctx.last_result, ctx.npc_messages)
    return Message.from_user(config.PROMPT_PIN.format(situation=situation, notebook=ctx.notebook.read()))
