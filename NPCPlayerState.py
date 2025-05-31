from pydantic_core.core_schema import none_schema

from PlayerState import PlayerState
from GameState import GameState
from dataclasses import dataclass, field
from collections import deque
from typing import List, Deque, Any
from enum import Enum, auto

class DogState(Enum):
    START = auto()
    EATING = auto()
    ATTACK = auto()
    OBSERVE = auto()
    GOHOME = auto()

#
# Our NPC Player - the Doggo
#
@dataclass
class NPCPlayerState(PlayerState):
    from Place import Place
    growl: int = 0
    dog_state: DogState = DogState.START

    next_loc : str = "" # Doggo seeks out place where player has been
    next_loc_wait : int=2   # but only if player has left for two game moves
    nogo_places: List[str] = field(default_factory=lambda: ["p_dach","p_ubahn2"]) # Dog can't go to these places.
    way_home: Deque[Place] = field(default_factory=deque) # Falls Hund nach Hause geht

    def NPC_game_move(self, gs:GameState) -> str:
        """
        Doggo routine

        The dog behaves as follows:

        0) Start
           state = start

        1) Food in his place:
           eat food (discard food from gs.objects and place, do nothing for 3 game cycles)
           state = "eating"

        2) Someone in his place:
           warn two game cycles, attack in third cycle
           state = "threat to attack"

        3) Someone in visible neighbor place:
           Watch neighbor place: walk to neighbor place when place empty
           state = observe

        4) Nobody in neighbor place:
           walk home (Geldautomat)



        :param gs:
        :return str:
        """
        print("+++ Dog Data:")
        print(f"+++ dog_state = {self.dog_state}, dog is in {self.location.name}")

        match self.dog_state:
            case DogState.START:
                # Something to eat?
                if self.check_state_eating(gs):
                    return self.setup_state_eating(gs)
                # Someone to attack?
                if self.check_state_attack(gs):
                    return self.setup_state_attack(gs)
                # someone to observe?
                if self.check_state_observe(gs):
                    return self.setup_state_observe(gs)
                #if self.check_state_gohome(gs):
                #    return self.setup_state_go(gs)
                return "nichts"
            case DogState.ATTACK:
                #
                # Other Player still in my place? If not, return to START state
                #

                if not self.check_state_attack(gs):
                    self.attack_counter = 2
                    self.dog_state = DogState.START
                    return "nichts"
                #
                # OK - still here: who are you?
                #
                pl = None
                for p in gs.players:
                    if p!=self and p.location == self.location:
                        pl = p
                        break

                if self.attack_counter > 0:
                    self.attack_counter = self.attack_counter - 1
                    l = 2*(3-self.attack_counter)
                    rs = f'**G{"R"*l}{"O"*l}{"A"*l}{"R"*l}{"!"*l}'

                    return f'interaktion {pl.name} "**{rs}**"'
                else:
                    return f"angreifen {pl.name}"

            case DogState.EATING:
                print("**Dog frisst noch!**")
                self.eat_counter = self.eat_counter -1
                if self.eat_counter == 0:
                    self.dog_state = DogState.START
                return "nichts"

            case DogState.OBSERVE:
                #
                # Did someone enter my place --> initiate attack state
                # else execute observe place
                #
                if self.check_state_attack(gs):
                    return self.setup_state_attack(gs)

                if self.check_state_observe(gs):
                    #print(f"**Dog wartet noch längstens {self.next_loc_wait} weiter**")
                    #self.next_loc_wait = self.next_loc_wait - 1
                    print(f'Dog lauert darauf, als nächstes zu {self.next_loc} zu gehen.')
                    return "nichts"
                else:
                    if not self.next_loc in self.nogo_places:
                        rval = f"gehe {self.next_loc}"
                        self.dog_state = DogState.START
                        return rval
                    else:
                        if self.check_state_gohome(gs):
                            print("**Dog geht jetzt zu seinem Stammplatz.**")
                            return self.setup_state_gohome(gs)
                        else:
                            print("**Dog kann nicht zu seinem Stammplatz, er bleibt nun hier**")
                            self.dog_state = DogState.START

            case DogState.GOHOME:
                nl = self.way_home.popleft()
                if nl:
                    return f'gehe {nl.name}'
                else:
                    self.dog_state = DogState.START
                    print("**Dog ist nun wieder an seinem Stammplatz**")
                    return "nichts"


            case _:
                return "nichts" # default/unknown state

    def check_state_gohome(self, gs: GameState):
        if gs.find_shortest_path(self.location,gs.places["o_geldautomat"]) != None:
            return True
        return False

    def setup_state_gohome(self, gs: GameState):
        ret = gs.find_shortest_path(self.location, gs.places["o_geldautomat"])
        if ret != None:
            self.way_home = deque(ret)
            self.dog_state = DogState.GOHOME
        else:
            return "nichts"

    def check_state_observe(self, gs: GameState):
        dsts = []
        for w in self.location.ways:
            dsts.append(w.destination.name)
        for pl in gs.players:
            if pl.location.name in dsts:
                return True
        return False

    def setup_state_observe(self, gs: GameState):
        dsts = []
        for w in self.location.ways:
            dsts.append(w.destination.name)
        pl = ""
        for p in gs.players:
            if p.location.name in dsts:
                pl = p.location.name
        if pl != "":
            self.dog_state = DogState.OBSERVE
            self.next_loc = pl
            self.next_loc_wait = 1
            print(f"**Dog beobachtet nun {pl}**")
            return "nichts"

    def check_state_attack(self, gs: GameState):
        #
        # Anybody here besides me?
        #
        for p in gs.players:
            if p != self and p.location == self.location:
                return True
            else:
                return False
    def setup_state_attack(self, gs: GameState):
        #
        #
        #
        for p in gs.players:
            if p != self and p.location == self.location:
                self.dog_state = DogState.ATTACK
                self.attack_counter = 1
                return f'interaktion {p.name} "**Grrr!**"'
        else:
            return "nichts"

    def check_state_eating(self, gs: GameState):
        for i in self.location.place_objects:
            if i.name in ["o_salami", "o_pizza"]:
                return True
            else:
                return False

    def setup_state_eating(self, gs: GameState):
        for i in self.location.place_objects:
            f = None
            if i.name in ["o_salami","o_pizza"]:
                f = i
                break
        if f != None:
            self.location.place_objects.remove(f)
            del gs.objects[f.name]
            self.dog_state = DogState.EATING
            print(f"**Dog frisst {f.name}**")
            self.eat_counter = 3
            return "nichts"

    def NPC_game_move_old(self, gs:GameState) -> str:
        """
        Doggo routine

        The dog behaves as follows:

        0) Start
           state = start

        1) Food in his place:
           eat food (discard food from gs.objects and place, do nothing for 3 game cycles)
           state = "eating"

        2) Someone in his place:
           warn two game cycles, attack in third cycle
           state = "threat to attack"

        3) Someone in visible neighbor place:
           Watch neighbor place: walk to neighbor place when place empty
           state = observe

        4) Nobody in neighbor place:
           walk home (Geldautomat)



        :param gs:
        :return str:
        """

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