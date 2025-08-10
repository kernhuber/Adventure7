"""
Special functions when a GameObject is "taken"
"""
from GameState import GameState
from PlayerState import PlayerState

def _F(gs: GameState):
    """Return the structured flags container (GameFlags) from GameState."""
    return gs.get_flags()

def o_leiter_take_f(gs: GameState, pl: PlayerState=None) -> str:
    """ If Leiter is taken away, some paths may become invisible"""
    if _F(gs).leiter:
        gs.leiter = False
        return "Du hast die Leiter nun bei Dir, aber so kannst du nicht mehr auf den Schuppen klettern"
    else:
        gs.leiter = False
        return "Du hast die Leiter nun bei dir."

def o_fahrradkette_take_f(gs: GameState, pl: PlayerState=None) -> str:
    return "Du hast die Fahrradkette gefunden! Damit kannst Du Dein Fahrrad reparieren!"

def o_blumentopf_take_f(gs: GameState, pl: PlayerState=None) -> str:
    f = ""
    schluessel = gs.objects["o_schluessel"]
    if schluessel.hidden and pl.location == schluessel.ownedby:
        schluessel.hidden = False
        f = "***Und siehe da: unter dem Blumentopf lag ein Schlüssel!***"
    return f"Du hast den Blumentopf nun bei dir. {f}"