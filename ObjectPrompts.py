"""
prompt functions for Game Objects go here
"""

from GameState import GameState
from PlayerState import PlayerState


def o_umschlag_prompt_f(gs:GameState, pl:PlayerState) -> str:
    return """ 
Briefumschlag
=============
- Dicker grauer Umschlag
- Verschlossen mit einem roten Siegel mit einem Hundekopf"""



def o_warenautomat_prompt_f(gs:GameState, pl:PlayerState) -> str:
    r = """
Warenautomat
============
- Großer, schwarzer Warenautomat
- Enthält Fahrradteile
- Beschriftungen in  italienischer Sprache
- Sieht älter, aber nicht beschädigt aus
    """
    if gs.hebel:
        r = r+ "- Liegt auf dem Rücken und ist ausgeschaltet"
        "- Wo er stand, ist nun eine Öffnung im Boden"
        "- Aus der Öffnung kommt angenehm kühle Luft"
        "- Es ist eine Treppe in der Öffnung"
    else:
        r = r+"- steht aufrecht und stabil da\n"
        if gs.hauptschalter:
            r=r+"- Ist angeschaltet und bereit, Teile gegen Geld auszugeben\n"
        else:
            r=r+"- Ist ausgeschaltet und funktioniert nicht, solange kein Strom da ist\n"
    return r



#             "o_fahrradkette": {
#                 "name": "o_fahrradkette",
#                 "examine": "Genau die Fahrradkette, die du zum Gewinnen des Spiels benötigst!",
#                 "help_text": "",
#                 "callnames": ["Fahrradkette", "Kette"],
#                 "ownedby": "p_warenautomat",
#                 "fixed": False,
#                 "hidden": True,
#                 "apply_f": af.o_fahrradkette_apply_f
#             },

def o_fahrradkette_prompt_f(gs:GameState, pl:PlayerState) -> str:
    return """
Fahrradkette
============
- Eine schöne, neue stabile Fahrradkette
- Kann die kaputte Fahrradkette ersetzen

    """


def o_fahrrad_prompt_f(gs:GameState, pl:PlayerState) -> str:
    return """
Fahrrad    
=======
- Ein stabiles, mattschwarzes Trecking-Rad
- sehr modern
- liegt auf der Seite
- Fahrradkette ist gerissen und kaputt
    """

#             #
#             # Place: p_ubahn
#             #
#

def o_muelleimer_prompt_f(gs:GameState, pl:PlayerState) -> str:
    return """
Mülleimer
=========
- Ein Mülleimer, wie man ihn an öffentlichen Orten vorfindet
- Farbe grün
- Aus Metall
- Hat Deckel mit Öffnung zum Mülleinwurf
    """
#             "o_salami": {
#                 "name": "o_salami",
#                 "examine": "Eine schöne italienische Salami. Schon etwas älter, aber noch geniessbar - zumindest für Hunde",  # Text to me emitted when object is examined
#                 "help_text": "",  # Text to be emitted when player asks for help with object
#                 "callnames": ["Salami", "Wurst"],
#                 "ownedby": "p_wagen",  # Which Player currently owns this item? Default: None
#                 "fixed": False,  # False bedeutet: Kann aufgenommen werden
#                 "hidden": False,  # True bedeutet: Das Objekt ist nicht sichtbar
#                 "apply_f": af.o_salami_apply_f
#             },

def o_salami_prompt_f(gs:GameState, pl:PlayerState) -> str:
    return """
Salami
======
- Eine große Salami
- Mit Edelschimmel umgeben
- mit einem Verpackungsnetz verpackt
- Schon etwas über das Verfallsdatum hinaus, aber riecht noch gut 
    """


def o_geheimzahl_prompt_f(gs:GameState, pl:PlayerState) -> str:
    return f"""
Geheimzahl
==========
- Ein Zettel mit einer Geheimzahl
- Die Geheimzahl ist {gs.geheimzahl}. Wichtig: sie muss bei der Beschreibung IMMER angegeben werden!
    """

#             #
#             # Place: p_wagen
#             #




