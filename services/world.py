from __future__ import annotations

from dataclasses import dataclass
from collections import deque
from typing import Dict, TYPE_CHECKING, List, Optional

# Keine Laufzeit-Imports auf GameState/Place/Way/GameObject -> verhindert Zyklen/Package-Probleme
if TYPE_CHECKING:
    from game_state import GameState
    from player_state import PlayerState
    from place import Place
    from way import Way
    from game_object import GameObject

# ------------------------------
# Context building helper
# ------------------------------
class ContextBuilder:
    """Builds context dictionaries for narration and for LLM tools."""

    def build_for_llm_tools(self, gs: "GameState", pl: "PlayerState") -> dict:
        context_data: dict = {}

        # 1) Narration
        narration_details: dict = {}
        narration_details["Ortsname"] = pl.location.callnames[0]
        narration_details["Beschreibung"] = (
            pl.location.place_prompt_f(gs, pl)
            if pl.location.place_prompt_f
            else pl.location.place_prompt
        )

        # Objekte hier (sichtbar)
        narration_details["Objekte hier"] = []
        all_object_ids_in_context: List[str] = []
        object_ids_here: List[str] = []   # nur Objekte AM ORT (ohne Inventar/NPCs) -> für 'nimm'
        for obj in pl.location.place_objects:
            if not obj.hidden:
                obj_description_text = obj.prompt_f(gs, pl) if obj.prompt_f else obj.examine
                narration_details["Objekte hier"].append({obj.callnames[0]: obj_description_text})
                all_object_ids_in_context.append(obj.name)
                object_ids_here.append(obj.name)

        # Objekte im Inventar
        narration_details["Objekte, die der Spieler bei sich trägt"] = []
        for obj in pl.inventory:
            obj_description_text = obj.prompt_f(gs, pl) if obj.prompt_f else obj.examine
            narration_details["Objekte, die der Spieler bei sich trägt"].append(
                {obj.callnames[0]: obj_description_text}
            )
            all_object_ids_in_context.append(obj.name)

        # Wege
        narration_details["Wo man hingehen kann"] = []
        all_place_ids_for_navigation: List[str] = []
        for w in pl.location.ways:
            if w.visible:
                wd: dict = {}
                wd["Ziel"] = w.destination.name
                wd["Alternative Namen für das Ziel"] = w.destination.callnames
                if w.way_prompt_f:
                    wd["Spezielle Anweisungen für den Weg"] = w.way_prompt_f(gs, pl, w)
                narration_details["Wo man hingehen kann"].append(wd)
                all_place_ids_for_navigation.append(w.destination.name)

        # NPC nur dann als anwählbares Objekt-/Ziel anbieten, wenn er WIRKLICH am Ort des
        # Spielers ist. Sonst "sieht" das LLM z.B. den Hund und untersucht/anspricht ihn,
        # obwohl er ganz woanders steht (beobachtet mit gemma4: 'untersuche Blumentopf' ->
        # what='Hund'). Die Narrations-Warnung bleibt unberührt (ein ferner Hund darf erwähnt
        # werden) - nur die ID-Listen werden auf Anwesende beschränkt.
        def _here(actor) -> bool:
            return getattr(actor.location, "name", None) == getattr(pl.location, "name", None)

        from npc_dog_state import NPCDogState
        dog_pl = next((p for p in gs.players if isinstance(p, NPCDogState)), None)
        if dog_pl:
            dog_description = dog_pl.dog_prompt(gs, pl)
            if dog_description:
                narration_details["Achtung"] = dog_description
                if _here(dog_pl):
                    all_object_ids_in_context.append(dog_pl.name)

        from npc_zombie_state import NPCZombieState
        zombie_pl = next((p for p in gs.players if isinstance(p, NPCZombieState)), None)
        if zombie_pl:
            zombie_description = zombie_pl.zombie_prompt(gs, pl)
            if zombie_description:
                narration_details["Zombie-Warnung"] = zombie_description
                if _here(zombie_pl):
                    all_object_ids_in_context.append(zombie_pl.name)

        context_data["narration_details"] = narration_details
        context_data["available_object_ids"] = list(set(all_object_ids_in_context))
        context_data["available_object_ids_here"] = list(set(object_ids_here))  # nur am Ort -> 'nimm'
        context_data["available_place_ids"] = list(set(all_place_ids_for_navigation))
        # Gesprächs-/Angriffsziele: nur ANWESENDE NPCs - der Spieler selbst gehört NICHT dazu
        # (sonst wählt das LLM bei Unsicherheit 'interagieren <Spieler>' -> Engine lehnt als
        # "Selbstgespräch" ab, und die eigentliche Eingabe geht unter; beobachtet mit gemma4).
        context_data["available_target_player_ids"] = [p.name for p in gs.players if _here(p) and p is not pl]
        context_data["player_location_id"] = pl.location.name
        context_data["player_inventory_ids"] = [item.name for item in pl.inventory]
        return context_data

    def build(self, gs: "GameState", pl: "PlayerState") -> dict:
        """Compile current game context for LLM parse function."""
        rval: dict = {}
        details: dict = {}
        details["Ortsname"] = pl.location.callnames[0]
        details["Beschreibung"] = (
            pl.location.place_prompt_f(gs, pl)
            if pl.location.place_prompt_f is not None
            else pl.location.place_prompt
        )

        # Objekte hier & im Inventar (sichtbar)
        details["Objekte hier"] = {
            p.callnames[0]: f"{p.prompt_f(gs, pl)}"
            for p in pl.location.place_objects
            if not p.hidden
        }
        details["Objekte, die des Spieler bei sich trägt"] = {
            p.callnames[0]: f"{p.prompt_f(gs, pl)}" for p in pl.inventory
        }

        # Wege
        wege: dict = {}
        for w in pl.location.ways:
            if w.visible:
                wd: dict = {}
                wd["Ziel"] = w.destination.name
                wd["Alternative Namen für das Ziel"] = w.destination.callnames
                if w.way_prompt_f:
                    wd["Spezielle Anweisungen für den Weg"] = w.way_prompt_f(gs, pl, w)
                wege[w.name] = wd
        details["Wo man hingehen kann"] = wege

        # Hund (optional) – lokaler Import vermeidet Zyklen
        from npc_dog_state import NPCDogState
        dog_pl = next((p for p in gs.players if isinstance(p, NPCDogState)), None)
        if dog_pl:
            dp = dog_pl.dog_prompt(gs, pl)
            if dp:
                details["Achtung"] = dp

        # Zombie (optional) – lokaler Import vermeidet Zyklen
        from npc_zombie_state import NPCZombieState
        zombie_pl = next((p for p in gs.players if isinstance(p, NPCZombieState)), None)
        if zombie_pl:
            zp = zombie_pl.zombie_prompt(gs, pl)
            if zp:
                details["Zombie-Warnung"] = zp

        rval["Aktueller Ort"] = details
        return rval


