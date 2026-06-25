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
from game_verbs import GameVerbsMixin
from game_turn import GameTurnMixin


class GameState(GameVerbsMixin, GameTurnMixin):

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

