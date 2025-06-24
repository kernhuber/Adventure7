from GameState import GameState
from PlayerState import PlayerState
from GameObject import GameObject
"""
 Reveal Functions Functions executed when a game object is "revealed

"""
def o_blumentopf_reveal_f(gs: GameState, pl:PlayerState=None, what: GameObject=None, onwhat: GameObject=None) ->str:
    if gs.objects["o_schluessel"].hidden:
        retstr = "Ein alter Blumentopf - aber warte: **unter dem Blumentopf liegt ein Schlüssel!!!**"
        gs.objects["o_blumentopf"].examine = "Unter diesem Blumentopf hast Du den Schlüssel gefunden"
        gs.objects["o_schluessel"].hidden = False
        return retstr
    else:
        return gs.objects["o_blumentopf"].examine

def o_skelett_reveal_f(gs: GameState, pl:PlayerState=None, what: GameObject=None, onwhat: GameObject=None) ->str:
    if gs.objects["o_geldboerse"].hidden:
        gs.objects["o_geldboerse"].hidden = False
        gs.objects["o_skelett"].examine = "Bei diesem Knochenmann hast Du eine Geldbörse gefunden!"
        return "Oh weh, der sitzt wohl schon länger hier! Ein Skelett, welches einen verschlissenen Anzug trägt. **Im Anzug findest du eine Geldboerse!**"

    else:
        return gs.objects["o_skelett"].examine

def o_geldboerse_reveal_f(gs: GameState, pl:PlayerState=None, what: GameObject=None, onwhat: GameObject=None) ->str:
    if gs.objects["o_ec_karte"].hidden:
        gs.objects["o_ec_karte"].hidden = False
        gs.objects["o_geldboerse"].examine = "In dieser Geldbörse hast Du eine EC-Karte gefunden"
        return "Fein! Hier ist eine EC-Karte! Die passt bestimmt in einen Geldautomaten!"
    else:
        return gs.objects["o_geldboerse"].examine

def o_muelleimer_reveal_f(gs: GameState, pl:PlayerState=None, what: GameObject=None, onwhat: GameObject=None) ->str:
    if gs.objects["o_geheimzahl"].hidden:
        from random import randint
        gs.geheimzahl = randint(1, 9999)
        gs.objects["o_geheimzahl"].hidden = False
        gs.objects["o_geheimzahl"].examine = f"Eine Geheimzahl: {gs.geheimzahl:04}"
        return f"Im Mülleimer findest Du einen Zettel mit einer Geheimzahl! Die Geheimzahl ist: {gs.geheimzahl:04}"
    else:
        return gs.objects["o_geheimzahl"].examine

