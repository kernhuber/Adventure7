from PlayerState import PlayerState
from GameState import GameState
from dataclasses import dataclass, field
from Utils import tw_print, dprint, dl


@dataclass
class ExplosionState(PlayerState):
    """ NPC Player *Explosion* - lives for 3 rounds and eliminates things where it explodes, possibly triggering further actions"""

    kaboom_timer: int = 3  # Detonate in "koboom_timer" rounds

    # name: str

    def explosion_input(self, gs: GameState) -> str:
        """
        Verarbeite Explosion - sammelt Nachrichten für Web-UI UND gibt sie an Konsole aus

        Returns:
            str: Gesammelte Explosions-Nachrichten für Web-UI (oder "nichts" wenn keine Explosion)
        """
        explosion_messages = []

        def log_explosion(msg, console_only=False):
            """Helper: Ausgabe an Konsole UND sammeln für Web-UI"""
            tw_print(msg)
            if not console_only:
                explosion_messages.append(msg)

        def log_explosion_simple(msg, console_only=False):
            """Helper: Ausgabe an Konsole (print) UND sammeln für Web-UI"""
            print(msg)
            if not console_only:
                explosion_messages.append(msg)

        from Place import Place
        owner = gs.objects["o_sprengladung"].ownedby
        if isinstance(owner, Place):
            self.location = owner
        elif isinstance(owner, PlayerState):
            self.location = owner.location
        else:
            self.location = None

        # KORRIGIERTE TIMER-LOGIK
        self.kaboom_timer -= 1  # Timer runtersetzen

        if self.kaboom_timer > 0:
            # Noch Zeit bis zur Explosion
            timer_msg = f"***Sprengladung explodiert in {self.kaboom_timer} Spielzügen in {self.location.name}***"
            log_explosion(timer_msg)
            return timer_msg  # Gib Timer-Nachricht für Web-UI zurück
        else:
            # 💥 EXPLOSION! 💥 (Timer ist jetzt 0 oder weniger)

            # return self.do_kaboom_location(gs)
            #
            # Der Rest wir dnicht mehr ausgeführt
            #
            log_explosion("***(((( KABUMM!!! ))))***")
            log_explosion(f"Die Sprengladung explodiert hier: {self.location.name}")

            #
            # Remove Sprengladung from anyones inventory, if listed there, then from gs object list
            #
            for i in gs.players:
                i.remove_from_inventory(gs.objects["o_sprengladung"])

            delobjs = []
            delplayers = []

            # Spieler eliminieren die am Explosionsort sind

            # for p in gs.players:
            #     if type(p) is not ExplosionState:
            #         if p.location == self.location:
            #             log_explosion(f"Es hat auch ***{p.name}*** erwischt, der dummerweise am selben Platz war!!")
            #             if p.inventory:
            #                 log_explosion("Und auch die Objekte in seinem/ihrem Inventory (sofern vorhanden):")
            #                 for o in p.inventory:
            #                     log_explosion(f"- {o.name}")
            #                     delobjs.append(o)
            #             dprint(dl.EXPLOSIONSTATE, f" ... removing player {p.name}")
            #             delplayers.append(p)
            #     else:
            #         delplayers.append(p)

            # Orts-spezifische Effekte


            #
            # Wenn die Sprengladung in p_dach, p_schuppen oder p_innen explodiert, werden alle
            # Objekte darin zerstört sowie alle Spieler an diesen Orten.
            #
            p_schuppen = gs.places["p_schuppen"]
            p_dach = gs.places["p_dach"]
            p_innen = gs.places["p_innen"]
            if self.location in [p_schuppen, p_dach, p_innen]:
                delplayers = [p for p in gs.players if p.location.name in ["p_schuppen", "p_dach", "p_innen"]]
                delobjs = p_schuppen.place_objects + p_dach.place_objects + p_innen.place_objects
                gs.ways["w_schuppen_dach"].visible = False
                gs.ways["w_dach_schuppen"].visible = False
                gs.ways["w_schuppen_innen"].visible = False
                gs.ways["w_innen_schuppen"].visible = False
                gs.schuppen_intakt = False
                gs.dach = False
            else:
                delplayers = [p for p in gs.players if p.location == self.location]
                delobjs = self.location.place_objects
            #
            # Jetzt die Objekte in den Inventories der betroffenen Spieler
            #
            if delplayers:
                log_explosion("Folgende Spieler hat es erwischt:")

            for p in delplayers:
                if not isinstance(p,ExplosionState):
                    log_explosion(f"🪦 {p.name}")
                    delobjs = delobjs + p.inventory

            # if self.location.name == "p_warenautomat":
            #     gs.warenautomat_intakt = False
            #     import random
            #     nl = random.choice(
            #         ["p_ubahn", "p_warenautomat", "p_geldautomat", "p_schuppen", "p_dach", "p_felsen", "p_innen"])
            #     dprint(dl.EXPLOSIONSTATE, f"Spoiler: die Fahrradkette ist nun hier: {nl}")
            #
            #     gs.objects["o_fahrradkette"].hidden = False
            #     gs.objects["o_fahrradkette"].ownedby = gs.places[nl]
            #     gs.places[nl].place_objects.append(gs.objects["o_fahrradkette"])
            #     log_explosion(
            #         "  -->***Der Warenautomat! Mit all seinem Inhalt!*** Ob die Fahrradkette irgendwo zu finden ist?")

            if self.location.name == "p_geldautomat":
                gs.geldautomat_intakt = False  # Fixed: war == statt =
                log_explosion("  -->***Der Geldautomat ist zerstört!***")
            #
            # Spezialfall Fahrradkette: diese wird nicht zerstört, sondern fliegt durch die Gegend und landet irgendwo
            #
            fk = gs.objects["o_fahrradkette"]
            fk_flag = False
            if fk in delobjs:
                import random
                #
                # Fahrradkette wird nicht aus dem Spiel gelöscht, sondern bekommt einen neuen Ort
                #
                delobjs.remove(fk)
                no_fly_locs = ["p_hoehle", "p_wagen", "p_ubahn2"]

                if self.location in [p_schuppen, p_dach, p_innen]:
                    no_fly_locs = no_fly_locs.append(["p_dach", "p_innen"])

                fly_locs_str = [l for l in gs.places if l not in no_fly_locs]

                fk_new_loc_str = random.choice(fly_locs_str)
                fk_new_loc = gs.places[fk_new_loc_str]
                fk_new_loc.place_objects.append(fk)
                fk.ownedby = fk_new_loc
                fk_flag = True
                dprint(dl.EXPLOSIONSTATE, f"Die Fahrradkette ist jetzt hier: {fk_new_loc.callnames[0]}")

            # Objekte eliminieren
            log_explosion("***Folgende Objekte*** sind pulverisiert worden")


            for o in delobjs:
                if o.name != "o_fahrradkette":
                    log_explosion_simple(f"- {o.callnames[0]}")


                # Spezielle Objekt-Effekte
                if o.name == "o_felsen":
                    log_explosion("##***--> Aha!! Hier wird der Eingang zu einer Höhle sichtbar!***")
                    gs.places[
                        "p_felsen"].description = "Dort, wo der Felsen lag, ist nun nur noch Geröll ... und der Eingang zu einer Höhle"
                    gs.felsen = False
                elif o.name == "o_schuppen":
                    gs.ways["w_schuppen_dach"].visible = False
                    gs.ways["w_schuppen_innen"].visible = False
                    log_explosion(
                        "  --> ***Der Schuppen! Mit all seinem Inhalt!*** Und auf das Dach kannst du nun logischerweise auch nicht mehr!")
                elif o.name == "o_warenautomat":
                    gs.ways["w_warenautomat_ubahn"].visible = True
                    gs.ways["w_ubahn_warenautomat"].visible = True
                    gs.hebel = True
                    log_explosion("  --> ***Der Warenautomat ist gesprengt! Ein Zugang zur U-Bahn wird sichtbar!***")

            # Cleanup: Entferne zerstörte Objekte und Spieler
            self.location.place_objects = []
            for o in delobjs:
                if o.name in gs.objects:
                    del gs.objects[o.name]

            for p in delplayers:
                if p in gs.players:
                    gs.players.remove(p)

            # Gewinn-/Verlust-Check
            if self.location.name not in ["p_felsen", "p_warenautomat"]:
                log_explosion(
                    "***Die Sprengladung ist leider am falschen Ort explodiert. Du kannst das Spiel nicht mehr gewinnen. Verwende 'quit' um es zu beenden, oder sieh dich noch ein wenig um, wenn es dich interessiert.***")
            else:
                log_explosion("***Die Explosion war erfolgreich!***")

            # Sammle alle Nachrichten für Web-UI
            if explosion_messages:
                return "\n".join(explosion_messages)
            else:
                return "💥 EXPLOSION! 💥"  # Fallback falls keine Messages gesammelt wurden
