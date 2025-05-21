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

    def __init__(self):
        self.init_game()

    def _init_places(self, defs) -> Dict[str, Place]:
        places = {}

        for place_name, place_data in defs.items():
            place = Place(
                name=place_name,
                description=place_data["description"],
                place_prompt=place_data["place_prompt"],
                ways=[],  # Wird später in _init_ways gefüllt
                place_objects=[]  # Wird später in _init_objects gefüllt
            )
            places[place_name] = place

        return places

    def _init_ways(self, defs: dict, places: Dict[str, Place]) -> List[Way]:
        ways = []

        for way_name, way_data in defs.items():
            source_name = way_data["source"]
            dest_name = way_data["destination"]

            source_place = places[source_name]
            dest_place = places[dest_name] if dest_name else None

            obstruction = way_data["obstruction_check"]
            if obstruction is None:
                obstruction = lambda state: False  # Default-Funktion

            way = Way(
                name=way_name,
                source=source_place,
                destination=dest_place,
                text_direction=way_data["text_direction"],
                obstruction_check=obstruction,
                description=way_data["description"]
            )

            # Im source-Place registrieren
            source_place.ways.append(way)

            ways.append(way)

        return ways

    def _init_objects(self, defs: dict, places: Dict[str, Place]) -> List[GameObject]:
        objects = []

        for obj_name, obj_data in defs.items():
            obj = GameObject(
                name=obj_data["name"],
                examine=obj_data["examine"],
                help_text=obj_data.get("help_text", ""),
                fixed=obj_data.get("fixed", False),
                hidden=obj_data.get("hidden", False)
            )
            ownedby_str = obj_data.get("ownedby", None)
            if ownedby_str in places:
                obj.ownedby = places[ownedby_str]
            else:
                obj.ownedby = None
            # obj.ownedby = obj_data.get("ownedby", None)
            obj.apply_f = obj_data.get("apply_f", None)

            # Füge das Objekt dem passenden Place hinzu
            for place in places.values():
                if obj_name in place.name:
                    place.place_objects.append(obj)
                    break

            objects.append(obj)

        return objects

    @classmethod
    def old_from_definitions(cls, place_defs, way_defs, object_defs, player_names):
        # Factory-Methode zur Initialisierung eines vollständigen GameState
        instance = cls.__new__(cls)


        instance.places = instance._init_places(place_defs)
        instance.ways = instance._init_ways(way_defs, instance.places)
        instance.objects = instance._init_objects(object_defs, instance.places)

        #instance.players = instance._init_players(player_names)

        instance.time = 0
        instance.debug_mode = False
        return instance

    def from_definitions(self,place_defs, way_defs, object_defs, player_names):
        self.places = self._init_places(place_defs)
        self.ways = self._init_ways(way_defs, self.places)
        self.objects = self._init_objects(object_defs, self.places)
        self.players = []
        self.time = 0
        self.debug_mode = False

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
                        print(f'               "ownedby": "{k}",  # Which Player currently owns this item? Default: None')
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

    def add_player(self,name):
        start_room = self.places["p_start"]
        self.players.append(PlayerState(name,start_room))


    def init_game(self):
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
            "o_umschlag":{
                "name": "o_umschlag",
                "examine": "Ein versiegelter Briefumschlag",
                "help_text": "Dieser Umschlag muss sein Ziel erreichen, sonst geht die Welt unter!",
                "ownedby": "",
                "fixed": False,
                "hidden": True,
                "apply_f": o_umschlag_apply_f
            },
            "o_warenautomat": {
                "name": "o_warenautomat",
                "examine": "",  # Text to me emitted when object is examined
                "help_text": "",  # Text to be emitted when player asks for help with object
                "ownedby": "p_warenautomat",  # Which Player currently owns this item? Default: None
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
                "ownedby": "p_ubahn",  # Which Player currently owns this item? Default: None
                "fixed": False,  # False bedeutet: Kann aufgenommen werden
                "hidden": False,  # True bedeutet: Das Objekt ist nicht sichtbar
                "apply_f": o_muelleimer_apply_f
            },
            "o_salami": {
                "name": "o_salami",
                "examine": "",  # Text to me emitted when object is examined
                "help_text": "",  # Text to be emitted when player asks for help with object
                "ownedby": "p_ubahn",  # Which Player currently owns this item? Default: None
                "fixed": False,  # False bedeutet: Kann aufgenommen werden
                "hidden": False,  # True bedeutet: Das Objekt ist nicht sichtbar
                "apply_f": o_salami_apply_f
            },
            "o_geheimzahl": {
                "name": "o_geheimzahl",
                "examine": "",  # Text to me emitted when object is examined
                "help_text": "",  # Text to be emitted when player asks for help with object
                "ownedby": "p_ubahn",  # Which Player currently owns this item? Default: None
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
                "ownedby": "p_wagen",  # Which Player currently owns this item? Default: None
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
                "ownedby": "p_ubahn2",  # Which Player currently owns this item? Default: None
                "fixed": False,  # False bedeutet: Kann aufgenommen werden
                "hidden": False,  # True bedeutet: Das Objekt ist nicht sichtbar
                "apply_f": o_pizzaautomat_apply_f
            },
            "o_geld_lire": {
                "name": "o_geld_lire",
                "examine": "",  # Text to me emitted when object is examined
                "help_text": "",  # Text to be emitted when player asks for help with object
                "ownedby": "p_ubahn2",  # Which Player currently owns this item? Default: None
                "fixed": False,  # False bedeutet: Kann aufgenommen werden
                "hidden": False,  # True bedeutet: Das Objekt ist nicht sichtbar
                "apply_f": o_geld_lire_apply_f
            },
            "o_pizza": {
                "name": "o_pizza",
                "examine": "",  # Text to me emitted when object is examined
                "help_text": "",  # Text to be emitted when player asks for help with object
                "ownedby": "p_ubahn2",  # Which Player currently owns this item? Default: None
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
                "ownedby": "p_geldautomat",  # Which Player currently owns this item? Default: None
                "fixed": False,  # False bedeutet: Kann aufgenommen werden
                "hidden": False,  # True bedeutet: Das Objekt ist nicht sichtbar
                "apply_f": o_geldautomat_apply_f
            },
            "o_geld_dollar": {
                "name": "o_geld_dollar",
                "examine": "",  # Text to me emitted when object is examined
                "help_text": "",  # Text to be emitted when player asks for help with object
                "ownedby": "p_geldautomat",  # Which Player currently owns this item? Default: None
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
                "ownedby": "p_schuppen",  # Which Player currently owns this item? Default: None
                "fixed": False,  # False bedeutet: Kann aufgenommen werden
                "hidden": False,  # True bedeutet: Das Objekt ist nicht sichtbar
                "apply_f": o_schuppen_apply_f
            },
            "o_blumentopf": {
                "name": "o_blumentopf",
                "examine": "",  # Text to me emitted when object is examined
                "help_text": "",  # Text to be emitted when player asks for help with object
                "ownedby": "p_schuppen",  # Which Player currently owns this item? Default: None
                "fixed": False,  # False bedeutet: Kann aufgenommen werden
                "hidden": False,  # True bedeutet: Das Objekt ist nicht sichtbar
                "apply_f": o_blumentopf_apply_f
            },
            "o_schluessel": {
                "name": "o_schluessel",
                "examine": "",  # Text to me emitted when object is examined
                "help_text": "",  # Text to be emitted when player asks for help with object
                "ownedby": "p_schuppen",  # Which Player currently owns this item? Default: None
                "fixed": False,  # False bedeutet: Kann aufgenommen werden
                "hidden": False,  # True bedeutet: Das Objekt ist nicht sichtbar
                "apply_f": o_schluessel_apply_f
            },
            "o_stuhl": {
                "name": "o_stuhl",
                "examine": "",  # Text to me emitted when object is examined
                "help_text": "",  # Text to be emitted when player asks for help with object
                "ownedby": "p_schuppen",  # Which Player currently owns this item? Default: None
                "fixed": False,  # False bedeutet: Kann aufgenommen werden
                "hidden": False,  # True bedeutet: Das Objekt ist nicht sichtbar
                "apply_f": o_stuhl_apply_f
            },
            "o_schrott": {
                "name": "o_schrott",
                "examine": "",  # Text to me emitted when object is examined
                "help_text": "",  # Text to be emitted when player asks for help with object
                "ownedby": "p_schuppen",  # Which Player currently owns this item? Default: None
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
                "ownedby": "p_dach",  # Which Player currently owns this item? Default: None
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
                "ownedby": "p_innen",  # Which Player currently owns this item? Default: None
                "fixed": False,  # False bedeutet: Kann aufgenommen werden
                "hidden": False,  # True bedeutet: Das Objekt ist nicht sichtbar
                "apply_f": o_leiter_apply_f
            },
            "o_skelett": {
                "name": "o_skelett",
                "examine": "",  # Text to me emitted when object is examined
                "help_text": "",  # Text to be emitted when player asks for help with object
                "ownedby": "p_innen",  # Which Player currently owns this item? Default: None
                "fixed": False,  # False bedeutet: Kann aufgenommen werden
                "hidden": False,  # True bedeutet: Das Objekt ist nicht sichtbar
                "apply_f": o_skelett_apply_f
            },
            "o_geldboerse": {
                "name": "o_geldboerse",
                "examine": "",  # Text to me emitted when object is examined
                "help_text": "",  # Text to be emitted when player asks for help with object
                "ownedby": "p_innen",  # Which Player currently owns this item? Default: None
                "fixed": False,  # False bedeutet: Kann aufgenommen werden
                "hidden": False,  # True bedeutet: Das Objekt ist nicht sichtbar
                "apply_f": o_geldboerse_apply_f
            },
            "o_ec_karte": {
                "name": "o_ec_karte",
                "examine": "",  # Text to me emitted when object is examined
                "help_text": "",  # Text to be emitted when player asks for help with object
                "ownedby": "p_innen",  # Which Player currently owns this item? Default: None
                "fixed": False,  # False bedeutet: Kann aufgenommen werden
                "hidden": False,  # True bedeutet: Das Objekt ist nicht sichtbar
                "apply_f": o_ec_karte_apply_f
            },
            "o_pinsel": {
                "name": "o_pinsel",
                "examine": "",  # Text to me emitted when object is examined
                "help_text": "",  # Text to be emitted when player asks for help with object
                "ownedby": "p_innen",  # Which Player currently owns this item? Default: None
                "fixed": False,  # False bedeutet: Kann aufgenommen werden
                "hidden": False,  # True bedeutet: Das Objekt ist nicht sichtbar
                "apply_f": o_pinsel_apply_f
            },
            "o_farbeimer": {
                "name": "o_farbeimer",
                "examine": "",  # Text to me emitted when object is examined
                "help_text": "",  # Text to be emitted when player asks for help with object
                "ownedby": "p_innen",  # Which Player currently owns this item? Default: None
                "fixed": False,  # False bedeutet: Kann aufgenommen werden
                "hidden": False,  # True bedeutet: Das Objekt ist nicht sichtbar
                "apply_f": o_farbeimer_apply_f
            },

        }

        player_names = ["Spieler1"]
        #
        # Added new Stuff in place_defs? --> Uncomment the following functions in order to emit skeletons
        # for objects and their apply-Functions as well as ways.
        #

        # emit_waydefs(place_defs, way_defs)
        # emit_objdefs(place_defs, object_defs)

        self.from_definitions(place_defs, way_defs, object_defs, player_names)
    #
# Apply-Functions for Objects
#
def o_umschlag_apply_f(gamestate, player=None, onwhat=None) -> str:
    return "Hiermit solltest du kein Schindluder treiben!"

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

# g = GameState()
# print(g)