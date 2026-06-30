from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from game_state import GameState
    from player_state import PlayerState
    from game_object import GameObject
    from place import Place
    from way import Way

def _F(gs: "GameState"):
    """Return the structured flags container (GameFlags) from GameState."""
    return gs.get_flags()
"""
prompt functions for Game Objects go here
"""



def o_umschlag_prompt_f(gs: "GameState", pl: "PlayerState") -> str:
    return """ 
Briefumschlag
=============
- Dicker grauer Umschlag
- Verschlossen mit einem roten Siegel mit einem Hundekopf"""



def o_warenautomat_prompt_f(gs: "GameState", pl: "PlayerState") -> str:
    r = """
Warenautomat
============
- Großer, schwarzer Warenautomat
- Enthält Fahrradteile
- Beschriftungen in  italienischer Sprache
- Sieht älter, aber nicht beschädigt aus
    """
    if _F(gs).hebel:
        r = r+ "- Liegt auf dem Rücken und ist ausgeschaltet"
        "- Wo er stand, ist nun eine Öffnung im Boden"
        "- Aus der Öffnung kommt angenehm kühle Luft"
        "- Es ist eine Treppe in der Öffnung"
    else:
        r = r+"- steht aufrecht und stabil da\n"
        if _F(gs).hauptschalter:
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

def o_fahrradkette_prompt_f(gs: "GameState", pl: "PlayerState") -> str:
    return """
Fahrradkette
============
- Eine schöne, neue stabile Fahrradkette
- Kann die kaputte Fahrradkette ersetzen

    """


def o_fahrrad_prompt_f(gs: "GameState", pl: "PlayerState") -> str:
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

def o_muelleimer_prompt_f(gs: "GameState", pl: "PlayerState") -> str:
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

def o_salami_prompt_f(gs: "GameState", pl: "PlayerState") -> str:
    return """
Salami
======
- Eine große Salami
- Mit Edelschimmel umgeben
- mit einem Verpackungsnetz verpackt
- Schon etwas über das Verfallsdatum hinaus, aber riecht noch gut 
    """


def o_geheimzahl_prompt_f(gs: "GameState", pl: "PlayerState") -> str:
    return f"""
Geheimzahl
==========
- Ein Zettel mit einer Geheimzahl
- Die Geheimzahl ist {_F(gs).geheimzahl}. Wichtig: sie muss bei der Beschreibung IMMER angegeben werden!
    """

#             #
#             # Place: p_wagen
#             #




def o_tuerschliesser_prompt_f(gs: "GameState", pl: "PlayerState") -> str:
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

def o_pizzaautomat_prompt_f(gs: "GameState", pl: "PlayerState") -> str:
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


def o_geld_lire_prompt_f(gs: "GameState", pl: "PlayerState") -> str:
    return """
Lire
====
- Eine Menge Lire
- Münzen und Scheine
    """


def o_pizza_prompt_f(gs: "GameState", pl: "PlayerState") -> str:
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


def o_geldautomat_prompt_f(gs: "GameState", pl: "PlayerState") -> str:
    r = """
Geldautomat
===========

- Etwa anderthalb Meter Hoch
- Hat oben ein Schild, auf dem "Geldautomat" steht
- Matt-Schwarze Farbe
- Hat Bildschirm un Tastatur
- Hat einen Geldausgabeschacht
    """
    if _F(gs).hauptschalter:
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
def o_geld_dollar_prompt_f(gs: "GameState", pl: "PlayerState") -> str:
    return """
Dollar
======
- Eine Menge US-Dollar
- Große und kleine Scheine
- Die Dollar kann man nehmen, aufnehmen, aufklauben, einstecken, an sich nehmen. 
- Die Dollar kann man auch in etwas hineinstecken oder mit ihnen bezahlen oder kaufen. 
- sie können auch als US-Geld oder US-Dollar bezeichnet werden

Beispiele:

Nimm die Dollar aus dem Geldautomaten --> 'nimm o_geld_dollar'
Nimm die scheine aus dem Geldautomaten --> 'nimm o_geld_dollar'
Stecke die Dollar in den Pizza-Automaten --> 'anwenden o_geld_dollar o_pizzaautomat'
Kaufe mit den US-Dollar eine Pizza am Automaten --> 'anwenden o_geld_dollar o_pizzaautomat'
    """

