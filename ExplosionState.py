
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
    name: "explosion"
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

            #
            # Remove Sprengladung from anyones inventory, if listed there, then from gs object list
            #
            for i in gs.players:
                i.remove_from_inventory(gs.objects["o_sprengladung"])


            delobjs = []
            delplayers = []
            for p in gs.players:
                if p != self:
                    if p.location == self.location:
                        print(f"Es hat auch {p.name} erwischt, der dummerweise am selben Platz war!!")
                        print("Und auch die Objekte in seinem/ihrem Inventory (sofern vorhanden):")
                        for o in p.inventory:
                            print(f"* {o.name}")
                            delobjs.append(o)
                        print(f" ... removing player {p.name}")
                        delplayers.append(p)
                else:
                    delplayers.append(p)

            print("Folgende Objekte sind pulverisiert worden")
            for o in self.location.place_objects:
                print(f"* {o.name}")
                delobjs.append(o)
                if o.name == "o_felsen":
                    print("  --> Aha!! Hier wird der Eingang zu einer Höhle sichtbar!")
                    gs.places["p_felsen"].description = "Dort, wo der Felsen lag, ist nun nur noch Geröll ... und der Eingang zu einer Höhle"
                    gs.felsen = False
                elif o.name == "o_schuppen":
                    gs.ways["w_schuppen_dach"].visible = False
                    gs.ways["w_schuppen_innen"].visible = False
                    print("  --> Der Schuppen! Mit all seinem Inhalt! Und auf das Dach kannst du nun logischerweise auch nicht mehr!")
                else:
                    pass
            for o in delobjs:
                del(gs.objects[o.name])
                del(o)
            for p in delplayers:
                gs.players.remove(p)
                del(p)


            return "nichts"
