from __future__ import annotations
from Place import Place
from Way import Way
from typing import Dict, List
from PlayerState import PlayerState
from GameObject import GameObject
from typing import Any

#
# Maintains the state from the game perspective. There are player states as well
#

from typing import Callable

def make_obstruction_check(locked: bool) -> Callable[['GameState'], bool]:
    return lambda state: locked

class GameState:
    def __init__(self, room_definitions, way_definitions, object_definitions,player_names):
        self.places: Dict[str, Place] = self._init_places(room_definitions)
        self.ways: List[Way] = self._init_ways(way_definitions)
        self.objects: List[GameObject] = self._init_objects(object_definitions)
        self.players: List[PlayerState] = self._init_players(player_names)
        self.time = 0
        self.debug_mode = False

    def _init_places(self, defs) -> Dict[str, Place]:
        rooms = {}

        return rooms

    def _init_ways(self, ways_data: List[Dict[str, Any]]) -> List[Way]:
        ways: List[Way] = []

            #ways.append(way)
            #source_room.ways.append(way)
        return ways

    def _init_players(self, names) -> List[PlayerState]:
        return [PlayerState(location=self.places["halle"]) for name in names]

    def _init_objects(self, objects_data: List[Dict[str, Any]]) -> List[GameObject]:
        objects: List[GameObject] = []

        return objects

    @classmethod
    def from_definitions(cls, place_defs, way_defs, object_defs, player_names):
        # Factory-Methode zur Initialisierung eines vollständigen GameState
        instance = cls.__new__(cls)

        #instance.objects = instance._init_objects(object_defs)
        instance.places = instance._init_places(place_defs)
        #instance.ways = instance._init_ways(way_defs)

        #instance.players = instance._init_players(player_names)

        instance.time = 0
        instance.debug_mode = False
        return instance


def emit_waydefs(pl,wy):
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

def emit_objdefs(pl,ob):
    fnlist = []
    for k,v in pl.items():
        print("     #")
        print(f"     # Place: {k}")
        print("     #\n")
        w = v["objects"]


        if w != None:
            for i in w:
                if i not in ob:
                    print(f'        "{i}":{{')
                    print(f'               "name":"{i}",')
                    print('               "examine":"",  # Text to me emitted when object is examined')
                    print('               "help_text":"", # Text to be emitted when player asks for help with object')
                    print('               "ownedby": None,  # Which Player currently owns this item? Default: None')
                    print('               "fixed": False, # False bedeutet: Kann aufgenommen werden')
                    print('               "hidden": False,  # True bedeutet: Das Objekt ist nicht sichtbar')
                    fname = f"{i}_apply_f"
                    fnlist.append(fname)
                    print(f'               "apply_f":{fname}')
                    print("               },")
    print()
    for n in fnlist:
        print(f'def {n}(gamestate, player=None, onwhat=None) -> str:')
        print('     pass')
        print()

