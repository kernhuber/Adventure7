"""Per-turn game rules for GameState.

GameTurnMixin owns the rule logic that drives a single turn. It starts with the
switch-timer countdown and grows (in later Step 3 sub-steps) to include NPC turns
and the thirst / turn-advance / game-over effects. These rules previously lived in
the web layer (webserver/command_engine.py, webserver/npc_runner.py); moving them
here makes GameState the home of game rules, testable without the web GUI.

Relies on the host class (GameState) for get_flags(), players, the verb engine, etc.
"""
from __future__ import annotations


class GameTurnMixin:
    def tick_switch_timers(self):
        """Per-turn countdown of the control-room / generator-room switch timers.

        When a timer reaches zero the corresponding switch flips back off, unless the
        zombie is cooperative. Runs once per turn, after all NPCs have acted.
        """
        f = self.get_flags()
        if f.schalter_kontrollraum_timer > 0:
            f.schalter_kontrollraum_timer -= 1
            if f.schalter_kontrollraum_timer <= 0 and not f.zombie_cooperative:
                f.schalter_kontrollraum = False
        if f.schalter_generatorraum_timer > 0:
            f.schalter_generatorraum_timer -= 1
            if f.schalter_generatorraum_timer <= 0 and not f.zombie_cooperative:
                f.schalter_generatorraum = False
