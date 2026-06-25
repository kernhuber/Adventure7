from __future__ import annotations

import json
import os
from collections import deque


from Place import Place
from Way import Way
from typing import Dict, List
from typing import Set
from PlayerState import PlayerState
from GameObject import GameObject
from services.world import GameFlags, WorldModel, ContextBuilder

from Utils import tw_print, dprint, dl, dpprint
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from services.interfaces import LLMClient

#
# Maintains the state from the game perspective. There are player states as well
#

from typing import Callable


from WayPrompts import w_dach_schuppen_prompt_f


class GameState:

    # --- Central list of flag field names kept in sync with GameFlags ---
    # Keep in Sync with Class GameFlags in services/world.py
    FLAG_FIELDS: Set[str] = {
        "schuppentuer",
        "leiter",
        "hebel",
        "geheimzahl",
        "wagen_ubahn2",
        "felsen",
        "hauptschalter",
        "dach",
        "warenautomat_intakt",
        "geldautomat_intakt",
        "schuppen_intakt",
        "flasche_voll",
        "falltuer_offen",
        "werbeplakat_offen",
        "korridor_offen",
        "game_over",
        "game_won",
        "time",
        "debug_mode",
        "zombie_awake",
        "zombie_cooperative",
        "schalter_kontrollraum",
        "schalter_generatorraum",
        "schalter_kontrollraum_timer",
        "schalter_generatorraum_timer",
        "umschlag_geheimbotschaft",
    }

    # Provide legacy attribute access to flags (read)
    def __getattr__(self, name: str):
        # Called only if normal attribute lookup fails
        if name in getattr(self, "FLAG_FIELDS", set()) and hasattr(self, "_flags"):
            return getattr(self._flags, name)
        raise AttributeError(name)

    # Keep GameFlags in sync when legacy attributes are set (write)
    def __setattr__(self, name, value):
        # During __init__, _flags may not exist yet; fall back to default behavior
        if name.startswith("_") or not hasattr(self, "_flags"):
            return object.__setattr__(self, name, value)
        if name in self.FLAG_FIELDS:
            object.__setattr__(self._flags, name, value)
            # Also keep a shadow attribute for any existing direct reads in older code paths
            return object.__setattr__(self, name, value)
        return object.__setattr__(self, name, value)

    # World containers exposed as properties (stay backward-compatible)
    @property
    def objects(self):
        return self._world.objects

    @objects.setter
    def objects(self, value):
        self._world.objects = value

    @property
    def ways(self):
        return self._world.ways

    @ways.setter
    def ways(self, value):
        self._world.ways = value

    @property
    def places(self):
        return self._world.places

    @places.setter
    def places(self, value):
        self._world.places = value

    def __init__(self, *, llm: "LLMClient | None" = None):
        self.llm = llm
        self._context = ContextBuilder()
        self._world = WorldModel()

        # self.objects = None
        # self.ways = None
        # self.places = None
        # self.web_sessions = {}      # Tracking für aktive Web-Sessions
        # self.active_minigames = {}  # Tracking für laufende Mini-Games
        # self.cmd_q = {}        # Will be populated by WebGameServer class
        self.init_game()

    #
    #  Initialization functions
    #
    def emit_waydefs(self,pl,wy):
        for k,v in pl.items():
            print("     #")
            print(f"     # Place: {k}")
            print("     #\n")
            w = v["ways"]


            if w != None:
                for i in w:
                    if i not in wy:
                        print(f'        "{i}":{{')
                        print(f'               "source":"{k}",')
                        print('               "destination":"",')
                        print('               "text_direction":"",')
                        print('               "obstruction_check":None,')
                        print('               "description":""')
                        print("               },")

    def emit_objdefs(self,pl,ob):
        """ Helper Function: emits object definition and functions so they can be copy-pasted into source code"""
        fnlist = [] # Apply Functions
        rvlist = [] # Reveal Functions
        for k,v in pl.items():
            print("     #")
            print(f"     # Place: {k}")
            print("     #\n")
            w = v["objects"]


            if w:
                for i in w:
                    if i not in ob:
                        print(f'        "{i}":{{')
                        print(f'               "name":"{i}",')
                        print('               "examine":"",  # Text to me emitted when object is examined')
                        print('               "help_text":"", # Text to be emitted when player asks for help with object')
                        print(f'               "ownedby": "{k}",  # Which Player currently owns this item? Default: None')
                        print('               "fixed": False, # False bedeutet: Kann aufgenommen werden')
                        print('               "hidden": False,  # True bedeutet: Das Objekt ist nicht sichtbar')
                        fname = f"{i}_apply_f"
                        fnlist.append(fname)
                        rvname = f"{i}_reveal_f"
                        rvlist.append(rvname)
                        print(f'               "apply_f":{fname} # Funktion, die aufgerufen wird, wenn das Objekt angewandt wird (verb_apply)')
                        print(f'               "reveal_f":{fname} # Funktion, die aufgerufen wird, wenn das Objekt untersucht wird (verb_examine')

                        print("               },")
        print("""#
        # Apply-Functions - are called by verb_apply and perform actions, in an object is applied or applied to another object
        #
        """)
        for n in fnlist:
            if not hasattr(self,n):
                print(f'def {n}(gamestate, player=None, what=None, onwhat=None) -> str:')
                print('     return ""')
                print()
        print("""#
        # Reveal-Functions - are called when an object is examined and by examining it reveals something else, 
        # for example unhides another object or a way or a place
        #
        """)
        for n in rvlist:
            if not hasattr(self,n):
                print(f'def {n}(gamestate, player=None, what=None, onwhat=None) -> str:')
                print('     return ""')
                print()

    def add_player(self,name, npc=False):
        from NPCDogState import NPCDogState
        if npc:
            start_room = self.places["p_geldautomat"]
            self.players.append(NPCDogState(name=name, location=start_room))
        else:
            start_room = self.places["p_start"]
            self.players.append(PlayerState(name,start_room))


    def init_game(self):
        #
        # Wege, die verschlossen sind
        #
        self.players = []
        self.time = 0
        self.debug_mode = False
        #
        # Game State Variables and Flags
        #
        self.schuppentuer=False
        self.leiter = False
        self.hebel = False                 # Warenautomat --> Ubahn
        from random import randint
        self.geheimzahl = f"{randint(1, 9999):04d}"
        # self.geheimzahl = 18513            # Geldautomat - wobei der nur zwischen 0 und 999 akzeptiert
        self.ubahn_in_otherstation = False # Ist unsere U-Bahn in Station 2?
        self.felsen = True                 # Ist der Felsen noch im Weg?
        self.hauptschalter = False         # Ohne Strom geht hier gar nichts
        self.dach = True                   # An Ende hat jemand das Dach weggesprengt
        self.warenautomat_intakt = True    # oder den Warenautomat
        self.geldautomat_intakt = True     # oder den Geldautomat
        self.schuppen_intakt = True        # oder den Schuppen
        self.flasche_voll = True           # Eine Grace Period von 20 Zügen, danach muss der Spieler den Wasserspender entdeckt haben
        self.game_over = False             # Na hoffentlich noch nicht so schnell!
        self.game_won = False              # Wenn true, hat der Spieler das Spiel gewonnen.
        self.zombie_awake = False
        self.zombie_cooperative = False
        self.schalter_kontrollraum = False
        self.schalter_generatorraum = False
        self.schalter_kontrollraum_timer = 0
        self.schalter_generatorraum_timer = 0
        self.umschlag_geheimbotschaft = False
        # Mirror flags into a structured container (GameFlags) for future decoupling
        self._flags = GameFlags(
            schuppentuer=self.schuppentuer,
            leiter=self.leiter,
            hebel=self.hebel,
            geheimzahl=self.geheimzahl,
            wagen_ubahn2=self.ubahn_in_otherstation,
            felsen=self.felsen,
            hauptschalter=self.hauptschalter,
            dach=self.dach,
            warenautomat_intakt=self.warenautomat_intakt,
            geldautomat_intakt=self.geldautomat_intakt,
            schuppen_intakt=self.schuppen_intakt,
            game_over=self.game_over,
            game_won=self.game_won,
            time=self.time,
            debug_mode=self.debug_mode,
            zombie_awake=self.zombie_awake,
            zombie_cooperative=self.zombie_cooperative,
            schalter_kontrollraum=self.schalter_kontrollraum,
            schalter_generatorraum=self.schalter_generatorraum,
            schalter_kontrollraum_timer=self.schalter_kontrollraum_timer,
            schalter_generatorraum_timer=self.schalter_generatorraum_timer,
            umschlag_geheimbotschaft=self.umschlag_geheimbotschaft,
        )
        #self.llm = GeminiInterface()       # Unser Sprachmodell
        # Prefer injected LLM; fallback to local GeminiInterface to avoid module-level import cycles
        if self.llm is None:
            from GeminiInterface import GeminiInterface  # local import prevents import cycles
            self.llm = GeminiInterface()  # Unser Sprachmodell
        self.gamelog = []                  # Wir schneiden alles für das LLM mit

        #self.objects = None
        #self.ways = None
        #self.places = None
        self._world.places = {}
        self._world.ways = {}
        self._world.objects = {}

        #
        # Web Interface
        #
        self.web_sessions = {}      # Tracking für aktive Web-Sessions
        self.active_minigames = {}  # Tracking für laufende Mini-Games
        self.cmd_q = {}        # Will be populated by WebGameServer class

        #
        # Place definitions
        #
        import GameApplyFunctions as af
        import GameTakeFunctions as tf
        import GameRevealFunctions as rf
        import GameObstructionCheckFunctions as ocf
        import PlacePrompts as pp
        import ObjectPrompts as op
        import WayPrompts as wp

        module_map = {
            "GameApplyFunctions": af,
            "GameTakeFunctions": tf,
            "GameRevealFunctions": rf,
            "GameObstructionCheckFunctions": ocf,
            "PlacePrompts": pp,
            "ObjectPrompts": op,
            "WayPrompts": wp,
        }

        # Build the world via WorldLoader (load world.json -> validate -> build).
        from services.world_loader import WorldLoader
        loader = WorldLoader()
        external_defs = loader.load(module_map)
        if external_defs:
            place_defs, way_defs, object_defs = external_defs
            loader.validate(place_defs, way_defs, object_defs)
        else:
            dprint(dl.GAMESTATE,"FATAL: No external definitions. Terminating game ...")
            exit(-1)

        loader.build(self._world, place_defs, way_defs, object_defs)

    #
    # Utility Functions
    #
    def obj_name_from_friendly_name(self, n:str)->str:
        return self._world.obj_name_from_friendly_name(n)

    def place_name_from_friendly_name(self, n:str)->str:
        dprint(dl.GAMESTATE, f"This is place_name_from_friendly_name({n})")
        return self._world.place_name_from_friendly_name(n)

    from typing import List, Optional

    #
    # Find shortest Path between two places
    #
    def find_shortest_path(self, start: Place, goal: Place) -> Optional[List[Way]]:
        return self._world.find_shortest_path(self, start, goal)
    #
    # Verbs to be executed
    #
    def check_game_over_old(self):
        """ Based on current configuration: is the game over?"""
        if self.game_over:
            return True     # Trivial
        pl = next((p for p in self.players if type(p) is PlayerState),None)
        if not pl:
            return True     # No more Players in the game
        #
        # Einige andere Kriterien: wenn das Spiel komplexer wird, könnte diese Routine
        # rech aufwändig werden.
        #
        sprengladung_weg = self.objects.get("o_sprengladung",None) is None

        if sprengladung_weg:
            if self.felsen:
                return True  # Felsen noch da, aber keine Sprengladung mehr

            if not self.schuppen_intakt:
                return True  # Man kann den Warenautomaten ohne den Hebel nicht mehr bewegen

            if not self.geldautomat_intakt:
                return True  # Ich kann keine Dollars mehr ziehen

        return False

    def check_game_over(self):
        """ Based on current configuration: is the game over?"""
        f = self.get_flags()  # <-- zentraler Zugriff auf Flags

        if f.game_over:
            return True  # Trivial

        pl = next((p for p in self.players if type(p) is PlayerState), None)
        if not pl:
            return True  # No more Players in the game

        # Einige andere Kriterien: wenn das Spiel komplexer wird, könnte diese Routine
        # recht aufwändig werden.

        # Kette:
        # Wir testen nur, ob
        # - der Spieler die Kette im Inventar hat , oder
        # - es einen Weg vom Spieler zur Kette gibt, und die Kette sichtbar ist
        # wenn dem so ist, kann das Spiel weitergehen, auch wenn die Sprengladung an einem falschen Ort ist.
        # pl enthält an dieser Stelle den Spieler (s.o.)

        kette = self.objects.get("o_fahrradkette",None)
        if not kette:
            return True     # Die Kette ist aus dem Spiel geflogen - Game over
        if kette in pl.inventory:
            return False    # Player hat Kette bei sich - alles in Ordnung - kein Gamne Over
        if kette.hidden and not f.warenautomat_intakt:
            return True     # Warenautomat gesprengt und Kette nicht auffindbar --> Game Over

        sp = self._world.find_shortest_path(self,pl.location,kette.ownedby) # Tatsächlich zweimal "self"
        if sp is not None and not kette.hidden:
            return False    # Es gibt einen Weg vom Spieler zur Kette und die Kette ist nicht hidden


        sprengladung_weg = self.objects.get("o_sprengladung", None) is None

        if sprengladung_weg:
            if f.felsen:
                return True  # Felsen noch da, aber keine Sprengladung mehr

            if not f.schuppen_intakt:
                return True  # Man kann den Warenautomaten ohne den Hebel nicht mehr bewegen

            if not f.geldautomat_intakt:
                return True  # Ich kann keine Dollars mehr ziehen

            if not "o_solaranlage" in self._world.objects: # Er hat die Solaranlage gesprengt ...
                return True

        return False

    def compile_current_game_context_for_llm_tools(self, pl: 'PlayerState') -> dict:
        return self._context.build_for_llm_tools(self, pl)

    def compile_current_game_context(self, pl: PlayerState):
        return self._context.build(self, pl)

    def get_flags(self) -> GameFlags:
        """Access to the structured flags container (in addition to legacy attributes)."""
        return self._flags

    def verb_execute_json(self, pl: PlayerState, command_dict: dict, session_id=None) -> str:
        """ Instead of a string (see verb_execute) cmd is a dictionary as was returned by the LLM as structured
            return to LLM user input"""
        # self.cur_session_id = session_id
        if "function_call" not in command_dict:
            return "Interner Fehler: Ungültiges Befehlsformat."

        dpprint(dl.GAMESTATE,command_dict)

        func_call = command_dict["function_call"]
        func_name = func_call["name"]
        args = func_call.get("args", {})
        #
        # Python magic
        #

        vtab = {
            "anwenden":(self.verb_apply,2),
            "nimm":(self.verb_take,1),
            "ablegen":(self.verb_drop,1),
            "umsehen":(self.verb_context,0),
            "untersuche": (self.verb_examine,1),
            "hilfe":(self.verb_help,0),
            "gehe":(self.verb_walk,1),
            "toeten": (self.verb_kill,1),
            "angreifen": (self.verb_attack,0),
            "inventory": (self.verb_inventory,0),
            "context": (self.verb_context,0),
            "dogstate": (self.verb_dogstate,0),
            "quit": (self.verb_quit,0),
            "nichts": (self.verb_noop,0),
            #"interagiere": (self.verb_interact,2),
            #"interaktion": (self.verb_interact, 2),
            "zurueckweisen": (self.verb_reject,1),
            "zurückweisen": (self.verb_reject, 1),
            "unbekannt": (self.verb_unknown,0),
            "json_write": (self.verb_json_write,0)
        }
        verb,numargs = vtab.get(func_name,(None,None))
        if verb is None:
            dprint(dl.GAMESTATE, f"verb_execute_json: Unknown verb '{func_name}' — not in vtab")
            return f"Das Kommando '{func_name}' wurde nicht erkannt."
        r=verb(pl,session_id, **args)
        return r




    def verb_unknown(self, pl: PlayerState, session_id=None):
        from pprint import pprint
        print("LLM did not understand input correctly. Current Player atomic command queue:")
        pprint(pl.cmd_q)
        return "nichts"

    def verb_dogstate(self, pl: PlayerState, session_id=None):
        from NPCDogState import NPCDogState
        from pprint import pprint
        dgf = None
        for p in self.players:
            if type(p) is NPCDogState:
                dgf = p
                break
        if not dgf:
            return ("Kein Hund mehr im Spiel!!")
        else:
            pprint(dgf,depth=2)
            return "nichts"



    async def async_verb_interact(self, pl: PlayerState, session_id, who, firstmessage=""):
        #
        # Check if there is a npc named who, and if (s)he is in the same location as pl
        # This verb is called
        #
        import asyncio
        pl_who = next((p for p in self.players if p.name == who), None)
        if not pl_who:
            return f"{who}? Kenne ich nicht"

        if pl_who == pl:
            return "Selbstgespräche werden hier lieber nicht geführt."

        if pl.location != pl_who.location:
            return f"{who} ist nicht hier."

        if session_id in self.web_sessions:
            if "WebDialogs" in self.web_sessions[session_id]:
                wd: object = self.web_sessions[session_id]["WebDialogs"]
                #await wd.do_chat(self, pl, pl_who, firstmessage)
                #asyncio.run(wd.do_chat(self, pl, pl_who, firstmessage))
                await wd.do_chat(self, pl, pl_who, firstmessage)
        return "nichts"


    def verb_apply(self, pl: PlayerState, session_id, what, towhat=None):

        r="Nichts anzuwenden"
        if what is None:
            return r

        found_what = self.obj_name_from_friendly_name(what)
        found_towhat = self.obj_name_from_friendly_name(towhat) if towhat is not None else None
        if found_what:
            o_what = self.objects.get(found_what)
            if not ( o_what in pl.inventory or o_what in pl.location.place_objects):
                return f"Ein/eine {what} gibt es hier nicht."
        else:
            return "Sowas kenne ich nicht"

        if found_towhat:
            o_towhat = self.objects.get(found_towhat)
            if not (o_towhat in pl.inventory or o_towhat in pl.location.place_objects):
                return f"Ein/eine {towhat} gibt es hier nicht."

        if towhat is not None:
            # r = f"apply {what} to {towhat} in this context"
            r=""
            if o_what is not None:
                r = r+ "\n" + o_what.apply_f(self, pl, o_what, o_towhat)
        else:
            # r = f"apply {what} in this context"
            r=""
            if o_what is not None:
                r = r+ "\n"+ o_what.apply_f(self, pl, o_what, None)

        return r

    def verb_take(self, pl: PlayerState, session_id, whato):
        what = self.obj_name_from_friendly_name(whato)
        loc = pl.location
        # obj = loc.place_objects.get(what) - egal
        obj = None
        for o in loc.place_objects:
            if o.name == what:
                obj = o
                break
        if obj == None:
            r= "Sowas gibt es hier nicht."
        else:
            if not obj.fixed:

                pl.add_to_inventory(obj)
                if obj.take_f != None:
                    r= obj.take_f(self,pl)
                else:
                    r= f"Du hast {what} nun bei dir"
            else:
                r = f"Du kannst {what} nicht aufnehmen"
        return r

    def verb_drop(self, pl: PlayerState, session_id, whato):
        what = self.obj_name_from_friendly_name(whato)
        if what is None:
            return "Sowas kenne ich nicht"

        obj = self.objects.get(what)
        if obj == None:
            return "Sowas gibt es in diesem Spiel nicht!"

        if pl.is_in_inventory(obj):
            pl.remove_from_inventory(obj)
            obj.hidden = False
            obj.ownedby = pl.location
            pl.location.place_objects.append(obj)
            r = f'Objekt {what} in/auf/am {pl.location.name} abgelegt'
            return r

        r= f'{what} ist nicht in {pl.name} inventory'

        return r

    def verb_lookaround_old(self, pl: PlayerState, session_id):
        loc = pl.location
        retstr = f"""**Ort: {pl.location.name}**
{pl.location.place_prompt_f(self,pl) if pl.location.place_prompt_f else pl.location.place_prompt}


Am Ort sind folgende Objekte zu sehen:"""
        rs = ""
        for i in pl.location.place_objects:
            if not i.hidden:
                rs = rs+f'\n- {i.callnames[0]} - {i.examine}'
        if rs == "":
            rs="(keine)"
        dogfound = None
        from NPCDogState import NPCDogState
        for d in self.players:
            if type(d) is NPCDogState:
                dogfound = d
        if dogfound and dogfound.location == pl.location:
            print("\n!!!! Da ist ein großer Hund bei dir  !!!!\n")
        can_go = []
        for p in pl.location.ways:
            if p.visible and p.obstruction_check(self) == "Free":
                can_go.append(p.destination)
        if dogfound and dogfound.location in can_go:
            print(f"\n!! Da ist ein großer Hund in deiner Nachbarschaft (bei/beim) {dogfound.location.callnames[0]} !!\n")

        retstr = retstr+rs+"\n\nDu kannst folgende wege gehen:\n"
        loc = pl.location
        for w in loc.ways:
            if w.visible:
                retstr = retstr + f'- {w.destination.callnames[0]} ({w.destination.name})\n'
        return retstr

    def verb_lookaround_llm(self, pl: PlayerState, session_id):

        rval = self.llm.generate_scene_description(self.compile_current_game_context(pl))
        return rval

    def verb_lookaround(self, pl: PlayerState, session_id):
        r=self.llm.narrate(self,pl)
        return r


    def verb_help(self, pl: PlayerState, session_id):
        rval = """
    Du musst Dein Fahrrad reparieren, um rechtzeitig den Umschlag, den Du 
    hoffentlich noch bei dir hast, an sein Ziel zu bringen. Sonst geht die 
    Welt unter. 
    
    Folgende Kommandos kannst du absetzen:
    
    hilfe  ............................ Diese Hilfe
    nichts ............................ Eine Spielrunde abwarten
    quit .............................. Spiel beenden
    
    Ansonsten gib als Freitext das ein, was du tun möchtest 
    
    Beispiele:
    
    "Gehe zum Schuppen und untersuche den Stuhl"
    "Gehe dahin, wo der Hund ist"
    "Nimm die Geheimzahl an dich"
    
    Achtung
    =======
    * Achte auf den Hund! Dieser ist dir nicht wohlgesonnen! Du kannst ihn 
      für einige Runden besänftigen, indem du ihn mit etwas fütterst!
    * Du wirst im Laufe der Zeit Durst bekommen. Suche dir etwas, wo du
      trinken kannst, sonst ist das Spiel zu Ende
    
        """
        return rval

    def verb_walk(self, pl: PlayerState, session_id, direction: str):
        #
        # Player walks into "direction" (either name of way or name of destination)
        #
        # (1) Is there a way from his current location?
        #   (1a) if yes, is there an obstacle in the way?
        #     (1aa) if no --> walk, return success message
        #     (1ab) else --> return failure message (Obstacle in way)
        # (2) return failure message ("There is no path here")
        w_found = None
        direction_found = self.place_name_from_friendly_name(direction)
        w_found = next((w for w in pl.location.ways if w.destination.name==direction_found), None)

        if w_found is None:
            return f"Es existiert kein Weg zum Ort {direction}"
        if not w_found.visible:
            return "Diesen Weg sehe ich hier nicht!"
        ob = w_found.obstruction_check(self)

        if ob != "Free":
            return ob  # If there is an obstacle, function returns string different from "Free"

        #
        # Finally - we can go the way
        #
        pl.location = w_found.destination
        r = f"{pl.name} ist nun hier: {pl.location.callnames[0]} "
        return r

    def verb_examine(self, pl: PlayerState, session_id, what: str):
        #
        # Does an object with that name exist in the users inventory or in the current location?
        # if so, return its examine string, if not, return failure ("No such thing here")
        obj_here = None
        what_found = self.obj_name_from_friendly_name(what)
        retstr = "So etwas gibt es hier nicht, und du hast sowas auch nicht bei dir."
        if what_found is None:
            return retstr

        for i in pl.inventory:
            if i.name == what_found:
                obj_here = i
                retstr = f"Du trägst {i.name} gerade bei dir."
                break
        if obj_here == None:
            retstr = ""
            for i in pl.location.place_objects:
                if i.name == what_found:
                    obj_here = i
                    break
        if obj_here != None:

            #
            # Sometimes examinig one thing reveals another thing
            #
            """
            if what == "o_blumentopf":
                if self.objects["o_schluessel"].hidden:
                    retstr = retstr + "Ein alter Blumentopf - aber warte: **unter dem Blumentopf liegt ein Schlüssel!!!**"
                    self.objects["o_blumentopf"].examine = "Unter diesem Blumentopf hast Du den Schlüssel gefunden"
                    self.objects["o_schluessel"].hidden = False
            elif what == "o_skelett":
                if self.objects["o_geldboerse"].hidden:
                    retstr = retstr + "Oh weh, der sitzt wohl schon länger hier! Ein Skelett, welches einen verschlissenen Anzug trägt. **Im Anzug findest du eine Geldboerse!**"
                    self.objects["o_geldboerse"].hidden = False
                    self.objects["o_skelett"].examine = "Bei diesem Knochenmann hast Du eine Geldbörse gefunden!"
            elif what == "o_geldboerse":
                if self.objects["o_ec_karte"].hidden:
                    self.objects["o_ec_karte"].hidden = False
                    self.objects["o_geldboerse"].examine = "In dieser Geldbörse hast Du eine EC-Karte gefunden"
                    retstr = retstr + "Fein! Hier ist eine EC-Karte! Die passt bestimmt in einen Geldautomaten!"
            elif what == "o_muelleimer":
                if self.objects["o_geheimzahl"].hidden:
                    from random import randint
                    self.geheimzahl = randint(1,9999)
                    self.objects["o_geheimzahl"].hidden = False
                    self.objects["o_geheimzahl"].examine = f"Eine Geheimzahl: {self.geheimzahl:04}"
                    retstr = retstr + f"Im Mülleimer findest Du einen Zettel mit einer Geheimzahl! Die Geheimzahl ist: {self.geheimzahl:04}"
"""
            if self.objects[what_found].reveal_f != None:
                retstr = retstr + self.objects[what_found].reveal_f(self,pl,what_found, None)

            else:
                retstr = retstr + f"{obj_here.examine}"
        else:
            retstr = f'{what_found} - sowas gibt es hier nicht!'
        return retstr

    def verb_llm(self, pl:PlayerState, session_id):
        from pprint import pprint
        from rich.prompt import Prompt
        user_input = ""
        while user_input == "":
            ui = Prompt.ask(f"(llm-test) Was tust du jetzt, {pl.name}? Deine Eingabe")
            if ui != None:
                user_input = ui.strip().lower()
            else:
                user_input = ""
        gi = (self.llm.parse_user_input_to_commands(
            user_input,

            self.compile_current_game_context(pl)
        ))
        pprint(gi)
        return "nichts"

    def verb_kill(self, pl: PlayerState, session_id, whom):
        self.game_over = True
        return f"{pl.name} tötet {whom} in heldischem Kampf"

    def verb_inventory(self, pl: PlayerState, session_id):
        tw_print("**Du trägst bei dir:**")
        for i in pl.get_inventory():
            tw_print(f'- "{i.name}" --> {i.examine}')
        return "nichts"

    def verb_context(self, pl: PlayerState, session_id):
        """ERWEITERTE Kontext-Ausgabe mit Web-Interface Info"""
        from pprint import pprint

        # Bestehende Kontext-Ausgabe
        r = self.compile_current_game_context(pl)
        pprint(r)

        # NEUE Web-Interface Debug-Info
        if self.is_web_interface_active():
            print("\n=== WEB-INTERFACE STATUS ===")
            self.debug_web_status()

    def verb_quit(self, pl: PlayerState, session_id):
        self.game_over  = True
        return f"{pl.name} beendet das Spiel."

    def verb_noop(self, pl: PlayerState, session_id):
        if type(pl) is PlayerState:
            return "Du tust nichts"
        else:
            return ""

    #def verb_interact(self, pl: PlayerState, whom, input):
    #    return f'{pl.name} an {whom}:  "{input}"'

    def verb_reject(self, pl: PlayerState, session_id, why, **kwargs)->str:
        """ LLM rejects to do something because it did not understand user input and provides explanation in "why" """
        return f'***Nachricht von der Spielleitung:*** {why}'


    def verb_attack(self, pl: PlayerState, session_id, whom="")->str:
        """ Player attacks dog which needs to be in the same place as Player"""
        from NPCDogState import NPCDogState
        dog = next(d for d in self.players if type(d) is NPCDogState)
        #dog = None
        #for d in self.players:
        #    if type(d) is NPCDogState:
        #        dog = d
        #        break
        if dog is None:
            return "Es gibt gar keinen Hund mehr im Spiel"

        if dog.location != pl.location:
            return "Da ist gar kein Hund bei dir, den Du angreifen könntest"

        else:
            r = dog.gets_attacked(self, pl)
            return ""
            #return f"(Angriff auf den Hund abgeschlossen)"

    def verb_json_write(self,pl:PlayerState, session_id) -> str:
        """
        Write structures as JSON
        :param pl:
        :return:
        """
        from json import dump
        # Writing to a JSON file with skipkeys=True
        with open("output.json", "w") as outfile:
            json.dump(self.places, outfile, skipkeys=True)


    # Zusätzlich: Neuer Befehl für Layout-Wechsel
    def verb_layout(gs, pl: PlayerState, session_id) -> str:
        """Wechsle Layout-Modus"""
        # Diese Funktion würde in GameState hinzugefügt
        return "layout_toggle"  # Spezieller Return-Code

    #
    # Additional code for web based mini games
    #

    from WebDialogs import WebDialogs

    def register_web_session(self, session_id, websocket=None):
        """Registriere eine neue Web-Session"""
        from WebDialogs import WebDialogs

        # Ensure per-session command queue exists
        if session_id not in self.cmd_q:
            self.cmd_q[session_id] = []

        sess = {
            'websocket': websocket,
            'active': True,
            'minigame_active': False,
            'created_at': self.time,
            'WebDialogs': WebDialogs(websocket, session_id),
            # Added fields expected by web_backend_server
            'type': 'real',
            'game': self,
            'cmd_q': self.cmd_q[session_id],
        }
        self.web_sessions[session_id] = sess
        return sess


    def unregister_web_session(self, session_id):
        """Entferne eine Web-Session"""
        if session_id in self.web_sessions:
            del self.web_sessions[session_id]
        if session_id in self.active_minigames:
            del self.active_minigames[session_id]

    def is_web_interface_active(self):
        """Prüfe ob mindestens eine Web-Session aktiv ist"""
        return len(self.web_sessions) > 0

    def start_minigame_session(self, session_id, game_type, player):
        """Starte eine Mini-Game Session"""
        self.active_minigames[session_id] = {
            'game_type': game_type,
            'player': player,
            'started_at': self.time,
            'status': 'active'
        }
        if session_id in self.web_sessions:
            self.web_sessions[session_id]['minigame_active'] = True

    def complete_minigame_session(self, session_id, result):
        """Beende eine Mini-Game Session"""
        if session_id in self.active_minigames:
            from NPCDogState import NPCDogState, DogFight

            result_map = {
                'WON': DogFight.WON,
                'LOST': DogFight.LOST,
                'TIE': DogFight.TIE
            }

            dog_result = result_map.get(result, DogFight.TIE)
            dog = next((p for p in self.players if isinstance(p, NPCDogState)), None)
            if dog and hasattr(dog, 'set_fight_result'):
                dog.set_fight_result(dog_result)

            del self.active_minigames[session_id]
            if session_id in self.web_sessions:
                self.web_sessions[session_id]['minigame_active'] = False

    def debug_web_status(self):
        """
        Debug-Ausgabe für Web-Interface Status
        """
        from Utils import dprint, dl

        dprint(dl.GAMESTATE, f"🌐 Web-Sessions: {len(self.web_sessions)}")
        for session_id, info in self.web_sessions.items():
            dprint(dl.GAMESTATE, f"  - {session_id}: active={info['active']}, minigame={info['minigame_active']}")

        dprint(dl.GAMESTATE, f"🎮 Active Mini-Games: {len(self.active_minigames)}")
        for session_id, info in self.active_minigames.items():
            dprint(dl.GAMESTATE, f"  - {session_id}: {info['game_type']} ({info['status']})")

    def get_session_id_for_player(self, player: PlayerState) -> str:
        if hasattr(self, 'web_sessions'):
            for sid, ws in self.web_sessions.items():
                if hasattr(player, "session_id") and player.session_id == sid:
                    return sid
        return None

