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
        r = r+"- steht aufrecht und stabil da"
        if gs.hauptschalter:
            r=r+"- Ist angeschaltet und bereit, Teile gegen Geld auszugeben"
        else:
            r=r+"- Ist ausgeschaltet und funktioniert nicht, solange kein Strom da ist"
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
    """
#             "o_geld_lire": {
#                 "name": "o_geld_lire",
#                 "examine": "Italienische Lira! Eine ganze Menge davon! Die hat man schon lange nicht mehr gesehen!",  # Text to me emitted when object is examined
#                 "help_text": "",  # Text to be emitted when player asks for help with object
#                 "callnames": ["Lire", "Lira", "italienische Lira", "italienische Lire", "italienisches Geld"],
#                 "ownedby": "p_ubahn2",  # Which Player currently owns this item? Default: None
#                 "fixed": False,  # False bedeutet: Kann aufgenommen werden
#                 "hidden": True,  # True bedeutet: Das Objekt ist nicht sichtbar
#                 "apply_f": af.o_geld_lire_apply_f
#             },
#             "o_pizza": {
#                 "name": "o_pizza",
#                 "examine": "Eine Salami-Pizza mit viel Käse.",  # Text to me emitted when object is examined
#                 "help_text": "",  # Text to be emitted when player asks for help with object
#                 "callnames": ["Pizza"],
#                 "ownedby": "p_ubahn2",  # Which Player currently owns this item? Default: None
#                 "fixed": False,  # False bedeutet: Kann aufgenommen werden
#                 "hidden": True,  # True bedeutet: Das Objekt ist nicht sichtbar
#                 "apply_f": af.o_pizza_apply_f
#             },
#             #
#             # Place: p_geldautomat
#             #
#
#             "o_geldautomat": {
#                 "name": "o_geldautomat",
#                 "examine": "Ein Geldautomat, der sehr neu aussieht. Er ist klar mit 'ATM' gekennzeichnet. Man muss eine Karte einstecken, eine Geheimnummer eingeben, und wenn Geld auf dem Konto ist, kann man es abheben.",  # Text to me emitted when object is examined
#                 "help_text": "",  # Text to be emitted when player asks for help with object
#                 "ownedby": "p_geldautomat",  # Which Player currently owns this item? Default: None
#                 "callnames": ["Geldautomat", "ATM"],
#                 "fixed": True,  # False bedeutet: Kann aufgenommen werden
#                 "hidden": False,  # True bedeutet: Das Objekt ist nicht sichtbar
#                 "apply_f": af.o_geldautomat_apply_f
#             },
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
#             #
#             # Place: p_schuppen
#             #
#
#             "o_schuppen": {
#                 "name": "o_schuppen",
#                 "examine": "Ein alter Holzschuppen, in dem womöglich interessante Dinge sind. "
#                            "Der Schuppen muss aufgeschlossen werden, sonst kann man ihn nicht betreten.",  # Text to me emitted when object is examined
#                 "help_text": "",  # Text to be emitted when player asks for help with object
#                 "ownedby": "p_schuppen",  # Which Player currently owns this item? Default: None
#                 "callnames": ["Schuppen", "Holzschuppen"],
#                 "fixed": True,  # False bedeutet: Kann aufgenommen werden
#                 "hidden": False,  # True bedeutet: Das Objekt ist nicht sichtbar
#                 "apply_f": af.o_schuppen_apply_f
#             },
#             "o_blumentopf": {
#                 "name": "o_blumentopf",
#                 "examine": "Ein alter Blumentopf aus Ton.",  # Text to me emitted when object is examined
#                 "help_text": "",  # Text to be emitted when player asks for help with object
#                 "ownedby": "p_schuppen",  # Which Player currently owns this item? Default: None
#                 "callnames": ["Blumentopf"],
#                 "fixed": False,  # False bedeutet: Kann aufgenommen werden
#                 "hidden": False,  # True bedeutet: Das Objekt ist nicht sichtbar
#                 "apply_f": af.o_blumentopf_apply_f,
#                 "reveal_f": rf.o_blumentopf_reveal_f
#             },
#             "o_schluessel": {
#                 "name": "o_schluessel",
#                 "examine": "Ein Schlüssel aus Metall.",  # Text to me emitted when object is examined
#                 "help_text": "",  # Text to be emitted when player asks for help with object
#                 "ownedby": "p_schuppen",  # Which Player currently owns this item? Default: None
#                 "callnames": ["Schlüssel", "Schluessel"],
#                 "fixed": False,  # False bedeutet: Kann aufgenommen werden
#                 "hidden": True,  # True bedeutet: Das Objekt ist nicht sichtbar
#                 "apply_f": af.o_schluessel_apply_f
#             },
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
#             "o_schrott": {
#                 "name": "o_schrott",
#                 "examine": "Eine Menge Schrott! Hier kanns man stundelang herumsuchen - aber man wird hier nichts besonderes finden.",  # Text to me emitted when object is examined
#                 "help_text": "",  # Text to be emitted when player asks for help with object
#                 "ownedby": "p_schuppen",  # Which Player currently owns this item? Default: None
#                 "callnames": ["Schrott", "Schrotthaufen"],
#                 "fixed": True,  # False bedeutet: Kann aufgenommen werden
#                 "hidden": False,  # True bedeutet: Das Objekt ist nicht sichtbar
#                 "apply_f": af.o_schrott_apply_f
#             },
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
#             #
#             # Place: p_innen
#             #
#
#             "o_leiter": {
#                 "name": "o_leiter",
#                 "examine": "Eine stablie Holzleiter",  # Text to me emitted when object is examined
#                 "help_text": "",  # Text to be emitted when player asks for help with object
#                 "ownedby": "p_innen",  # Which Player currently owns this item? Default: None
#                 "callnames": ["Leiter"],
#                 "fixed": False,  # False bedeutet: Kann aufgenommen werden
#                 "hidden": False,  # True bedeutet: Das Objekt ist nicht sichtbar
#                 "apply_f": af.o_leiter_apply_f, # Funktion: Leiter wurd "angewandt"
#                 "take_f": tf.o_leiter_take_f # Funktion: Leiter wird aufgenommen
#             },
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