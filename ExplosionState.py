
from PlayerState import PlayerState
from GameState import GameState
from dataclasses import dataclass, field
from collections import deque
from typing import List, Deque, Any
from enum import Enum, auto

@dataclass
class ExplosionState(PlayerState):
    """ NPC Player *Explosion* - lives for 3 rounds and eliminates things where it explodes, possibly triggering further actions"""

    kaboom_timer: int = 3    # Detonate in "koboom_timer" rounds

    def explosion_input(self, gs:GameState) -> str:
        from Place import Place
        owner = gs.objects["o_sprengladung"].ownedby
        if isinstance(owner, Place):
            self.location = owner
        elif isinstance(owner, PlayerState):
            self.location = owner.location
        else:
            self.location = None

        if self.kaboom_timer > 0:
            self.kaboom_timer = self.kaboom_timer - 1
            print(f":::: Sprengladung explodiert {self.kaboom_timer} Spielzügen in {self.location.name}")
            return "nichts"
        else:
            print(f"**** KABUMM!!! ****")
            print(f"Die Sprengladung explodiert hier: {self.location.name}")
            print("... gottseidank nicht mehr als ein Böller. Nichts passiert.")
            #
            # Remove Sprengladung from anyones inventory, if listed there, then from gs object list
            #
            for i in gs.players:
                i.remove_from_inventory(gs.objects["o_sprengladung"])

            del(gs.objects["o_sprengladung"])
            #
            # Finally, remove myself from player list
            #
            gs.players.remove(self)
            return "nichts"
