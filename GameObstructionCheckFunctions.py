"""
Functions which check, if a Way is obstructed. They return the String "Free", if the
way is not obstructed, the reason for obstruction otherwise
"""
from GameState import GameState

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