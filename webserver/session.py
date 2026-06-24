"""Registry of active web sessions for the backend.

A :class:`SessionManager` owns the set of live web sessions (one per connected
client), keyed by ``session_id``. Each session is currently a plain dict; a typed
``GameSession`` will replace it when the command engine is extracted.

The manager exists now mainly to give each session's ``WebDialogs`` and scene cache
a single, per-session owner. Previously the server held one ``self.wd`` that every
newly connecting client overwrote, so a command in one session could route its
dialogs (pin pad, mini-game, game-over) to another client's websocket. Storing
``web_dialogs`` inside the session removes that cross-talk.

SessionManager is intentionally dict-compatible (``mgr[sid]``, ``sid in mgr``,
``del mgr[sid]`` …) so the existing call sites keep working unchanged during the
ongoing refactor.
"""
from typing import Dict, Iterator


class SessionManager:
    def __init__(self):
        self._sessions: Dict[str, dict] = {}

    def __contains__(self, session_id) -> bool:
        return session_id in self._sessions

    def __getitem__(self, session_id) -> dict:
        return self._sessions[session_id]

    def __setitem__(self, session_id, session: dict) -> None:
        self._sessions[session_id] = session

    def __delitem__(self, session_id) -> None:
        del self._sessions[session_id]

    def __iter__(self) -> Iterator[str]:
        return iter(self._sessions)

    def __len__(self) -> int:
        return len(self._sessions)

    def get(self, session_id, default=None):
        return self._sessions.get(session_id, default)

    def items(self):
        return self._sessions.items()