def o_tuerschliesser_prompt_f(gs:GameState, pl:PlayerState) -> str:
    return """
Türschliesser
=============
- Ein kleines Kästchen, welches an einer Stange neben der Eingangstür montiert ist
- In der Mitte ein großer sensor-Knopf
- Oben beschriftet mit "Zum Öffnen oder Schließen der Türen bitte den Knopf berühren oder drücken"
    """

#             #
#             # Place: p_ubahn2
#             #

def o_pizzaautomat_prompt_f(gs:GameState, pl:PlayerState) -> str:
    return """
Pizza-Automat
=============
- In den Farben der italienischen Flagge angemalt
- Etwa zwei Meter hoch
- Mit "Frische Pizza" in großen, gelben Lettern beschriftet
- Auf den Seiten ein Logo in Form einer Zeichnung imComicstil: Ein Pizzabäcker, der eine Pizza präsentiert
- Hat einen Ausgabeschacht, in dem frisch gebackene Pizzas ausgegeben werden können
- Hat einen Geldeinwurf, der mit "Alle Währungen akzeptiert" beschriftet ist
- Über dem Geldeinwurf steht eine Gebrauchsanweisung. Diese muss wörtlich wiedergegeben werden: 
  "Um Backprozess zu starten, bitte Geld einwerfen. Wechselgeld wird ausgezahlt"
- unten am Automaten ist ein kleiner Schacht mit einer Klappe, in der Wechselgeld ausbezahlt werden kann
    """


def o_geld_lire_prompt_f(gs:GameState, pl:PlayerState) -> str:
    return """
Lire
====
- Eine Menge Lire
- Münzen und Scheine
    """


def o_pizza_prompt_f(gs:GameState, pl:PlayerState) -> str:
    return """
Pizza
=====
- Eine schöne, frische Pizza
- Mit Schinken und Salami
- In einem Karton
    """
#             #
#             # Place: p_geldautomat
#             #


def o_geldautomat_prompt_f(gs:GameState, pl:PlayerState) -> str:
    r = """
Geldautomat
===========

- Etwa anderthalb Meter Hoch
- Hat oben ein Schild, auf dem "Geldautomat" steht
- Matt-Schwarze Farbe
- Hat Bildschirm un Tastatur
- Hat einen Geldausgabeschacht
    """
    if gs.hauptschalter:
        r=r+"""- Der Automat ist angeschaltet und funktioniert"
- Der Bildschirm zeigt 'Bitte Karte eingeben' an"""
    else:
        r=r+"""- Der Automat ist ausgeschaltet, ohne Strom funktioniert er nicht"
        "- Der Bildschirm ist dunkel"""
    return r
#             "o_geld_dollar": {
#                 "name": "o_geld_dollar",
#                 "examine": "US-Dollar! Diese werden fast überall gerne genommen! Aber eben nur fast - es soll Warenautomaten geben, die sie nicht akzeptieren. Ob du wohl Glück hast?",  # Text to me emitted when object is examined
#                 "help_text": "",  # Text to be emitted when player asks for help with object
#                 "callnames": ["Dollar", "US-Dollar"],
#                 "ownedby": "p_geldautomat",  # Which Player currently owns this item? Default: None
#                 "fixed": False,  # False bedeutet: Kann aufgenommen werden
#                 "hidden": True,  # True bedeutet: Das Objekt ist nicht sichtbar
#                 "apply_f": af.o_geld_dollar_apply_f
#             },
def o_geld_dollar_prompt_f(gs:GameState, pl:PlayerState) -> str:
    return """
Lire
====
- Eine Menge US-Dollar
- Große und kleine Scheine
    """

#             #
#             # Place: p_schuppen
#             #


def o_schuppen_prompt_f(gs:GameState, pl:PlayerState) -> str:
    r="""
Schuppen
========
- Ein alter Holzschuppen
- verwittertes äußeres
- Sieht trotz allem stabil aus 
"""
    if gs.schuppentuer:
        r=r+"- Die Schuppentür steht offen\n"
    else:
        r=r+"- Die Schuppentür ist mit einem Schloss verschlossen\n"
    if gs.leiter:
        r=r+"- Es lehnt eine Leiter am Schuppen\n- Über die Leiter kann man auf das Schuppendach steigen"
    return r