#             #
#             # Place: p_schuppen
#             #


def o_schuppen_prompt_f(gs: "GameState", pl: "PlayerState") -> str:
    r="""
Schuppen
========
- Ein alter Holzschuppen
- verwittertes äußeres
- Sieht trotz allem stabil aus 
- Auf dem Dach ragt etwas in die Höhe, was eine Antenne oder ein Hebel sein könnte
"""
    if not _F(gs).dach:
        r=r+"- DerSchuppen hat kein Dach mehr. \n- Es sieht aus, als wäre das Dach weggesprengt worden."
    if _F(gs).schuppentuer:
        r=r+"- Die Schuppentür steht offen\n"
    else:
        r=r+"- Die Schuppentür ist mit einem Schloss verschlossen\n"
    if _F(gs).leiter:
        r=r+"- Es lehnt eine Leiter am Schuppen\n- Über die Leiter kann man auf das Schuppendach steigen"
    return r



def o_blumentopf_prompt_f(gs: "GameState", pl: "PlayerState") -> str:
    return """
Blumentopf
==========
- Ein alter Blumentopf aus Ton
- Farbe Terracotta
    """


def o_schluessel_prompt_f(gs: "GameState", pl: "PlayerState") -> str:
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

def o_stuhl_prompt_f(gs: "GameState", pl: "PlayerState") -> str:
    return """
Stuhl
=====
- Ein rostiger, alter Gartenstuhl 
- Sieht nicht stabil aus
- Man macht sich bestimmt dreckig, wenn man sich darauf setzt
    """


def o_schrott_prompt_f(gs: "GameState", pl: "PlayerState") -> str:
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
def o_hebel_prompt_f(gs: "GameState", pl: "PlayerState") -> str:
    r="""
Hebel
=======
- Ein großer Hebel aus Metall
- Etwa einen Meter hoch
- sieht aus, wie ein Hebel, mit dem man Eisenbahnweichen stellen könnte
- Etwas rostig, aber scheint funktional
- Ein kleines Schild am Boden zeigt zwei mögliche Stellungen des Hebels an: "U-Bahn" und "Warenautomat" 
    """
    if _F(gs).hebel:
        r=r+'- Der Hebel steht auf Stellung "U-Bahn"\n'
    else:
        r=r+'- Der Hebel steht auf Stellung "Warenautomat"\n'
    return r
#             #
#             # Place: p_innen
#             #

def o_leiter_prompt_f(gs: "GameState", pl: "PlayerState") -> str:
    return """
Leiter
======
- Eine stabile Leiter aus Holz
- bestimmt zwei Meter lang 

Verwendung der Leiter
=====================
- Man kann die Leiter aufgestellen, stellen,  lehnen, oder anlehnen werden
- Beispiel: 'Lehne die Leiter an den Schuppen', "stelle die Leiter an den Felsen"
- in dem Fall liefere "anwenden Leiter Schuppen" oder "anwenden Leiter Felsen" zurück 
"""



def o_skelett_prompt_f(gs: "GameState", pl: "PlayerState") -> str:
    return """
Skelett
=======
- Eine Skelett in einem Nadelstreifenanzug
- Hat einen Hut auf, passend zum Anzug
- Ist schon länger hier, man weiss nicht, wer es mal war, und wie es hierhergekommen ist
- schlechter Zustand
- ekelig (mumifizierte Fleischreste)
- gruselig
"""



