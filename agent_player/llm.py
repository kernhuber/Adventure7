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
from agent_player.tools import Werkzeug


# --- neutrale Datenstrukturen (unabhängig vom Anbieter) --------------------------------
@dataclass
class Aufruf:
    """Ein Werkzeugaufruf des Modells."""
    name: str
    args: dict = field(default_factory=dict)


@dataclass
class AufrufErgebnis:
    """Das Ergebnis eines Aufrufs, das ans Modell zurückgeht."""
    name: str
    text: str


@dataclass
class Antwort:
    """Antwort des Modells: Freitext und/oder Werkzeugaufrufe, plus Verbrauch."""
    text: str = ""
    aufrufe: list[Aufruf] = field(default_factory=list)
    tokens_ein: int = 0
    tokens_aus: int = 0
    roh: Any = None                      # Original des Anbieters (Gemini braucht es für Folgeanfragen)


@dataclass
class Nachricht:
    """Eine Nachricht im Gesprächsverlauf einer Runde: 'user' | 'model' | 'tool'."""
    rolle: str
    text: str = ""
    aufrufe: list[Aufruf] = field(default_factory=list)
    ergebnisse: list[AufrufErgebnis] = field(default_factory=list)
    roh: Any = None

    @staticmethod
    def vom_nutzer(text: str) -> "Nachricht":
        return Nachricht("user", text=text)

    @staticmethod
    def vom_modell(antwort: Antwort) -> "Nachricht":
        return Nachricht("model", text=antwort.text, aufrufe=antwort.aufrufe, roh=antwort.roh)

    @staticmethod
    def werkzeug_ergebnisse(ergebnisse: list[AufrufErgebnis]) -> "Nachricht":
        return Nachricht("tool", ergebnisse=ergebnisse)


class AgentLLM:
    """Schnittstelle: Nachrichten + Werkzeuge hinein, Text und/oder Werkzeugaufrufe heraus."""
    modell: str = "?"

    async def frage(self, system: str, nachrichten: list[Nachricht], werkzeuge: list[Werkzeug]) -> Antwort:
        raise NotImplementedError


# --- Gemini-Umsetzung --------------------------------------------------------------------
class GeminiAgentLLM(AgentLLM):
    def __init__(self, modell: str):
        # Import erst hier: so lassen sich die übrigen Module ohne Google-SDK laden/testen.
        from google import genai
        apikey = os.environ.get("GOOGLE_API_KEY")
        if not apikey:
            from dotenv import load_dotenv
            load_dotenv("apikey.env")
            apikey = os.getenv("GOOGLE_API_KEY")
        self.modell = modell
        self.client = genai.Client(api_key=apikey)

    async def frage(self, system: str, nachrichten: list[Nachricht], werkzeuge: list[Werkzeug]) -> Antwort:
        # Der SDK-Aufruf ist synchron: in einem Thread ausführen, damit der Server (Pause-Knopf!) frei bleibt.
        return await asyncio.to_thread(self._frage_blockierend, system, nachrichten, werkzeuge)

    def _frage_blockierend(self, system: str, nachrichten: list[Nachricht], werkzeuge: list[Werkzeug]) -> Antwort:
        from google.genai import types
        inhalt = self._inhalt_bauen(nachrichten, types)
        deklarationen = [self._deklaration(w, types) for w in werkzeuge]
        config = types.GenerateContentConfig(
            system_instruction=system,
            tools=[types.Tool(function_declarations=deklarationen)],
            # Wir führen Werkzeuge SELBST aus (loop.py), das SDK soll das nicht automatisch tun.
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )
        antwort = None
        for versuch in range(3):
            try:
                antwort = self.client.models.generate_content(model=self.modell, contents=inhalt, config=config)
                break
            except Exception as e:
                vorueber = any(c in str(e) for c in ("503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED", "504", "DEADLINE"))
                if vorueber and versuch < 2:
                    dprint(dl.AGENT, f"Gemini vorübergehend nicht erreichbar ({str(e)[:60]}), neuer Versuch")
                    import time
                    time.sleep(2 ** versuch)
                    continue
                raise
        return self._antwort_lesen(antwort)

    @staticmethod
    def _deklaration(w: Werkzeug, types):
        eigenschaften = {p.name: types.Schema(type=types.Type.STRING, description=p.beschreibung) for p in w.parameter}
        pflicht = [p.name for p in w.parameter if p.pflicht]
        parameter = types.Schema(type=types.Type.OBJECT, properties=eigenschaften, required=pflicht) if eigenschaften else None
        return types.FunctionDeclaration(name=w.name, description=w.beschreibung, parameters=parameter)

    @staticmethod
    def _inhalt_bauen(nachrichten: list[Nachricht], types) -> list:
        inhalt = []
        for n in nachrichten:
            if n.rolle == "user":
                inhalt.append(types.Content(role="user", parts=[types.Part(text=n.text)]))
            elif n.rolle == "model":
                if n.roh is not None:
                    # Original-Antwort zurückgeben (enthält bei Gemini 2.5 u. a. die "Denk-Signaturen").
                    inhalt.append(n.roh)
                else:
                    teile = [types.Part(text=n.text)] if n.text else []
                    teile += [types.Part.from_function_call(name=a.name, args=a.args) for a in n.aufrufe]
                    inhalt.append(types.Content(role="model", parts=teile))
            else:  # "tool"
                teile = [types.Part.from_function_response(name=e.name, response={"ergebnis": e.text}) for e in n.ergebnisse]
                inhalt.append(types.Content(role="user", parts=teile))
        return inhalt

    @staticmethod
    def _antwort_lesen(antwort) -> Antwort:
        text, aufrufe, roh = "", [], None
        kandidaten = getattr(antwort, "candidates", None) or []
        if kandidaten and kandidaten[0].content is not None:
            roh = kandidaten[0].content
            for teil in roh.parts or []:
                if getattr(teil, "function_call", None):
                    aufrufe.append(Aufruf(teil.function_call.name, dict(teil.function_call.args or {})))
                elif getattr(teil, "text", None) and not getattr(teil, "thought", False):
                    text += teil.text
        um = getattr(antwort, "usage_metadata", None)
        ein = getattr(um, "prompt_token_count", 0) or 0
        aus = (getattr(um, "candidates_token_count", 0) or 0) + (getattr(um, "thoughts_token_count", 0) or 0)
        return Antwort(text=text.strip(), aufrufe=aufrufe, tokens_ein=ein, tokens_aus=aus, roh=roh)
