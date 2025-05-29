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
    #
    #  Initialization functions
    #
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

    def _init_ways(self, defs: dict, places: Dict[str, Place]) -> Dict[str, Way]:
        ways = {}

        for way_name, way_data in defs.items():
            source_name = way_data["source"]
            dest_name = way_data["destination"]
            v = way_data.get("visible")
            if v == None:
                visible = True
            else:
                visible = v
            source_place = places[source_name]
            dest_place = places[dest_name] if dest_name else None

            obstruction = way_data["obstruction_check"]
            if obstruction is None:
                obstruction = lambda state: "Free"  # Default-Funktion

            way = Way(
                name=way_name,
                source=source_place,
                destination=dest_place,
                text_direction=way_data["text_direction"],
                obstruction_check=obstruction,
                visible = visible,
                description=way_data["description"]
            )

            # Im source-Place registrieren
            source_place.ways.append(way)

            ways[way_name] = way

        return ways

    def _init_objects(self, defs: dict, places: Dict[str, Place]) -> Dict[str, GameObject]:
        objects = {}

        for obj_name, obj_data in defs.items():
            obj = GameObject(
                name=obj_data["name"],
                examine=obj_data["examine"],
                help_text=obj_data.get("help_text", ""),
                fixed=obj_data.get("fixed", False),
                hidden=obj_data.get("hidden", False),
                apply_f=obj_data.get("apply_f", None)
            )
            fn = obj_data.get("apply_f", None)
            obj.apply_f = fn
            ownedby_str = obj_data.get("ownedby", None)
            if ownedby_str in places:
                obj.ownedby = places[ownedby_str]
            else:
                obj.ownedby = None
            # obj.ownedby = obj_data.get("ownedby", None)


            # Füge das Objekt dem passenden Place hinzu
            for place in places.values():
                if ownedby_str == place.name:
                    place.place_objects.append(obj)
                    break

            objects[obj_data["name"]] = obj

        return objects

    def from_definitions(self,place_defs, way_defs, object_defs):
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

    def add_player(self,name, npc=False):
        from NPCPlayerState import NPCPlayerState
        if npc:
            start_room = self.places["p_geldautomat"]
            self.players.append(NPCPlayerState(name=name,location=start_room))
        else:
            start_room = self.places["p_start"]
            self.players.append(PlayerState(name,start_room))


    def init_game(self):
        #
        # Wege, die verschlossen sind
        #
        self.schuppentuer=False
        self.leiter = False
        self.hebel = False
        #
        # Place definitions
        #

        place_defs = {
            "p_start": {
                "description": "Ein unbenannter Ort an einer staubigen, monotonen Strasse durch eine heiße Wüste. ",
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
                "description": "Im inneren des Holzschuppens",
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
                "destination": "p_warenautomat",
                "text_direction": "zum Warenautomat",
                "obstruction_check": None,
                "description": ""
            },
            "w_start_geldautomat": {
                "source": "p_start",
                "destination": "p_geldautomat",
                "text_direction": "zum Geldautomaten",
                "obstruction_check": None,
                "description": ""
            },
            "w_start_schuppen": {
                "source": "p_start",
                "destination": "p_schuppen",
                "text_direction": "zum Schuppen",
                "obstruction_check": None,
                "description": ""
            },
            #
            # Place: p_warenautomat
            #

            "w_warenautomat_start": {
                "source": "p_warenautomat",
                "destination": "p_start",
                "text_direction": "zum Start, wo das kaputte Fahrrad liegt",
                "obstruction_check": None,
                "description": ""
            },
            "w_warenautomat_geldautomat": {
                "source": "p_warenautomat",
                "destination": "p_geldautomat",
                "text_direction": "zum Geldautomaten",
                "obstruction_check": None,
                "description": ""
            },
            "w_warenautomat_schuppen": {
                "source": "p_warenautomat",
                "destination": "p_schuppen",
                "text_direction": "zum Schuppen",
                "obstruction_check": None,
                "description": ""
            },
            "w_warenautomat_ubahn": {
                "source": "p_warenautomat",
                "destination": "p_ubahn",
                "text_direction": "herunter zur U-Bahn",
                "obstruction_check": w_warenautomat_ubahn_f,
                "visible": False,
                "description": "Eine Treppe, die zu einer U-Bahn-Station führt!"
            },
            #
            # Place: p_ubahn
            #

            "w_ubahn_warenautomat": {
                "source": "p_ubahn",
                "destination": "p_warenautomat",
                "text_direction": "hoch zum Warenautomaten",
                "obstruction_check": None,
                "description": ""
            },
            "w_ubahn_wagen": {
                "source": "p_ubahn",
                "destination": "p_wagen",
                "text_direction": "in den U-Bahnwagen hinein",
                "obstruction_check": None,
                "description": ""
            },
            #
            # Place: p_wagen
            #

            "w_wagen_ubahn": {
                "source": "p_wagen",
                "destination": "p_ubahn",
                "text_direction": "auf den Bahnsteig der U-Bahn",
                "obstruction_check": None,
                "description": ""
            },
            "w_wagen_ubahn2": {
                "source": "p_wagen",
                "destination": "p_ubahn2",
                "text_direction": "zur zweiten Haltestelle",
                "obstruction_check": None,
                "description": ""
            },
            #
            # Place: p_ubahn2
            #

            "w_ubahn2_wagen": {
                "source": "p_ubahn2",
                "destination": "p_wagen",
                "text_direction": "in den U-Bahnwagen",
                "obstruction_check": None,
                "description": ""
            },
            #
            # Place: p_geldautomat
            #

            "w_geldautomat_start": {
                "source": "p_geldautomat",
                "destination": "p_start",
                "text_direction": "zum Start, wo das kaputte Fahrrad liegt",
                "obstruction_check": None,
                "description": ""
            },
            "w_geldautomat_warenautomat": {
                "source": "p_geldautomat",
                "destination": "p_warenautomat",
                "text_direction": "zum Warenautomaten",
                "obstruction_check": None,
                "description": ""
            },
            "w_geldautomat_schuppen": {
                "source": "p_geldautomat",
                "destination": "p_schuppen",
                "text_direction": "zum Schuppen",
                "obstruction_check": None,
                "description": ""
            },
            #
            # Place: p_schuppen
            #

            "w_schuppen_start": {
                "source": "p_schuppen",
                "destination": "p_start",
                "text_direction": "zum Start",
                "obstruction_check": None,
                "description": ""
            },
            "w_schuppen_warenautomat": {
                "source": "p_schuppen",
                "destination": "p_warenautomat",
                "text_direction": "zum Warenautomat",
                "obstruction_check": None,
                "description": ""
            },
            "w_schuppen_geldautomat": {
                "source": "p_schuppen",
                "destination": "p_geldautomat",
                "text_direction": "zum Geldautomaten",
                "obstruction_check": None,
                "description": ""
            },
            "w_schuppen_innen": {
                "source": "p_schuppen",
                "destination": "p_innen",
                "text_direction": "in den Schuppen hinein",
                "obstruction_check": w_schuppen_innen_f,
                "description": ""
            },
            "w_schuppen_dach": {
                "source": "p_schuppen",
                "destination": "p_dach",
                "visible": False,
                "text_direction": "auf das Dach des Schuppens",
                "obstruction_check": w_schuppen_dach_f,
                "description": ""
            },
            #
            # Place: p_dach
            #

            "w_dach_schuppen": {
                "source": "p_dach",
                "destination": "p_schuppen",
                "text_direction": "vom dach des Schuppens herunter",
                "obstruction_check": None,
                "description": ""
            },
            #
            # Place: p_innen
            #

            "w_innen_schuppen": {
                "source": "p_innen",
                "destination": "p_schuppen",
                "text_direction": "aus dem Schuppen heraus",
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
                "examine": "Ein Warenautomat mit Fahrradteilen. Er enthält tatsächlich auch eine Fahrradkette! Jetzt bräuchte man Geld - und zwar italienische Lira. Dieser Automat akzeptiert nur diese!",  # Text to me emitted when object is examined
                "help_text": "",  # Text to be emitted when player asks for help with object
                "ownedby": "p_warenautomat",  # Which Player currently owns this item? Default: None
                "fixed": True,  # False bedeutet: Kann aufgenommen werden
                "hidden": False,  # True bedeutet: Das Objekt ist nicht sichtbar
                "apply_f":  o_warenautomat_apply_f

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
                "examine": "Italienische Lira! Eine ganze Menge davon! Die hat man schon lange nicht mehr gesehen!",  # Text to me emitted when object is examined
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
                "examine": "Ein Geldautomat. Man muss eine Karte einstecken, eine Geheimnummer eingeben, und wenn Geld auf dem Konto ist, kann man es abheben.",  # Text to me emitted when object is examined
                "help_text": "",  # Text to be emitted when player asks for help with object
                "ownedby": "p_geldautomat",  # Which Player currently owns this item? Default: None
                "fixed": True,  # False bedeutet: Kann aufgenommen werden
                "hidden": False,  # True bedeutet: Das Objekt ist nicht sichtbar
                "apply_f": o_geldautomat_apply_f
            },
            "o_geld_dollar": {
                "name": "o_geld_dollar",
                "examine": "US-Dollar! Diese werden fast überall gerne genommen! Aber eben nur fast - es soll Warenautomaten geben, die sie nicht akzeptieren. Ob du wohl Glück hast?",  # Text to me emitted when object is examined
                "help_text": "",  # Text to be emitted when player asks for help with object
                "ownedby": "p_geldautomat",  # Which Player currently owns this item? Default: None
                "fixed": False,  # False bedeutet: Kann aufgenommen werden
                "hidden": True,  # True bedeutet: Das Objekt ist nicht sichtbar
                "apply_f": o_geld_dollar_apply_f
            },
            #
            # Place: p_schuppen
            #

            "o_schuppen": {
                "name": "o_schuppen",
                "examine": "Ein alter Holzschuppen, in dem womöglich interessante Dinge sind.",  # Text to me emitted when object is examined
                "help_text": "",  # Text to be emitted when player asks for help with object
                "ownedby": "p_schuppen",  # Which Player currently owns this item? Default: None
                "fixed": True,  # False bedeutet: Kann aufgenommen werden
                "hidden": False,  # True bedeutet: Das Objekt ist nicht sichtbar
                "apply_f": o_schuppen_apply_f
            },
            "o_blumentopf": {
                "name": "o_blumentopf",
                "examine": "Ein alter Blumentopf.",  # Text to me emitted when object is examined
                "help_text": "",  # Text to be emitted when player asks for help with object
                "ownedby": "p_schuppen",  # Which Player currently owns this item? Default: None
                "fixed": False,  # False bedeutet: Kann aufgenommen werden
                "hidden": False,  # True bedeutet: Das Objekt ist nicht sichtbar
                "apply_f": o_blumentopf_apply_f
            },
            "o_schluessel": {
                "name": "o_schluessel",
                "examine": "Ein Schlüssel! Der sieht so aus, als könnte er hier noch irgendwo wichtig sein!",  # Text to me emitted when object is examined
                "help_text": "",  # Text to be emitted when player asks for help with object
                "ownedby": "p_schuppen",  # Which Player currently owns this item? Default: None
                "fixed": False,  # False bedeutet: Kann aufgenommen werden
                "hidden": True,  # True bedeutet: Das Objekt ist nicht sichtbar
                "apply_f": o_schluessel_apply_f
            },
            "o_stuhl": {
                "name": "o_stuhl",
                "examine": "Ein rostiger, alter Gartenstuhl. Da machst du dich bestimmt dreckig, wenn du dich draufsetzt!",  # Text to me emitted when object is examined
                "help_text": "",  # Text to be emitted when player asks for help with object
                "ownedby": "p_schuppen",  # Which Player currently owns this item? Default: None
                "fixed": False,  # False bedeutet: Kann aufgenommen werden
                "hidden": False,  # True bedeutet: Das Objekt ist nicht sichtbar
                "apply_f": o_stuhl_apply_f
            },
            "o_schrott": {
                "name": "o_schrott",
                "examine": "Eine Menge Schrott! Hier kannst Du stundelang herumsuchen - aber (Spoilerwarnung) dur wirst hier nichts besonderes finden.",  # Text to me emitted when object is examined
                "help_text": "",  # Text to be emitted when player asks for help with object
                "ownedby": "p_schuppen",  # Which Player currently owns this item? Default: None
                "fixed": True,  # False bedeutet: Kann aufgenommen werden
                "hidden": False,  # True bedeutet: Das Objekt ist nicht sichtbar
                "apply_f": o_schrott_apply_f
            },
            #
            # Place: p_dach
            #

            "o_hebel": {
                "name": "o_hebel",
                "examine": "Ein Hebel!! Was passiert wohl, wenn du diesen betätigst?",  # Text to me emitted when object is examined
                "help_text": "",  # Text to be emitted when player asks for help with object
                "ownedby": "p_dach",  # Which Player currently owns this item? Default: None
                "fixed": True,  # False bedeutet: Kann aufgenommen werden
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
                "examine": "Ein Skelett!! In einem Anzug!! Wie lange das wohl schon hier sitzt?",  # Text to me emitted when object is examined
                "help_text": "",  # Text to be emitted when player asks for help with object
                "ownedby": "p_innen",  # Which Player currently owns this item? Default: None
                "fixed": True,  # False bedeutet: Kann aufgenommen werden
                "hidden": False,  # True bedeutet: Das Objekt ist nicht sichtbar
                "apply_f": o_skelett_apply_f
            },
            "o_geldboerse": {
                "name": "o_geldboerse",
                "examine": "Eine alte Geldbörse aus Leder.",  # Text to me emitted when object is examined
                "help_text": "",  # Text to be emitted when player asks for help with object
                "ownedby": "p_innen",  # Which Player currently owns this item? Default: None
                "fixed": False,  # False bedeutet: Kann aufgenommen werden
                "hidden": True,  # True bedeutet: Das Objekt ist nicht sichtbar
                "apply_f": o_geldboerse_apply_f
            },
            "o_ec_karte": {
                "name": "o_ec_karte",
                "examine": "Eine alte EC-Karte. Ob die noch geht?",  # Text to me emitted when object is examined
                "help_text": "",  # Text to be emitted when player asks for help with object
                "ownedby": "p_innen",  # Which Player currently owns this item? Default: None
                "fixed": False,  # False bedeutet: Kann aufgenommen werden
                "hidden": True,  # True bedeutet: Das Objekt ist nicht sichtbar
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

        #
        # Added new Stuff in place_defs? --> Uncomment the following functions in order to emit skeletons
        # for objects and their apply-Functions as well as ways.
        #

        # emit_waydefs(place_defs, way_defs)
        # emit_objdefs(place_defs, object_defs)

        self.from_definitions(place_defs, way_defs, object_defs)
    #
    # Utility Functions
    #
    from typing import List, Optional

    #
    # Find shortest Path between two places
    #
    def find_shortest_path(self, start: Place, goal: Place) -> Optional[List[Way]]:
        from collections import deque
        queue = deque()
        queue.append((start, []))  # Elemente sind Tupel: (aktueller Ort, bisheriger Pfad)
        visited = set()

        while queue:
            current_place, path_so_far = queue.popleft()

            if current_place == goal:
                return path_so_far  # Erfolgreich: Rückgabe des Pfads als Liste von Way-Objekten

            if current_place.name in visited:
                continue

            visited.add(current_place.name)

            for way in current_place.ways:
                if way.visible and way.destination.name not in visited and way.obstruction_check(self)=="Free":
                    new_path = path_so_far + [way]
                    queue.append((way.destination, new_path))

        return None  # Kein Pfad gefunden
    #
    # Verbs to be executed
    #

    def verb_apply(self, pl: PlayerState, what, towhat):
        if towhat == None:
            r = f"apply {what} in this context"
            o_what = self.objects.get(what)
            if o_what != None:
                r = r+ "\n"+ o_what.apply_f(self, pl, o_what, None)
        else:
            r = f"apply {what} to {towhat} in this context"
            o_what = self.objects.get(what)
            if towhat=="dog":
                o_towhat = PlayerState("dog", None) # Temporary Player State
            else:
                o_towhat = self.objects.get(towhat)

            if o_what != None:
                r = r+ "\n" + o_what.apply_f(self, pl, o_what, o_towhat)
        return r

    def verb_take(selfs, pl: PlayerState, what):
        loc = pl.location
        # obj = loc.place_objects.get(what)
        obj = None
        for o in loc.place_objects:
            if o.name == what:
                obj = o
                break
        if obj == None:
            return "Sowas gibt es hier nicht."
        else:
            pl.add_to_inventory(obj)
            return f"Du hast {what} nun bei dir"

    def verb_drop(self, pl: PlayerState, what):
        obj = self.objects.get(what)
        if obj == None:
            return "Sowas gibt es in diesem Spiel nicht!"

        if pl.is_in_inventory(obj):
            pl.remove_from_inventory(obj)
            obj.hidden = False
            pl.location.place_objects.append(obj)
            return f'Objekt {what} in/auf/am {pl.location.name} abgelegt'

        return f'{what} ist nicht in {pl.name} inventory'

    def verb_lookaround(self, pl: PlayerState):
        loc = pl.location
        retstr = f"""**Ort: {pl.location.name}**
{pl.location.description}

Am Ort sind folgende Objekte zu sehen:"""
        rs = ""
        for i in pl.location.place_objects:
            if not i.hidden:
                rs = rs+f'\n- {i.name} - {i.examine}'
        if rs == "":
            rs="(keine)"
        retstr = retstr+rs+"\n\nDu kannst folgende wege gehen:\n"
        loc = pl.location
        for w in loc.ways:
            if w.visible:
                retstr = retstr + f'- {w.name} ... führt zu {w.destination.name}\n'
        return retstr


    def verb_walk(self, pl: PlayerState, direction: str):
        #
        # Player walks into "direction" (either name of way or name of destination)
        #
        # (1) Is there a way from his current location?
        #   (1a) if yes, is there an obstacle in the way?
        #     (1aa) if no --> walk, return success message
        #     (1ab) else --> return failure message (Obstacle in way)
        # (2) return failure message ("There is no path here")

        w_found = None
        for w in pl.location.ways:
            if w.name == direction or w.destination.name == direction:
                w_found = w
                break
        if w_found == None:
            return "Dieser Weg existiert hier nicht!"
        ob = w_found.obstruction_check(self)

        if ob != "Free":
            return ob  # If there is an obstacle, function returns string different from "Free"

        #
        # Finally - we can go the way
        #
        pl.location = w_found.destination
        return f"Du bist nun hier: {pl.location.name} - {pl.location.description}"

    def verb_examine(self, pl: PlayerState, what: str):
        #
        # Does an object with that name exist in the users inventory or in the current location?
        # if so, return its examine string, if not, return failure ("No such thing here")
        obj_here = None
        retstr = "So etwas gibt es hier nicht, und du hast sowas auch nicht bei dir."
        for i in pl.inventory:
            if i.name == what:
                obj_here = i
                retstr = f"Du trägst {i.name} gerade bei dir."
                break
        if obj_here == None:
            retstr = ""
            for i in pl.location.place_objects:
                if i.name == what:
                    obj_here = i
                    break
        if obj_here != None:

            #
            # Sometimes examinig one thing reveals another thing
            #
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

            else:
                retstr = retstr + f"{obj_here.examine}"
        else:
            retstr = f'{what} - sowas gibt es hier nicht!'
        return retstr


#
# Apply-Functions for Objects
#
def o_schluessel_apply_f(gs: GameState, pl: PlayerState=None, what: GameObject=None, onwhat: GameObject=None) -> str:
    #
    # Ich bin der Schlüssel - einzig sinnvolle Applikation: Schuppen
    #
    if pl != None:
        #
        # Haben wir den SChlüssel dabei oder liegt er am aktuellen Ort? --> Anwenden
        #
        loc = pl.location
        if loc != gs.places["p_schuppen"]:
            return "Das ergibt hier keinen Sinn."
        if pl.is_in_inventory(what) or (what in pl.location.place_objects) and (onwhat == gs.objects["o_schuppen"]):
            gs.schuppentuer = True
            return "Klick - die Tür geht auf"

        else:
            return "Das geht hier nicht: "
    else:
        return "... kein Spieler? Wie soll das gehen?"

def o_umschlag_apply_f(gs: GameState, pl: PlayerState=None, what: GameObject=None, onwhat: GameObject=None) -> str:
    return "Hiermit solltest du kein Schindluder treiben!"

def o_warenautomat_apply_f(gs: GameState, pl: PlayerState=None, what: GameObject=None, onwhat: GameObject=None) -> str:
    pass


def o_muelleimer_apply_f(gs: GameState, pl: PlayerState=None, what: GameObject=None, onwhat: GameObject=None) -> str:
    pass


def o_salami_apply_f(gs: GameState, pl: PlayerState=None, what: GameObject=None, onwhat: GameObject=None) -> str:
    pass


def o_geheimzahl_apply_f(gs: GameState, pl: PlayerState=None, what: GameObject=None, onwhat: GameObject=None) -> str:
    pass


def o_tuerschliesser_apply_f(gs: GameState, pl: PlayerState=None, what: GameObject=None, onwhat: GameObject=None) -> str:
    pass


def o_pizzaautomat_apply_f(gs: GameState, pl: PlayerState=None, what: GameObject=None, onwhat: GameObject=None) -> str:
    pass


def o_geld_lire_apply_f(gs: GameState, pl: PlayerState=None, what: GameObject=None, onwhat: GameObject=None) -> str:
    pass


def o_pizza_apply_f(gs: GameState, pl: PlayerState=None, what: GameObject=None, onwhat: GameObject=None) -> str:
    pass


def o_geldautomat_apply_f(gs: GameState, pl: PlayerState=None, what: GameObject=None, onwhat: GameObject=None) -> str:
    pass


def o_geld_dollar_apply_f(gs: GameState, pl: PlayerState=None, what: GameObject=None, onwhat: GameObject=None) -> str:
    pass


def o_schuppen_apply_f(gs: GameState, pl: PlayerState=None, what: GameObject=None, onwhat: GameObject=None) -> str:
    pass


def o_blumentopf_apply_f(gs: GameState, pl: PlayerState=None, what: GameObject=None, onwhat: GameObject=None) -> str:
    pass




def o_stuhl_apply_f(gs: GameState, pl: PlayerState=None, what: GameObject=None, onwhat: GameObject=None) -> str:
    pass


def o_schrott_apply_f(gs: GameState, pl: PlayerState=None, what: GameObject=None, onwhat: GameObject=None) -> str:
    pass


def o_hebel_apply_f(gs: GameState, pl: PlayerState=None, what: GameObject=None, onwhat: GameObject=None) -> str:
    #
    # Ich bin der Hebel - ich kann nicht auf "irgendwas" angewandt werden, ich kann nur selber
    # angewandt werden.
    #
    if pl != None:
        if pl.location == gs.places["p_dach"]:
            if gs.hebel:
                gs.hebel = False
                gs.ways["w_warenautomat_ubahn"].visible = False
                gs.objects["o_warenautomat"].examine = "Ein Warenautomat mit Fahrradteilen. Er enthält tatsächlich auch eine Fahrradkette! Jetzt bräuchte man Geld - und zwar italienische Lira. Dieser Automat akzeptiert nur diese!"
                return "Es rumpelt - und der Warenautomat richtet sich wieder auf!"
            else:
                gs.hebel = True
                gs.ways["w_warenautomat_ubahn"].visible = True
                gs.objects["o_warenautomat"].examine = "Ein Warenautomat, der auf dem Rücken liegt. Da wo er stand, führt eine Treppe nach unten!"
                return "Es rumpelt - Die siehst, wie der Warenautomat sich langsam auf den Rücken legt. Da wo er stand, ist nun eine Öffnung!"
    else:
        return "??? Kein Spieler ???"


def o_leiter_apply_f(gs: GameState, pl: PlayerState=None, what: GameObject=None, onwhat: GameObject=None) -> str:
    #
    # Ich bin die Leiter - einzig sinnvolle Applikation: an den Schuppen anlehnen
    #
    if pl != None:
        #
        # Haben wir die Leiter dabei?
        #
        if onwhat.name == "dog":
            #
            # Mit der Leiter gegen den Hund
            #
            dog = None
            for d in gs.players:
                if d.name=="Dog":
                    dog=d
                    break
            if d==None:
                return "Kein Hund hier!"
            retour = gs.find_shortest_path(pl.location,gs.places["p_geldautomat"])
            if retour == None:
                return "Du gehst mit der Leiter auf den Hund los - aber er kann nicht an seinen Stammplatz flüchten!"

            dog.growl=0
            dog.next_location = ""
            dog.next_location_wait = 2
            dog.location = gs.places["p_geldautomat"]

            return "Mit einer Leiter gegen einen Hund! Wie unfair! Aber immerhin der Hund rennt jammernd an seinen Stammplatz, den Geldautomaten."

        loc = pl.location
        if onwhat != gs.objects["o_schuppen"]:
            return "Die Leiter rutscht ab und fällt um. Das mit der Leiter ergibt hier sowieso keinen Sinn."
        if pl.is_in_inventory(what) or (what in pl.location.place_objects):
            gs.leiter = True
            pl.remove_from_inventory(what)
            loc.place_objects.append(what)
            #
            # Weg Sichtbar machen
            #
            gs.ways["w_schuppen_dach"].visible = True

            return "Du kannst jetzt auf den Schuppen steigen!"
        else:
            return "Das geht hier nicht: "
    else:
        return "... kein Spieler? Wie soll das gehen?"


def o_skelett_apply_f(gs: GameState, pl: PlayerState=None, what: GameObject=None, onwhat: GameObject=None) -> str:
    pass


def o_geldboerse_apply_f(gs: GameState, pl: PlayerState=None, what: GameObject=None, onwhat: GameObject=None) -> str:
    pass


def o_ec_karte_apply_f(gs: GameState, pl: PlayerState=None, what: GameObject=None, onwhat: GameObject=None) -> str:
    pass


def o_pinsel_apply_f(gs: GameState, pl: PlayerState=None, what: GameObject=None, onwhat: GameObject=None) -> str:
    pass


def o_farbeimer_apply_f(gs: GameState, pl: PlayerState=None, what: GameObject=None, onwhat: GameObject=None) -> str:
    pass
#
# Obstruction Check Functions
#
def w_schuppen_innen_f(gs: GameState):
    if gs.schuppentuer == False:
        return "Dieser Weg ist versperrt - die Tür ist abgeschlossen!"
    else:
        return "Free"

def w_schuppen_dach_f(gs: GameState):
    if gs.leiter == False:
        return "Hier kommst du nicht so ohne weiteres hoch!"
    else:
        return "Free"

def w_warenautomat_ubahn_f(gs: GameState):
    if gs.hebel:
        return "Free"
    else:
        return "Ist hier ein Weg? Und wenn, dann ist er versperrt!"

def huhu() -> str:
    return ("--- huhu ---")
# g = GameState()
# print(g)