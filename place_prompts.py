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
For the LLM interaction: Some places have differing Prompt snippets depending
on changes in game- and/or player state. Instead of setting these in the object
itself, a function is called
"""

def p_warenautomat_place_prompt_f(gs: "GameState", pl: "PlayerState"=None) -> str:
    return """
Warenautomat
============
- An diesem Ort befindet sich der Warenautomat für Fahrradteile, der weiter unten beschrieben wird
    """

def p_felsnische_place_prompt_f(gs: "GameState", pl: "PlayerState")-> str:
    rv = """
Felsnische
==========
- Hier ist eine Nische in einem Hügel aus Gestein und Felsen.
- Ein Weg führt auf ein Plateau auf dem Hügel.
"""
    if _F(gs).felsen:
        return f"{rv}- Ein Trampelpfad führt zu dem Hügel und endet vor einem Felsblock, der weiter unten beschrieben wird.\n"
    else:
        return f"{rv}- Spuren einer großen Explosion sind zu sehen.\n- Wo vorher ein Felsblock lag, ist nun der Eingang zu einer Höhle.\n"

def p_hoehle_place_prompt_f(gs: "GameState", pl: "PlayerState") -> str:
    rv = """
Höhle
=====
- Im Gegensatz zu außen ist es im inneren der Höhle schön kühl. 
- Es riecht ein wenig nach Verwesung
- Die Wände der Höhle sind aus Granitgestein
- der Boden ist aus gestampftem Lehm. """
    if _F(gs).korridor_offen:
        rv = f"""{rv}
- Eine große, schwere Stahltür steht offen und gibt den Weg in einen Korridor frei
"""
    else:
        rv = f"""{rv}
- Eine grosse, schwere Stahltür versperrt einen Weg.
- Durch ein kleines, vergittertes Fenster in der Stahtür kann man einen Korridor auf der anderen Seite erkennen.
- Auf dieser Seite sitzt an der Tür ein großes Handrad mit einem Riegel - dreht man daran, lässt sich die Tür möglicherweise von Hand entriegeln. Wichtig: diesen Öffnungs-Mechanismus erwähnen.
"""

    if _F(gs).hauptschalter:
        return f"{rv}- Eine Glühbirne hängt von der Decke und erleuchtet die Höhle.\n- Man kann elektrisches Summen vernehmen\n"
    else:
        return f"{rv}- Eine Glühbirne hängt von der Decke, aber sie ist ausgeschaltet.\n- Das einzige Licht kommt vom Höhleneingang"

def p_schuppen_place_prompt_f(gs: "GameState", pl: "PlayerState") -> str:
    rv ="""
Schuppen
========

Unbedingt beachten: 

* Alle Objekte an diesem Ort liegen VOR dem Schuppen oder um den Schuppen herum. 
  Wichtig: Auch wenn die Schuppentür bzw der Schuppen offen ist, liegt keins der Objekte IM Schuppen.
  
* Interpretiere Benutzereingaben wie "...gehe in den Schuppen" oder "...gehe hinein" so, als
  hätte der Benutzer "gehe nach innen" eingegeben. Gemeint ist dann nämlich der Ort "innen"
"""
    if _F(gs).schuppen_intakt:
        rv = rv+"- Hier ist Holzschuppen, der weiter unten beschrieben wird\n"
    else:
        rv = rv+"- Trümmer eines Holzschuppens liegen herum\n- Es sieht so aus, als hätte eine große Explosion stattgefunden\n"


    return rv

def p_innen_place_prompt_f(gs: "GameState", pl: "PlayerState") -> str:
    rv = """
Im Inneren des Schuppens
========================
"""
    if _F(gs).dach:
        rv = rv + """- Es riecht muffig und staubig. 
- Grelles Sonnenlicht dringt durch Ritzen zwischen den Brettern und die offene Tür. """

    else:
        rv = rv + """- Der Schuppen hat kein Dach mehr.
- Das grelle Sonnenlicht erleuchtet alle Gegenstände Erbarmungslos."""

    return rv

def p_warenautomat_place_prompt_f(gs: "GameState", pl: "PlayerState") -> str:
    rv = """
Warenautomat
============
"""
    if not _F(gs).warenautomat_intakt:
        rv = rv+ """- verschmauchter Boden
- Explosionsspuren
- einige Trümmer eines Warenautomaten
- Ein Eingang zu einer U-Bahn-Station, wo vorher der Warenautomat stand
- der Warenautomat wurde aber offensichtlich gesprengt
"""

    else:
        rv = rv+""" - Hier ist ein Warenautomat, der weiter unten beschrieben wird 
"""
    return rv

def p_geldautomat_place_prompt_f(gs: "GameState", pl: "PlayerState") -> str:
    rv = """
Geldautomat
===========
"""
    if not _F(gs).geldautomat_intakt:
        rv= rv+ """- verschmauchter Boden
- Explosionsspuren
- einige Trümmer eines Geldautomaten
- Papierschnipsel, die vorher mal Dollarscheine waren
- der Geldautomat wurde aber offensichtlich gesprengt
"""

    else:
        rv = rv + """- Ein Geldautomat, der weiter unten beschrieben ist 
"""
    return rv

def p_ubahn_place_prompt_f(gs: "GameState", pl: "PlayerState") -> str:
    rs = f"""
