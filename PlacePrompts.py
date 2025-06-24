"""
For the LLM interaction: Some places have differing Prompt snippets depending
on changes in game- and/or player state. Instead of setting these in the object
itself, a function is called
"""
from GameState import GameState
from PlayerState import PlayerState

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

def p_schuppen_place_prompt_f(gs: GameState, pl: PlayerState) -> str:
    rv ="Es ist heiss und die Sonne knallt erbarmungslos vom Himmel. Hier ist ein alter Holzschuppen. "
    if gs.dach:
        rv=rv+"Seine Bretter sind verwittert, aber der Schuppen ist intakt. "

    else:
        rv=rv+"Die Bretter sind verwittert. Er wirkt baufällig. Er hat kein Dach mehr. "
    if gs.schuppentuer:
        rv = rv+"Die Schuppentür steht offen. "
    else:
        rv = rv+"Der Schuppen ist abgeschlossen. "
    if gs.leiter:
        rv = rv+"Eine Leiter lehnt am Schuppen"

    return rv


def p_innen_place_prompt_f(gs: GameState, pl: PlayerState) -> str:
    rv = "Es ist heiss und die Sonne knallt erbarmungslos vom Himmel. Wir sind innerhalb eines alten Holzschuppens. "
    if gs.dach:
        rv = rv + "Es riecht muffig und staubig, und ein wenig nach Verwesung. Grelles Sonnenlicht dringt durch Ritzen zwischen den Brettern und die offene Tür. "

    else:
        rv = rv + "Der Schuppen hat kein Dach mehr. Das grelle Sonnenlicht erleuchtet alle Gegenstände Erbarmungslos."

    return rv