def o_geldboerse_prompt_f(gs: "GameState", pl: "PlayerState") -> str:
    return """
Geldbörse
=========
- Eine alte Geldbörse aus Leder
- abgewetzt
- war mal schwarz
- schlechter Zustand
- enthält kein Geld
"""


def o_ec_karte_prompt_f(gs: "GameState", pl: "PlayerState") -> str:
    return """
EC-Karte
========
- Eine EC-Karte einer bekannten Bank
- noch gültig
"""


def o_pinsel_prompt_f(gs: "GameState", pl: "PlayerState") -> str:
    return """
Pinsel
======
- Eine alter Rundpinsel
- die Borsten sind mit eingetrockneter rosa Farbe verklebt
"""


def o_farbeimer_prompt_f(gs: "GameState", pl: "PlayerState") -> str:
    return """
Farbeimer
=========
- Eine alter Farbeimer
- fast leer
- am Boden Reste eingetrockneter rosa Farbe
"""
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

def o_sprengladung_prompt_f(gs: "GameState", pl: "PlayerState") -> str:
    return """
Sprengladung
============
- Eine Sprengladung aus Dynamitstangen und einer automatischen Zünder
- der Zünder ist am Kopf der Dynamitstangen angebracht
- auf dem Zünder ist ein roter Knopf
- An der Ladung ist ein Zettel angebracht mit folgendem Text:
  "Nach betätigen des Zünders explodiert die Ladung in drei Spielzügen!"
  (DIESEN TEXT UNBEDINGT WÖRTLICH WIEDERGEBEN!)
"""
#             #
#             # Place: Felsen
#             #
#             "o_felsen": {
#                 "name": "o_felsen",
#                 "examine": "Ein großer Felsen",
#                 "help_text": "Ob der Felsen hier wirklich liegen soll?",
#                 "ownedby": "p_felsnische",
#                 "callnames": ["Felsen", "Felsblock", "Stein", "Gesteinsblock"],
#                 "fixed": True,
#                 "hidden": False,
#                 "apply_f": af.o_felsen_apply_f
#             },

def o_felsen_prompt_f(gs: "GameState", pl: "PlayerState") -> str:
    return """
Felsen
======
- Eine großer Felsblock aus Granit
- viele Tonnen schwer
- unmöglich zu bewegen
- sieht so aus, als sei er hier hingerollt
- versperrt möglicherweise etwas 
- liegt auf einem Trampelpfad genau vor dem Berg

"""
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

def o_hauptschalter_prompt_f(gs: "GameState", pl: "PlayerState") -> str:
    return """
Hauptschalter
=============
- Eine großer Sicherungsschalter
- Farbe ist rot

Anwendung
=========
- der Schalter kann geschaltet, geschlossen, gedrückt oder betätigt werden
- der Schalter kann auch als Schalter, Hauptschalter, Sicherung, Sicherungsschalte oder Breaker bezeichnet werden
- Beispiele: "betätige den Schakter", "drücke den Sicherungsschalter", "Schließe den Breaker"
- Liefer in solchen Fällen "anwenden hauptschalter" zurück

"""

def o_wasserspender_prompt_f(gs: "GameState", pl: "PlayerState") -> str:
    return """
Wasserspender
=============
- Ein schöner Wasserspender aus Metall
- Er hat ein kleines Becken
- Aus einem kleinen Wasserhahn in Form eines Delfins sprudelt frisches, klares Wasser

Anwendung
=========
- Aus dem Wasserspender kann getrunken, gesoffen oder gesüffelt werden
- Man kann an oder mit ihm seinen Durst oder sogar seinen Brand stillen oder löschen
- Der Wasserspender kann auch als Trinkbrunnen oder Brunnen bezeichnet werden
- Liefere zum Trinken "anwenden wasserspender" zurück
- Hier kann auch die Flasche aufgefüllt werden, um eine Notreserve mitzunehmen
- Liefere zum Auffüllen der Flasche "anwenden flasche wasserspender" zurück
"""