U-Bahn Station
==============
- Im Gegensatz zur Oberfläche herrscht eine angenehm Kühle. Es ist wichtig, auf diesen Kontrast hinzuweisen 
- Alles sauber und aufgeräumt
- An der Wand hängen einige Werbeplakate: eins für eine Limonade, eins für ein Reisebüro. 
- Keine Schmierereien oder Graffitis
- Der Boden ist mit Marmorfliesen gefliest.
- Neonröhren tauchen alles in angenehmes Licht. 
- Reagiere auch, wenn dieser Ort mit "Bahnsteig" bezeichnet wird
{'- In der Station steht ein U-Bahn-Wagen, dessen Türen offen sind.' if not _F(gs).wagen_ubahn2 else ''}
    """
    return rs

def p_ubahn2_place_prompt_f(gs: "GameState", pl: "PlayerState") -> str:
    rs=f"""
Zweite U-Bahn Station
=====================
- Im Gegensatz zur Oberfläche herrscht eine angenehm Kühle. Es ist wichtig, auf diesen Kontrast hinzuweisen 
- Im Gegensatz zur ersten U-Bahn-Station ist die Luft etwas abgestanden
- Es riecht nach mediterranen Gewürzen
- Alles sauber und aufgeräumt
- An der Wand hängen einige Werbeplakate: eins für eine Limonade, eins für den neuen VW-Golf, ein weiteres, welches bei den Objekten genauer beschrieben wird. 
- Keine Schmierereien oder Graffitis
- Der Boden ist mit Marmorfliesen gefliest.
- Neonröhren tauchen alles in angenehmes Licht. 
- Reagiere auch, wenn dieser Ort mit "Bahnsteig" bezeichnet wird
{'- In der Station steht ein U-Bahn-Wagen, dessen Türen offen sind.' if _F(gs).wagen_ubahn2 else '- Dort, wo sonst der U-Bahn-Wagen hält, gibt ein schmaler, dunkler Durchgang den Weg in einen U-Bahn-Schacht frei. Es ist wichtig, diesen Durchgang zu erwähnen.'}
- Wichtig: du darfst den Hund in der Beschreibung ausschließlich nur erwähnen, wenn er im Wagen (p_wagen) oder hier am Ort ist. In allen 
  anderen Fällen kann man den Hund von hier nicht sehen.
    """
    return rs# --- missing_functions Output ---

# Quelle (Original): PlacePrompts.py

# Quelle (Stage)   : stage/PlacePrompts.py

# Enthalten: 8 fehlende Funktion(en): p_labor_place_prompt_f, p_bibliothek_place_prompt_f, p_korridor_place_prompt_f, p_besenkammer_place_prompt_f, p_generatorraum_place_prompt_f, p_ubahn_schacht_place_prompt_f, p_kontrollraum_place_prompt_f, p_solaranlage_place_prompt_f



def p_solaranlage_place_prompt_f(gs: "GameState", pl: "PlayerState") -> str:
    # TODO: implement callback
    return ""

def p_kontrollraum_place_prompt_f(gs: "GameState", pl: "PlayerState") -> str:
    rv = """
Kontrollraum
============
- Der Kontrollraum der kleinen U-Bahn-Anlage.
- An den Wänden hängen Schalttafeln, Monitore und vergilbte Betriebspläne.
- Daneben steht die U-Bahn-Steuerung mit einem Hebel ('Bahnsteig 1' / 'Bahnsteig 2').
"""
    if _F(gs).schalter_kontrollraum:
        rv += "- Der Notfall-Schalter leuchtet grün (aktiviert).\n"
    if _F(gs).wagen_ubahn2:
        rv += "- Die U-Bahn-Steuerung steht auf 'Bahnsteig 2' - der Wagen wartet am zweiten Bahnsteig.\n"
    else:
        rv += "- Die U-Bahn-Steuerung steht auf 'Bahnsteig 1' - der Wagen wartet am ersten Bahnsteig.\n"
    return rv

def p_ubahn_schacht_place_prompt_f(gs: "GameState", pl: "PlayerState") -> str:
    return f"""
U-Bahn-Schacht
==============
- Ein enger, dunkler Wartungsschacht neben dem zweiten Bahnsteig.
- An den Wänden laufen dicke Kabelstränge und rostige Rohre entlang.
- Es riecht nach Staub und altem Öl; von irgendwo tropft Wasser.
"""

def p_korridor_place_prompt_f(gs: "GameState", pl: "PlayerState") -> str:
    # TODO: implement callback
    return """
Korridor
========
- Ein kurzer, staubiger Korridor, von dem einige Türen abgehen
- Staubig
- Es riecht muffig nach Staub
- Weiss gekalkte Wände
- Trübes Licht durch alte Glühbirnen    
    """

def p_labor_place_prompt_f(gs: "GameState", pl: "PlayerState") -> str:
    # TODO: implement callback
    return """
Unterirdisches Labor    
====================
- Keine Fenster
- Labortische
- Elektronischer kram
- Chaos
- Unordentlich
"""

def p_bibliothek_place_prompt_f(gs: "GameState", pl: "PlayerState") -> str:
    # TODO: implement callback
    return """
Unterirdische Bibliothek
========================
- Keine Fenster
- Regale mit Büchern
- Staubig
- Muffiger Gestank
"""

def p_besenkammer_place_prompt_f(gs: "GameState", pl: "PlayerState") -> str:
    # TODO: implement callback
    return ""

def p_generatorraum_place_prompt_f(gs: "GameState", pl: "PlayerState") -> str:
    # TODO: implement callback
    return ""