def init_game():
    #
    # Place definitions
    #

    place_defs = {
        "p_start": {
            "description": "Ein unbenannter Ort an einer staubigen, monotonen Strasse durch eine heiße Wüste",
            "place_prompt": """
                To be done
            """,
            "ways": ["w_start_warenautomat","w_start_geldautomat", "w_start_schuppen"],
            "objects": [""]
        },
        "p_warenautomat": {
            "description": "Hier ist ein Warenautomat, an dem man Fahrradteile kaufen kann",
            "place_prompt": """
            To be done
        """,
            "ways": ["w_warenautomat_start", "w_warenautomat_geldautomat","w_warenautomat_schuppen","w_warenautomat_ubahn"],
            "objects": ["o_warenautomat"]
        },
        "p_ubahn": {
            "description": "Eine U-Bahn-Station",
            "place_prompt": """
        To be done
    """,
            "ways": ["w_ubahn_warenautomat", "w_ubahn_wagen"],
            "objects": ["o_muelleimer", "o_salami", "o_geheimzahl"]
        },
        "p_wagen": {
            "description": "Im U-Bahn-Wagen",
            "place_prompt": """
        To be done
    """,
            "ways": ["w_wagen_ubahn", "w_wagen_ubahn2"],
            "objects": ["o_tuerschliesser"]
        },
        "p_ubahn2": {
            "description": "Eine zweite U-Bahn-Station",
            "place_prompt": """
        To be done
    """,
            "ways": ["w_ubahn2_wagen"],
            "objects": ["o_pizzaautomat", "o_geld_lire", "o_pizza"]
        },
        "p_geldautomat": {
            "description": "Hier ist ein Geldautomat, an dem man Bargeld bekommen kann",
            "place_prompt": """
        To be done
    """,
            "ways": ["w_geldautomat_start", "w_geldautomat_warenautomat", "w_geldautomat_schuppen"],
            "objects": ["o_geldautomat", "o_geld_dollar"]
        },
        "p_schuppen": {
            "description": "Hier ist ein alter Holzschuppen",
            "place_prompt": """
        To be done
    """,
            "ways": ["w_schuppen_start", "w_schuppen_warenautomat", "w_schuppen_geldautomat","w_schuppen_innen","w_schuppen_dach"],
            "objects": ["o_schuppen","o_blumentopf","o_schluessel", "o_stuhl", "o_schrott"]
        },
        "p_dach": {
            "description": "Das Dach des Holzschuppens",
            "place_prompt": """
        To be done
    """,
            "ways": ["w_dach_schuppen"],
            "objects": ["o_hebel"]
        },
        "p_innen": {
            "description": "Das Dach des Holzschuppens",
            "place_prompt": """
        To be done
    """,
            "ways": ["w_innen_schuppen"],
            "objects": ["o_leiter", "o_skelett", "o_geldboerse", "o_ec_karte", "o_pinsel", "o_farbeimer"]
        },
    }

    way_defs = {
        #
        # Place: p_start
        #

        "w_start_warenautomat": {
            "source": "p_start",
            "destination": "",
            "text_direction": "",
            "obstruction_check": None,
            "description": ""
        },
        "w_start_geldautomat": {
            "source": "p_start",
            "destination": "",
            "text_direction": "",
            "obstruction_check": None,
            "description": ""
        },
        "w_start_schuppen": {
            "source": "p_start",
            "destination": "",
            "text_direction": "",
            "obstruction_check": None,
            "description": ""
        },
        #
        # Place: p_warenautomat
        #

        "w_warenautomat_start": {
            "source": "p_warenautomat",
            "destination": "",
            "text_direction": "",
            "obstruction_check": None,
            "description": ""
        },
        "w_warenautomat_geldautomat": {
            "source": "p_warenautomat",
            "destination": "",
            "text_direction": "",
            "obstruction_check": None,
            "description": ""
        },
        "w_warenautomat_schuppen": {
            "source": "p_warenautomat",
            "destination": "",
            "text_direction": "",
            "obstruction_check": None,
            "description": ""
        },
        "w_warenautomat_ubahn": {
            "source": "p_warenautomat",
            "destination": "",
            "text_direction": "",
            "obstruction_check": None,
            "description": ""
        },
        #
        # Place: p_ubahn
        #

        "w_ubahn_warenautomat": {
            "source": "p_ubahn",
            "destination": "",
            "text_direction": "",
            "obstruction_check": None,
            "description": ""
        },
        "w_ubahn_wagen": {
            "source": "p_ubahn",
            "destination": "",
            "text_direction": "",
            "obstruction_check": None,
            "description": ""
        },
        #
        # Place: p_wagen
        #

        "w_wagen_ubahn": {
            "source": "p_wagen",
            "destination": "",
            "text_direction": "",
            "obstruction_check": None,
            "description": ""
        },
        "w_wagen_ubahn2": {
            "source": "p_wagen",
            "destination": "",
            "text_direction": "",
            "obstruction_check": None,
            "description": ""
        },
        #
        # Place: p_ubahn2
        #

        "w_ubahn2_wagen": {
            "source": "p_ubahn2",
            "destination": "",
            "text_direction": "",
            "obstruction_check": None,
            "description": ""
        },
        #
        # Place: p_geldautomat
        #

        "w_geldautomat_start": {
            "source": "p_geldautomat",
            "destination": "",
            "text_direction": "",
            "obstruction_check": None,
            "description": ""
        },
        "w_geldautomat_warenautomat": {
            "source": "p_geldautomat",
            "destination": "",
            "text_direction": "",
            "obstruction_check": None,
            "description": ""
        },
        "w_geldautomat_schuppen": {
            "source": "p_geldautomat",
            "destination": "",
            "text_direction": "",
            "obstruction_check": None,
            "description": ""
        },
        #
        # Place: p_schuppen
        #

        "w_schuppen_start": {
            "source": "p_schuppen",
            "destination": "",
            "text_direction": "",
            "obstruction_check": None,
            "description": ""
        },
        "w_schuppen_warenautomat": {
            "source": "p_schuppen",
            "destination": "",
            "text_direction": "",
            "obstruction_check": None,
            "description": ""
        },
        "w_schuppen_geldautomat": {
            "source": "p_schuppen",
            "destination": "",
            "text_direction": "",
            "obstruction_check": None,
            "description": ""
        },
        "w_schuppen_innen": {
            "source": "p_schuppen",
            "destination": "",
            "text_direction": "",
            "obstruction_check": None,
            "description": ""
        },
        "w_schuppen_dach": {
            "source": "p_schuppen",
            "destination": "",
            "text_direction": "",
            "obstruction_check": None,
            "description": ""
        },
        #
        # Place: p_dach
        #

        "w_dach_schuppen": {
            "source": "p_dach",
            "destination": "",
            "text_direction": "",
            "obstruction_check": None,
            "description": ""
        },
        #
        # Place: p_innen
        #

        "w_innen_schuppen": {
            "source": "p_innen",
            "destination": "",
            "text_direction": "",
            "obstruction_check": None,
            "description": ""
        },

    }

    object_defs = {
        #
        # Place: p_warenautomat
        #

        "o_warenautomat": {
            "name": "o_warenautomat",
            "examine": "",  # Text to me emitted when object is examined
            "help_text": "",  # Text to be emitted when player asks for help with object
            "ownedby": None,  # Which Player currently owns this item? Default: None
            "fixed": False,  # False bedeutet: Kann aufgenommen werden
            "hidden": False,  # True bedeutet: Das Objekt ist nicht sichtbar
            "apply_f": o_warenautomat_apply_f
        },
        #
        # Place: p_ubahn
        #

        "o_muelleimer": {
            "name": "o_muelleimer",
            "examine": "",  # Text to me emitted when object is examined
            "help_text": "",  # Text to be emitted when player asks for help with object
            "ownedby": None,  # Which Player currently owns this item? Default: None
            "fixed": False,  # False bedeutet: Kann aufgenommen werden
            "hidden": False,  # True bedeutet: Das Objekt ist nicht sichtbar
            "apply_f": o_muelleimer_apply_f
        },
        "o_salami": {
            "name": "o_salami",
            "examine": "",  # Text to me emitted when object is examined
            "help_text": "",  # Text to be emitted when player asks for help with object
            "ownedby": None,  # Which Player currently owns this item? Default: None
            "fixed": False,  # False bedeutet: Kann aufgenommen werden
            "hidden": False,  # True bedeutet: Das Objekt ist nicht sichtbar
            "apply_f": o_salami_apply_f
        },
        "o_geheimzahl": {
            "name": "o_geheimzahl",
            "examine": "",  # Text to me emitted when object is examined
            "help_text": "",  # Text to be emitted when player asks for help with object
            "ownedby": None,  # Which Player currently owns this item? Default: None
            "fixed": False,  # False bedeutet: Kann aufgenommen werden
            "hidden": False,  # True bedeutet: Das Objekt ist nicht sichtbar
            "apply_f": o_geheimzahl_apply_f
        },
        #
        # Place: p_wagen
        #

        "o_tuerschliesser": {
            "name": "o_tuerschliesser",
            "examine": "",  # Text to me emitted when object is examined
            "help_text": "",  # Text to be emitted when player asks for help with object
            "ownedby": None,  # Which Player currently owns this item? Default: None
            "fixed": False,  # False bedeutet: Kann aufgenommen werden
            "hidden": False,  # True bedeutet: Das Objekt ist nicht sichtbar
            "apply_f": o_tuerschliesser_apply_f
        },
        #
        # Place: p_ubahn2
        #

        "o_pizzaautomat": {
            "name": "o_pizzaautomat",
            "examine": "",  # Text to me emitted when object is examined
            "help_text": "",  # Text to be emitted when player asks for help with object
            "ownedby": None,  # Which Player currently owns this item? Default: None
            "fixed": False,  # False bedeutet: Kann aufgenommen werden
            "hidden": False,  # True bedeutet: Das Objekt ist nicht sichtbar
            "apply_f": o_pizzaautomat_apply_f
        },
        "o_geld_lire": {
            "name": "o_geld_lire",
            "examine": "",  # Text to me emitted when object is examined
            "help_text": "",  # Text to be emitted when player asks for help with object
            "ownedby": None,  # Which Player currently owns this item? Default: None
            "fixed": False,  # False bedeutet: Kann aufgenommen werden
            "hidden": False,  # True bedeutet: Das Objekt ist nicht sichtbar
            "apply_f": o_geld_lire_apply_f
        },
        "o_pizza": {
            "name": "o_pizza",
            "examine": "",  # Text to me emitted when object is examined
            "help_text": "",  # Text to be emitted when player asks for help with object
            "ownedby": None,  # Which Player currently owns this item? Default: None
            "fixed": False,  # False bedeutet: Kann aufgenommen werden
            "hidden": False,  # True bedeutet: Das Objekt ist nicht sichtbar
            "apply_f": o_pizza_apply_f
        },
        #
        # Place: p_geldautomat
        #

        "o_geldautomat": {
            "name": "o_geldautomat",
            "examine": "",  # Text to me emitted when object is examined
            "help_text": "",  # Text to be emitted when player asks for help with object
            "ownedby": None,  # Which Player currently owns this item? Default: None
            "fixed": False,  # False bedeutet: Kann aufgenommen werden
            "hidden": False,  # True bedeutet: Das Objekt ist nicht sichtbar
            "apply_f": o_geldautomat_apply_f
        },
        "o_geld_dollar": {
            "name": "o_geld_dollar",
            "examine": "",  # Text to me emitted when object is examined
            "help_text": "",  # Text to be emitted when player asks for help with object
            "ownedby": None,  # Which Player currently owns this item? Default: None
            "fixed": False,  # False bedeutet: Kann aufgenommen werden
            "hidden": False,  # True bedeutet: Das Objekt ist nicht sichtbar
            "apply_f": o_geld_dollar_apply_f
        },
        #
        # Place: p_schuppen
        #

        "o_schuppen": {
            "name": "o_schuppen",
            "examine": "",  # Text to me emitted when object is examined
            "help_text": "",  # Text to be emitted when player asks for help with object
            "ownedby": None,  # Which Player currently owns this item? Default: None
            "fixed": False,  # False bedeutet: Kann aufgenommen werden
            "hidden": False,  # True bedeutet: Das Objekt ist nicht sichtbar
            "apply_f": o_schuppen_apply_f
        },
        "o_blumentopf": {
            "name": "o_blumentopf",
            "examine": "",  # Text to me emitted when object is examined
            "help_text": "",  # Text to be emitted when player asks for help with object
            "ownedby": None,  # Which Player currently owns this item? Default: None
            "fixed": False,  # False bedeutet: Kann aufgenommen werden
            "hidden": False,  # True bedeutet: Das Objekt ist nicht sichtbar
            "apply_f": o_blumentopf_apply_f
        },
        "o_schluessel": {
            "name": "o_schluessel",
            "examine": "",  # Text to me emitted when object is examined
            "help_text": "",  # Text to be emitted when player asks for help with object
            "ownedby": None,  # Which Player currently owns this item? Default: None
            "fixed": False,  # False bedeutet: Kann aufgenommen werden
            "hidden": False,  # True bedeutet: Das Objekt ist nicht sichtbar
            "apply_f": o_schluessel_apply_f
        },
        "o_stuhl": {
            "name": "o_stuhl",
            "examine": "",  # Text to me emitted when object is examined
            "help_text": "",  # Text to be emitted when player asks for help with object
            "ownedby": None,  # Which Player currently owns this item? Default: None
            "fixed": False,  # False bedeutet: Kann aufgenommen werden
            "hidden": False,  # True bedeutet: Das Objekt ist nicht sichtbar
            "apply_f": o_stuhl_apply_f
        },
        "o_schrott": {
            "name": "o_schrott",
            "examine": "",  # Text to me emitted when object is examined
            "help_text": "",  # Text to be emitted when player asks for help with object
            "ownedby": None,  # Which Player currently owns this item? Default: None
            "fixed": False,  # False bedeutet: Kann aufgenommen werden
            "hidden": False,  # True bedeutet: Das Objekt ist nicht sichtbar
            "apply_f": o_schrott_apply_f
        },
        #
        # Place: p_dach
        #

        "o_hebel": {
            "name": "o_hebel",
            "examine": "",  # Text to me emitted when object is examined
            "help_text": "",  # Text to be emitted when player asks for help with object
            "ownedby": None,  # Which Player currently owns this item? Default: None
            "fixed": False,  # False bedeutet: Kann aufgenommen werden
            "hidden": False,  # True bedeutet: Das Objekt ist nicht sichtbar
            "apply_f": o_hebel_apply_f
        },
        #
        # Place: p_innen
        #

        "o_leiter": {
            "name": "o_leiter",
            "examine": "",  # Text to me emitted when object is examined
            "help_text": "",  # Text to be emitted when player asks for help with object
            "ownedby": None,  # Which Player currently owns this item? Default: None
            "fixed": False,  # False bedeutet: Kann aufgenommen werden
            "hidden": False,  # True bedeutet: Das Objekt ist nicht sichtbar
            "apply_f": o_leiter_apply_f
        },
        "o_skelett": {
            "name": "o_skelett",
            "examine": "",  # Text to me emitted when object is examined
            "help_text": "",  # Text to be emitted when player asks for help with object
            "ownedby": None,  # Which Player currently owns this item? Default: None
            "fixed": False,  # False bedeutet: Kann aufgenommen werden
            "hidden": False,  # True bedeutet: Das Objekt ist nicht sichtbar
            "apply_f": o_skelett_apply_f
        },
        "o_geldboerse": {
            "name": "o_geldboerse",
            "examine": "",  # Text to me emitted when object is examined
            "help_text": "",  # Text to be emitted when player asks for help with object
            "ownedby": None,  # Which Player currently owns this item? Default: None
            "fixed": False,  # False bedeutet: Kann aufgenommen werden
            "hidden": False,  # True bedeutet: Das Objekt ist nicht sichtbar
            "apply_f": o_geldboerse_apply_f
        },
        "o_ec_karte": {
            "name": "o_ec_karte",
            "examine": "",  # Text to me emitted when object is examined
            "help_text": "",  # Text to be emitted when player asks for help with object
            "ownedby": None,  # Which Player currently owns this item? Default: None
            "fixed": False,  # False bedeutet: Kann aufgenommen werden
            "hidden": False,  # True bedeutet: Das Objekt ist nicht sichtbar
            "apply_f": o_ec_karte_apply_f
        },
        "o_pinsel": {
            "name": "o_pinsel",
            "examine": "",  # Text to me emitted when object is examined
            "help_text": "",  # Text to be emitted when player asks for help with object
            "ownedby": None,  # Which Player currently owns this item? Default: None
            "fixed": False,  # False bedeutet: Kann aufgenommen werden
            "hidden": False,  # True bedeutet: Das Objekt ist nicht sichtbar
            "apply_f": o_pinsel_apply_f
        },
        "o_farbeimer": {
            "name": "o_farbeimer",
            "examine": "",  # Text to me emitted when object is examined
            "help_text": "",  # Text to be emitted when player asks for help with object
            "ownedby": None,  # Which Player currently owns this item? Default: None
            "fixed": False,  # False bedeutet: Kann aufgenommen werden
            "hidden": False,  # True bedeutet: Das Objekt ist nicht sichtbar
            "apply_f": o_farbeimer_apply_f
        },

    }

    player_names = ["Spieler1"]
    emit_waydefs(place_defs, way_defs)
    emit_objdefs(place_defs, object_defs)

    return GameState.from_definitions(place_defs, way_defs, object_defs, player_names)