def o_flasche_prompt_f(gs: "GameState", pl: "PlayerState") -> str:
    if gs.flasche_voll:
        return """
Flasche
=============
- Eine Wasserflasche aus Glas
- Die Flasche ist voll


Anwendung
=========
- Aus der Flasche kann getrunken, gesoffen oder gesüffelt werden
- Man kann mit ihr seinen Durst oder sogar seinen Brand stillen oder löschen
- Liefere zum Trinken "anwenden Flasche" zurück
- Die Flasche kann am Wasserspender/Trinkbrunnen (in der U-Bahn) wieder aufgefüllt werden
- Liefere zum Auffüllen "anwenden flasche wasserspender" zurück
"""
    else:
        return """
Flasche
=============
- Eine Wasserflasche aus Glas
- Die Flasche ist leer


Anwendung
=========
- Aus einer leeren Flasche kann nicht getrunken werden
- Die Flasche kann aber am Wasserspender/Trinkbrunnen (in der U-Bahn) wieder aufgefüllt werden
- Liefere zum Auffüllen "anwenden flasche wasserspender" zurück
- Kann sie hier nicht aufgefüllt werden, kannst du mit ihr nichts tun: liefere dann "nichts" zurück
"""

def o_solaranlage_prompt_f(gs: "GameState", pl: "PlayerState") -> str:
    return """
Solaranlage
===========
- Eine große Solaranlage, die auf einem Gerüst steht
- Unter der Anlage ist es schattig und kühl
- Es wächst Gras unter der Anlage, also muss irgendwo Wasser sein, nur wo?
- Es summt - also liefert die Anlage Strom
- Ein Dickes Kabel verschwindet im Hügel
"""

def o_falltuer_prompt_f(gs: "GameState", pl: "PlayerState") -> str:
    if gs.falltuer_offen:
        return """ 
Falltür
=======
- Eine Falltür aus Metall
- Sie steht offen
"""
    else:
        return """
Falltür
=======
- Eine Falltür aus Metall
- Sie ist verschlossen
- Es scheint keinen Weg zu geben, sie von hier zu öffnen
    """

def o_tinktur_prompt_f(gs: "GameState", pl: "PlayerState") -> str:
    return """
Tinktur
=======
- Eine kleine Flasche mit einer durchsichtigen Flüssigkeit
- Das Etikett ist vergilbt und kaum noch lesbar
- Man kann nur noch 'Geheim...' entziffern
- Riecht leicht nach Zitrone und Chemikalien

Anwendung
=========
- Die Tinktur kann auf Gegenstände angewandt werden, um verborgene Botschaften sichtbar zu machen
- Beispiel: "Wende die Tinktur auf den Umschlag an" --> 'anwenden Tinktur Umschlag'
"""


def o_schalter_kontrollraum_prompt_f(gs: "GameState", pl: "PlayerState") -> str:
    r = """
Notfall-Schalter (Kontrollraum)
===============================
- Ein großer, roter Schalter an der Wand
- Darüber ein Schild: 'Notfall-Schalter 1/2 - Synchrone Aktivierung erforderlich'
- Ein zweiter Schalter befindet sich offenbar in einem anderen Raum
"""
    if _F(gs).schalter_kontrollraum:
        r += "- Der Schalter ist **aktiviert** und leuchtet grün\n"
    else:
        r += "- Der Schalter ist nicht aktiviert\n"
    return r


