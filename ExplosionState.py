

from PlayerState import PlayerState
from GameState import GameState
from dataclasses import dataclass, field
from Utils import tw_print, dprint, dl

@dataclass
class ExplosionState(PlayerState):
    """ NPC Player *Explosion* - lives for 3 rounds and eliminates things where it explodes, possibly triggering further actions"""

    kaboom_timer: int = 3    # Detonate in "koboom_timer" rounds
    #name: str

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
            tw_print(f"***Sprengladung explodiert in {self.kaboom_timer} Spielzügen in {self.location.name}***")
            return "nichts"
        else:
            tw_print(f"***(((( KABUMM!!! ))))***")
            tw_print(f"Die Sprengladung explodiert hier: {self.location.name}")

            #
            # Remove Sprengladung from anyones inventory, if listed there, then from gs object list
            #
            for i in gs.players:
                i.remove_from_inventory(gs.objects["o_sprengladung"])


            delobjs = []
            delplayers = []
            for p in gs.players:
                if type(p) is not ExplosionState:
                    if p.location == self.location:
                        tw_print(f"Es hat auch ***{p.name}*** erwischt, der dummerweise am selben Platz war!!")
                        tw_print("Und auch die Objekte in seinem/ihrem Inventory (sofern vorhanden):")
                        for o in p.inventory:
                            tw_print(f"- {o.name}")
                            delobjs.append(o)
                        dprint(dl.EXPLOSIONSTATE," ... removing player {p.name}")
                        delplayers.append(p)
                else:
                    delplayers.append(p)
            if self.location.name == "p_dach":
                gs.dach = False
                print("--- Der Schuppen hat nun kein Dach mehr! ---")
            elif self.location.name == "p_warenautomat":
                gs.warenautomat_intakt = False
                import random
                nl = random.choice(
                    ["p_ubahn", "p_warenautomat", "p_geldautomat", "p_schuppen", "p_dach", "p_felsen", "p_innen"])
                dprint(dl.EXPLOSIONSTATE,"Spoiler: die Fahrradkette ist nun hier: {nl}")

                gs.objects["o_fahrradkette"].hidden = False
                gs.objects["o_fahrradkette"].ownedby = gs.places[nl]
                gs.places[nl].place_objects.append(gs.objects["o_fahrradkette"])
                tw_print("  -->***Der Warenautomat! Mit all seinem Inhalt!*** Ob die Fahrradkette irgendwo zu finden ist?")

            elif self.location.name == "p_geldautomat":
                gs.geldautomat_intakt == False
            elif self.location.name == "p_schuppen":
                gs.schuppen_intakt = False

            tw_print("***Folgende Objekte*** sind pulverisiert worden")
            for o in self.location.place_objects:
                if o.name != "o_fahrradkette":
                    print(f"- {o.name}")
                    delobjs.append(o)
                if o.name == "o_felsen":
                    tw_print("##***--> Aha!! Hier wird der Eingang zu einer Höhle sichtbar!***")
                    gs.places["p_felsen"].description = "Dort, wo der Felsen lag, ist nun nur noch Geröll ... und der Eingang zu einer Höhle"
                    gs.felsen = False
                elif o.name == "o_schuppen":
                    gs.ways["w_schuppen_dach"].visible = False
                    gs.ways["w_schuppen_innen"].visible = False
                    tw_print("  --> ***Der Schuppen! Mit all seinem Inhalt!*** Und auf das Dach kannst du nun logischerweise auch nicht mehr!")
                elif o.name == "o_warenautomat":
                    gs.ways["w_warenautomat_ubahn"].visible = True
                    gs.ways["w_ubahn_warenautomat"].visible = True
                    gs.hebel = True




                else:
                    pass
            self.location.place_objects = []
            for o in delobjs:
                del gs.objects[o.name]

            for p in delplayers:
                gs.players.remove(p)


            if self.location.name not in ["p_felsen", "p_warenautomat"]:
                tw_print("***Die Sprengladung ist leider am falschen Ort explodiert. Du kannst das Spiel nicht mehr gewinnen. Verwende 'quit' um es zu beenden, oder sieh dich noch ein wenig um, wenn es dich interessiert.***")
            return "nichts"
