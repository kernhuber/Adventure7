"""
Creates data/world_bootstrap.json
"""

import game_apply_functions as af
import game_take_functions as tf
import game_reveal_functions as rf
import game_obstruction_check_functions as ocf
import place_prompts as pp
import object_prompts as op
import way_prompts as wp
import os
import json
from utils import dl, dprint

module_map = {
    "game_apply_functions": af,
    "game_take_functions": tf,
    "game_reveal_functions": rf,
    "game_obstruction_check_functions": ocf,
    "place_prompts": pp,
    "object_prompts": op,
    "way_prompts": wp,
}

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
        "ways": ["w_start_warenautomat", "w_start_geldautomat", "w_start_schuppen"],
        "objects": [""],
        "callnames": ["Start"]
    },
    "p_warenautomat": {
        "description": "Hier ist ein Warenautomat, an dem man Fahrradteile kaufen kann",
        "place_prompt": "",
        "place_prompt_f": pp.p_warenautomat_place_prompt_f,
        "ways": ["w_warenautomat_start", "w_warenautomat_geldautomat", "w_warenautomat_schuppen",
                 "w_warenautomat_ubahn", "w_warenautomat_felsen"],
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
        "callnames": ["Wagen", "Bahnwagen", "U-Bahnwagen"]
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
        "ways": ["w_geldautomat_start", "w_geldautomat_warenautomat", "w_geldautomat_schuppen", "w_geldautomat_felsen"],
        "objects": ["o_geldautomat", "o_geld_dollar"],
        "callnames": ["Geldautomat", "ATM"]
    },
    "p_schuppen": {
        "description": "Hier ist ein alter Holzschuppen",
        "place_prompt": "",
        "place_prompt_f": pp.p_schuppen_place_prompt_f,
        "ways": ["w_schuppen_start", "w_schuppen_warenautomat", "w_schuppen_geldautomat", "w_schuppen_innen",
                 "w_schuppen_dach", "w_schuppen_felsen"],
        "objects": ["o_schuppen", "o_blumentopf", "o_schluessel", "o_stuhl", "o_schrott"],
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
        "objects": ["o_leiter", "o_pinsel", "o_farbeimer"],
        "callnames": ["innen", "Innenraum", "drinnen", "nach innen", "in den schuppen"]
    },
    "p_felsnische": {
        "description": "Vor dem Berg liegt ein großer Felsen",
        "place_prompt": "",
        "place_prompt_f": pp.p_felsnische_place_prompt_f,
        "ways": ["w_felsen_hoehle", "w_felsen_schuppen", "w_felsen_warenautomat", "w_felsen_geldautomat"],
        "objects": ["o_felsen"],
        "callnames": ["Felsen", "Berg", "Hügel", "Huegel", "Felsblock"]
    },
    "p_hoehle": {
        "description": "In die Höhle, deren Eingang freigesprengt wurde.",
        "place_prompt": "",
        "place_prompt_f": pp.p_hoehle_place_prompt_f,
        "ways": ["w_hoehle_felsen"],
        "objects": ["o_skelett", "o_geldboerse", "o_ec_karte"],
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
            # Place: p_felsnische
            #
            "w_felsen_schuppen": {
                "source": "p_felsnische" ,
                "destination": "p_schuppen",
                "text_direction": "zum Schuppen",
                "obstruction_check": None,
                "description": ""
            },
            "w_schuppen_felsen": {
                "source": "p_schuppen",
                "destination": "p_felsnische",
                "text_direction": "zum Felsen",
                "obstruction_check": None,
                "description": ""
            },
            "w_felsen_warenautomat": {
                "source": "p_felsnische",
                "destination": "p_warenautomat",
                "text_direction": "zum Warenautomat",
                "obstruction_check": None,
                "description": ""
            },
            "w_warenautomat_felsen": {
                "source": "p_warenautomat",
                "destination": "p_felsnische",
                "text_direction": "zum Felsen",
                "obstruction_check": None,
                "description": ""
            },
            "w_felsen_geldautomat": {
                "source": "p_felsnische",
                "destination": "p_geldautomat",
                "text_direction": "zum Geldautomat",
                "obstruction_check": None,
                "description": ""
            },
            "w_geldautomat_felsen": {
                "source": "p_geldautomat",
                "destination": "p_felsnische",
                "text_direction": "zum Felsen",
                "obstruction_check": None,
                "description": ""
            },
            "w_felsen_hoehle": {
                "source": "p_felsnische",
                "destination": "p_hoehle",
                "text_direction": "in die Höhle",
                "obstruction_check": ocf.w_felsen_hoehle_f,
                "description": ""
            },
            "w_hoehle_felsen": {
                "source": "p_hoehle",
                "destination": "p_felsnische",
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
                "take_f": tf.o_blumentopf_take_f,
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
                "ownedby": "p_hoehle",  # Which Player currently owns this item? Default: None
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
                "ownedby": "p_hoehle",  # Which Player currently owns this item? Default: None
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
                "ownedby": "p_hoehle",  # Which Player currently owns this item? Default: None
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
                "ownedby": "p_felsnische",
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


# EXPORTER UTILITIES AND FINAL CALL (re-added)

def _func_to_string(fn, module_map):
    """
    Turn a known callable into a stable "Module.func" string for JSON export.
    Only functions coming from the known modules in module_map are exported.
    Unknown callables return None.
    """
    if not fn or not callable(fn):
        return None

    # Try to find the owning module entry in module_map by identity
    for mod_name, mod in module_map.items():
        cand = getattr(mod, getattr(fn, "__name__", ""), None)
        if cand is fn:
            return f"{mod_name}.{fn.__name__}"
    return None

def _export_world_to_json(place_defs, way_defs, object_defs, module_map, path="data/world_bootstrap.json"):
    """
    Export the in-memory definition dicts (place_defs / way_defs / object_defs) to a JSON file.
    Callbacks are converted to "Module.func" strings compatible with services.world_loader.WorldLoader.load().
    """

    def convert_places(src):
        out = {}
        for name, p in (src or {}).items():
            if not isinstance(p, dict):
                # If definitions are not plain dicts, assume already normalized
                p = dict(p)
            q = dict(p)
            # normalize callback fields
            if "place_prompt_f" in q:
                q["place_prompt_f"] = _func_to_string(q.get("place_prompt_f"), module_map)
            out[name] = q
        return out

    def convert_ways(src):
        out = {}
        for name, w in (src or {}).items():
            if not isinstance(w, dict):
                w = dict(w)
            q = dict(w)
            if "obstruction_check" in q:
                q["obstruction_check"] = _func_to_string(q.get("obstruction_check"), module_map)
            if "way_prompt_f" in q:
                q["way_prompt_f"] = _func_to_string(q.get("way_prompt_f"), module_map)
            out[name] = q
        return out

    def convert_objects(src):
        out = {}
        for name, o in (src or {}).items():
            if not isinstance(o, dict):
                o = dict(o)
            q = dict(o)
            for key in ("apply_f", "reveal_f", "take_f", "prompt_f"):
                if key in q:
                    q[key] = _func_to_string(q.get(key), module_map)
            out[name] = q
        return out

    data = {
        "place_defs": convert_places(place_defs),
        "way_defs": convert_ways(way_defs),
        "object_defs": convert_objects(object_defs),
    }

    # Ensure target directory exists
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)
        dprint(dl.GAMESTATE, f"[world.json] Export erfolgreich nach: {path}")
    except Exception as e:
        dprint(dl.GAMESTATE, f"[world.json] Export-Fehler: {e}")


if __name__ == "__main__":
    _export_world_to_json(place_defs, way_defs, object_defs, module_map)