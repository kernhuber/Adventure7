"""
Functions which check, if a Way is obstructed. They return the String "Free", if the
way is not obstructed, the reason for obstruction otherwise
"""
from GameState import GameState

def _F(gs: GameState):
    """Return the structured flags container (GameFlags) from GameState."""
    return gs.get_flags()

def w_schuppen_innen_f(gs: GameState):
    if not _F(gs).schuppentuer:
        return "Dieser Weg ist versperrt - die Tür ist abgeschlossen!"
    else:
        return "Free"

def w_warenautomat_ubahn_f(gs: GameState):
    if _F(gs).hebel:
        return "Free"
    else:
        return "Ist hier ein Weg? Und wenn, dann ist er versperrt!"

def w_felsen_hoehle_f(gs: GameState):
    if _F(gs).felsen:
        return "Da könnte ein Weg hinter dem Felsen sein - aber der Felsen liegt im Weg!"
    else:
        return "Free"

def w_schuppen_dach_f(gs: GameState):
    if _F(gs).dach:
        if not _F(gs).leiter:
            return "Hier kommst du nicht so ohne weiteres hoch!"
        else:
            return "Free"
    else:
        return "Da ist gar kein Dach mehr - das hat jemand weggesprengt! "# --- missing_functions Output ---

# Quelle (Original): ../GameObstructionCheckFunctions.py

# Quelle (Stage)   : GameObstructionCheckFunctions.py

# Enthalten: 4 fehlende Funktion(en): w_ubahn2_u_bahnschacht_obstruction_check, w_ubahnschacht_ubahn2_obstruction_check, w_korridor_hohle_obstruction_check, w_hohle_korridor_obstruction_check



def w_ubahn2_u_bahnschacht_obstruction_check(gs: "GameState", pl: "PlayerState", w: "Way") -> str:
    # TODO: implement callback
    return ""

def w_ubahnschacht_ubahn2_obstruction_check(gs: "GameState", pl: "PlayerState", w: "Way") -> str:
    # TODO: implement callback
    return ""

def w_hohle_korridor_obstruction_check(gs: "GameState", pl: "PlayerState", w: "Way") -> str:
    # TODO: implement callback
    return ""

def w_korridor_hohle_obstruction_check(gs: "GameState", pl: "PlayerState", w: "Way") -> str:
    # TODO: implement callback
    return ""
