"""Demo-mode fallbacks used when the real game engine is unavailable.

Extracted from web_backend_server.py (Step 1.3 refactor). These are pure functions
with no dependency on the game/LLM stack, so the demo path can run (and be tested)
standalone. ``create_demo_game_state`` also serves as the fallback state returned by
``serialization.serialize_real_game_state`` when serialization fails.
"""


def create_demo_game_state():
    """Erstelle Demo-GameState ohne echte Game-Module"""
    return {
        "round": 1,
        "game_over": False,
        "game_won": False,
        "player": {
            "name": "WebPlayer",
            "location": "Wüsten-Start",
            "thirst": 40,
            "inventory": ["Briefumschlag"]
        },
        "dog": {
            "location": "Geldautomat",
            "state": "Der Hund tut nichts... (Demo)"
        },
        "environment": {
            "objects": ["Kaputtes Fahrrad"],
            "ways": ["Zum Schuppen", "Zum Warenautomat", "Zum Geldautomat"],
            "blockedWays": []
        },
        "scene_description": """Du befindest dich in einer endlosen Wüste. Die Sonne brennt erbarmungslos herab. 
            Dein Fahrrad liegt kaputt neben dir - die Kette ist gerissen. Du musst einen Weg finden, 
            das Fahrrad zu reparieren und deinen wichtigen Briefumschlag rechtzeitig abzuliefern."""
    }


def process_simple_command_execution(command_dict):
    """Einfache Command-Ausführung ohne vollständige Game-Engine"""
    func_name = command_dict.get('function_call', {}).get('name', 'unknown')
    return f"Kommando '{func_name}' erkannt (vereinfachter Modus)"


def process_demo_command_execution(game_state, func_name, args):
    """Demo-Command-Ausführung"""
    if func_name == "hilfe":
        return "**Demo-Modus aktiv** - Verfügbare Kommandos: hilfe, umsehen, gehe, nimm, untersuche"
    elif func_name == "umsehen":
        return "Du blickst umher. Die Wüstensonne brennt erbarmungslos."
    elif func_name == "gehe":
        direction = args.get('direction', 'unbekannt')
        if "schuppen" in direction.lower():
            game_state["player"]["location"] = "Schuppen"
            game_state["environment"]["objects"] = ["Blumentopf", "Stuhl"]
            game_state["environment"]["ways"] = ["Zurück zum Start"]
            game_state["scene_description"] = "Du stehst vor einem alten Holzschuppen."
            return "Du gehst zum Schuppen."
        elif "start" in direction.lower():
            game_state["player"]["location"] = "Wüsten-Start"
            game_state["environment"]["objects"] = ["Kaputtes Fahrrad"]
            game_state["environment"]["ways"] = ["Zum Schuppen", "Zum Warenautomat", "Zum Geldautomat"]
            game_state["scene_description"] = "Du bist zurück am Startpunkt."
            return "Du kehrst zum Start zurück."
        else:
            return f"Du gehst zu: {direction}"
    elif func_name == "zurueckweisen":
        why = args.get('why', 'Unbekannter Grund')
        return f"***{why}***"
    else:
        return f"Demo-Kommando '{func_name}' ausgeführt"
