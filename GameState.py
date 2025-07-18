from __future__ import annotations

import json

from Place import Place
from Way import Way
from typing import Dict, List
from PlayerState import PlayerState
from GameObject import GameObject
from GeminiInterface import GeminiInterface
from Utils import tw_print, dprint, dl, dpprint

#
# Maintains the state from the game perspective. There are player states as well
#

from typing import Callable

from WayPrompts import w_dach_schuppen_prompt_f


class GameState:

    def __init__(self):
        self.objects = None
        self.ways = None
        self.places = None
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
                place_prompt_f=place_data.get("place_prompt_f",None),
                callnames = place_data.get("callnames",None),
                ways=[],  # Wird später in _init_ways gefüllt
                place_objects=[]  # Wird später in _init_objects gefüllt
            )
            place.callnames = [s.lower() for s in place.callnames ]
            places[place_name] = place

        return places

    def _init_ways(self, defs: dict, places: Dict[str, Place]) -> Dict[str, Way]:
        ways = {}

        for way_name, way_data in defs.items():
            source_name = way_data["source"]
            dest_name = way_data["destination"]
            v = way_data.get("visible")
            if v is None:
                visible = True
            else:
                visible = v



            source_place = places[source_name]
            dest_place = places[dest_name] if dest_name else None

            obstruction_f = way_data.get("obstruction_check", None)
            if obstruction_f is None:
                obstruction_f = lambda state: "Free"  # Default-Funktion

            way_prompt_f = way_data.get("way_prompt_f", None)

            way = Way(
                name=way_name,
                source=source_place,
                destination=dest_place,
                text_direction=way_data["text_direction"],
                obstruction_check=obstruction_f,
                way_prompt_f = way_prompt_f,
                visible = visible,
                description=way_data["description"]
            )

            # Im source-Place registrieren
            source_place.ways.append(way)

            ways[way_name] = way

        return ways

    def _init_objects(self, defs: dict, places: Dict[str, Place]) -> Dict[str, GameObject]:
        objects = {}
        from GameObject import GameObject
        for obj_name, obj_data in defs.items():

            obj = GameObject(
                name=obj_data["name"],
                examine=obj_data["examine"],
                help_text=obj_data.get("help_text", ""),
                fixed=obj_data.get("fixed", False),
                hidden=obj_data.get("hidden", False),
                callnames   = obj_data.get("callnames", None),
                apply_f     = obj_data.get("apply_f", None),
                reveal_f    = obj_data.get("reveal_f", None),
                take_f      = obj_data.get("take_f", None),
                prompt_f    = obj_data.get("prompt_f", None)
            )
            obj.callnames = [s.lower() for s in obj.callnames]
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
        self.players = []
        self.time = 0
        self.debug_mode = False
        #
        # Game State Variables and Flags
        #
        self.schuppentuer=False
        self.leiter = False
        self.hebel = False                 # Warenautomat --> Ubahn
        self.geheimzahl = 18513            # Geldautomat - wobei der nur zwischen 0 und 999 akzeptiert
        self.ubahn_in_otherstation = False # Ist unsere U-Bahn in Station 2?
        self.felsen = True                 # Ist der Felsen noch im Weg?
        self.hauptschalter = False         # Ohne Strom geht hier gar nichts
        self.dach = True                   # An Ende hat jemand das Dach weggesprengt
        self.warenautomat_intakt = True    # oder den Warenautomat
        self.geldautomat_intakt = True     # oder den Geldautomat
        self.schuppen_intakt = True        # oder den Schuppen
        self.game_over = False             # Na hoffentlich noch nicht so schnell!
        self.game_won = False              # Wenn true, hat der Spieler das Spiel gewonnen.
        self.llm = GeminiInterface()       # Unser Sprachmodell
        self.gamelog = []                  # Wir schneiden alles für das LLM mit

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

        place_defs = {
            "p_start": {
                "description": "Ein unbenannter Ort an einer staubigen, monotonen Strasse durch eine heiße Wüste. ",
                "place_prompt": """ 
Start
=====
- Ein unbenannter, eigenartiger Ort an einer staubigen, monotonen Strasse durch eine heiße Wüste. 
- Es liegt hier das kaputte Fahrrad, welches weiter unten beschrieben wird.
- Die Straße erstreckt sich in beiden Richtungen zum Horizont. 
                """,
                "ways": ["w_start_warenautomat","w_start_geldautomat", "w_start_schuppen"],
                "objects": [""],
                "callnames": ["Start"]
            },
            "p_warenautomat": {
                "description": "Hier ist ein Warenautomat, an dem man Fahrradteile kaufen kann",
                "place_prompt": "",
                "place_prompt_f": pp.p_warenautomat_place_prompt_f,
                "ways": ["w_warenautomat_start", "w_warenautomat_geldautomat","w_warenautomat_schuppen","w_warenautomat_ubahn","w_warenautomat_felsen"],
                "objects": ["o_warenautomat"],
                "callnames": ["Warenautomat"]
            },
            "p_ubahn": {
                "description": "Eine U-Bahn-Station",
                "place_prompt": """
U-Bahn Station
==============
- Im Gegensatz zur Oberfläche herrscht eine angenehm Kühle. Es ist wichtig, auf diesen Kontrast hinzuweisen 
- Alles sauber und aufgeräumt
- An der Wand hängen einige Werbeplakate: eins für eine Limonade, eins für ein Reisebüro. 
- Keine Schmierereien oder Graffitis
- Der Boden ist mit Marmorfliesen gefliest.
- Neonröhren tauchen alles in angenehmes Licht. 
- In der Station steht ein U-Bahn-Wagen, dessen Türen offen sind. 
        """,
                "ways": ["w_ubahn_warenautomat", "w_ubahn_wagen"],
                "objects": ["o_muelleimer", "o_salami", "o_geheimzahl"],
                "callnames": ["U-Bahn", "UBahn", "U-Bahnhof", "Bahnsteig", "Bahnhof"]
            },
            "p_wagen": {
                "description": "Im U-Bahn-Wagen",
                "place_prompt": """Im inneren des U-Bahnwagens ist es sauber. Neonlicht leuchtet über den Sitzreihen. Auch hier gibt es einige
                Werbeplakate, die in kleinen Rahmen über den Fenstern des Wagens angebracht sind. Sie werben für den neuartigen C64 von Commodore, 
                den großartigen ZX Spectrum von Sinclair und das neue Album "Best of 80ies". 
            
        """,
                "ways": ["w_wagen_ubahn", "w_wagen_ubahn2"],
                "objects": ["o_tuerschliesser"],
                "callnames": ["Wagen","Bahnwagen","U-Bahnwagen"]
            },
            "p_ubahn2": {
                "description": "Eine zweite U-Bahn-Station",
                "place_prompt": """
Zweite U-Bahn Station
=====================
- Im Gegensatz zur Oberfläche herrscht eine angenehm Kühle. Es ist wichtig, auf diesen Kontrast hinzuweisen 
- Im Gegensatz zur ersten U-Bahn-Station ist die Luft etwas abgestanden
- Es riecht nach mediterranen Gewürzen
- Alles sauber und aufgeräumt
- An der Wand hängen einige Werbeplakate: eins für eine Limonade, eins für den neuen VW-Golf, eins für den neuen Heimcomputer C64 von Commodore. 
- Keine Schmierereien oder Graffitis
- Der Boden ist mit Marmorfliesen gefliest.
- Neonröhren tauchen alles in angenehmes Licht. 
- In der Station steht ein U-Bahn-Wagen, dessen Türen offen sind.
- Wichtig: du darfst den Hund in der Beschreibung ausschließlich nur erwähnen, wenn er im Wagen (p_wagen) oder hier am Ort ist. In allen 
  anderen Fällen kann man den Hund von hier nicht sehen.
        """,
                "ways": ["w_ubahn2_wagen"],
                "objects": ["o_pizzaautomat", "o_geld_lire", "o_pizza"],
                "callnames": ["U-Bahn-2"]
            },
            "p_geldautomat": {
                "description": "Hier ist ein Geldautomat, an dem man Bargeld bekommen kann",
                "place_prompt": "",
                "place_prompt_f": pp.p_geldautomat_place_prompt_f,
                "ways": ["w_geldautomat_start", "w_geldautomat_warenautomat", "w_geldautomat_schuppen","w_geldautomat_felsen"],
                "objects": ["o_geldautomat", "o_geld_dollar"],
                "callnames": ["Geldautomat", "ATM"]
            },
            "p_schuppen": {
                "description": "Hier ist ein alter Holzschuppen",
                "place_prompt": "",
                "place_prompt_f": pp.p_schuppen_place_prompt_f,
                "ways": ["w_schuppen_start", "w_schuppen_warenautomat", "w_schuppen_geldautomat","w_schuppen_innen","w_schuppen_dach", "w_schuppen_felsen"],
                "objects": ["o_schuppen","o_blumentopf","o_schluessel", "o_stuhl", "o_schrott"],
                "callnames": ["Schuppen", "Holzschuppen"]
            },
            "p_dach": {
                "description": "Das Dach des Holzschuppens",
                "place_prompt": """
Auf dem Dach des Schuppens
==========================
- Man kann weit blicken. 
- Man sieht den Geldautomaten und den Warenautomaten, sowie einen Hügel aus Gestein. 
- Hier gibt es großen Hebel, der weiter unten beschrieben wird.
            
        """,
                "ways": ["w_dach_schuppen"],
                "objects": ["o_hebel"],
                "callnames": ["Dach", "Schuppendach"]
            },
            "p_innen": {
                "description": "Im inneren des Holzschuppens",
                "place_prompt": "",
                "place_prompt_f": pp.p_innen_place_prompt_f,
                "ways": ["w_innen_schuppen"],
                "objects": ["o_leiter", "o_skelett", "o_geldboerse", "o_ec_karte", "o_pinsel", "o_farbeimer"],
                "callnames": ["innen", "Innenraum", "drinnen", "nach innen", "in den schuppen"]
            },
            "p_felsen": {
                "description": "Vor dem Berg liegt ein großer Felsen",
                "place_prompt": "",
                "place_prompt_f": pp.p_felsen_place_prompt_f,
                "ways": ["w_felsen_hoehle","w_felsen_schuppen", "w_felsen_warenautomat", "w_felsen_geldautomat"],
                "objects": ["o_felsen"],
                "callnames": ["Felsen", "Berg", "Hügel", "Huegel", "Felsblock"]
            },
            "p_hoehle": {
                "description": "In die Höhle, deren Eingang freigesprengt wurde.",
                "place_prompt": "",
                "place_prompt_f": pp.p_hoehle_place_prompt_f,
                "ways": ["w_hoehle_felsen"],
                "objects": [],
                "callnames": ["Höhle", "Hoehle"]
            }
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
                "obstruction_check": ocf.w_warenautomat_ubahn_f,
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
                "way_prompt_f": wp.w_ubahn_warenautomat_prompt_f,
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
                "visible": True,
                "description": ""
            },
            "w_wagen_ubahn2": {
                "source": "p_wagen",
                "destination": "p_ubahn2",
                "text_direction": "zur zweiten Haltestelle",
                "obstruction_check": None,
                "visible": False,
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
                "description": "",
                "visible": False,
                "description": "",
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
                "obstruction_check": ocf.w_schuppen_innen_f,
                "description": ""
            },
            "w_schuppen_dach": {
                "source": "p_schuppen",
                "destination": "p_dach",
                "visible": False,
                "text_direction": "auf das Dach des Schuppens",
                "obstruction_check": ocf.w_schuppen_dach_f,
                "way_prompt_f": wp.w_schuppen_dach_prompt_f,
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
                "way_prompt_f": wp.w_dach_schuppen_prompt_f,
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
                "way_prompt_f": wp.w_innen_schuppen_prompt_f,
                "description": ""
            },
            #
            # Place: p_felsen
            #
            "w_felsen_schuppen": {
                "source": "p_felsen" ,
                "destination": "p_schuppen",
                "text_direction": "zum Schuppen",
                "obstruction_check": None,
                "description": ""
            },
            "w_schuppen_felsen": {
                "source": "p_schuppen",
                "destination": "p_felsen",
                "text_direction": "zum Felsen",
                "obstruction_check": None,
                "description": ""
            },
            "w_felsen_warenautomat": {
                "source": "p_felsen",
                "destination": "p_warenautomat",
                "text_direction": "zum Warenautomat",
                "obstruction_check": None,
                "description": ""
            },
            "w_warenautomat_felsen": {
                "source": "p_warenautomat",
                "destination": "p_felsen",
                "text_direction": "zum Felsen",
                "obstruction_check": None,
                "description": ""
            },
            "w_felsen_geldautomat": {
                "source": "p_felsen",
                "destination": "p_geldautomat",
                "text_direction": "zum Geldautomat",
                "obstruction_check": None,
                "description": ""
            },
            "w_geldautomat_felsen": {
                "source": "p_geldautomat",
                "destination": "p_felsen",
                "text_direction": "zum Felsen",
                "obstruction_check": None,
                "description": ""
            },
            "w_felsen_hoehle": {
                "source": "p_felsen",
                "destination": "p_hoehle",
                "text_direction": "in die Höhle",
                "obstruction_check": ocf.w_felsen_hoehle_f,
                "description": ""
            },
            "w_hoehle_felsen": {
                "source": "p_hoehle",
                "destination": "p_felsen",
                "text_direction": "aus der Höhle heraus zum Felsen",
                "obstruction_check": None,
                "way_prompt_f": wp.w_hoehle_felsen_prompt_f,
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
                "callnames": ["Umschlag", "Briefumschlag"],
                "ownedby": "",
                "fixed": False,
                "hidden": True,
                "apply_f": af.o_umschlag_apply_f,
                "prompt_f": op.o_umschlag_prompt_f
            },
            "o_warenautomat": {
                "name": "o_warenautomat",
                "examine": "Ein Warenautomat mit Fahrradteilen. Er enthält tatsächlich auch eine Fahrradkette! Der Automat ist gut in Schuss und wirkt neu.",  # Text to me emitted when object is examined
                "help_text": "",  # Text to be emitted when player asks for help with object
                "callnames": ["Warenautomat", "Automat"],
                "ownedby": "p_warenautomat",  # Which Player currently owns this item? Default: None
                "fixed": True,  # False bedeutet: Kann aufgenommen werden
                "hidden": False,  # True bedeutet: Das Objekt ist nicht sichtbar
                "apply_f":  af.o_warenautomat_apply_f,
                "prompt_f": op.o_warenautomat_prompt_f

            },
            "o_fahrradkette": {
                "name": "o_fahrradkette",
                "examine": "Genau die Fahrradkette, die du zum Gewinnen des Spiels benötigst!",
                "help_text": "",
                "callnames": ["Fahrradkette", "Kette"],
                "ownedby": "p_warenautomat",
                "fixed": False,
                "hidden": True,
                "apply_f": af.o_fahrradkette_apply_f,
                "prompt_f": op.o_fahrradkette_prompt_f
            },
            "o_fahrrad": {
                "name": "o_fahrrad",
                "examine": "Das Fahrrad, mit dem du gekommen bist",
                "help_text": "",
                "callnames": ["Fahrrad", "Rad"],
                "ownedby": "p_start",
                "fixed": True,
                "hidden": False,
                "apply_f": None,
                "prompt_f": op.o_fahrrad_prompt_f
            },

            #
            # Place: p_ubahn
            #

            "o_muelleimer": {
                "name": "o_muelleimer",
                "examine": "Ein Mülleimer, gefüllt mit Papier, Plastik und Glasmüll. Gottseidank ist nichts ekeliges drin.",  # Text to me emitted when object is examined
                "help_text": "",  # Text to be emitted when player asks for help with object
                "callnames": ["Mülleimer", "Muelleimer", "Abfalleimer", "Abfallbehälter", "Abfallbehaelter"],
                "ownedby": "p_ubahn",  # Which Player currently owns this item? Default: None
                "fixed": True,  # False bedeutet: Kann aufgenommen werden
                "hidden": False,  # True bedeutet: Das Objekt ist nicht sichtbar
                "apply_f": af.o_muelleimer_apply_f,
                "reveal_f": rf.o_muelleimer_reveal_f,
                "prompt_f": op.o_muelleimer_prompt_f
            },
            "o_wasserspender": {
                "name": "o_wasserspender",
                "examine": "Ein Wasserspender - hier kannst du genässlich trinken.",
                # Text to me emitted when object is examined
                "help_text": "",  # Text to be emitted when player asks for help with object
                "callnames": ["Wasserspender", "Quelle", "Trinkstelle", "Zapfhanh", "Trinkbrunnen", "Wasserstelle"],
                "ownedby": "p_ubahn",  # Which Player currently owns this item? Default: None
                "fixed": True,  # False bedeutet: Kann aufgenommen werden
                "hidden": False,  # True bedeutet: Das Objekt ist nicht sichtbar
                "apply_f": af.o_wasserspender_apply_f,
                # "reveal_f": rf.o_wasserspender_reveal_f,
                "prompt_f": op.o_wasserspender_prompt_f
            },
            "o_salami": {
                "name": "o_salami",
                "examine": "Eine schöne italienische Salami. Schon etwas älter, aber noch geniessbar - zumindest für Hunde",  # Text to me emitted when object is examined
                "help_text": "",  # Text to be emitted when player asks for help with object
                "callnames": ["Salami", "Wurst"],
                "ownedby": "p_wagen",  # Which Player currently owns this item? Default: None
                "fixed": False,  # False bedeutet: Kann aufgenommen werden
                "hidden": False,  # True bedeutet: Das Objekt ist nicht sichtbar
                "apply_f": af.o_salami_apply_f,
                "prompt_f": op.o_salami_prompt_f
            },
            "o_geheimzahl": {
                "name": "o_geheimzahl",
                "examine": "Eine Geheimzahl...",  # Text to me emitted when object is examined
                "help_text": "",  # Text to be emitted when player asks for help with object
                "callnames": ["Geheimzahl", "Geheimcode", "PIN", "Geheimnummer"],
                "ownedby": "p_ubahn",  # Which Player currently owns this item? Default: None
                "fixed": False,  # False bedeutet: Kann aufgenommen werden
                "hidden": True,  # True bedeutet: Das Objekt ist nicht sichtbar
                "apply_f": af.o_geheimzahl_apply_f,
                "prompt_f": op.o_geheimzahl_prompt_f
            },
            #
            # Place: p_wagen
            #

            "o_tuerschliesser": {
                "name": "o_tuerschliesser",
                "examine": "Ein Türschliesser - ein Kästchen mit einem Knopf. Wenn man diesen Betätigt, geht eine Tür auf oder zu.",  # Text to me emitted when object is examined
                "help_text": "",  # Text to be emitted when player asks for help with object
                "callnames": ["Türschliesser","Tuerschliesser", "Türschließer", "Tuerschließer"],
                "ownedby": "p_wagen",  # Which Player currently owns this item? Default: None
                "fixed": False,  # False bedeutet: Kann aufgenommen werden
                "hidden": False,  # True bedeutet: Das Objekt ist nicht sichtbar
                "apply_f": af.o_tuerschliesser_apply_f,
                "prompt_f": op.o_tuerschliesser_prompt_f
            },
            #
            # Place: p_ubahn2
            #

            "o_pizzaautomat": {
                "name": "o_pizzaautomat",
                "examine": "Ein Pizza-Automat, der angemalt ist wie die italienische Flagge. Auf seinen Seiten ist ein Koch also Comicfigur abgebildet. Man kann Geld einwerfen, und dann backt der Automat eine Pizza",  # Text to me emitted when object is examined
                "help_text": "",  # Text to be emitted when player asks for help with object
                "callnames": ["Pizzaautomat", "Pizza-Automat"],
                "ownedby": "p_ubahn2",  # Which Player currently owns this item? Default: None
                "fixed": True,  # False bedeutet: Kann aufgenommen werden
                "hidden": False,  # True bedeutet: Das Objekt ist nicht sichtbar
                "apply_f": af.o_pizzaautomat_apply_f,
                "prompt_f": op.o_pizzaautomat_prompt_f
            },
            "o_geld_lire": {
                "name": "o_geld_lire",
                "examine": "Italienische Lira! Eine ganze Menge davon! Die hat man schon lange nicht mehr gesehen!",  # Text to me emitted when object is examined
                "help_text": "",  # Text to be emitted when player asks for help with object
                "callnames": ["Lire", "Lira", "italienische Lira", "italienische Lire", "italienisches Geld"],
                "ownedby": "p_ubahn2",  # Which Player currently owns this item? Default: None
                "fixed": False,  # False bedeutet: Kann aufgenommen werden
                "hidden": True,  # True bedeutet: Das Objekt ist nicht sichtbar
                "apply_f": af.o_geld_lire_apply_f,
                "prompt_f": op.o_geld_lire_prompt_f
            },
            "o_pizza": {
                "name": "o_pizza",
                "examine": "Eine Salami-Pizza mit viel Käse.",  # Text to me emitted when object is examined
                "help_text": "",  # Text to be emitted when player asks for help with object
                "callnames": ["Pizza"],
                "ownedby": "p_ubahn2",  # Which Player currently owns this item? Default: None
                "fixed": False,  # False bedeutet: Kann aufgenommen werden
                "hidden": True,  # True bedeutet: Das Objekt ist nicht sichtbar
                "apply_f": af.o_pizza_apply_f,
                "prompt_f": op.o_pizza_prompt_f
            },
            #
            # Place: p_geldautomat
            #

            "o_geldautomat": {
                "name": "o_geldautomat",
                "examine": "Ein Geldautomat, der sehr neu aussieht. Er ist klar mit 'ATM' gekennzeichnet. Man muss eine Karte einstecken, eine Geheimnummer eingeben, und wenn Geld auf dem Konto ist, kann man es abheben.",  # Text to me emitted when object is examined
                "help_text": "",  # Text to be emitted when player asks for help with object
                "ownedby": "p_geldautomat",  # Which Player currently owns this item? Default: None
                "callnames": ["Geldautomat", "ATM"],
                "fixed": True,  # False bedeutet: Kann aufgenommen werden
                "hidden": False,  # True bedeutet: Das Objekt ist nicht sichtbar
                "apply_f": af.o_geldautomat_apply_f,
                "prompt_f": op.o_geldautomat_prompt_f
            },
            "o_geld_dollar": {
                "name": "o_geld_dollar",
                "examine": "US-Dollar! Diese werden fast überall gerne genommen! Aber eben nur fast - es soll Warenautomaten geben, die sie nicht akzeptieren. Ob du wohl Glück hast?",  # Text to me emitted when object is examined
                "help_text": "",  # Text to be emitted when player asks for help with object
                "callnames": ["Dollar", "US-Dollar"],
                "ownedby": "p_geldautomat",  # Which Player currently owns this item? Default: None
                "fixed": False,  # False bedeutet: Kann aufgenommen werden
                "hidden": True,  # True bedeutet: Das Objekt ist nicht sichtbar
                "apply_f": af.o_geld_dollar_apply_f,
                "prompt_f": op.o_geld_dollar_prompt_f
            },
            #
            # Place: p_schuppen
            #

            "o_schuppen": {
                "name": "o_schuppen",
                "examine": "Ein alter Holzschuppen, in dem womöglich interessante Dinge sind. "
                           "Der Schuppen muss aufgeschlossen werden, sonst kann man ihn nicht betreten.",  # Text to me emitted when object is examined
                "help_text": "",  # Text to be emitted when player asks for help with object
                "ownedby": "p_schuppen",  # Which Player currently owns this item? Default: None
                "callnames": ["Schuppen", "Holzschuppen"],
                "fixed": True,  # False bedeutet: Kann aufgenommen werden
                "hidden": False,  # True bedeutet: Das Objekt ist nicht sichtbar
                "apply_f": af.o_schuppen_apply_f,
                "prompt_f": op.o_schuppen_prompt_f
            },
            "o_blumentopf": {
                "name": "o_blumentopf",
                "examine": "Ein alter Blumentopf aus Ton.",  # Text to me emitted when object is examined
                "help_text": "",  # Text to be emitted when player asks for help with object
                "ownedby": "p_schuppen",  # Which Player currently owns this item? Default: None
                "callnames": ["Blumentopf"],
                "fixed": False,  # False bedeutet: Kann aufgenommen werden
                "hidden": False,  # True bedeutet: Das Objekt ist nicht sichtbar
                "apply_f": af.o_blumentopf_apply_f,
                "reveal_f": rf.o_blumentopf_reveal_f,
                "prompt_f": op.o_blumentopf_prompt_f
            },
            "o_schluessel": {
                "name": "o_schluessel",
                "examine": "Ein Schlüssel aus Metall.",  # Text to me emitted when object is examined
                "help_text": "",  # Text to be emitted when player asks for help with object
                "ownedby": "p_schuppen",  # Which Player currently owns this item? Default: None
                "callnames": ["Schlüssel", "Schluessel"],
                "fixed": False,  # False bedeutet: Kann aufgenommen werden
                "hidden": True,  # True bedeutet: Das Objekt ist nicht sichtbar
                "apply_f": af.o_schluessel_apply_f,
                "prompt_f": op.o_schluessel_prompt_f
            },
            "o_stuhl": {
                "name": "o_stuhl",
                "examine": "Ein rostiger, alter Gartenstuhl. Da macht man dich bestimmt dreckig, wenn man sich draufsetzt!",  # Text to me emitted when object is examined
                "help_text": "",  # Text to be emitted when player asks for help with object
                "ownedby": "p_schuppen",  # Which Player currently owns this item? Default: None
                "callnames": ["Stuhl", "Gartenstuhl", "Hocker"],
                "fixed": False,  # False bedeutet: Kann aufgenommen werden
                "hidden": False,  # True bedeutet: Das Objekt ist nicht sichtbar
                "apply_f": af.o_stuhl_apply_f,
                "prompt_f": op.o_stuhl_prompt_f
            },
            "o_schrott": {
                "name": "o_schrott",
                "examine": "Eine Menge Schrott! Hier kanns man stundelang herumsuchen - aber man wird hier nichts besonderes finden.",  # Text to me emitted when object is examined
                "help_text": "",  # Text to be emitted when player asks for help with object
                "ownedby": "p_schuppen",  # Which Player currently owns this item? Default: None
                "callnames": ["Schrott", "Schrotthaufen"],
                "fixed": True,  # False bedeutet: Kann aufgenommen werden
                "hidden": False,  # True bedeutet: Das Objekt ist nicht sichtbar
                "apply_f": af.o_schrott_apply_f,
                "prompt_f": op.o_schrott_prompt_f
            },
            #
            # Place: p_dach
            #

            "o_hebel": {
                "name": "o_hebel",
                "examine": "Ein großer, schwarzer Hebel aus Metall.",  # Text to me emitted when object is examined
                "help_text": "",  # Text to be emitted when player asks for help with object
                "ownedby": "p_dach",  # Which Player currently owns this item? Default: None
                "callnames": ["Hebel", "Schalter"],
                "fixed": True,  # False bedeutet: Kann aufgenommen werden
                "hidden": False,  # True bedeutet: Das Objekt ist nicht sichtbar
                "apply_f": af.o_hebel_apply_f,
                "prompt_f": op.o_hebel_prompt_f
            },
            #
            # Place: p_innen
            #

            "o_leiter": {
                "name": "o_leiter",
                "examine": "Eine stablie Holzleiter",  # Text to me emitted when object is examined
                "help_text": "",  # Text to be emitted when player asks for help with object
                "ownedby": "p_innen",  # Which Player currently owns this item? Default: None
                "callnames": ["Leiter"],
                "fixed": False,  # False bedeutet: Kann aufgenommen werden
                "hidden": False,  # True bedeutet: Das Objekt ist nicht sichtbar
                "apply_f": af.o_leiter_apply_f, # Funktion: Leiter wurd "angewandt"
                "take_f": tf.o_leiter_take_f, # Funktion: Leiter wird aufgenommen
                "prompt_f": op.o_leiter_prompt_f
            },
            "o_skelett": {
                "name": "o_skelett",
                "examine": "Ein Skelett!! In einem Anzug!! Das ist wohl schon länger hier! Wie das wohl hierhin gekommen ist?",  # Text to me emitted when object is examined
                "help_text": "",  # Text to be emitted when player asks for help with object
                "ownedby": "p_innen",  # Which Player currently owns this item? Default: None
                "callnames": ["Skelett", "Knochenmann"],
                "fixed": True,  # False bedeutet: Kann aufgenommen werden
                "hidden": False,  # True bedeutet: Das Objekt ist nicht sichtbar
                "apply_f": af.o_skelett_apply_f,
                "reveal_f": rf.o_skelett_reveal_f,
                "prompt_f": op.o_skelett_prompt_f
            },
            "o_geldboerse": {
                "name": "o_geldboerse",
                "examine": "Eine alte Geldbörse aus Leder.",  # Text to me emitted when object is examined
                "help_text": "",  # Text to be emitted when player asks for help with object
                "ownedby": "p_innen",  # Which Player currently owns this item? Default: None
                "callnames": ["Geldboerse", "Geldbörse", "Portemonaie", "Brieftasche"],
                "fixed": False,  # False bedeutet: Kann aufgenommen werden
                "hidden": True,  # True bedeutet: Das Objekt ist nicht sichtbar
                "apply_f": af.o_geldboerse_apply_f,
                "reveal_f": rf.o_geldboerse_reveal_f,
                "prompt_f": op.o_geldboerse_prompt_f
            },
            "o_ec_karte": {
                "name": "o_ec_karte",
                "examine": "Eine alte EC-Karte. Ob die noch geht?",  # Text to me emitted when object is examined
                "help_text": "",  # Text to be emitted when player asks for help with object
                "ownedby": "p_innen",  # Which Player currently owns this item? Default: None
                "callnames": ["Geldkarte", "EC-Karte", "ECKarte", "Kreditkarte"],
                "fixed": False,  # False bedeutet: Kann aufgenommen werden
                "hidden": True,  # True bedeutet: Das Objekt ist nicht sichtbar
                "apply_f": af.o_ec_karte_apply_f,
                "prompt_f": op.o_ec_karte_prompt_f
            },
            "o_pinsel": {
                "name": "o_pinsel",
                "examine": "Ein alter, vertrockneter Pinsel",  # Text to me emitted when object is examined
                "help_text": "",  # Text to be emitted when player asks for help with object
                "ownedby": "p_innen",  # Which Player currently owns this item? Default: None
                "callnames": ["Pinsel"],
                "fixed": False,  # False bedeutet: Kann aufgenommen werden
                "hidden": False,  # True bedeutet: Das Objekt ist nicht sichtbar
                "apply_f": af.o_pinsel_apply_f,
                "prompt_f": op.o_pinsel_prompt_f
            },
            "o_farbeimer": {
                "name": "o_farbeimer",
                "examine": "Ein Eimer mit vertrockneter, rosa Farbe.",  # Text to me emitted when object is examined
                "help_text": "",  # Text to be emitted when player asks for help with object
                "ownedby": "p_innen",  # Which Player currently owns this item? Default: None
                "callnames": ["Farbeimer"],
                "fixed": False,  # False bedeutet: Kann aufgenommen werden
                "hidden": False,  # True bedeutet: Das Objekt ist nicht sichtbar
                "apply_f": af.o_farbeimer_apply_f,
                "prompt_f": op.o_farbeimer_prompt_f
            },
            "o_sprengladung":{
                "name": "o_sprengladung",
                "examine": "Eine Sprengladung. Hiermit muss man bestimmt vorsichtig sein. Sie hat einen Knopf, mit dem man sie aktivieren kann.",
                "help_text": "Damit kann man viel kaputt machen, aber sicher auch einiges aus dem Weg räumen",
                "ownedby": "p_innen",
                "callnames": ["Sprengladung"],
                "fixed": False,
                "hidden": False,
                "apply_f": af.o_sprengladung_apply_f,
                "prompt_f": op.o_sprengladung_prompt_f
            },
            #
            # Place: Felsen
            #
            "o_felsen": {
                "name": "o_felsen",
                "examine": "Ein großer Felsen",
                "help_text": "Ob der Felsen hier wirklich liegen soll?",
                "ownedby": "p_felsen",
                "callnames": ["Felsen", "Felsblock", "Stein", "Gesteinsblock"],
                "fixed": True,
                "hidden": False,
                "apply_f": af.o_felsen_apply_f,
                "prompt_f": op.o_felsen_prompt_f
            },
            #
            # Place: Höhle
            #
            "o_hauptschalter": {
                "name": "o_hauptschalter",
                "examine": "Ein großer Sicherungsschalter",
                "help_text": "Dieser Schalter sieht wichtig aus!",
                "ownedby": "p_hoehle",
                "callnames": ["Schalter", "Hauptschalter", "Sicherung", "Sicherungsschalter", "Breaker"],
                "fixed": True,
                "hidden": False,
                "apply_f": af.o_hauptschalter_apply_f,
                "prompt_f": op.o_hauptschalter_prompt_f
            }

        }

        #
        # Added new Stuff in place_defs? --> Uncomment the following functions in order to emit skeletons
        # for objects and their apply-Functions as well as ways.
        #


        #emit_waydefs(place_defs, way_defs)
        #self.emit_objdefs(place_defs, object_defs)

        self.from_definitions(place_defs, way_defs, object_defs)

    #
    # Utility Functions
    #
    def obj_name_from_friendly_name(self, n:str)->str:
        """
        Return the object name from a user friendly name. For example:
        Geldautomat --> o_geldautomat

        If identifier is given and not found within objects list, just return it

        """
        for v in self.objects.values():
            if n in v.callnames:
                return v.name
        return n

    def place_name_from_friendly_name(self, n:str)->str:
        """
        Return the object name from a user friendly name. For example:
        Geldautomat --> p_geldautomat

        If identifier is given and not found within objects list, just return it

        """
        dprint(dl.GAMESTATE,f"This is place_name_from_friendly_name({n})")
        for v in self.places.values():
            if n in v.callnames:
                return v.name
        return n

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
    def compile_current_game_context_for_llm_tools(self, pl: 'PlayerState') -> dict:  # Name angepasst
        context_data = {}

        # 1. Informationen für die Narration (Bleiben als detaillierte Beschreibungen)
        narration_details = {}
        narration_details["Ortsname"] = pl.location.callnames[0]
        narration_details["Beschreibung"] = pl.location.place_prompt_f(self,
                                                                       pl) if pl.location.place_prompt_f else pl.location.place_prompt

        # Objekte hier und in den Nachbarfeldern
        # Nachbarfelder nötig für Sätze wie "gehe zum Schuppen und untersuche den Blumentopf"
        narration_details["Objekte hier"] = []
        all_object_ids_in_context = []  # Diese Liste sammeln wir für die 'enum's
        for obj in pl.location.place_objects:
            if not obj.hidden:
                # Nutze prompt_f, um die objektspezifische Beschreibung für die Narration zu bekommen
                obj_description_text = obj.prompt_f(self, pl) if obj.prompt_f else obj.examine
                narration_details["Objekte hier"].append({obj.callnames[0]: obj_description_text})
                all_object_ids_in_context.append(obj.name)  # Fügen die interne ID hinzu
        # narration_details["Objekte in benachbarten Feldern"] = []
        # all_object_ids_in_neighborhood = []
        # for neigh in pl.location.ways:
        #     for obj in neigh.destination.place_objects:
        #         if not obj.hidden:
        #             # Nutze prompt_f, um die objektspezifische Beschreibung für die Narration zu bekommen
        #             obj_description_text = obj.prompt_f(self, pl) if obj.prompt_f else obj.examine
        #             narration_details["Objekte in benachbarten Feldern"].append({obj.callnames[0]: obj_description_text})
        #             all_object_ids_in_neighborhood.append(obj.name)  # Fügen die interne ID hinzu

        # Objekte im Inventar des Spielers
        narration_details["Objekte, die der Spieler bei sich trägt"] = []
        for obj in pl.inventory:
            obj_description_text = obj.prompt_f(self, pl) if obj.prompt_f else obj.examine
            narration_details["Objekte, die der Spieler bei sich trägt"].append(
                {obj.callnames[0]: obj_description_text})
            all_object_ids_in_context.append(obj.name)  # Fügen die interne ID hinzu

        # Wege von diesem Feld und von den Nachbarfeldern
        # Nachbarfelder sind nötig für Sätze wie
        # "Springe vom Schuppen und gehe zum Warenautomat"
        narration_details["Wo man hingehen kann"] = []
        all_place_ids_for_navigation = []  # Diese Liste sammeln wir für die 'enum's
        allw = pl.location.ways.copy()
        # dstn = [dn.destination.name for dn in pl.location.ways] # Names of ways we can go to (avoid circles)
        # dstn.append(pl.location.name)               # also own name
        # for w in pl.location.ways:
        #     d = w.destination
        #     for v in d.ways:
        #         if v.destination.name not in dstn:
        #             allw.append(v)
        #             dstn.append(v.destination.name)

        for w in pl.location.ways:
            if w.visible:
                wd = {}
                wd["Ziel"] = w.destination.name
                wd["Alternative Namen für das Ziel"] = w.destination.callnames
                if w.way_prompt_f:
                    wd["Spezielle Anweisungen für den Weg"] = w.way_prompt_f(self, pl, w)
                narration_details["Wo man hingehen kann"].append(wd)
                all_place_ids_for_navigation.append(w.destination.name)  # Fügen die Ziel-ID hinzu

        # Hund (NPC)
        from NPCPlayerState import NPCPlayerState
        dog_pl = next((p for p in self.players if isinstance(p, NPCPlayerState)), None)
        if dog_pl:
            dog_description = dog_pl.dog_prompt(self, pl)
            if dog_description:
                narration_details["Achtung"] = dog_description
                all_object_ids_in_context.append(
                    dog_pl.name)  # Fügen auch den Hund als "Objekt" hinzu, das man anwenden kann (z.B. Salami an Hund)

        context_data["narration_details"] = narration_details  # Dies ist der Block für den Narrator-Prompt

        # 2. Spezifische Listen für LLM Tools (enum-Werte)
        context_data["available_object_ids"] = list(
            set(all_object_ids_in_context))  # Set für Einzigartigkeit, dann zurück zu Liste
        #context_data["available_object_ids_in_neighborhood"] = list(set(all_object_ids_in_neighborhood))
        context_data["available_place_ids"] = list(set(all_place_ids_for_navigation))

        # Die IDs aller Spieler, die ein Ziel sein könnten (primär der Spieler selbst und NPCs)
        context_data["available_target_player_ids"] = [p.name for p in self.players if
                                                       isinstance(p, PlayerState) or isinstance(p, NPCPlayerState)]

        # Aktueller Ort und Inventar (für den Parsing-Prompt, falls spezifische Aktionen damit verbunden sind)
        context_data["player_location_id"] = pl.location.name
        context_data["player_inventory_ids"] = [item.name for item in pl.inventory]

        return context_data

    def compile_current_game_context(self, pl: PlayerState):
        """
        Compile current game context for LLM parse function
        """
        from Way import Way
        rval = {}
        details = {}
        details["Ortsname"] = pl.location.callnames[0]
        if pl.location.place_prompt_f != None:
            details["Beschreibung"] = pl.location.place_prompt_f(self,pl)
        else:
            details["Beschreibung"] = pl.location.place_prompt
        details["Objekte hier"] = { p.callnames[0]:f"{p.prompt_f(self,pl)}" for p in pl.location.place_objects if not p.hidden}
        details["Objekte, die des Spieler bei sich trägt"] = {p.callnames[0]:f"{p.prompt_f(self,pl)}" for p in pl.inventory}
        #details["Wo man hingehen kann"] = {w.destination.callnames[0]:{"Alternative Bezeichnungen für den Weg":w.destination.callnames}  for w in pl.location.ways if w.visible}
        wege = {}
        for w in pl.location.ways:
            if w.visible:
                wd={}
                wd["Ziel"] = w.destination.name
                wd["Alternative Namen für das Ziel"] = w.destination.callnames
                if w.way_prompt_f:
                    wd["Spezielle Anweisungen für den Weg"] = w.way_prompt_f(self,pl,w)
                wege[w.name] = wd
        details["Wo man hingehen kann"] = wege
        #
        # Dog somewhere near?
        #
        from NPCPlayerState import NPCPlayerState, DogState
        dog_pl = None
        dog_around = False
        r=""
        for p in self.players:
            if type(p) is NPCPlayerState:
                dog_pl = p
                break
        #
        # Dog might have been killed by explosive charge, so in fact dog_pl MAY be None
        #


        if dog_pl:
            dp = dog_pl.dog_prompt(self,pl)
            if dp != "":
                details["Achtung"] = dp

        # details["Spieler-Inventory"] = {i.callnames[0]:i.name for i in pl.get_inventory()}
        rval["Aktueller Ort"] = details
        return rval

    def verb_execute_json(self, pl: PlayerState, command_dict: dict) -> str:
        """ Instead of a string (see verb_execute) cmd is a dictionary as was returned by the LLM as structured
            return to LLM user input"""
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
            "umsehen":(self.verb_lookaround,0),
            "untersuche": (self.verb_examine,1),
            "hilfe":(self.verb_help,0),
            "gehe":(self.verb_walk,1),
            "llm": (self.verb_llm,0),
            "toeten": (self.verb_kill,1),
            "angreifen": (self.verb_attack,0),
            "inventory": (self.verb_inventory,0),
            "context": (self.verb_context,0),
            "dogstate": (self.verb_dogstate,0),
            "quit": (self.verb_quit,0),
            "nichts": (self.verb_noop,0),
            "interaktion": (self.verb_interact,2),
            "zurueckweisen": (self.verb_reject,1),
            "zurückweisen": (self.verb_reject, 1),
            "unbekannt": (self.verb_unknown,0)
        }
        verb,numargs = vtab.get(func_name,(None,None))
        r=verb(pl,**args)
        return r


    def verb_execute(self, pl: PlayerState, input: str) -> str:
        # tokens = input.split()
        import regex as re
        # Regulärer Ausdruck zur Tokenisierung von Eingaben:
        # Er erkennt zwei Arten von Token:
        #
        # 1. Strings in doppelten Anführungszeichen, z. B. "Das ist ein Text"
        #    - erlaubt auch Escape-Sequenzen wie \" oder \n
        #    - Aufbau:
        #        "(             # öffnendes Anführungszeichen
        #         (?:           # Start einer non-capturing group
        #            \\.        # ein Escape-Zeichen (Backslash + beliebiges Zeichen)
        #            |          # oder
        #            [^"\\]     # ein beliebiges Zeichen außer " oder \
        #         )*            # beliebig oft
        #        )"             # schließendes Anführungszeichen
        #
        # 2. Bezeichner (Identifiers), z. B. hallo, Größe_12, übermorgen
        #    - Erlaubt Unicode-Buchstaben inkl. Umlaute und Akzente
        #    - Aufbau:
        #        [\p{L}_]       # Ein Unicode-Buchstabe oder Unterstrich am Anfang
        #        [\p{L}\p{N}_]* # Danach beliebig viele Buchstaben, Ziffern oder Unterstriche
        #
        # Das ganze Pattern verwendet die Unicode-Zeichenklassen von `regex`:
        #    \p{L} = Letter (Unicode-Buchstabe)
        #    \p{N} = Number (Unicode-Ziffer)
        #
        # Finaler Regex:
        #    r'"(?:\\.|[^"\\])*"|[\p{L}_][\p{L}\p{N}_]*'
        #
        # Hinweis:
        # - Kein Whitespace-Matching oder Sonderzeichen wie +, =, etc. werden erkannt – sie bleiben unberücksichtigt.
        # - Damit eignet sich der Ausdruck gut für einfache Spracheingaben oder das Parsen einfacher Skriptzeilen.
        tokens = re.findall(r'#[^#]*#|[\p{L}_][\p{L}\p{N}_-]*[\p{L}\p{N}_]', input)
        #
        # Jetzt noch Anführungszeichen entfernen falls nötig
        #
        tokens = [t[1:-1] if t.startswith('#') else t for t in tokens]

        vtab = {
            "anwenden":(self.verb_apply,2),
            "nimm":(self.verb_take,1),
            "ablegen":(self.verb_drop,1),
            "umsehen":(self.verb_lookaround,0),
            "untersuche": (self.verb_examine,1),
            "hilfe":(self.verb_help,0),
            "gehe":(self.verb_walk,1),
            "llm": (self.verb_llm,0),
            "toeten": (self.verb_kill,1),
            "angreifen": (self.verb_attack,0),
            "inventory": (self.verb_inventory,0),
            "context": (self.verb_context,0),
            "dogstate": (self.verb_dogstate,0),
            "quit": (self.verb_quit,0),
            "nichts": (self.verb_noop,0),
            "interaktion": (self.verb_interact,2),
            "zurueckweisen": (self.verb_reject,1),
            "zurückweisen": (self.verb_reject, 1),
            "unbekannt": (self.verb_unknown,0)
        }
        verb,numargs = vtab.get(tokens[0],(None,None))
        if verb != None:
            r = ""
            arg1 = tokens[1] if len(tokens) > 1 else None
            arg2 = tokens[2] if len(tokens) > 2 else None
            if numargs == 0:
                r = verb(pl)
            elif numargs == 1:
                r = verb(pl,arg1)
            elif numargs == 2:
                r = verb(pl,arg1,arg2)
            else:
                raise Exception("Config Error!")
        else:
            r = "Unbekanntes Kommando"
        return r

    def verb_unknown(self, pl: PlayerState):
        from pprint import pprint
        print("LLM did not understand input correctly. Current Player atomic command queue:")
        pprint(pl.cmd_q)
        return "nichts"

    def verb_dogstate(self, pl: PlayerState):
        from NPCPlayerState import NPCPlayerState
        from pprint import pprint
        dgf = None
        for p in self.players:
            if type(p) is NPCPlayerState:
                dgf = p
                break
        if not dgf:
            return ("Kein Hund mehr im Spiel!!")
        else:
            pprint(dgf,depth=2)
            return "nichts"

    def verb_apply(self, pl: PlayerState, what, towhat=None):

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

    def verb_take(self, pl: PlayerState, whato):
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
                    tw_print(obj.take_f(self,pl))
                r= f"Du hast {what} nun bei dir"
            else:
                r = f"Du kannst {what} nicht aufnehmen"
        return r

    def verb_drop(self, pl: PlayerState, whato):
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

    def verb_lookaround_old(self, pl: PlayerState):
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
        from NPCPlayerState import NPCPlayerState
        for d in self.players:
            if type(d) is NPCPlayerState:
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

    def verb_lookaround_llm(self, pl: PlayerState):

        rval = self.llm.generate_scene_description(self.compile_current_game_context(pl))
        return rval

    def verb_lookaround(self, pl: PlayerState):
        r=self.llm.narrate(self,pl)
        return r


    def verb_help(self, pl: PlayerState):
        rval = """
    Du musst Dein Fahrrad reparieren, um rechtzeitig den Umschlag, den Du 
    hoffentlich noch bei dir hast, an sein Ziel zu bringen. Sonst geht die 
    Welt unter. 
    
    Folgende Kommandos kannst du absetzen:
    
    hilfe  ............................ Diese Hilfe
    inventory ......................... Zeigt an, was du gerade bei dir hast
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

    def verb_examine(self, pl: PlayerState, what: str):
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

    def verb_llm(self, pl:PlayerState):
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

    def verb_kill(self, pl: PlayerState, whom):
        self.game_over = True
        return f"{pl.name} tötet {whom} in heldischem Kampf"

    def verb_inventory(self, pl: PlayerState):
        tw_print("**Du trägst bei dir:**")
        for i in pl.get_inventory():
            tw_print(f'- "{i.name}" --> {i.examine}')
        return "nichts"

    def verb_context(self, pl:PlayerState):
        from pprint import pprint
        r = self.compile_current_game_context(pl)
        pprint(r)
        return "nichts"

    def verb_quit(self, pl: PlayerState):
        self.game_over  = True
        return f"{pl.name} beendet das Spiel."

    def verb_noop(self, pl: PlayerState):
        if type(pl) is PlayerState:
            return "Du tust nichts"
        else:
            return ""

    def verb_interact(self, pl: PlayerState, who, what):
        return f'{pl.name} an {who}:  "{what}"'

    def verb_reject(self, pl: PlayerState, why)->str:
        """ LLM rejects to do something because it did not understand user input and provides explanation in "why" """
        return f'***Nachricht von der Spielleitung:*** {why}'


    def verb_attack(self, pl: PlayerState, whom="")->str:
        """ Player attacks dog which needs to be in the same place as Player"""
        from NPCPlayerState import NPCPlayerState
        dog = None
        for d in self.players:
            if type(d) is NPCPlayerState:
                dog = d
                break
        if dog is None:
            return "Es gibt gar keinen Hund mehr im Spiel"

        if dog.location != pl.location:
            return "Da ist gar kein Hund bei dir, den Du angreifen könntest"

        else:
            r = dog.gets_attacked(self, pl)
            return ""
            #return f"(Angriff auf den Hund abgeschlossen)"



#
# Obstruction Check Functions
#








