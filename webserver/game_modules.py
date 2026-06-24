"""Optional import of the real game-engine modules.

When the game package is importable this exposes ``GameState`` / ``PlayerState`` and
sets ``GAME_MODULES_AVAILABLE = True``; otherwise the server runs in demo mode and
both names are ``None``. Kept in its own module so ``server.py`` and the command /
NPC modules can share the single flag without importing each other (avoiding a
circular import).
"""
import sys
import os

from Utils import dprint, dl

try:
    from GameState import GameState
    from PlayerState import PlayerState

    GAME_MODULES_AVAILABLE = True
    dprint(dl.WEBGUI, "✅ Game-Module erfolgreich importiert")
except ImportError as e:
    GameState = None
    PlayerState = None
    dprint(dl.WEBGUI, f"⚠️  Game-Module nicht verfügbar: {e}")
    dprint(dl.WEBGUI, "⚠️  Verwende Demo-Modus")
    GAME_MODULES_AVAILABLE = False

    #
    # PyInstaller-Mode?
    #
    if hasattr(sys, '_MEIPASS'):
        # Im PyInstaller-Betrieb
        base_path = sys._MEIPASS
        os.chdir(base_path)
