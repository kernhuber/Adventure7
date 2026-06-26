"""
Special functions when a GameObject is "taken"
"""
from game_state import GameState
from player_state import PlayerState

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

def _awaken_zombie(gs: GameState, pl: PlayerState) -> str:
    """Shared zombie awakening logic for both examine and take."""
    from npc_zombie_state import NPCZombieState
    from utils import dprint, dl

    _F(gs).zombie_awake = True

    # Remove the skeleton from the cave
    skelett = gs.objects.get("o_skelett")
    if skelett:
        if skelett in pl.location.place_objects:
            pl.location.place_objects.remove(skelett)
        del gs.objects["o_skelett"]

    # Create zombie NPC at the player's current location
    zombie = NPCZombieState(name="Zombie", location=pl.location)
    dprint(dl.ZOMBIE, f"Zombie erwacht in {pl.location.name}!")

    # Move EC card to zombie's inventory
    ec_karte = gs.objects.get("o_ec_karte")
    if ec_karte:
        if ec_karte in pl.location.place_objects:
            pl.location.place_objects.remove(ec_karte)
        if ec_karte in pl.inventory:
            pl.inventory.remove(ec_karte)
        ec_karte.hidden = False
        zombie.inventory.append(ec_karte)
        ec_karte.ownedby = zombie

    gs.players.append(zombie)

    return (
        "***Das Skelett beginnt sich zu bewegen!*** Knochen knacken, der Nadelstreifenanzug "
        "raschelt, und langsam richtet sich die Gestalt auf. Wo eben noch leere Augenhöhlen "
        "waren, glimmt nun ein schwaches, rötliches Licht. "
        "Der Zombie steht vor dir, schwankend aber aufrecht. "
        "In seiner knochigen Hand hält er eine EC-Karte. "
        "Mit einer heiseren, krächzenden Stimme fragt er: "
        "***'Suchst du etwa... die hier?'***"
    )


def o_geldboerse_take_f(gs: GameState, pl: PlayerState=None) -> str:
    """Taking the wallet awakens the zombie if not already awake."""
    if _F(gs).zombie_awake:
        return "Du hast die Geldbörse aufgenommen."
    zombie_text = _awaken_zombie(gs, pl)
    return "Du greifst nach der Geldbörse - und in diesem Moment geschieht etwas Unheimliches! " + zombie_text


def o_blumentopf_take_f(gs: GameState, pl: PlayerState=None) -> str:
    f = ""
    schluessel = gs.objects["o_schluessel"]
    if schluessel.hidden and pl.location == schluessel.ownedby:
        schluessel.hidden = False
        f = "***Und siehe da: unter dem Blumentopf lag ein Schlüssel!***"
    return f"Du hast den Blumentopf nun bei dir. {f}"