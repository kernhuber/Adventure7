from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from GameState import GameState
    from PlayerState import PlayerState
    from GameObject import GameObject
    from Place import Place


"""
 Reveal Functions Functions executed when a game object is "revealed

"""


def o_blumentopf_reveal_f(gs: "GameState", pl: "PlayerState" = None, what: "GameObject" = None,
                          onwhat: "GameObject" = None) -> str:
    if gs.objects["o_schluessel"].hidden:
        retstr = "Ein alter Blumentopf - aber warte: **unter dem Blumentopf liegt ein Schlüssel!!!**"
        gs.objects["o_blumentopf"].examine = "Unter diesem Blumentopf hast Du den Schlüssel gefunden"
        gs.objects["o_schluessel"].hidden = False
        return retstr
    else:
        return gs.objects["o_blumentopf"].examine


def o_skelett_reveal_f(gs: "GameState", pl: "PlayerState" = None, what: "GameObject" = None,
                       onwhat: "GameObject" = None) -> str:
    if gs.objects["o_geldboerse"].hidden:
        gs.objects["o_geldboerse"].hidden = False
        gs.objects["o_geldboerse"].ownedby = pl.location
        gs.objects["o_skelett"].examine = "Bei diesem Knochenmann hast Du eine Geldbörse gefunden!"
        return "Oh weh, der sitzt wohl schon länger hier! Ein Skelett, welches einen verschlissenen Anzug trägt. **Im Anzug findest du eine Geldboerse!**"

    else:
        return gs.objects["o_skelett"].examine


def o_geldboerse_reveal_f(gs: "GameState", pl: "PlayerState" = None, what: "GameObject" = None,
                          onwhat: "GameObject" = None) -> str:
    from GameTakeFunctions import _awaken_zombie, _F

    o_geldboerse = gs.objects["o_geldboerse"]

    # If zombie is already awake, just return examine text
    if _F(gs).zombie_awake:
        return o_geldboerse.examine

    # Examining the wallet awakens the zombie
    zombie_text = _awaken_zombie(gs, pl)
    o_geldboerse.examine = "Eine alte, abgewetzte Geldbörse. Sie ist leer."

    return "Du öffnest die Geldbörse - und in diesem Moment geschieht etwas Unheimliches! " + zombie_text


def o_muelleimer_reveal_f(gs: "GameState", pl: "PlayerState" = None, what: "GameObject" = None,
                          onwhat: "GameObject" = None) -> str:
    if gs.objects["o_geheimzahl"].hidden:
        from random import randint
        gs.objects["o_geheimzahl"].hidden = False
        gs.objects["o_geheimzahl"].examine = f"Eine Geheimzahl: {gs.geheimzahl}"
        return f"Im Mülleimer findest Du einen Zettel mit einer Geheimzahl! Die Geheimzahl ist: {gs.geheimzahl}"
    else:
        return gs.objects["o_geheimzahl"].examine