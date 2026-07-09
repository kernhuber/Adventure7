"""LLM-Backend-Auswahl an EINER Stelle.

Liest den Schalter ``utils.LLM_BACKEND`` und liefert den passenden ``LLMClient``-Adapter.
Die Engine bleibt dadurch unabhängig vom konkreten LLM (siehe ``services/interfaces.py``
und ``services/adapters.py``). Die Gemma/Ollama-Seite wird **lazy** importiert, damit der
Standard-Pfad (Gemini) ohne installiertes ``ollama`` funktioniert.
"""
from __future__ import annotations

from utils import dprint, dl


def make_llm(backend: str | None = None):
    """Baue den LLM-Adapter gemäß ``utils.LLM_BACKEND`` (oder explizitem ``backend``)."""
    if backend is None:
        from utils import LLM_BACKEND as backend  # zur Laufzeit lesen (nicht beim Import fixieren)

    key = (backend or "gemini").strip().lower()
    if key == "gemma":
        dprint(dl.LLM, "🦙 LLM-Backend: Gemma (lokal via Ollama)")
        from services.adapters import LLMClientGemma  # lazy: zieht ollama erst hier herein
        return LLMClientGemma()

    if key != "gemini":
        dprint(dl.LLM, f"⚠️ Unbekanntes LLM_BACKEND '{backend}', falle auf 'gemini' zurück.")
    else:
        dprint(dl.LLM, "☁️ LLM-Backend: Gemini (google-genai)")
    from services.adapters import LLMClientGemini
    return LLMClientGemini()
