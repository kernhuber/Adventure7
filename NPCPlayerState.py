from PlayerState import PlayerState
from GameState import GameState
from dataclasses import dataclass, field
from typing import List
#
# Our NPC Player - the Doggo
#
@dataclass
class NPCPlayerState(PlayerState):
    growl: int = 0
    next_loc : str = "" # Doggo seeks out place where player has been
    next_loc_wait : int=2   # but only if player has left for two game moves
    nogo_places: List[str] = field(default_factory=lambda: ["p_dach","p_ubahn2"]) # Dog can't go to these places.

    def NPC_game_move(self, gs:GameState):
        #
        # Doggo gets mad when others are in same location
        #

        others = False
        for p in gs.players:
            if p != self:
                if p.location == self.location:
                    others=True
                    if self.growl ==0:
                        self.growl = 1
                        return f'interagiere {p.name} "**Grrrrr!**"'
                    elif self.growl==1:
                        self.growl = 2
                        return f'interagiere {p.name} "**GRROAAAARRRR!**"'
                    else:
                        self.growl = 0
                        return f'angreifen {p.name}'
        if not others:
            self.growl = 0
        #
        # Now check the surrounding places: anybody there? If so, wait, until away (one round), then check out place
        #
        for neigh in self.location.ways:
            if neigh.visible and neigh.destination.name not in self.nogo_places and neigh.obstruction_check(gs) == "Free":
                n = neigh.destination
                for p in gs.players:
                    if p != self and p.location == n:
                        self.next_loc = n.name
                        self.next_loc_wait = 1
                        break

        if self.next_loc != "":
            if self.next_loc_wait > 0:
                self.next_loc_wait = self.next_loc_wait - 1
                return "nichts"
            else:
                rval = f'gehe {self.next_loc}'
                self.next_loc = ""
                return rval
        else:
            return "nichts"