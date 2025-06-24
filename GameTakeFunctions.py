"""
Special functions when a GameObject is "taken"
"""
from GameState import GameState
from PlayerState import PlayerState

def o_leiter_take_f(gs: GameState, pl: PlayerState=None) -> str:
    """ If Leiter is taken away, some paths may become invisible"""
    if gs.leiter:
        gs.leiter = False
        return "Du kannst jetzt nicht mehr auf den Schuppen klettern"
    else:
        gs.leiter = False
        return ""

def o_fahrradkette_take_f(gs: GameState, pl: PlayerState=None) -> str:
    return "Du hast die Fahrradkette gefunden! Damit kannst Du Dein Fahrrad reparieren!"