def o_u_bahn_steuerung_prompt_f(gs: "GameState", pl: "PlayerState") -> str:
    pos = "Bahnsteig 2" if _F(gs).wagen_ubahn2 else "Bahnsteig 1"
    return f"""
U-Bahn-Steuerung
================
- Ein Steuerpult mit einem großen Hebel, beschriftet mit 'Bahnsteig 1' und 'Bahnsteig 2'
- Damit lässt sich der U-Bahn-Wagen fernsteuern - er rollt zum gewählten Bahnsteig
- Der Hebel steht gerade auf '{pos}'
- Man kann die Steuerung betätigen/umlegen/anwenden, um den Wagen zu rufen
  (Synonyme: U-Bahn-Steuerung, Steuerung, Steuerpult, Hebel)
- Wichtig: Steht der Wagen an Bahnsteig 1, gibt er am zweiten Bahnsteig einen Durchgang
  zum U-Bahn-Schacht frei
"""


def o_schalter_generatorraum_prompt_f(gs: "GameState", pl: "PlayerState") -> str:
    r = """
Notfall-Schalter (Generatorraum)
================================
- Ein großer, roter Schalter an der Wand
- Darüber ein Schild: 'Notfall-Schalter 2/2 - Synchrone Aktivierung erforderlich'
- Ein zweiter Schalter befindet sich offenbar in einem anderen Raum
"""
    if _F(gs).schalter_generatorraum:
        r += "- Der Schalter ist **aktiviert** und leuchtet grün\n"
    else:
        r += "- Der Schalter ist nicht aktiviert\n"
    return r


def o_stahltuer_prompt_f(gs: "GameState", pl: "PlayerState") -> str:
    if _F(gs).korridor_offen:
        return """
Stahltür
========
- Eine große, schwere Stahltür - sie steht jetzt offen und gibt den Weg in den Korridor frei
- Synonyme: Stahltür, Eisentür, Panzertür, Tür
"""
    return """
Stahltür
========
- Eine große, schwere Stahltür, die einen Korridor versperrt
- Auf dieser Seite sitzt ein massives Handrad mit einem Riegel
- Man kann versuchen, sie zu öffnen/entriegeln, z.B. 'öffne die Stahltür', 'drehe das Rad',
  'entriegle die Tür' - das entspricht 'anwenden o_stahltuer'
- Synonyme: Stahltür, Eisentür, Panzertür, Handrad, Tür
"""


def o_manual_prompt_f(gs: "GameState", pl: "PlayerState") -> str:
    return """
Betriebshandbuch (Manual)
=========================
- Ein abgegriffenes Betriebshandbuch der Anlage
- Auf dem Umschlag steht 'Notfall-Betrieb - Bedienungsanleitung'
- Man kann es lesen ('lies das Manual', 'lese die Bedienungsanleitung') - das entspricht 'anwenden'
- Darin steht offenbar, wie man die Anlage im Notfall wieder startet
- Man kann es auch aufnehmen und mitnehmen
- Synonyme: Manual, Gebrauchsanweisung, Bedienungsanleitung, Betriebsanleitung, Handbuch, Anleitung
"""


def o_werbeplakat_prompt_f(gs: "GameState", pl: "PlayerState") -> str:
    if _F(gs).kontrollraum_offen:
        return """
Werbeplakat
===========
- Ein Werbeplakat, das eigentlich eine Tür ist
- Es steht offen und gibt einen kurzen Gang frei, der in einen Kontrollraum führt
- Auf dem Plakat ist Werbung für Unterhaltungstechnik aus den 80er Jahren (Videorekorder, Stereoanlagen, Heimcomputer)
- In diesem Kontext kann man zum Werbeplakat auch Plakat, Tür, oder Plakattür sagen
- Man kann es schliessen, zumachen, zuklappen oder ähnliches
"""
    else:
        return """
Werbeplakat
===========
- Ein großes Werbeplakat
- Auf dem Plakat ist Werbung für Unterhaltungstechnik aus den 80er Jahren (Videorekorder, Stereoanlagen, Heimcomputer)
- Das Plakat hat Scharniere auf der linken Seite, und einen Griff auf der rechten Seite - könnte eine versteckte Tür sein?
- Man kann an dem Plakat ziehen, es öffnen oder aufklappen oder ähnliches
    """