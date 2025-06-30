"""
For the LLM interaction: Some places have differing Prompt snippets depending
on changes in game- and/or player state. Instead of setting these in the object
itself, a function is called
"""
from GameState import GameState
from PlayerState import PlayerState

def p_warenautomat_place_prompt_f(gs: GameState, pl: PlayerState=None) -> str:
    return """
Warenautomat
============
- An diesem Ort befindet sich der Warenautomat für Fahrradteile, der weiter unten beschrieben wird
    """

def p_felsen_place_prompt_f(gs:GameState, pl: PlayerState)-> str:
    rv = """
Felsen
======
- Hier ist ein Hügel aus Gestein und Felsen. 
- Das Gestein ist so bröckelig, dass man nicht auf den Hügel steigen kann.
"""
    if gs.felsen:
        return f"{rv}- Ein Trampelpfad führt zu dem Hügel und endet vor einem Felsblock, der weiter unten beschrieben wird.\n"
    else:
        return f"{rv}- Spuren einer großen Explosion sind zu sehen.\- Wo vorher ein Felsblock lag, ist nun der Eingang zu einer Höhle.\n"

def p_hoehle_place_prompt_f(gs: GameState, pl: PlayerState) -> str:
    rv = """
Höhle
=====
- Im Gegensatz zu außen ist es im inneren der Höhle schön kühl. 
- Die Wände der Höhle sind aus Granitgestein
- der Boden ist aus gestampftem Lehm. """
    if gs.hauptschalter:
        return f"{rv}- Eine Glühbirne hängt von der Decke und erleuchtet die Höhle.\n- Man kann elektrisches Summen vernehmen\n"
    else:
        return f"{rv}- Eine Glühbirne hängt von der Decke, aber sie ist ausgeschaltet.\n- Das einzige Licht kommt vom Höhleneingang"

def p_schuppen_place_prompt_f(gs: GameState, pl: PlayerState) -> str:
    rv ="""
Schuppen
========
"""
    if gs.schuppen_intakt:
        rv = rv+"- Hier ist Holzschuppen, der weiter unten beschrieben wird\n"
    else:
        rv = rv+"- Trümmer eines Holzschuppens liegen herum\n- Es sieht so aus, als hätte eine große Explosion stattgefunden\n"


    return rv

def p_innen_place_prompt_f(gs: GameState, pl: PlayerState) -> str:
    rv = """
Im Inneren des Schuppens
========================
"""
    if gs.dach:
        rv = rv + """- Es riecht muffig und staubig, und ein wenig nach Verwesung. 
- Grelles Sonnenlicht dringt durch Ritzen zwischen den Brettern und die offene Tür. """

    else:
        rv = rv + """- Der Schuppen hat kein Dach mehr.
- Das grelle Sonnenlicht erleuchtet alle Gegenstände Erbarmungslos."""

    return rv

def p_warenautomat_place_prompt_f(gs: GameState, pl: PlayerState) -> str:
    rv = """
Warenautomat
============
"""
    if not gs.warenautomat_intakt:
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

def p_geldautomat_place_prompt_f(gs: GameState, pl: PlayerState) -> str:
    rv = """
Geldautomat
===========
"""
    if not gs.geldautomat_intakt:
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

