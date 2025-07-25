from pydantic_core.core_schema import none_schema

from PlayerState import PlayerState
from GameState import GameState
from dataclasses import dataclass, field
from collections import deque
from typing import List, Deque, Any
from enum import Enum, auto
from Utils import tw_print, dprint, dl

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
    dog_state_message: str = "Der Hund tut nichts"
    command_after_fight: str = None

    next_loc : Deque[Place] = field(default_factory=deque) # Doggo seeks out place where player has been
    next_loc_wait : int=2   # but only if player has left for two game moves
    attack_counter: int=2   # Until dog attacks
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


        # NEUE Prüfung für Web-Mini-Game Ergebnisse
        if hasattr(self, '_pending_fight_result'):
            result = self._pending_fight_result
            del self._pending_fight_result
            return self.process_fight_result(gs, result)

            # ... bestehender Code bleibt unverändert ...
        dprint(dl.NPCPLAYERSTATE,"+++ Dog Data:")
        dprint(dl.NPCPLAYERSTATE,f"+++ dog_state = {self.dog_state}, dog is in {self.location.name}")
        #
        # Player has initiated fight, fight was executed, so do  this:
        #
        if self.command_after_fight:
            r = self.command_after_fight
            self.command_after_fight = None
            return r
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
                self.dog_state_message = "Der Hund tut nichts."
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
                    self.dog_state_message = "Der Hund tut nichts."
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
                    self.dog_state_message = f"{rs} - Der Hund ist sauer und greift gleich an!"
                    return f'interaktion {pl.name} "**{rs}**"'
                else:
                    return self.do_attack_state(gs, pl)

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
                else:
                    return self.setup_state_gohome(gs)
                self.dog_state_message = "Der Hund tut nichts."
                return "nichts"

            case DogState.GOHOME:
                if not self.way_home:
                    self.dog_state = DogState.START
                    self.dog_state_message = "Der Hund tut nichts."
                    return "nichts"

                nl = self.way_home.popleft()
                if nl:
                    if self.can_dog_go(gs, nl.destination.name):
                        tw_print(f"Auf seinem Weg zum Geldautomaten geht der Hund hierhin: {nl.destination.callnames[0]} ({nl.destination.name})")
                        self.dog_state_message = f"Der Hund geht jetzt hierhin: {nl.destination.callnames[0]}"
                        return f'gehe {nl.destination.name}'
                    else:
                        self.dog_state_message = "Der Hund tut nichts."
                        return "nichts"
                else:
                    self.dog_state = DogState.START
                    tw_print("**Der Hund ist nun wieder an seinem Stammplatz**")
                    self.dog_state_message = "Der Hund ist an seinem Stammplatz (Geldautomat) und tut nichts."
                    return "nichts"


            case _:
                self.dog_state_message = "Der Hund tut nichts."
                return "nichts" # default/unknown state

    def do_attack_state(self,gs: GameState, pl: PlayerState):
        # If in text mode, the routine executes a complete dogfight. The result
        # is a string, indicating what the dog is doing **after** the fight:
        # TIE: Nothing
        # WON: Kill opponent
        # LOST: flee
        #
        # If in web mode, this routine merely INITIATES a dog fight to be executed by
        # the web interface by returning a special string. The results of the fight
        # are processed in subsequent steps.
        #
        # Erkenne ob Web-Interface aktiv ist
        is_web_interface = (hasattr(gs, 'web_sessions') and
                            len(getattr(gs, 'web_sessions', {})) > 0)

        if not is_web_interface:
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
                return f"toeten {pl.name}"
            elif ds == DogFight.LOST:
                #
                # Escape to a neighbor location
                #
                import random
                l = len(self.location.ways)
                w = []
                for l in self.location.ways:
                    if (l.obstruction_check(gs) == "Free" and l.visible and self.can_dog_go(gs, l.destination.name)):
                        w.append(l.destination.name)

                if w:
                    flight = random.choice(w)
                    print(f"Der Hund flüchtet jaulend nach {flight}")
                    return f"gehe {flight}"
                else:
                    print("Der Hund kann von hier aus nirgendwo hin!")
                    return "nichts"
            else:
                return "nichts"
        else:
            #
            # Web Interface
            #
            # Web-Interface: Trigger Mini-Game über spezielle Nachricht
            import random
            game_types = ['circle_fight', 'sum_fight', 'odd_even_fight', 'close_fight']
            selected_game = random.choice(game_types)
            dprint(dl.NPCPLAYERSTATE, f"🎮 Starte Web-Mini-Game: {selected_game}")

            # KORRIGIERT: Verwende richtige Attribut-Namen und DogState-Werte
            self.dog_state = DogState.ATTACK  # KORRIGIERT: dog_state (nicht dog_status)
            self.attack_counter = 2
            self.dog_state_message = "Der Hund kämpft gerade!"

            return f"MINIGAME:{selected_game}"

    def gets_attacked(self, gs:GameState, pl:PlayerState):
        """Dog gets attacked by Player!"""
        self.dog_state = DogState.ATTACK
        self.way_home = deque()
        self.next_loc = deque()
        r = self.do_attack_state(gs,pl)
        self.command_after_fight = r
        return r

    def check_state_gohome(self, gs: GameState):
        if self.way_home and gs.find_shortest_path(self.location,gs.places["o_geldautomat"]) != None:
            return True
        return False

    def setup_state_gohome(self, gs: GameState):
        ret = gs.find_shortest_path(self.location, gs.places["p_geldautomat"])
        if ret != None:
            self.way_home = deque(ret)
            self.dog_state = DogState.GOHOME
        self.dog_state_message = "Der Hund tut nichts."
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
                nl = self.next_loc.popleft()
                tw_print(f"***Der Hund geht zum/zur {nl.callnames[0]}.***")
                self.dog_state_message = f"Der Hund läuft zum/zur {nl.callnames[0]}."
                return f"gehe {nl.name}"
            else:
                self.dog_state_message = "Der Hund tut nichts."
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
            tw_print(f"**Der Hund beobachtet nun den Ort {pl.callnames[0]}**")
            self.dog_state_message = f"Der Hund beobachtet nun den Ort {pl.callnames[0]}"
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
                self.dog_state_message = "Der Hund wird sauer..."
                return f'interaktion {p.name} "**Grrr!**"'
        else:
            self.dog_state_message = "Der Hund tut nichts."
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
            tw_print(f"**Der Hund frisst {f.name}**")
            self.dog_state_message = f"**Der Hund frisst {f.name}**"
            self.eat_counter = 3
        return "nichts"

    def do_state_eating(self, gs: GameState):
        tw_print("**Der Hund frisst noch!**")
        self.dog_state_message = "**Der Hund frisst noch!**"
        self.eat_counter = self.eat_counter - 1

        if self.eat_counter == 0:
            rs = DogState.START
        else:
            rs = DogState.EATING
        return rs,"nichts"

    def dog_prompt(self,gs: GameState,pl: PlayerState):

        pp = None
        if self.location == pl.location:
            pp = f"!!! Ein Hund befindet sich am selben Ort wie {pl.name} !!!"
        else:
            loc = []
            for l in pl.location.ways:
                loc.append(l.destination)
            if self.location in loc:
                pp = f"!!! Ein Hund befindet sich in der Nähe von {pl.name}, und zwar am Ort {self.location.callnames[0]} !!!"
        dmood = ""
        match self.dog_state:
            case DogState.ATTACK:
                dmood = "- Der Hund ist sehr wütend und greift gleich an"
            case DogState.TRACE:
                dmood = "- Der Hund scheint dich zu beobachten"
            case DogState.EATING:
                dmood = "- Der Hund frisst gerade etwas und ist abgelenkt"
        if pp:
            return f"""
+------+            
+ Hund +
+------+

{pp}

Beschreibung des Hundes
=======================
- Riesig (mehr als ein Meter)
- Räudiges Fell in grau-brauner Farbe
- verschlagener, intelligenter Blick
- Lange Zähne
- Hungrig - sabbert vor Hunger
- Pfoten, die man als Pranken bezeichnen kann
{dmood}
"""
        else:
            return ""

    # NEUE Methoden am Ende der NPCPlayerState-Klasse hinzufügen:

    def gets_attacked_new(self, gs: GameState, pl: PlayerState):
        """
        KORRIGIERTE VERSION mit richtigen DogState-Werten
        Player attacks dog - starte Mini-Game
        """
        from Utils import dprint, dl
        import random

        dprint(dl.NPCPLAYERSTATE, f"🥊 {pl.name} greift {self.name} an!")

        # Erkenne ob Web-Interface aktiv ist
        is_web_interface = (hasattr(gs, 'web_sessions') and
                            len(getattr(gs, 'web_sessions', {})) > 0)

        if is_web_interface:
            # Web-Interface: Trigger Mini-Game über spezielle Nachricht
            game_types = ['circle_fight', 'sum_fight', 'odd_even_fight', 'close_fight']
            selected_game = random.choice(game_types)
            dprint(dl.NPCPLAYERSTATE, f"🎮 Starte Web-Mini-Game: {selected_game}")

            # KORRIGIERT: Verwende richtige Attribut-Namen und DogState-Werte
            self.dog_state = DogState.ATTACK  # KORRIGIERT: dog_state (nicht dog_status)
            self.attack_counter = 2
            self.dog_state_message = "Der Hund kämpft gerade!"

            return f"MINIGAME:{selected_game}"
        else:
            # Text-Interface: Bestehende MiniGames.py Logik
            dprint(dl.NPCPLAYERSTATE, f"🎮 Starte Text-Mini-Game")

            from MiniGames import MiniGames
            mg = MiniGames()
            fight_result = mg.fight()
            return self.process_fight_result(gs, fight_result)

    def process_fight_result(self, gamestate, fight_result):
        """
        KORRIGIERTE VERSION mit richtigen DogState-Werten
        Verarbeite das Ergebnis eines Kampfes (für beide Interface-Typen)
        """
        from Utils import dprint, dl
        import random

        dprint(dl.NPCPLAYERSTATE, f"🎯 Kampfergebnis: {fight_result}")

        if fight_result == DogFight.WON:
            # Hund gewinnt - KORRIGIERT: Verwende DogState.ATTACK
            self.dog_state = DogState.ATTACK  # KORRIGIERT: dog_state (nicht dog_status)
            self.attack_counter = 1  # KORRIGIERT: Reduziert für sofortigen Angriff
            self.dog_state_message = "Der Hund hat dich besiegt und ist nun sehr aggressiv!"

            return """***Der Hund springt dich an und du kannst dich gerade noch zurückziehen! 
    Der Hund knurrt bedrohlich und wirkt sehr aggressiv. Du solltest hier schnell verschwinden!***"""

        elif fight_result == DogFight.LOST:
            # Hund verliert - KORRIGIERT: Verwende DogState.GOHOME (Hund flieht)
            self.dog_state = DogState.GOHOME  # KORRIGIERT: Hund geht nach Hause
            self.attack_counter = 0
            self.dog_state_message = "Der Hund ist verängstigt und läuft weg"

            # Setze way_home für Flucht zum Geldautomat
            try:
                ret = gamestate.find_shortest_path(self.location, gamestate.places["p_geldautomat"])
                if ret:
                    self.way_home = deque(ret)
            except:
                pass

            return """***Du hast den Hund im fairen Kampf besiegt! Er winselt und läuft mit eingezogenem Schwanz davon. 
    Du hast ihn nicht verletzt, aber er wird dich eine Weile in Ruhe lassen.***"""

        else:  # DogFight.TIE
            # Unentschieden - KORRIGIERT: Verwende DogState.TRACE (Hund beobachtet)
            self.dog_state = DogState.TRACE  # KORRIGIERT: Hund wird vorsichtig
            self.attack_counter = 2  # Verzögerter Angriff
            self.dog_state_message = "Der Hund ist vorsichtig und beobachtet dich"

            return """***Das Duell endet unentschieden. Ihr blickt euch wachsam an, 
    beide bereit zum nächsten Zug. Der Hund respektiert deine Kampfkraft, 
    ist aber noch nicht besiegt.***"""

    def set_fight_result(self, fight_result):
        """
        Setze Kampfergebnis für nächsten NPC-Zug (für Web-Interface)
        KEINE ÄNDERUNG NÖTIG
        """
        self._pending_fight_result = fight_result

    # ============== ALTERNATIVE SICHERE VERSION ==============

    def gets_attacked_safe(self, gs: GameState, pl: PlayerState):
        """
        SICHERE ALTERNATIVE - falls immer noch Probleme auftreten
        Ändert dog_state nicht, nur attack_counter und message
        """
        from Utils import dprint, dl
        import random

        dprint(dl.NPCPLAYERSTATE, f"🥊 {pl.name} greift {self.name} an!")

        # Einfache Web-Interface Erkennung
        is_web_interface = (pl.name == "WebPlayer")

        if is_web_interface:
            game_types = ['circle_fight', 'sum_fight', 'odd_even_fight', 'close_fight']
            selected_game = random.choice(game_types)
            dprint(dl.NPCPLAYERSTATE, f"🎮 Web-Mini-Game: {selected_game}")

            # SICHER: Nur diese Werte ändern
            self.attack_counter = 2
            self.dog_state_message = "Der Hund kämpft gerade!"
            # dog_state bleibt unverändert

            return f"MINIGAME:{selected_game}"
        else:
            # Text-Interface
            from MiniGames import MiniGames
            mg = MiniGames()
            fight_result = mg.fight()
            return self.process_fight_result_safe(gs, fight_result)

    def process_fight_result_safe(self, gamestate, fight_result):
        """
        SICHERE VERSION - minimal invasive Änderungen
        """
        if fight_result == DogFight.WON:
            self.attack_counter = 1
            self.dog_state_message = "Der Hund hat gewonnen und ist aggressiv!"
            return "***Der Hund hat dich besiegt!***"

        elif fight_result == DogFight.LOST:
            self.attack_counter = 0
            self.dog_state_message = "Der Hund ist verängstigt"
            return "***Du hast den Hund besiegt!***"

        else:  # TIE
            self.attack_counter = 2
            self.dog_state_message = "Der Hund ist vorsichtig"
            return "***Unentschieden!***"

    # ============== DEBUGGING AUSGABE ==============

    def debug_dogstate_info(self):
        """
        Debug-Funktion: Zeige aktuellen Hund-Zustand
        """
        print("🔍 DEBUG: Aktueller Hund-Zustand:")
        print(f"   dog_state: {self.dog_state} (Typ: {type(self.dog_state)})")
        print(f"   attack_counter: {self.attack_counter}")
        print(f"   dog_state_message: {self.dog_state_message}")
        print(f"   location: {self.location.name if self.location else 'None'}")

        print(f"🔍 Verfügbare DogState-Werte:")
        for state in DogState:
            print(f"   - DogState.{state.name} = {state}")