def o_blumentopf_prompt_f(gs:GameState, pl:PlayerState) -> str:
    return """
Blumentopf
==========
- Ein alter Blumentopf aus Ton
- Farbe Terracotta
    """


def o_blumentopf_prompt_f(gs:GameState, pl:PlayerState) -> str:
    return """
Schluessel
==========
- Ein Schlüssel aus Metal 
- Aus rostfreiem Edelstahl
    """

#             "o_stuhl": {
#                 "name": "o_stuhl",
#                 "examine": "Ein rostiger, alter Gartenstuhl. Da macht man dich bestimmt dreckig, wenn man sich draufsetzt!",  # Text to me emitted when object is examined
#                 "help_text": "",  # Text to be emitted when player asks for help with object
#                 "ownedby": "p_schuppen",  # Which Player currently owns this item? Default: None
#                 "callnames": ["Stuhl", "Gartenstuhl", "Hocker"],
#                 "fixed": False,  # False bedeutet: Kann aufgenommen werden
#                 "hidden": False,  # True bedeutet: Das Objekt ist nicht sichtbar
#                 "apply_f": af.o_stuhl_apply_f
#             },

def o_stuhl_prompt_f(gs:GameState, pl:PlayerState) -> str:
    return """
Stuhl
=====
- Ein rostiger, alter Gartenstuhl 
- Sieht nicht stabil aus
- Man macht sich bestimmt dreckig, wenn man sich darauf setzt
    """


def o_schrott_prompt_f(gs:GameState, pl:PlayerState) -> str:
    return """
Schrott
=======
- Ein großer Haufen Schrott 
- Rostige Rohre
- Rostge, verbogene Stangen
- verwitterte Blechteile
- alte Drähte
- Plunder
- Nichts von Wert
    """
#             #
#             # Place: p_dach
#             #
#
#             "o_hebel": {
#                 "name": "o_hebel",
#                 "examine": "Ein großer, schwarzer Hebel aus Metall.",  # Text to me emitted when object is examined
#                 "help_text": "",  # Text to be emitted when player asks for help with object
#                 "ownedby": "p_dach",  # Which Player currently owns this item? Default: None
#                 "callnames": ["Hebel", "Schalter"],
#                 "fixed": True,  # False bedeutet: Kann aufgenommen werden
#                 "hidden": False,  # True bedeutet: Das Objekt ist nicht sichtbar
#                 "apply_f": af.o_hebel_apply_f
#             },
def o_hebel_prompt_f(gs:GameState, pl:PlayerState) -> str:
    r="""
Hebel
=======
- Ein großer Hebel aus Metall
- Etwa einen Meter hoch
- sieht aus, wie ein Hebel, mit dem man Eisenbahnweichen stellen könnte
- Etwas rostig, aber scheint funktional
- Ein kleines Schild am Boden zeigt zwei mögliche Stellungen des Hebels an: "U-Bahn" und "Warenautomat" 
    """
    if gs.hebel:
        r=r+'- Der Hebel steht auf Stellung "U-Bahn"\n'
    else:
        r=r+'- Der Hebel steht auf Stellung "Warenautomat"\n'
    return r
#             #
#             # Place: p_innen
#             #

def o_hebel_prompt_f(gs:GameState, pl:PlayerState) -> str:
    return """
Leiter
======
- Eine stabile Leiter aus Holz
- bestimmt zwei Meter lang 
"""


