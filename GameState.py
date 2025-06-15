from __future__ import annotations

import json

from Place import Place
from Way import Way
from typing import Dict, List
from PlayerState import PlayerState
from GameObject import GameObject
from GeminiInterface import GeminiInterface
from Utils import tw_print, dprint




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
            if v == None:
                visible = True
            else:
                visible = False



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
        from GameObject import GameObject
        for obj_name, obj_data in defs.items():
            obj = GameObject(
                name=obj_data["name"],
                examine=obj_data["examine"],
                help_text=obj_data.get("help_text", ""),
                fixed=obj_data.get("fixed", False),
                hidden=obj_data.get("hidden", False),
                callnames=obj_data.get("callnames", None),
                apply_f=obj_data.get("apply_f", None),
                reveal_f = obj_data.get("reveal_f", None),
                take_f = obj_data.get("take_f", None),
                prompt_f = obj_data.get("prompt_f", None)
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
        self.game_over = False             # Na hoffentlich noch nicht so schnell!
        self.llm = GeminiInterface()       # Unser Sprachmodell
        self.gamelog = []                  # Wir schneiden alles für das LLM mit
        #
        # Place definitions
        #

        place_defs = {
            "p_start": {
                "description": "Ein unbenannter Ort an einer staubigen, monotonen Strasse durch eine heiße Wüste. ",
                "place_prompt": """ Ein unbenannter, eigenartiger Ort an einer staubigen, monotonen Strasse durch eine heiße Wüste. 
                Es liegt hier das kaputte Fahrrad, welches zu reparieren ist. Die Straße erstreckt sich in beiden Richtungen 
                zum Horizont. Der Spieler kann erst wieder auf der Straße fahren, wenn sein Fahrrad repariert ist.
                """,
                "ways": ["w_start_warenautomat","w_start_geldautomat", "w_start_schuppen"],
                "objects": [""],
                "callnames": ["Start"]
            },
            "p_warenautomat": {
                "description": "Hier ist ein Warenautomat, an dem man Fahrradteile kaufen kann",
                "place_prompt": """Schon ulkig - Hier ist mitten in der Wüste ein Warenautomat, an dem man Fahrradteile kaufen kann. 
            """,
                "place_prompt_f": p_warenautomat_place_prompt_f,
                "ways": ["w_warenautomat_start", "w_warenautomat_geldautomat","w_warenautomat_schuppen","w_warenautomat_ubahn","w_warenautomat_felsen"],
                "objects": ["o_warenautomat"],
                "callnames": ["Warenautomat"]
            },
            "p_ubahn": {
                "description": "Eine U-Bahn-Station",
                "place_prompt": """Eine angenehm kühle U-Bahn-Station. Es ist offenbar länger niemand hier gewesen, aber dennoch ist alles sauber
                und aufgeräumt. An der Wand hängen einige Werbeplakate: eins für eine Limonade, eins für ein Reisebüro. Der Boden ist mit Marmorfliesen
                gefliest. Neonröhren tauchen alles in angenehmes Licht. Es tut gut, sich hier unten zu erfrischen und vor der WÜstenhitze zu verstecken,
                die an der Oberfläche herrscht. In der Station steht ein U-Bahn-Wagen, dessen Türen offen sind. Alles sieht sauber aus, es gibt keine
                Schmierereien oder Graffitis.

        """,
                "ways": ["w_ubahn_warenautomat", "w_ubahn_wagen"],
                "objects": ["o_muelleimer", "o_salami", "o_geheimzahl"],
                "callnames": ["U-Bahn", "UBahn", "U-Bahnhof"]
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
                "place_prompt": """Eine angenehm kühle U-Bahn-Station, aber die Luft ist etwas abgestanden. Es ist offenbar länger niemand hier gewesen, 
                aber dennoch ist alles sauber und aufgeräumt. An der Wand hängen einige Werbeplakate: eins für eine Limonade, eins für den neuen VW-Golf. 
                Der Boden ist mit Marmorfliesen
                gefliest. Neonröhren tauchen alles in angenehmes Licht. In der Station steht der U-Bahn-Wagen, mit dem du gerade gekommen bist, dessen Türen 
                stehen offen. Alles sieht sauber aus, es gibt keine Schmierereien oder Graffitis.
        """,
                "ways": ["w_ubahn2_wagen"],
                "objects": ["o_pizzaautomat", "o_geld_lire", "o_pizza"],
                "callnames": ["U-Bahn-2"]
            },
            "p_geldautomat": {
                "description": "Hier ist ein Geldautomat, an dem man Bargeld bekommen kann",
                "place_prompt": """Die Sonne brennt vom Himmel. Es ist furchtbar heiss. Wie ein Fremdkörper steht hier ein
                Geldautomat
            
        """,
                "ways": ["w_geldautomat_start", "w_geldautomat_warenautomat", "w_geldautomat_schuppen","w_geldautomat_felsen"],
                "objects": ["o_geldautomat", "o_geld_dollar"],
                "callnames": ["Geldautomat", "ATM"]
            },
            "p_schuppen": {
                "description": "Hier ist ein alter Holzschuppen",
                "place_prompt": """Wir befinden uns vor einem alten Holzschuppen. Mitten in der Wüste. Es ist heiss und die Sonne knallt vom Himmel.
            To be done
        """,
                "ways": ["w_schuppen_start", "w_schuppen_warenautomat", "w_schuppen_geldautomat","w_schuppen_innen","w_schuppen_dach", "w_schuppen_felsen"],
                "objects": ["o_schuppen","o_blumentopf","o_schluessel", "o_stuhl", "o_schrott"],
                "callnames": ["Schuppen", "Holzschuppen"]
            },
            "p_dach": {
                "description": "Das Dach des Holzschuppens",
                "place_prompt": """Wir befinden uns auf dem Dach des Holzschuppens von hier aus können wir weit blicken. Man sieht den Geldautomaten und
                den Warenautomaten, sowie einen Hügel aus Gestein. Hier gibt es auch einen alten Hebel.
            
        """,
                "ways": ["w_dach_schuppen"],
                "objects": ["o_hebel"],
                "callnames": ["Dach", "Schuppendach"]
            },
            "p_innen": {
                "description": "Im inneren des Holzschuppens",
                "place_prompt": """Im inneren des Schuppens ist es genauso heiss wie ausserhalb. Die Luft riecht nach Staub, und ein weiterer,
                unterschwelliger Verwesungsgeruch mischt sich dazu. Durch Ritzen in der Holzwand dringt gerade genug Licht in den Innenraum,
                das man sich umsehen kann und erkennt, was sich hier befindet.
            
        """,
                "ways": ["w_innen_schuppen"],
                "objects": ["o_leiter", "o_skelett", "o_geldboerse", "o_ec_karte", "o_pinsel", "o_farbeimer"],
                "callnames": ["innen", "Innenraum", "drinnen"]
            },
            "p_felsen": {
                "description": "Vor dem Berg liegt ein großer Felsen",
                "place_prompt": "",
                "place_prompt_f": p_felsen_place_prompt_f,
                "ways": ["w_felsen_hoehle","w_felsen_schuppen", "w_felsen_warenautomat", "w_felsen_geldautomat"],
                "objects": ["o_felsen"],
                "callnames": ["Felsen", "Berg", "Hügel", "Huegel", "Felsblock"]
            },
            "p_hoehle": {
                "description": "In die Höhle, deren Eingang freigesprengt wurde.",
                "place_prompt": "",
                "place_prompt_f": p_hoehle_place_prompt_f,
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
                "hidden": True
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
                "obstruction_check": w_felsen_hoehle_f,
                "description": ""
            },
            "w_hoehle_felsen": {
                "source": "p_hoehle",
                "destination": "p_felsen",
                "text_direction": "aus der Höhle heraus zum Felsen",
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
                "callnames": ["Umschlag", "Briefumschlag"],
                "ownedby": "",
                "fixed": False,
                "hidden": True,
                "apply_f": o_umschlag_apply_f
            },
            "o_warenautomat": {
                "name": "o_warenautomat",
                "examine": "Ein Warenautomat mit Fahrradteilen. Er enthält tatsächlich auch eine Fahrradkette! Der Automat ist gut in Schuss und wirkt neu.",  # Text to me emitted when object is examined
                "help_text": "",  # Text to be emitted when player asks for help with object
                "callnames": ["Warenautomat", "Automat"],
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
                "examine": "Ein Mülleimer, gefüllt mit Papier, Plastik und Glasmüll. Gottseidank ist nichts ekeliges drin.",  # Text to me emitted when object is examined
                "help_text": "",  # Text to be emitted when player asks for help with object
                "callnames": ["Mülleimer", "Muelleimer", "Abfalleimer", "Abfallbehälter", "Abfallbehaelter"],
                "ownedby": "p_ubahn",  # Which Player currently owns this item? Default: None
                "fixed": True,  # False bedeutet: Kann aufgenommen werden
                "hidden": False,  # True bedeutet: Das Objekt ist nicht sichtbar
                "apply_f": o_muelleimer_apply_f,
                "reveal_f": o_muelleimer_reveal_f
            },
            "o_salami": {
                "name": "o_salami",
                "examine": "Eine schöne italienische Salami. Schon etwas älter, aber noch geniessbar - zumindest für Hunde",  # Text to me emitted when object is examined
                "help_text": "",  # Text to be emitted when player asks for help with object
                "callnames": ["Salami", "Wurst"],
                "ownedby": "p_wagen",  # Which Player currently owns this item? Default: None
                "fixed": False,  # False bedeutet: Kann aufgenommen werden
                "hidden": False,  # True bedeutet: Das Objekt ist nicht sichtbar
                "apply_f": o_salami_apply_f
            },
            "o_geheimzahl": {
                "name": "o_geheimzahl",
                "examine": "Eine Geheimzahl...",  # Text to me emitted when object is examined
                "help_text": "",  # Text to be emitted when player asks for help with object
                "callnames": ["Geheimzahl", "Geheimcode", "PIN", "Geheimnummer"],
                "ownedby": "p_ubahn",  # Which Player currently owns this item? Default: None
                "fixed": False,  # False bedeutet: Kann aufgenommen werden
                "hidden": True,  # True bedeutet: Das Objekt ist nicht sichtbar
                "apply_f": o_geheimzahl_apply_f
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
                "apply_f": o_tuerschliesser_apply_f
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
                "apply_f": o_pizzaautomat_apply_f
            },
            "o_geld_lire": {
                "name": "o_geld_lire",
                "examine": "Italienische Lira! Eine ganze Menge davon! Die hat man schon lange nicht mehr gesehen!",  # Text to me emitted when object is examined
                "help_text": "",  # Text to be emitted when player asks for help with object
                "callnames": ["Lire", "Lira", "italienische Lira", "italienische Lire", "italienisches Geld"],
                "ownedby": "p_ubahn2",  # Which Player currently owns this item? Default: None
                "fixed": False,  # False bedeutet: Kann aufgenommen werden
                "hidden": True,  # True bedeutet: Das Objekt ist nicht sichtbar
                "apply_f": o_geld_lire_apply_f
            },
            "o_pizza": {
                "name": "o_pizza",
                "examine": "Eine Salami-Pizza mit viel Käse.",  # Text to me emitted when object is examined
                "help_text": "",  # Text to be emitted when player asks for help with object
                "callnames": ["Pizza"],
                "ownedby": "p_ubahn2",  # Which Player currently owns this item? Default: None
                "fixed": False,  # False bedeutet: Kann aufgenommen werden
                "hidden": True,  # True bedeutet: Das Objekt ist nicht sichtbar
                "apply_f": o_pizza_apply_f
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
                "apply_f": o_geldautomat_apply_f
            },
            "o_geld_dollar": {
                "name": "o_geld_dollar",
                "examine": "US-Dollar! Diese werden fast überall gerne genommen! Aber eben nur fast - es soll Warenautomaten geben, die sie nicht akzeptieren. Ob du wohl Glück hast?",  # Text to me emitted when object is examined
                "help_text": "",  # Text to be emitted when player asks for help with object
                "callnames": ["Dollar", "US-Dollar"],
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
                "examine": "Ein alter Holzschuppen, in dem womöglich interessante Dinge sind. "
                           "Der Schuppen muss aufgeschlossen werden, sonst kann man ihn nicht betreten.",  # Text to me emitted when object is examined
                "help_text": "",  # Text to be emitted when player asks for help with object
                "ownedby": "p_schuppen",  # Which Player currently owns this item? Default: None
                "callnames": ["Schuppen", "Holzschuppen"],
                "fixed": True,  # False bedeutet: Kann aufgenommen werden
                "hidden": False,  # True bedeutet: Das Objekt ist nicht sichtbar
                "apply_f": o_schuppen_apply_f
            },
            "o_blumentopf": {
                "name": "o_blumentopf",
                "examine": "Ein alter Blumentopf aus Ton.",  # Text to me emitted when object is examined
                "help_text": "",  # Text to be emitted when player asks for help with object
                "ownedby": "p_schuppen",  # Which Player currently owns this item? Default: None
                "callnames": ["Blumentopf"],
                "fixed": False,  # False bedeutet: Kann aufgenommen werden
                "hidden": False,  # True bedeutet: Das Objekt ist nicht sichtbar
                "apply_f": o_blumentopf_apply_f,
                "reveal_f": o_blumentopf_reveal_f
            },
            "o_schluessel": {
                "name": "o_schluessel",
                "examine": "Ein Schlüssel aus Metall.",  # Text to me emitted when object is examined
                "help_text": "",  # Text to be emitted when player asks for help with object
                "ownedby": "p_schuppen",  # Which Player currently owns this item? Default: None
                "callnames": ["Schlüssel", "Schluessel"],
                "fixed": False,  # False bedeutet: Kann aufgenommen werden
                "hidden": True,  # True bedeutet: Das Objekt ist nicht sichtbar
                "apply_f": o_schluessel_apply_f
            },
            "o_stuhl": {
                "name": "o_stuhl",
                "examine": "Ein rostiger, alter Gartenstuhl. Da macht man dich bestimmt dreckig, wenn man sich draufsetzt!",  # Text to me emitted when object is examined
                "help_text": "",  # Text to be emitted when player asks for help with object
                "ownedby": "p_schuppen",  # Which Player currently owns this item? Default: None
                "callnames": ["Stuhl", "Gartenstuhl", "Hocker"],
                "fixed": False,  # False bedeutet: Kann aufgenommen werden
                "hidden": False,  # True bedeutet: Das Objekt ist nicht sichtbar
                "apply_f": o_stuhl_apply_f
            },
            "o_schrott": {
                "name": "o_schrott",
                "examine": "Eine Menge Schrott! Hier kanns man stundelang herumsuchen - aber man wird hier nichts besonderes finden.",  # Text to me emitted when object is examined
                "help_text": "",  # Text to be emitted when player asks for help with object
                "ownedby": "p_schuppen",  # Which Player currently owns this item? Default: None
                "callnames": ["Schrott", "Schrotthaufen"],
                "fixed": True,  # False bedeutet: Kann aufgenommen werden
                "hidden": False,  # True bedeutet: Das Objekt ist nicht sichtbar
                "apply_f": o_schrott_apply_f
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
                "apply_f": o_hebel_apply_f
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
                "apply_f": o_leiter_apply_f, # Funktion: Leiter wurd "angewandt"
                "take_f": o_leiter_take_f # Funktion: Leiter wird aufgenommen
            },
            "o_skelett": {
                "name": "o_skelett",
                "examine": "Ein Skelett!! In einem Anzug!! Das ist wohl schon länger hier! Wie das wohl hierhin gekommen ist?",  # Text to me emitted when object is examined
                "help_text": "",  # Text to be emitted when player asks for help with object
                "ownedby": "p_innen",  # Which Player currently owns this item? Default: None
                "callnames": ["Skelett", "Knochenmann"],
                "fixed": True,  # False bedeutet: Kann aufgenommen werden
                "hidden": False,  # True bedeutet: Das Objekt ist nicht sichtbar
                "apply_f": o_skelett_apply_f,
                "reveal_f": o_skelett_reveal_f
            },
            "o_geldboerse": {
                "name": "o_geldboerse",
                "examine": "Eine alte Geldbörse aus Leder.",  # Text to me emitted when object is examined
                "help_text": "",  # Text to be emitted when player asks for help with object
                "ownedby": "p_innen",  # Which Player currently owns this item? Default: None
                "callnames": ["Geldboerse", "Geldbörse", "Portemonaie", "Brieftasche"],
                "fixed": False,  # False bedeutet: Kann aufgenommen werden
                "hidden": True,  # True bedeutet: Das Objekt ist nicht sichtbar
                "apply_f": o_geldboerse_apply_f,
                "reveal_f": o_geldboerse_reveal_f
            },
            "o_ec_karte": {
                "name": "o_ec_karte",
                "examine": "Eine alte EC-Karte. Ob die noch geht?",  # Text to me emitted when object is examined
                "help_text": "",  # Text to be emitted when player asks for help with object
                "ownedby": "p_innen",  # Which Player currently owns this item? Default: None
                "callnames": ["Geldkarte", "EC-Karte", "ECKarte", "Kreditkarte"],
                "fixed": False,  # False bedeutet: Kann aufgenommen werden
                "hidden": True,  # True bedeutet: Das Objekt ist nicht sichtbar
                "apply_f": o_ec_karte_apply_f
            },
            "o_pinsel": {
                "name": "o_pinsel",
                "examine": "Ein alter, vertrockneter Pinsel",  # Text to me emitted when object is examined
                "help_text": "",  # Text to be emitted when player asks for help with object
                "ownedby": "p_innen",  # Which Player currently owns this item? Default: None
                "callnames": ["Pinsel"],
                "fixed": False,  # False bedeutet: Kann aufgenommen werden
                "hidden": False,  # True bedeutet: Das Objekt ist nicht sichtbar
                "apply_f": o_pinsel_apply_f
            },
            "o_farbeimer": {
                "name": "o_farbeimer",
                "examine": "Ein Eimer mit vertrockneter, rosa Farbe.",  # Text to me emitted when object is examined
                "help_text": "",  # Text to be emitted when player asks for help with object
                "ownedby": "p_innen",  # Which Player currently owns this item? Default: None
                "callnames": ["Farbeimer"],
                "fixed": False,  # False bedeutet: Kann aufgenommen werden
                "hidden": False,  # True bedeutet: Das Objekt ist nicht sichtbar
                "apply_f": o_farbeimer_apply_f
            },
            "o_sprengladung":{
                "name": "o_sprengladung",
                "examine": "Eine Sprengladung. Hiermit muss man bestimmt vorsichtig sein. Sie hat einen Knopf, mit dem man sie aktivieren kann.",
                "help_text": "Damit kann man viel kaputt machen, aber sicher auch einiges aus dem Weg räumen",
                "ownedby": "p_innen",
                "callnames": ["Sprengladung"],
                "fixed": False,
                "hidden": False,
                "apply_f": o_sprengladung_apply_f
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
                "apply_f": o_felsen_apply_f
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
                "apply_f": o_hauptschalter_apply_f
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
        dprint(f"This is place_name_from_friendly_name({n})")
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

    def compile_current_game_context(self, pl: PlayerState):
        from Way import Way
        rval = {}
        details = {}
        details["Ortsname"] = {pl.location.callnames[0]:pl.location.name}
        if pl.location.place_prompt_f != None:
            details["Beschreibung"] = pl.location.place_prompt_f(self,pl)
        else:
            details["Beschreibung"] = pl.location.place_prompt
        details["Objekte hier"] = { p.callnames[0]:f"{p.examine}" for p in pl.location.place_objects if not p.hidden}
        details["Wo man hingehen kann"] = {w.destination.callnames[0]:w.destination.name for w in pl.location.ways if w.visible}
        #
        # Dog somewhere near?
        #
        from NPCPlayerState import NPCPlayerState, DogState
        dog_pl = None
        dog_around = False
        r=""
        for p in self.players:
            if isinstance(p,NPCPlayerState):
                dog_pl = p
                break
        #
        # Dog might have been killed by explosive charge, so in fact dog_pl MAY be None
        #


        if dog_pl is not None:
            if dog_pl.location == pl.location:
                r = "Hier ist ein großer Hund."
                dog_around = True
            else:

                for w in dog_pl.location.ways:
                    if w.destination == pl.location:
                        r = f"Großer Hund bei/in {dog_pl.location.callnames[0]}."
                        dog_around = True
        if dog_around:
            match dog_pl.dog_state:
                case DogState.EATING:
                    r=r+" Der Hund frisst gerade etwas."
                case DogState.TRACE:
                    r=r+" Der Hund hat Witterung aufgenommen und verfolgt den Spieler."
                case DogState.ATTACK:
                    r=r+" Der Hund ist wütend und in Angriffslaune."
                case _:
                    r = r+" Der Hund tut nichts weiter."
            details["Achtung"] = r

        # details["Spieler-Inventory"] = {i.callnames[0]:i.name for i in pl.get_inventory()}
        rval["Aktueller Ort"] = details
        return rval

    def verb_apply(self, pl: PlayerState, what, towhat):

        if towhat == None:
            # r = f"apply {what} in this context"
            r=""
            o_what = self.objects.get(what)
            if o_what != None:
                r = r+ "\n"+ o_what.apply_f(self, pl, o_what, None)
        else:
            # r = f"apply {what} to {towhat} in this context"
            r=""
            o_what = self.objects.get(what)
            if towhat=="dog":
                o_towhat = PlayerState("dog", None) # Temporary Player State
            else:
                o_towhat = self.objects.get(towhat)

            if o_what != None:
                r = r+ "\n" + o_what.apply_f(self, pl, o_what, o_towhat)

        return r

    def verb_take(self, pl: PlayerState, what):

        loc = pl.location
        # obj = loc.place_objects.get(what)
        obj = None
        for o in loc.place_objects:
            if o.name == what:
                obj = o
                break
        if obj == None:
            r= "Sowas gibt es hier nicht."
        else:
            pl.add_to_inventory(obj)
            if obj.take_f != None:
                tw_print(obj.take_f(self,pl))
            r= f"Du hast {what} nun bei dir"

        return r

    def verb_drop(self, pl: PlayerState, what):

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

    def verb_lookaround_traditional(self, pl: PlayerState):
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

    def verb_lookaround(self, pl: PlayerState):

        rval = self.llm.generate_scene_description(self.compile_current_game_context(pl))
        return rval

    def verb_help(self, pl: PlayerState):
        rval = f"***Du bist hier: {pl.location.callnames[0]}***\n"
        rval = rval+pl.location.description+"\n"
        #
        # General: Hund und Sprengladung
        #
        rval = rval + """
        
        Dir stehen folgende Kommandos zur Verfügung:
        
        nimm <objekt>:        Ein Objekt in Dein Ingentory aufnehmen
        ablegen <objekt>:     Ein Objekt aus Deinem Inventory am aktuellen Ort ablegen
        untersuche <objekt>:  Ein Objekt untersuchen
        anwenden <o1> <o2>:   Objekt o1 auf Objekt o2 anwenden
        anwenden <o>:         Objekt o anwenden
        gehe <ort>:           An einen Ort gehen (Ort muss dir bei "umsehen" angezeigt werden)
        inventory:            Dein Inventory ansehen
        
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
        r = f"Du bist nun hier: {pl.location.name} - {pl.location.description}"
        return r

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
            if self.objects[what].reveal_f != None:
                retstr = retstr + self.objects[what].reveal_f(self,pl,what, None)

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
    if pl.location != gs.places["p_wagen"]:
        return "Hier ist kein Türschließer"

    if gs.ubahn_in_otherstation:
        gs.ubahn_in_otherstation = False
        gs.ways["w_wagen_ubahn"].visible = True
        gs.ways["w_wagen_ubahn2"].visible = False
        gs.ways["w_ubahn_wagen"].visible = True
        gs.ways["w_ubahn2_wagen"].visible = False
        return "Die Tür schließt sich. Der Wagen setzt sich in Bewegung, und fährt zurück zum ersten Bahnsteig. Die Tür öffnet sich wieder."
    else:
        gs.ubahn_in_otherstation = True
        gs.ways["w_wagen_ubahn"].visible = False
        gs.ways["w_wagen_ubahn2"].visible = True
        gs.ways["w_ubahn_wagen"].visible = False
        gs.ways["w_ubahn2_wagen"].visible = True
        return "Die Tür schließt sich. Der Wagen setzt sich in Bewegung, und hält nach kurzer Fahrt an einem zweiten Bahnsteig. Die Tür öffnet sich wieder."



def o_pizzaautomat_apply_f(gs: GameState, pl: PlayerState=None, what: GameObject=None, onwhat: GameObject=None) -> str:
    pass


def o_geld_lire_apply_f(gs: GameState, pl: PlayerState=None, what: GameObject=None, onwhat: GameObject=None) -> str:
    if pl.location.name == "p_warenautomat" and onwhat.name == "o_warenautomat":
        if not pl.is_in_inventory(gs.objects["o_umschlag"]):
            return "Es wäre alles so schön - leider fällt dir auf, dass du den wichtigen Briefumschlag irgendwo verlegt hast. Finde ihn erst!"
        if not gs.hebel:
            if not gs.hauptschalter:
                return "Eigentlich sollte dies gar nicht passieren können - aber der Automat hat keinen Strom!"
            gs.game_over = True
            return """Du wirfst die italienischen Lira in den Warenautomat - und er akzeptiert sie ohne zu murren.
Du erwirbst eine Fahrradkette, reparierst damit dein kaputtes Fahrrad, und radelst von dannen.
***Du hast das Spiel gewonnen!***"""
        else:
            return "Der Automat liegt auf dem Rücken - da kann man gar nichts einwerfen!"
    else:
        return "Das geht hier nicht!"


def o_pizza_apply_f(gs: GameState, pl: PlayerState=None, what: GameObject=None, onwhat: GameObject=None) -> str:
    pass


def o_geldautomat_apply_f(gs: GameState, pl: PlayerState=None, what: GameObject=None, onwhat: GameObject=None) -> str:
    pass


def o_geld_dollar_apply_f(gs: GameState, pl: PlayerState=None, what: GameObject=None, onwhat: GameObject=None) -> str:
    #
    # Ich bin das Dollar-Bündel - mich kann man auf den Warenautomaten und auf den Pizza-Automaten anwenden, wenn
    # der Raum stimmt
    #

    if pl.location.name == "p_warenautomat" and onwhat.name=="o_warenautomat":
        if gs.hebel:
            return 'Der Warenautomat liegt auf dem Bauch. Er ist zwar völlig intakt, und nicht zerbrochen, aber da kann man kein Geld einwerfen!'
        else:
            if not gs.hauptschalter:
                return "Der Automat ist ausgeschaltet"
            else:
                return 'Der Automat zeigt an: "Mi dispiace molto, ma in questa macchina si accettano solo lire italiane.". Er will also italienische Lira haben - aber wo bekomme ich die her?'

    if pl.location.name == "p_ubahn2" and onwhat.name=="o_pizzaautomat":
        #
        # Wenn der Hund in einem früheren Spielschritt die Pizza gegessen hat, mache eine neue
        #
        if gs.objects.get("o_pizza"):
            gs.objects["o_pizza"].hidden = False
        else:
            gs.objects["o_pizza"] = GameObject("o_pizza","Eine schöne, frisch gemachte Pizza","",False,None)
            gs.objects["o_pizza"].hidden = False
            gs.objects["o_pizza"].ownedby = gs.places["p_ubahn2"]
        gs.objects["o_geld_lire"].hidden = False
        return 'Es dauert, und der Automat bereitet eine wunderschöne Pizza für dich zu, die Du im Ausgabefach findest. Und dann klappert es - es wird Dir Wechselgeld ausgezahlt, **und zwar in italienischen Lira!**'
    return "Du scheinst mit den Dollars hier wnig anfangen zu können..."


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
    if not gs.hauptschalter:
        return "Du ruckelst am Hebel, aber nichts passiert"
    if pl != None:
        if pl.location == gs.places["p_dach"]:
            if gs.hebel:
                gs.hebel = False
                gs.ways["w_warenautomat_ubahn"].visible = False
                gs.places["p_warenautomat"].description = "Hier steht ein Warenautomat, an dem man Fahrradteile kaufen kann."
                gs.objects["o_warenautomat"].examine = "Ein Warenautomat mit Fahrradteilen. Er enthält tatsächlich auch eine Fahrradkette! Jetzt bräuchte man Geld - und zwar italienische Lira. Dieser Automat akzeptiert nur diese!"
                return "Es rumpelt - und der Warenautomat richtet sich wieder auf!"
            else:
                gs.hebel = True
                gs.ways["w_warenautomat_ubahn"].visible = True
                gs.objects["o_warenautomat"].examine = "Ein Warenautomat, der auf dem Rücken liegt. Da wo er stand, führt eine Treppe nach unten!"
                gs.places["p_warenautomat"].description = "Hier liegt ein Warenautomat auf dem Rücken. Da wo er wohl gestanden hat, ist eine Öffnung im Boden. Man sieht darin eine Treppe - es geht zu einer U-Bahn-Station!"
                return "Es rumpelt - Die siehst, wie der Warenautomat sich langsam auf den Rücken legt. Da wo er stand, ist nun eine Öffnung - und darin eine Treppe zu einer U-Bahn-Station!"
        else:
            return "Hier ist kein Hebel!"
    else:
        return "??? Kein Spieler ???"


def o_sprengladung_apply_f(gs: GameState, pl: PlayerState=None, what: GameObject=None, onwhat: GameObject=None) -> str:
    from ExplosionState import ExplosionState
    xpl = ExplosionState(gs, location=pl.location)
    xpl.name = "Explosion"
    gs.players.append(xpl)
    return "Die Sprengladung ist nun scharf gemacht!"

def o_felsen_apply_f(gs: GameState, pl: PlayerState=None, what: GameObject=None, onwhat: GameObject=None) -> str:
    return "Wie willst Du denn den Felsen auf IRGENDWAS anwenden? Du hast keine Superkräfte!"

def o_hauptschalter_apply_f(gs: GameState, pl: PlayerState=None, what: GameObject=None, onwhat: GameObject=None) -> str:
    if gs.hauptschalter:
        return "Du hast den Schalter bereits betätigt - alles hat Strom"
    else:
        gs.hauptschalter = True
        return "Du betätigst den Schalter. Irgendwo läuft ein Generator an - du hörst elektrisches Summen... Strom!"

def o_leiter_apply_f(gs: GameState, pl: PlayerState=None, what: GameObject=None, onwhat: GameObject=None) -> str:
    #
    # Ich bin die Leiter - einzig sinnvolle Applikation: an den Schuppen anlehnen
    #
    if pl != None:
        #
        # Haben wir die Leiter dabei?
        #
        if onwhat != None and isinstance(onwhat,PlayerState) and onwhat.name == "dog":
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

def o_leiter_take_f(gs: GameState, pl: PlayerState=None) -> str:
    """ If Leiter is taken away, some paths may become invisible"""
    if gs.leiter:
        gs.leiter = False
        return "Du kannst jetzt nicht mehr auf den Schuppen klettern"
    else:
        gs.leiter = False
        return ""

def o_skelett_apply_f(gs: GameState, pl: PlayerState=None, what: GameObject=None, onwhat: GameObject=None) -> str:
    pass


def o_geldboerse_apply_f(gs: GameState, pl: PlayerState=None, what: GameObject=None, onwhat: GameObject=None) -> str:
    pass


def o_ec_karte_apply_f(gs: GameState, pl: PlayerState=None, what: GameObject=None, onwhat: GameObject=None) -> str:
    if not gs.hauptschalter:
        return "Sieht so aus, als wäre der Automat ausgeschaltet"

    if pl.location.name!="p_geldautomat" and onwhat.name!="o_geldautomat":
        return "Ich verstehe nicht, was genau du mit der Geldkarte machen willst!"

    print(f"{'*'*60}")
    print(f"*{' '*58}*")
    s=("Bitte geben sie die Geheimzahl ein!").center(58," ")
    print(f'*{s}*')
    print(f"*{' ' * 58}*")
    print(f"{'*' * 60}")
    z = -1
    while z<0:
        x = input("Geheimzahl: ")
        if x.isdigit():
            z = int(x)
    if gs.geheimzahl == z:
        gs.objects["o_geld_dollar"].visible = True
        return "**Die Zahl stimmt!** Du tippst die entsprechenden Tasten - der Automat rattert, und spuckt ein Bündel Scheine aus. Frisch gedruckte US-Dollar!"
    else:
        return " --- Die Zahl ist falsch. ---"


def o_pinsel_apply_f(gs: GameState, pl: PlayerState=None, what: GameObject=None, onwhat: GameObject=None) -> str:
    pass


def o_farbeimer_apply_f(gs: GameState, pl: PlayerState=None, what: GameObject=None, onwhat: GameObject=None) -> str:
    pass

#
# Reveal Functions
#
def o_blumentopf_reveal_f(gs: GameState, pl:PlayerState=None, what: GameObject=None, onwhat: GameObject=None) ->str:
    if gs.objects["o_schluessel"].hidden:
        retstr = "Ein alter Blumentopf - aber warte: **unter dem Blumentopf liegt ein Schlüssel!!!**"
        gs.objects["o_blumentopf"].examine = "Unter diesem Blumentopf hast Du den Schlüssel gefunden"
        gs.objects["o_schluessel"].hidden = False
        return retstr
    else:
        return gs.objects["o_blumentopf"].examine

def o_skelett_reveal_f(gs: GameState, pl:PlayerState=None, what: GameObject=None, onwhat: GameObject=None) ->str:
    if gs.objects["o_geldboerse"].hidden:
        gs.objects["o_geldboerse"].hidden = False
        gs.objects["o_skelett"].examine = "Bei diesem Knochenmann hast Du eine Geldbörse gefunden!"
        return "Oh weh, der sitzt wohl schon länger hier! Ein Skelett, welches einen verschlissenen Anzug trägt. **Im Anzug findest du eine Geldboerse!**"

    else:
        return gs.objects["o_skelett"].examine

def o_geldboerse_reveal_f(gs: GameState, pl:PlayerState=None, what: GameObject=None, onwhat: GameObject=None) ->str:
    if gs.objects["o_ec_karte"].hidden:
        gs.objects["o_ec_karte"].hidden = False
        gs.objects["o_geldboerse"].examine = "In dieser Geldbörse hast Du eine EC-Karte gefunden"
        return "Fein! Hier ist eine EC-Karte! Die passt bestimmt in einen Geldautomaten!"
    else:
        return gs.objects["o_geldboerse"].examine

def o_muelleimer_reveal_f(gs: GameState, pl:PlayerState=None, what: GameObject=None, onwhat: GameObject=None) ->str:
    if gs.objects["o_geheimzahl"].hidden:
        from random import randint
        gs.geheimzahl = randint(1, 9999)
        gs.objects["o_geheimzahl"].hidden = False
        gs.objects["o_geheimzahl"].examine = f"Eine Geheimzahl: {gs.geheimzahl:04}"
        return f"Im Mülleimer findest Du einen Zettel mit einer Geheimzahl! Die Geheimzahl ist: {gs.geheimzahl:04}"
    else:
        return gs.objects["o_geheimzahl"].examine


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

def w_felsen_hoehle_f(gs: GameState):
    if gs.felsen:
        return "Da könnte ein Weg hinter dem Felsen sein - aber der Felsen liegt im Weg!"
    else:
        return "Free"

#
# Prompt Functions for dynamic prompts
#
def p_warenautomat_place_prompt_f(gs: GameState, pl: PlayerState=None) -> str:
    rv = "Ein heisser Tag mitten in der Wüste. Die Luft ist trocken flirrt vor Hitze. Die Sonne knallt unerbittlich vom Himmel herab"
    if gs.hebel:
        return rv+"Hier ist ein Warenautomat, der auf dem Rücken liegt. Wo er stand, ist nun ein Treppenabgang zu einer U-Bahn-Station"
    else:
        return rv+"Hier ist ein Warenautomat mit Fahrradteilen. Er enthält viele Teile. Er enthält auch eine Fahrradkette"

def p_felsen_place_prompt_f(gs:GameState, pl: PlayerState)-> str:
    rv = """Ein heisser Tag mitten in der Wüste. Die Luft ist trocken und heiss, die Sonne knallt unerbittlich vom Himmel herab. Hier
    ist ein Hügel aus Gestein. Das gestein ist so bröckelig, dass man nicht auf den Hügel steigen kann.
    """
    if gs.felsen:
        return f"{rv} Ein Trampelpfad führt zu dem Hügel und endet vor einem Felsblock."
    else:
        return f"{rv} Wo vorher ein Felsblock lag, ist nun der Eingang in eine Höhle."

def p_hoehle_place_prompt_f(gs: GameState, pl: PlayerState) -> str:
    rv = """Im inneren der Höhle ist es schön kühl. Die Wände sind aus Gestein, der Boden aus gestampftem Lehm. An der Wand ein
    großer Schalter"""
    if gs.hauptschalter:
        return f"{rv} Eine Glühbirne hängt von der Decke und erleuchtet die Höhle. Man kann elektrisches Summen vernehmen."
    else:
        return f"{rv} Eine Glühbirne hängt von der Decke, aber sie ist ausgeschaltet. Das einzige Licht kommt vom Höhleneingang"


def huhu() -> str:
    return ("--- huhu ---")



