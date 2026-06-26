"""
Functions which check, if a Way is obstructed. They return the String "Free", if the
way is not obstructed, the reason for obstruction otherwise
"""
from game_state import GameState

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


def w_wagen_ubahn1_f(gs: GameState):
    if not _F(gs).wagen_ubahn2:
        return "Free"
    else:
        return "Du kannst von hier nicht auf den ersten Bahnsteig gehen"


def w_ubahn1_wagenf(gs: GameState):
    if not _F(gs).wagen_ubahn2:
        return "Free"
    else:
        return "Hier ist kein Wagen mehr!"


def w_wagen_ubahn2_f(gs: GameState):
    if _F(gs).wagen_ubahn2:
        return "Free"
    else:
        return "Du kannst von hier nicht auf den zweiten Bahnsteig gehen"


def w_ubahn2_wagenf(gs: GameState):
    if _F(gs).wagen_ubahn2:
        return "Free"
    else:
        return "Hier ist kein Wagen mehr!"

# Quelle (Original): ../GameObstructionCheckFunctions.py

# Quelle (Stage)   : GameObstructionCheckFunctions.py

# Enthalten: 4 fehlende Funktion(en): w_ubahn2_ubahnschacht_obstruction_check, w_ubahnschacht_ubahn2_obstruction_check, w_korridor_hohle_obstruction_check, w_hohle_korridor_obstruction_check



def w_ubahn2_ubahnschacht_obstruction_check(gs: "GameState") -> str:
    # TODO: implement callback
    return "Free"

def w_ubahnschacht_ubahn2_obstruction_check(gs: "GameState") -> str:
    # TODO: implement callback
    return "Free"

def w_hoehle_korridor_obstruction_check(gs: "GameState") -> str:
    if gs.korridor_offen:
        return "Free"
    else:
        return "Die Stahltür ist fest verschlossen. Durch ein kleines, vergittertes Fenster kannst du auf der anderen Seite der Tür einen Korridor erkennen."


def w_korridor_hoehle_obstruction_check(gs: "GameState") -> str:
    # TODO:
    return ""

def w_solaranlage_ubahn2_obstruction_check(gs: "GameState") -> str:
    if _F(gs).korridor_offen:
        return "Free"
    else:
        return "Die Falltür ist fest verschlossen. Wohin sie nur führen mag? Und wie öffnet man sie?"

def w_ubahn2_solaranlage_obstruction_check(gs: "GameState") -> str:
    # TODO: implement callback
    return ""

def w_ubahn2_kontrollraum_obstruction_check(gs: "GameState") -> str:
    # TODO: implement callback
    return ""

def w_kontrollraum_ubahn2_obstruction_check(gs: "GameState") -> str:
    # TODO: implement callback
    return ""

def w_ubahn2_ubahnschacht_obstruction_check(gs: "GameState") -> str:
    # TODO: implement callback
    return ""

def w_ubahn_schacht_korridor_obstruction_check(gs: "GameState") -> str:
    # TODO: implement callback
    return ""

def w_labor_korridor_obstruction_check(gs: "GameState") -> str:
    # TODO: implement callback
    return ""

def w_korridor_labor_obstruction_check(gs: "GameState") -> str:
    # TODO: implement callback
    return ""

def w_korridor_bibliothek_obstruction_check(gs: "GameState") -> str:
    # TODO: implement callback
    return ""

def w_korridor_besenkammer_obstruction_check(gs: "GameState") -> str:
    # TODO: implement callback
    return ""

def w_besenkammer_korridor_obstruction_check(gs: "GameState") -> str:
    # TODO: implement callback
    return ""

def w_generatorraum_labor_obstruction_check(gs: "GameState") -> str:
    # TODO: implement callback
    return ""

def w_labor_generatorraum_obstruction_check(gs: "GameState") -> str:
    # TODO: implement callback
    return ""
