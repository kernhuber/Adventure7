from pydantic_core.core_schema import none_schema

from PlayerState import PlayerState
from GameState import GameState
from dataclasses import dataclass, field
from collections import deque
from typing import List, Deque, Any
from enum import Enum, auto
from Utils import tw_print, dprint

class DogState(Enum):
    START = auto()
    EATING = auto()
    ATTACK = auto()
    TRACE = auto()
    GOHOME = auto()

class DogFight(Enum):
    WON = auto()
    LOST = auto()
    TIE = auto()
#
# Our NPC Player - the Doggo
#
@dataclass
class NPCPlayerState(PlayerState):
    from Place import Place
    from MiniGames import MiniGames

    growl: int = 0
    dog_state: DogState = DogState.START

    next_loc : Deque[Place] = field(default_factory=deque) # Doggo seeks out place where player has been
    next_loc_wait : int=2   # but only if player has left for two game moves
    nogo_places: List[str] = field(default_factory=lambda: ["p_dach","p_ubahn2"]) # Dog can't go to these places.
    way_home: Deque[Place] = field(default_factory=deque) # Falls Hund nach Hause geht
    fightgames: MiniGames = field(default_factory = MiniGames)

    def can_dog_go(self, gs: GameState, plc:str)-> bool:
        if plc in self.nogo_places:
            return False

        for w in self.location.ways:
            if w.destination.name == plc:
                if w.visible and w.obstruction_check(gs) == "Free":
                    return True
        return False

    def NPC_game_move(self, gs:GameState) -> str:
        """
        Doggo routine



        :param gs:
        :return str:
        """
        dprint("+++ Dog Data:")
        dprint(f"+++ dog_state = {self.dog_state}, dog is in {self.location.name}")

        match self.dog_state:
            case DogState.START:
                # Something to eat?
                if self.check_state_eating(gs):
                    return self.setup_state_eating(gs)
                # Someone to attack?
                if self.check_state_attack(gs):
                    return self.setup_state_attack(gs)
                # someone to observe?
                if self.check_state_trace(gs):
                    return self.setup_state_trace(gs)
                #if self.check_state_gohome(gs):
                #    return self.setup_state_go(gs)
                return "nichts"

            case DogState.ATTACK:
                # Something to eat?
                if self.check_state_eating(gs):
                    return self.setup_state_eating(gs)
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
                    if p!=self and type(p) is PlayerState and p.location == self.location:
                        pl = p
                        break

                if self.attack_counter > 0:
                    self.attack_counter = self.attack_counter - 1
                    l = 2*(3-self.attack_counter)
                    rs = f'**G{"R"*l}{"O"*l}{"A"*l}{"R"*l}{"!"*l}'

                    return f'interaktion {pl.name} "**{rs}**"'
                else:
                    print("""
********************************
*** Du kämpfst mit dem Hund! ***
********************************
                    """)
                    ds = self.fightgames.fight()
                    if ds == DogFight.WON:
                        #
                        # Kill player
                        #
                        return f"angreifen {pl.name}"
                    elif ds == DogFight.LOST:
                        #
                        # Escape to a neighbor location
                        #
                        import random
                        l = len(self.location.ways)
                        w = []
                        for l in self.location.ways:
                            if (l.obstruction_check(gs) == "Free" and l.visible and self.can_dog_go(gs, l.name)):
                                w.append(l.destination.name )

                        if w:
                            flight = random.choice(w)
                            print(f"Der Hund flüchtet jaulend nach {flight}")
                            return f"gehe {flight}"
                        else:
                            print("Der Hund kann von hier aus nirgendwo hin!")
                            return "nichts"
                    else:
                        return "nichts"

            case DogState.EATING:
                s,rs = self.do_state_eating(gs)
                self.dog_state = s
                return rs

            case DogState.TRACE:
                #
                # Did someone enter my place --> initiate attack state
                # else execute observe place
                #
                if self.check_state_eating(gs):
                    return self.setup_state_eating(gs)
                if self.check_state_attack(gs):
                    return self.setup_state_attack(gs)

                if self.check_state_trace(gs):
                    return self.setup_state_trace(gs)
                return "nichts"

            case DogState.GOHOME:
                nl = self.way_home.popleft()
                if nl:
                    if self.can_dog_go(gs, nl.name):
                        return f'gehe {nl.name}'
                    else:
                        return "nichts"
                else:
                    self.dog_state = DogState.START
                    tw_print("**Dog ist nun wieder an seinem Stammplatz**")
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

    def check_state_trace(self, gs: GameState):
        if self.next_loc:
            return True

        dsts = []
        for w in self.location.ways:
            dsts.append(w.destination.name)
        for pl in gs.players:
            if pl.location.name in dsts:
                return True
        return False

    def setup_state_trace(self, gs: GameState):
        dsts = []

        if self.next_loc:
            self.dog_state = DogState.TRACE
            if self.can_dog_go(gs, self.next_loc[0].name):
                return f"gehe {self.next_loc.popleft().name}"
            else:
                return "nichts"

        for w in self.location.ways:
            dsts.append(w.destination)
        pl = ""
        for p in gs.players:
            if p.location in dsts:
                pl = p.location
                break

        if pl != None and self.can_dog_go(gs, pl.name):
            self.dog_state = DogState.TRACE
            self.next_loc.append(pl)
            tw_print(f"**Dog beobachtet nun {pl.name}**")

        return "nichts"

    def check_state_attack(self, gs: GameState):
        #
        # Anybody here besides me?
        #
        for p in gs.players:
            if p != self and p.location == self.location and type(p) is PlayerState:
                return True

        return False

    def setup_state_attack(self, gs: GameState):
        #
        #
        #
        for p in gs.players:
            if p != self and type(p) is PlayerState and p.location == self.location:
                self.dog_state = DogState.ATTACK
                self.attack_counter = 1
                return f'interaktion {p.name} "**Grrr!**"'
        else:
            return "nichts"

    def check_state_eating(self, gs: GameState):
        for i in self.location.place_objects:
            if i.name in ["o_salami", "o_pizza"]:
                return True

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
            tw_print(f"**Dog frisst {f.name}**")
            self.eat_counter = 3
        return "nichts"

    def do_state_eating(self, gs: GameState):
        tw_print("**Dog frisst noch!**")
        self.eat_counter = self.eat_counter - 1

        if self.eat_counter == 0:
            rs = DogState.START
        else:
            rs = DogState.EATING
        return rs,"nichts"

    def fight(self) -> DogFight:
        """
        Minigame: does number provided by player beat number provided by dog?
        * both numbers one from 1,2,3,4
        * 4 beats 3, 3 beats 2, 2 beats 1, 1 beats 4
        * All other combinations -> TIE
        * Check if dog has won -> return WON
        * Check if player has lost -> return LOST
        :param p: Player input (number from 1,2,3,4)
        :return: DogFight state (WON, LOST, TIE) from Dog's perspective
        """
        import random
        d = random.randint(1,3)


        tw_print(f"***{'#'*40}***")
        tw_print("***Kampf mit dem Hund!***".center(40))
        tw_print("Regeln:  3 schlägt 2, 2 schlägt 1, 1 schlägt 3 \n... alles andere: Unentschieden")

        inp = ""
        while inp not in ["1","2","3"]:
            inp = input("Gib eine Zahl aus 1,2,3 ein: ")
        p = int(inp.strip())
        tw_print(f"Du hast: {p}")
        tw_print(f"Hund hat: {d}")
        #
        # Modulo calc: scale 1,2,3 to 0,1,2
        #
        d=d-1
        p=p-1
        if (d+1)%3 == p:
            tw_print("***Der Hund verliert den Kampf!***")
            return DogFight.LOST
        if (p+1)%3 == d:
            tw_print("***Du verlierst den Kampf gegen den Hund!***")
            return DogFight.WON
        tw_print("***Unentschieden!***")
        return DogFight.TIE