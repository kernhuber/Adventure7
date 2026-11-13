"""Die schmale Modell-Schnittstelle des Agenten – und ihre Gemini-Umsetzung.

LERNPUNKT: Der Rest des Pakets kennt nur `AgentLLM.frage(...)`: "hier sind System-Prompt,
Nachrichten und Werkzeuge – gib mir Text und/oder Werkzeugaufrufe zurück". Ein anderes Modell
(z. B. Claude über die Anthropic-API) wäre eine weitere Klasse in einer weiteren Datei;
loop.py, tools.py und context.py bleiben unverändert. Ebenso das Fake-Modell (fake_llm.py).
"""
import asyncio
import os
from dataclasses import dataclass, field
from typing import Any

from utils import dprint, dl
from agent_player.tools import ToolSpec


# --- neutrale Datenstrukturen (unabhängig vom Anbieter) --------------------------------
@dataclass
class ToolCall:
    """Ein Werkzeugaufruf des Modells."""
    name: str
    args: dict = field(default_factory=dict)


@dataclass
class ToolResult:
    """Das Ergebnis eines Aufrufs, das ans Modell zurückgeht."""
    name: str
    text: str


@dataclass
class ModelReply:
    """Antwort des Modells: Freitext und/oder Werkzeugaufrufe, plus Verbrauch."""
    text: str = ""
    calls: list[ToolCall] = field(default_factory=list)
    tokens_in: int = 0
    tokens_out: int = 0
    raw: Any = None                      # Original des Anbieters (Gemini braucht es für Folgeanfragen)


@dataclass
class Message:
    """Eine Nachricht im Gesprächsverlauf einer Runde: 'user' | 'model' | 'tool'."""
    role: str
    text: str = ""
    calls: list[ToolCall] = field(default_factory=list)
    results: list[ToolResult] = field(default_factory=list)
    raw: Any = None

    @staticmethod
    def from_user(text: str) -> "Nachricht":
        return Message("user", text=text)

    @staticmethod
    def from_model(response: ModelReply) -> "Nachricht":
        return Message("model", text=response.text, calls=response.calls, raw=response.raw)

    @staticmethod
    def tool_results(results: list[ToolResult]) -> "Nachricht":
        return Message("tool", results=results)


class AgentLLM:
    """Schnittstelle: Nachrichten + Werkzeuge hinein, Text und/oder Werkzeugaufrufe heraus."""
    model: str = "?"

    async def ask(self, system: str, messages: list[Message], tools: list[ToolSpec]) -> ModelReply:
        raise NotImplementedError


# --- Gemini-Umsetzung --------------------------------------------------------------------
class GeminiAgentLLM(AgentLLM):
    def __init__(self, model: str):
        # Import erst hier: so lassen sich die übrigen Module ohne Google-SDK laden/testen.
        from google import genai
        apikey = os.environ.get("GOOGLE_API_KEY")
        if not apikey:
            from dotenv import load_dotenv
            load_dotenv("apikey.env")
            apikey = os.getenv("GOOGLE_API_KEY")
        self.model = model
        self.client = genai.Client(api_key=apikey)

    async def ask(self, system: str, messages: list[Message], tools: list[ToolSpec]) -> ModelReply:
        # Der SDK-Aufruf ist synchron: in einem Thread ausführen, damit der Server (Pause-Knopf!) frei bleibt.
        return await asyncio.to_thread(self._ask_blocking, system, messages, tools)

    def _ask_blocking(self, system: str, messages: list[Message], tools: list[ToolSpec]) -> ModelReply:
        from google.genai import types
        conversation = self._build_conversation(messages, types)
        declarations = [self._declaration(w, types) for w in tools]
        config = types.GenerateContentConfig(
            system_instruction=system,
            tools=[types.Tool(function_declarations=declarations)],
            # Wir führen Werkzeuge SELBST aus (loop.py), das SDK soll das nicht automatisch tun.
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )
        response = None
        for attempt in range(3):
            try:
                response = self.client.models.generate_content(model=self.model, contents=conversation, config=config)
                break
            except Exception as e:
                transient = any(c in str(e) for c in ("503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED", "504", "DEADLINE"))
                if transient and attempt < 2:
                    dprint(dl.AGENT, f"Gemini vorübergehend nicht erreichbar ({str(e)[:60]}), neuer Versuch")
                    import time
                    time.sleep(2 ** attempt)
                    continue
                raise
        return self._read_reply(response)

    @staticmethod
    def _declaration(w: ToolSpec, types):
        props = {p.name: types.Schema(type=types.Type.STRING, description=p.description) for p in w.parameters}
        required = [p.name for p in w.parameters if p.required]
        parameters = types.Schema(type=types.Type.OBJECT, properties=props, required=required) if props else None
        return types.FunctionDeclaration(name=w.name, description=w.description, parameters=parameters)

    @staticmethod
    def _build_conversation(messages: list[Message], types) -> list:
        conversation = []
        for n in messages:
            if n.role == "user":
                conversation.append(types.Content(role="user", parts=[types.Part(text=n.text)]))
            elif n.role == "model":
                if n.raw is not None:
                    # Original-Antwort zurückgeben (enthält bei Gemini 2.5 u. a. die "Denk-Signaturen").
                    conversation.append(n.raw)
                else:
                    chunks = [types.Part(text=n.text)] if n.text else []
                    chunks += [types.Part.from_function_call(name=a.name, args=a.args) for a in n.calls]
                    conversation.append(types.Content(role="model", parts=chunks))
            else:  # "tool"
                chunks = [types.Part.from_function_response(name=e.name, response={"ergebnis": e.text}) for e in n.results]
                conversation.append(types.Content(role="user", parts=chunks))
        return conversation

    @staticmethod
    def _read_reply(response) -> ModelReply:
        text, calls, raw = "", [], None
        candidates = getattr(response, "candidates", None) or []
        if candidates and candidates[0].content is not None:
            raw = candidates[0].content
            for chunk in raw.parts or []:
                if getattr(chunk, "function_call", None):
                    calls.append(ToolCall(chunk.function_call.name, dict(chunk.function_call.args or {})))
                elif getattr(chunk, "text", None) and not getattr(chunk, "thought", False):
                    text += chunk.text
        usage = getattr(response, "usage_metadata", None)
        tok_in = getattr(usage, "prompt_token_count", 0) or 0
        tok_out = (getattr(usage, "candidates_token_count", 0) or 0) + (getattr(usage, "thoughts_token_count", 0) or 0)
        return ModelReply(text=text.strip(), calls=calls, tokens_in=tok_in, tokens_out=tok_out, raw=raw)
