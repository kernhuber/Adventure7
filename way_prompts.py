"""
Special Prompts for 'Way' objects.
Suppposed to determine, if you can walk or run along a way, or if you need to for example climb it
"""
# from GameState import GameState
from way import Way
#from PlayerState import PlayerState

def w_schuppen_dach_prompt_f(gs:"GameState", pl:"PlayerState", w:Way) -> str:
    r = w.obstruction_check(gs)
    if r == "Free":
        return """
        *** Diesen Weg kann man nur erklimmen, klettern, steigen, besteigen oder gehen. 
        Beispiele: 
        'klettere auf das Dach' 
        'erklimme die Leiter'
        'gehe auf das Dach'
        'klettere auf den Schuppen'
        in diesen und vergleichbaren Fällen liefere 'gehe dach' zurück
        """
    else:
        return r

def w_dach_schuppen_prompt_f(gs:"GameState", pl:"PlayerState", w:Way) -> str:
    return """
    *** Diesen Weg kann man gehen, herabsteigen, heruntersteigen oder auch herunterspringen.
    Beispiele:
    'klettere hinunter'
    'springe vom Dach"
    'steige vom Schuppen herab'
    in diesen oder Vergleichbaren Fällen liefere 'gehe schuppen" zurück
    """

def w_innen_schuppen_prompt_f(gs:"GameState", pl:"PlayerState", w:Way) -> str:
    return """
    *** Verben für diesen Weg: gehen, verlassen.
    Beispiele:
    'gehe nach außen'
    'verlasse den Schuppen"
    'gehe aus dem Schuppen'
    in diesen oder Vergleichbaren Fällen liefere 'gehe p_schuppen" zurück
    """

def w_ubahn_warenautomat_prompt_f(gs:"GameState", pl:"PlayerState", w:Way) -> str:
    return """
* Diesen weg kann man gehen, hinaufsteigen, herausgehen, laufen, hinauflaufen oder rauflaufen
* Dieser Weg ist implizit eine Rolltreppe, ein Weg an die Oberfläche oder aus der U-Bahnstation heraus
* Dieser weg führt zu o_warenautomat, Oberfläche, nach draussen, zurück - alles, was aus einer U-Bahn-Station an die Oberfläche führt
* Beispiele:
- gehe an die Oberfläche zurück
- steige die treppe hoch
- laufe wieder nach draussen zurück
- steige die Rolltreppe hoch (auch wenn gar keine Treppe bei den Objekten ist)
- gehe zum Warenautomat
- verlasse die U-Bahn-Station
* In all diesen Beispielen, und anderen Situationen, in denen der Spieler die U-Bahn-Station über diesen Weg verlässt, liefere
'gehe p_warenautomat' zurück

"""

def w_hoehle_felsen_prompt_f(gs:"GameState", pl:"PlayerState", w:Way) -> str:
    return """
* Diesen Weg kann man gehen, laufen. Man kann mit ihm die Höhle verlassen und aus der Höhle rausgehen.
* Dieser Weg wird implizit gegangen, wenn jemand die Höhle verlässt oder nach draussen geht
* Beispiele:
- Verlasse die Höhle
- Gehe aus der Höhle raus
- Gehe raus
- Gehe nach draussen
* Liefere in diesen und ähnlichen Fällen 'gehe p_felsen' zurück
    """

def w_solaranlage_plateau_prompt_f(gs:"GameState", pl:"PlayerState", w:Way) -> str:
    return """
* Dieser Weg ist ein Pfad von der Solaranlage zum Plateau auf dem Hügel
* Man kann diesen Weg gehen, laufen, erklimmen, erklettern und sich anderweitig auf ihm bewegen.
* Liefere "gehe p_plateau" zurück, wenn dieser Weg beschritten wird
"""

def w_plateau_solaranlage_prompt_f(gs:"GameState", pl:"PlayerState", w:Way) -> str:
    return """
* Dieser Weg ist ein Pfad vom Plateau auf dem Hügel zu einer großen Solaranlage
* Man kann diesen Weg gehen, laufen, herabklettern und sich anderweitig auf ihm bewegen.
* Liefere "gehe p_solaranlage" zurück, wenn dieser Weg beschritten wird
"""# --- missing_functions Output ---

# Quelle (Original): ../WayPrompts.py

# Quelle (Stage)   : WayPrompts.py

# Enthalten: 6 fehlende Funktion(en): w_felsen_plateau_prompt_f, w_ubahnschacht_ubahn2_prompt_f, w_plateau_felsen_prompt_f, w_hohle_korridor_prompt_f, w_korridor_hohle_prompt_f, w_ubahn2_ubahnschacht_prompt_f



def w_plateau_felsen_prompt_f(gs: "GameState", pl: "PlayerState", w: "Way") -> str:
    # TODO: implement callback
    return """
Dieser Weg führt vom Plateau auf dem Hügel zum Felsen oder zum Höhleneingang.
Man kann diesen Weg gehen, laufen, herabklettern, herablaufen oder sich anderweitig auf ihm bewegen.
Liefere "gege p_felsen" zurück, wenn dieser Weg beschritten wird.
            """

def w_felsen_plateau_prompt_f(gs: "GameState", pl: "PlayerState", w: "Way") -> str:
    # TODO: implement callback
    return """
Dieser Weg führt vom Felsen oder Höhleneingang zu einem Plateau auf dem Hügel.
Man kann diesen Weg gehen, laufen hinaufklettern, hinauflaufen oder sich anderweitig auf ihm bewegen.
Liefere "gehe p_plateau" zurück, wenn dieser Weg beschritten wird.
    """

def w_ubahn2_ubahnschacht_prompt_f(gs: "GameState", pl: "PlayerState", w: "Way") -> str:
    # TODO: implement callback
    return ""

def w_ubahnschacht_ubahn2_prompt_f(gs: "GameState", pl: "PlayerState", w: "Way") -> str:
    # TODO: implement callback
    return ""

def w_hoehle_korridor_prompt_f(gs: "GameState", pl: "PlayerState", w: "Way") -> str:

    r = w.obstruction_check(gs)
    if r == "Free":
        return """
    Der Weg führt in einen Korridor, von dem weitere Wege abgehen.
    Man kann diesen Weg gehen, in ihn hineingehen, ihn beschreiten oder ähnliches. Wenn der Weg beschritten wird,
    liefere "gehe p_korridor" zurück.
    """
    else:
        return r

def w_korridor_hohle_prompt_f(gs: "GameState", pl: "PlayerState", w: "Way") -> str:
    # TODO: ...
    return ""
