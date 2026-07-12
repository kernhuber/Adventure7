"""Convert the live GameState into the JSON-serialisable dict the web GUI expects.

Extracted from web_backend_server.py (Step 1.3 refactor). On any failure it falls
back to the demo state so the front-end always receives a well-formed payload.
"""
import traceback

from utils import dprint, dl
from webserver.demo import create_demo_game_state


def serialize_real_game_state(game, session_id=None):
    """Konvertiere echtes GameState zu JSON-Format"""
    from npc_dog_state import NPCDogState
    from npc_zombie_state import NPCZombieState
    try:
        player = game.players[0] if game.players else None
        if not player:
            return create_demo_game_state()

        # Finde Hund (kann None sein falls Hund eliminiert wurde)
        dog = next((d for d in game.players if type(d) is NPCDogState), None)

        # Sichere Zugriffe
        current_location = getattr(player, 'location', None)
        if not current_location:
            return create_demo_game_state()

        # Objekte
        visible_objects = []
        try:
            for obj in getattr(current_location, 'place_objects', []):
                if not getattr(obj, 'hidden', True):
                    callnames = getattr(obj, 'callnames', ['Unbekanntes Objekt'])
                    if callnames:
                        visible_objects.append(callnames[0])
        except:
            pass

        # Wege
        available_ways = []
        blocked_ways = []
        try:
            for way in getattr(current_location, 'ways', []):
                if getattr(way, 'visible', True):
                    try:
                        obstruction = way.obstruction_check(game) if hasattr(way, 'obstruction_check') else "Free"
                        destination = getattr(way, 'destination', None)
                        if destination:
                            dest_name = getattr(destination, 'callnames', ['Unbekanntes Ziel'])
                            dest_name = dest_name[0] if dest_name else 'Unbekanntes Ziel'

                            if obstruction == "Free":
                                available_ways.append(dest_name)
                            else:
                                blocked_ways.append(f"{dest_name} ({obstruction})")
                    except:
                        pass
        except:
            pass

        # Szenenbeschreibung - NUR wenn explizit angefordert

        scene_description = game.llm.narrate(game, player)


        # Hund-Informationen
        dog_info = {
            "location": "Unbekannt",
            "state": "Kein Hund im Spiel"
        }
        if dog:
            try:
                dog_location = getattr(dog.location, 'callnames', ['Unbekannt'])
                dog_state_obj = getattr(dog, 'dog_state', None)
                # "angry" while the dog is in its ATTACK state (growling/sauer); the
                # transient "attack" (mini-game) blink is driven by the frontend from
                # the 'minigame' NPC action.
                dog_mood = "angry" if (dog_state_obj is not None
                                       and getattr(dog_state_obj, "name", "") == "ATTACK") else "normal"
                dog_info = {
                    "location": dog_location[0] if dog_location else 'Unbekannt',
                    "state": getattr(dog, 'dog_state_message', 'Der Hund tut nichts'),
                    "here": dog.location == player.location if player else False,
                    "mood": dog_mood,
                }
            except:
                pass
        # Zombie-Informationen
        zombie_info = {
            "location": "Unbekannt",
            "state": "Kein Zombie im Spiel"
        }
        zombie = next((z for z in game.players if isinstance(z, NPCZombieState)), None)
        if zombie:
            try:
                zombie_location = getattr(zombie.location, 'callnames', ['Unbekannt'])
                zombie_state_obj = getattr(zombie, 'zombie_state', None)
                zombie_info = {
                    "location": zombie_location[0] if zombie_location else 'Unbekannt',
                    "state": getattr(zombie, 'zombie_state_message', 'Der Zombie tut nichts'),
                    # Enum-Name (z.B. "HUNTING") -> steuert die Glüh-Farbe des Icons im GUI.
                    "zstate": getattr(zombie_state_obj, 'name', '') if zombie_state_obj is not None else '',
                    "here": zombie.location == player.location if player else False
                }
            except:
                pass

        return {
            "round": getattr(game, 'time', 1),
            "game_over": getattr(game, 'game_over', False),
            "game_won": getattr(game, 'game_won', False),
            "power_main": getattr(game, 'hauptschalter', False),
            "player": {
                "name": getattr(player, 'name', player.name),
                "location": getattr(current_location, 'callnames', ['Unbekannt'])[0],
                "thirst": getattr(player, 'thirst_counter', 40),
                "inventory": [getattr(item, 'callnames', ['Unbekanntes Item'])[0]
                              for item in getattr(player, 'inventory', [])]
            },
            "dog": dog_info,
            "zombie": zombie_info,
            # Endspiel: Zählerstände der beiden Notfall-Schalter (0 = inaktiv). Das GUI zeigt sie
            # an, damit sich Spieler und Zombie beim Aktivieren koordinieren können, auch wenn sie
            # in verschiedenen Räumen sind.
            "switches": {
                "kontrollraum": getattr(game, 'schalter_kontrollraum_timer', 0),
                "generatorraum": getattr(game, 'schalter_generatorraum_timer', 0),
            },
            "environment": {
                "objects": visible_objects,
                "ways": available_ways,
                "blockedWays": blocked_ways
            },
            "scene_description": scene_description
        }

    except Exception as e:
        dprint(dl.WEBGUI, f"❌ Fehler beim Serialisieren: {e}")
        traceback.print_exc()  # gibt den kompletten Stacktrace auf stderr aus
        return create_demo_game_state()