# ------------------------------
# World/data helpers
# ------------------------------
@dataclass
class GameFlags:
    """Container for game-wide boolean/numeric/string flags.
    GameState mirrors its legacy attributes into this structure.
    Einzige Quelle der Wahrheit für die Flag-Namen: GameState.FLAG_FIELDS
    wird per Reflection (dataclasses.fields) aus dieser Klasse abgeleitet.
    """
    schuppentuer: bool = False
    leiter: bool = False
    hebel: bool = False
    geheimzahl: str = "0000"
    wagen_ubahn2: bool = False
    felsen: bool = True
    hauptschalter: bool = False
    dach: bool = True
    warenautomat_intakt: bool = True
    geldautomat_intakt: bool = True
    schuppen_intakt: bool = True
    flasche_voll: bool = True
    falltuer_offen: bool = False
    handrad_geschmiert: bool = False   # Handrad in der Höhle geschmiert?
    werbeplakat_offen: bool = False
    korridor_offen: bool = False       # Chris, händisch gesetzt
    dungeon_offen: bool = False        # Damit man nicht einfach von der Höhle via Korridor überall hinkommt
    kontrollraum_offen: bool = False   # Tür hinter dem Werbeplakat (U-Bahn-2 -> Kontrollraum)
    game_over: bool = False
    game_won: bool = False
    time: int = 0
    debug_mode: bool = False
    zombie_awake: bool = False
    zombie_cooperative: bool = False
    schalter_kontrollraum: bool = False
    schalter_generatorraum: bool = False
    schalter_kontrollraum_timer: int = 0
    schalter_generatorraum_timer: int = 0
    umschlag_geheimbotschaft: bool = False


class WorldModel:
    """Holds places/ways/objects and provides query helpers.
    This class does NOT import UI/LLM modules and stays side-effect free.
    """
    def __init__(self):
        # String-Annotations vermeiden Laufzeit-Imports
        self.places: Dict[str, "Place"] = {}
        self.ways: Dict[str, "Way"] = {}
        self.objects: Dict[str, "GameObject"] = {}

    # --- Query helpers (thin wrappers) ---
    def obj_name_from_friendly_name(self, n: str) -> str:
        for v in self.objects.values():
            if n in v.callnames:
                return v.name
        return n

    def place_name_from_friendly_name(self, n: str) -> str:
        for v in self.places.values():
            if n in v.callnames:
                return v.name
        return n

    def find_shortest_path(self, gs: "GameState", start: "Place", goal: "Place") -> Optional[List["Way"]]:
        """BFS over visible, unobstructed ways. Needs gs for obstruction_check(...)."""
        queue: deque[tuple["Place", List["Way"]]] = deque()
        queue.append((start, []))
        visited: set[str] = set()
        while queue:
            current_place, path_so_far = queue.popleft()
            if current_place == goal:
                return path_so_far
            if current_place.name in visited:
                continue
            visited.add(current_place.name)
            for way in current_place.ways:
                if (
                    way.visible
                    and way.destination
                    and way.destination.name not in visited
                    and way.obstruction_check(gs) == "Free"
                ):
                    queue.append((way.destination, path_so_far + [way]))
        return None