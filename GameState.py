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

    object_defs = {}

    player_names = ["Spieler1"]
    emit_waydefs(place_defs, way_defs)
    # emit_objdefs(place_defs)

    return GameState.from_definitions(place_defs, way_defs, object_defs, player_names)

init_game()