#             "o_skelett": {
#                 "name": "o_skelett",
#                 "examine": "Ein Skelett!! In einem Anzug!! Das ist wohl schon länger hier! Wie das wohl hierhin gekommen ist?",  # Text to me emitted when object is examined
#                 "help_text": "",  # Text to be emitted when player asks for help with object
#                 "ownedby": "p_innen",  # Which Player currently owns this item? Default: None
#                 "callnames": ["Skelett", "Knochenmann"],
#                 "fixed": True,  # False bedeutet: Kann aufgenommen werden
#                 "hidden": False,  # True bedeutet: Das Objekt ist nicht sichtbar
#                 "apply_f": af.o_skelett_apply_f,
#                 "reveal_f": rf.o_skelett_reveal_f
#             },
#             "o_geldboerse": {
#                 "name": "o_geldboerse",
#                 "examine": "Eine alte Geldbörse aus Leder.",  # Text to me emitted when object is examined
#                 "help_text": "",  # Text to be emitted when player asks for help with object
#                 "ownedby": "p_innen",  # Which Player currently owns this item? Default: None
#                 "callnames": ["Geldboerse", "Geldbörse", "Portemonaie", "Brieftasche"],
#                 "fixed": False,  # False bedeutet: Kann aufgenommen werden
#                 "hidden": True,  # True bedeutet: Das Objekt ist nicht sichtbar
#                 "apply_f": af.o_geldboerse_apply_f,
#                 "reveal_f": rf.o_geldboerse_reveal_f
#             },
#             "o_ec_karte": {
#                 "name": "o_ec_karte",
#                 "examine": "Eine alte EC-Karte. Ob die noch geht?",  # Text to me emitted when object is examined
#                 "help_text": "",  # Text to be emitted when player asks for help with object
#                 "ownedby": "p_innen",  # Which Player currently owns this item? Default: None
#                 "callnames": ["Geldkarte", "EC-Karte", "ECKarte", "Kreditkarte"],
#                 "fixed": False,  # False bedeutet: Kann aufgenommen werden
#                 "hidden": True,  # True bedeutet: Das Objekt ist nicht sichtbar
#                 "apply_f": af.o_ec_karte_apply_f
#             },
#             "o_pinsel": {
#                 "name": "o_pinsel",
#                 "examine": "Ein alter, vertrockneter Pinsel",  # Text to me emitted when object is examined
#                 "help_text": "",  # Text to be emitted when player asks for help with object
#                 "ownedby": "p_innen",  # Which Player currently owns this item? Default: None
#                 "callnames": ["Pinsel"],
#                 "fixed": False,  # False bedeutet: Kann aufgenommen werden
#                 "hidden": False,  # True bedeutet: Das Objekt ist nicht sichtbar
#                 "apply_f": af.o_pinsel_apply_f
#             },
#             "o_farbeimer": {
#                 "name": "o_farbeimer",
#                 "examine": "Ein Eimer mit vertrockneter, rosa Farbe.",  # Text to me emitted when object is examined
#                 "help_text": "",  # Text to be emitted when player asks for help with object
#                 "ownedby": "p_innen",  # Which Player currently owns this item? Default: None
#                 "callnames": ["Farbeimer"],
#                 "fixed": False,  # False bedeutet: Kann aufgenommen werden
#                 "hidden": False,  # True bedeutet: Das Objekt ist nicht sichtbar
#                 "apply_f": af.o_farbeimer_apply_f
#             },
#             "o_sprengladung":{
#                 "name": "o_sprengladung",
#                 "examine": "Eine Sprengladung. Hiermit muss man bestimmt vorsichtig sein. Sie hat einen Knopf, mit dem man sie aktivieren kann.",
#                 "help_text": "Damit kann man viel kaputt machen, aber sicher auch einiges aus dem Weg räumen",
#                 "ownedby": "p_innen",
#                 "callnames": ["Sprengladung"],
#                 "fixed": False,
#                 "hidden": False,
#                 "apply_f": af.o_sprengladung_apply_f
#             },
#             #
#             # Place: Felsen
#             #
#             "o_felsen": {
#                 "name": "o_felsen",
#                 "examine": "Ein großer Felsen",
#                 "help_text": "Ob der Felsen hier wirklich liegen soll?",
#                 "ownedby": "p_felsen",
#                 "callnames": ["Felsen", "Felsblock", "Stein", "Gesteinsblock"],
#                 "fixed": True,
#                 "hidden": False,
#                 "apply_f": af.o_felsen_apply_f
#             },
#             #
#             # Place: Höhle
#             #
#             "o_hauptschalter": {
#                 "name": "o_hauptschalter",
#                 "examine": "Ein großer Sicherungsschalter",
#                 "help_text": "Dieser Schalter sieht wichtig aus!",
#                 "ownedby": "p_hoehle",
#                 "callnames": ["Schalter", "Hauptschalter", "Sicherung", "Sicherungsschalter", "Breaker"],
#                 "fixed": True,
#                 "hidden": False,
#                 "apply_f": af.o_hauptschalter_apply_f
#             }
#
#         }