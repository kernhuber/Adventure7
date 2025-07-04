"""
Special Prompts for 'Way' objects.
Suppposed to determine, if you can walk or run along a way, or if you need to for example climb it
"""
# from GameState import GameState
from Way import Way
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