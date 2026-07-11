"""Gemeinsamer Narrations-Prompt-Aufbau für ALLE LLM-Backends (Gemini, Gemma, ...).

Baut aus dem Spielzustand (Ort, Objekte, Wege, anwesende NPCs) den faktentreuen
Erzähler-Prompt. Bewusst **backend-neutral**: keine google-/ollama-Importe; die NPC-Klassen
werden lazy importiert, damit die Datei überall (auch im Sandbox) ladbar bleibt.

Herkunft: 1:1 aus ``GeminiInterface.gen_narration_prompt`` extrahiert, damit Gemini UND Gemma
denselben reichen Prompt nutzen. Vorher hatte Gemma eine kondensierte Fassung, die Hund/Zombie
und die Wege NICHT erwähnte -> knappe Narration ohne NPCs. Jetzt teilen sich beide diese eine
Quelle (siehe CLAUDE.md, Gemma-Narration).
"""
from __future__ import annotations


def build_narration_prompt(gs, pl) -> str:
    """Faktentreuer Erzähler-Prompt für den aktuellen Ort des Spielers ``pl``.

    Enthält: generelles Wüsten-Szenario, Ortsbeschreibung, sichtbare Objekte, begehbare
    Wege und die Präsenz-/Stimmungshinweise der anwesenden NPCs (Hund/Zombie). Die
    volatile "Vorherige Beschreibung" gehört bewusst NICHT hierher (sie ist die eigene
    frühere Ausgabe und würde den Narrations-Cache brechen) - das Backend hängt sie bei
    der Generierung selbst an.
    """
    if pl.location.place_prompt_f:
        pl_loc_prompt = pl.location.place_prompt_f(gs, pl)
    else:
        pl_loc_prompt = pl.location.place_prompt

    r = f"""
Du bist der Erzähler in einem Adventure-Spiel. Deine Aufgabe ist es, die folgenden Informationen
zu einem Stimmungsvollen Text zusammenzufassen. Halte Dich dabei strikt an die Vorgaben und erfinde
keine neuen Orte, Gegenstände, Akteure oder sonstige Dinge. Deine Zusammenfassung sollte 500 Zeichen
nicht überschreiten.

+---------------------+
+ Generelles Szenario +
+---------------------+
Sofern der Spieler sich an den Orten start, warenautomat, geldautomat, dach oder felsen befindet,
gilt folgendes generelles Szenario
- Wüste
- Greller Sonnenschein
- extrem heiss

An anderen Orten wird das Szenario in der Ortsbeschreibung beschrieben. In diesem Fall
verwende das dort angegebene Szenario

Rede den Spieler in der ersten Person an!

+-------------------------------------+
+ Ort des Spielers oder der Spielerin +
+-------------------------------------+
- {pl.name} (Spieler/Spielerin) befindet sich am Ort "{pl.location.callnames[0]}"

Die Ortsbeschreibung:
=====================

{pl_loc_prompt}

+-----------------------+
+ Objekte an diesem Ort +
+-----------------------+
        """
    for obj in pl.location.place_objects:
        if not obj.hidden:
            r = r + obj.prompt_f(gs, pl)
    r = r + """
+----------------------------+
+ Wege, die hier existrieren +
+----------------------------+
"""
    for w in pl.location.ways:
        if w.visible:
            f = w.obstruction_check(gs)
            if f != "Free":
                r = r + f"- {f}"
            else:
                r = r + f"- {w.destination.callnames[0]}"
            r = r + "\n"

    # Anwesende NPCs: ihre *_prompt-Methoden liefern die Präsenz-/Stimmungshinweise
    # ("!!! Ein Hund befindet sich am selben Ort !!!" bzw. die Zombie-Warnung), damit
    # der Erzähler sie erwähnt. Lazy-Import vermeidet Zyklen / schwere Backends.
    from npc_dog_state import NPCDogState
    dog = next((d for d in gs.players if type(d) is NPCDogState), None)
    if dog:
        r = r + "\n" + dog.dog_prompt(gs, pl)

    from npc_zombie_state import NPCZombieState
    zombie = next((z for z in gs.players if isinstance(z, NPCZombieState)), None)
    if zombie:
        zp = zombie.zombie_prompt(gs, pl)
        if zp:
            r = r + "\n" + zp

    return r
