"""
Functions which check, if a Way is obstructed. They return the String "Free", if the
way is not obstructed, the reason for obstruction otherwise
"""
from game_state import GameState

def _F(gs: GameState):
    """Return the structured flags container (GameFlags) from GameState."""
    return gs.get_flags()


def _deep_locked(gs: GameState, reason: str = "Der Weg tiefer in die Anlage ist noch versperrt.") -> str:
    """Gemeinsames Gate für die unterirdische Anlage (Kontrollraum, U-Bahn-Schacht,
    Korridor, Labor, Bibliothek, Besenkammer, Generatorraum): alles dahinter ist erst
    begehbar, wenn ``korridor_offen`` gesetzt ist.

    HINWEIS: ``korridor_offen`` wird derzeit noch NIRGENDS auf True gesetzt - es fehlt
    noch der "Öffner" (z.B. ein Schalter/Hebel/Schlüssel). Bis dahin bleibt die Anlage
    verschlossen (außer in GHOSTMODE, das alle obstruction_checks umgeht).
    """
    return "Free" if _F(gs).korridor_offen else reason

def w_schuppen_innen_obstruction_check(gs: GameState):
    if not _F(gs).schuppentuer:
        return "Dieser Weg ist versperrt - die Tür ist abgeschlossen!"
    else:
        return "Free"

def w_warenautomat_ubahn_obstruction_check(gs: GameState):
    if _F(gs).hebel:
        return "Free"
    else:
        return "Ist hier ein Weg? Und wenn, dann ist er versperrt!"

def w_felsen_hoehle_obstruction_check(gs: GameState):
    if _F(gs).felsen:
        return "Da könnte ein Weg hinter dem Felsen sein - aber der Felsen liegt im Weg!"
    else:
        return "Free"

def w_schuppen_dach_obstruction_check(gs: GameState):
    if _F(gs).dach:
        if not _F(gs).leiter:
            return "Hier kommst du nicht so ohne weiteres hoch!"
        else:
            return "Free"
    else:
        return "Da ist gar kein Dach mehr - das hat jemand weggesprengt! "# --- missing_functions Output ---


def w_wagen_ubahn_obstruction_check(gs: GameState):
    if not _F(gs).wagen_ubahn2:
        return "Free"
    else:
        return "Du kannst von hier nicht auf den ersten Bahnsteig gehen"


def w_ubahn_wagen_obstruction_check(gs: GameState):
    if not _F(gs).wagen_ubahn2:
        return "Free"
    else:
        return "Hier ist kein Wagen mehr!"


def w_wagen_ubahn2_obstruction_check(gs: GameState):
    if _F(gs).wagen_ubahn2:
        return "Free"
    else:
        return "Du kannst von hier nicht auf den zweiten Bahnsteig gehen"


def w_ubahn2_wagen_obstruction_check(gs: GameState):
    if _F(gs).wagen_ubahn2:
        return "Free"
    else:
        return "Hier ist kein Wagen mehr!"

# Quelle (Original): ../GameObstructionCheckFunctions.py

# Quelle (Stage)   : GameObstructionCheckFunctions.py

# Enthalten: 4 fehlende Funktion(en): w_ubahn2_ubahnschacht_obstruction_check, w_ubahnschacht_ubahn2_obstruction_check, w_korridor_hohle_obstruction_check, w_hohle_korridor_obstruction_check



# --- Unterirdische Anlage: alle Wege hinter dem Korridor-Gate (``korridor_offen``) ----
# Früher waren das TODO-Stubs, die "" zurückgaben -> die Serialisierung wertete sie als
# blockiert, daher war die gesamte Tiefe (Kontrollraum, U-Bahn-Schacht, Labor, ...)
# unerreichbar. Jetzt einheitlich über ``_deep_locked`` an ``korridor_offen`` gehängt.

def w_hoehle_korridor_obstruction_check(gs: "GameState") -> str:
    if _F(gs).korridor_offen:
        return "Free"
    else:
        return "Die Stahltür ist fest verschlossen. Durch ein kleines, vergittertes Fenster kannst du auf der anderen Seite der Tür einen Korridor erkennen."


def w_korridor_hoehle_obstruction_check(gs: "GameState") -> str:
    return _deep_locked(gs)

def w_solaranlage_ubahn2_obstruction_check(gs: "GameState") -> str:
    if _F(gs).korridor_offen:
        return "Free"
    else:
        return "Die Falltür ist fest verschlossen. Wohin sie nur führen mag? Und wie öffnet man sie?"

def w_ubahn2_solaranlage_obstruction_check(gs: "GameState") -> str:
    # Der Weg ist die Geheimtür hinter dem Werbeplakat. Verstecken/Aufdecken regelt die
    # Sichtbarkeit (o_werbeplakat_apply_f schaltet ``visible``); ist die Tür sichtbar,
    # ist sie auch begehbar. Wichtig: "Free" zurückgeben (nicht ""), sonst wertet die
    # Serialisierung den Weg als blockiert und er taucht nicht in der Umgebung auf.
    return "Free"

def w_ubahn2_kontrollraum_obstruction_check(gs: "GameState") -> str:
    return _deep_locked(gs, "Die Tür zum Kontrollraum ist verschlossen.")

def w_kontrollraum_ubahn2_obstruction_check(gs: "GameState") -> str:
    return _deep_locked(gs)

def w_ubahn2_ubahnschacht_obstruction_check(gs: "GameState") -> str:
    # Der U-Bahn-Wagen versperrt am zweiten Bahnsteig den schmalen Durchgang zum Schacht.
    # Nur wenn er an Bahnsteig 1 wartet (wagen_ubahn2 == False), ist der Weg frei - dann
    # blendet ihn _shuttle_wagon() in der Umgebung ein (visible). Gesteuert wird der Wagen
    # über die U-Bahn-Steuerung (Kontrollraum) bzw. den Türschliesser (im Wagen).
    if not _F(gs).wagen_ubahn2:
        return "Free"
    return "Der wartende U-Bahn-Wagen versperrt den schmalen Durchgang zum U-Bahn-Schacht."

def w_ubahnschacht_ubahn2_obstruction_check(gs: "GameState") -> str:
    # Rückweg aus dem Schacht auf den Bahnsteig ist immer frei (kein Soft-Lock, falls der
    # Wagen zurückkehrt, während man im Schacht ist).
    return "Free"

def w_ubahn_schacht_korridor_obstruction_check(gs: "GameState") -> str:
    return _deep_locked(gs)

def w_labor_korridor_obstruction_check(gs: "GameState") -> str:
    return _deep_locked(gs)

def w_korridor_labor_obstruction_check(gs: "GameState") -> str:
    return _deep_locked(gs)

def w_korridor_bibliothek_obstruction_check(gs: "GameState") -> str:
    return _deep_locked(gs)

def w_korridor_besenkammer_obstruction_check(gs: "GameState") -> str:
    return _deep_locked(gs)

def w_besenkammer_korridor_obstruction_check(gs: "GameState") -> str:
    return _deep_locked(gs)

def w_generatorraum_labor_obstruction_check(gs: "GameState") -> str:
    return _deep_locked(gs)

def w_labor_generatorraum_obstruction_check(gs: "GameState") -> str:
    return _deep_locked(gs)
