from PlayerState import PlayerState
from GameState import GameState
from dataclasses import dataclass, field
from collections import deque
from typing import List, Deque, Any
#
# Our NPC Player - the Doggo
#
@dataclass
class NPCPlayerState(PlayerState):
    from Place import Place
    growl: int = 0
    next_loc : str = "" # Doggo seeks out place where player has been
    next_loc_wait : int=2   # but only if player has left for two game moves
    nogo_places: List[str] = field(default_factory=lambda: ["p_dach","p_ubahn2"]) # Dog can't go to these places.
    way_home: Deque[Place] = field(default_factory=deque) # Falls Hund nach Hause geht
    def NPC_game_move(self, gs:GameState):
        #
        # Are we on our way home? If so, walk, and that's it.
        #
        if self.way_home:
            print((" Dog walks home ").center(60,"+"))
            n = self.way_home.popleft()
            return f'gehe {n.name}'

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
        # Now check the surrounding places: anybody there? If so, wait, until away (one round), then check out place.
        # Walk home, if other player does not leave place for 3 rounds
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
                #
                # Are there other players in the spot I am curious about? If so, initiate walk home.
                #
                for p in gs.players:
                    if p!= self:
                        if p.location.name == self.next_loc:
                            self.way_home = deque(gs.find_shortest_path(self.location, gs.places["o_geldautomat"]))
                            rval = f'gehe {self.way_home.popleft().name}'
                        else:
                            rval = f'gehe {self.next_loc}'
                            self.next_loc = ""

                return rval
        else:
            return "nichts"