#
# Apply-Functions for Objects
#

def o_warenautomat_apply_f(gamestate, player=None, onwhat=None) -> str:
    pass


def o_muelleimer_apply_f(gamestate, player=None, onwhat=None) -> str:
    pass


def o_salami_apply_f(gamestate, player=None, onwhat=None) -> str:
    pass


def o_geheimzahl_apply_f(gamestate, player=None, onwhat=None) -> str:
    pass


def o_tuerschliesser_apply_f(gamestate, player=None, onwhat=None) -> str:
    pass


def o_pizzaautomat_apply_f(gamestate, player=None, onwhat=None) -> str:
    pass


def o_geld_lire_apply_f(gamestate, player=None, onwhat=None) -> str:
    pass


def o_pizza_apply_f(gamestate, player=None, onwhat=None) -> str:
    pass


def o_geldautomat_apply_f(gamestate, player=None, onwhat=None) -> str:
    pass


def o_geld_dollar_apply_f(gamestate, player=None, onwhat=None) -> str:
    pass


def o_schuppen_apply_f(gamestate, player=None, onwhat=None) -> str:
    pass


def o_blumentopf_apply_f(gamestate, player=None, onwhat=None) -> str:
    pass


def o_schluessel_apply_f(gamestate, player=None, onwhat=None) -> str:
    pass


def o_stuhl_apply_f(gamestate, player=None, onwhat=None) -> str:
    pass


def o_schrott_apply_f(gamestate, player=None, onwhat=None) -> str:
    pass


def o_hebel_apply_f(gamestate, player=None, onwhat=None) -> str:
    pass


def o_leiter_apply_f(gamestate, player=None, onwhat=None) -> str:
    pass


def o_skelett_apply_f(gamestate, player=None, onwhat=None) -> str:
    pass


def o_geldboerse_apply_f(gamestate, player=None, onwhat=None) -> str:
    pass


def o_ec_karte_apply_f(gamestate, player=None, onwhat=None) -> str:
    pass


def o_pinsel_apply_f(gamestate, player=None, onwhat=None) -> str:
    pass


def o_farbeimer_apply_f(gamestate, player=None, onwhat=None) -> str:
    pass


init_game()