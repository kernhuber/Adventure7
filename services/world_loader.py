"""World construction for the game.

WorldLoader loads the external world definition (data/world.json), resolves dotted
callback references (e.g. "GameApplyFunctions.o_xxx") to callables, validates the
definitions, and builds Place / Way / GameObject instances into a WorldModel.

Extracted from GameState (Step 2.1 refactor). Pure construction: it touches no LLM
and no runtime game state, so it can be imported and unit-tested standalone.
"""
import json
import os
from typing import Dict

from place import Place
from way import Way
from game_object import GameObject
from utils import dprint, dl


class WorldLoader:
    def resolve_func_from_string(self, ref, module_map):
        """
        Resolve dotted function references coming from JSON, e.g.
        "GameApplyFunctions.o_warenautomat_apply_f" into a callable.

        Accepted formats:
          - None or "" -> returns None
          - already-callable -> returns as-is
          - "Module.func" where Module is one of: GameApplyFunctions, GameTakeFunctions,
            GameRevealFunctions, GameObstructionCheckFunctions, PlacePrompts, ObjectPrompts, WayPrompts
        """
        if not ref:
            return None
        if callable(ref):
            return ref
        if isinstance(ref, str):
            # Allow "Module.func" or "Module:func"
            ref = ref.replace(":", ".")
            if "." not in ref:
                return None
            mod_name, func_name = ref.split(".", 1)
            mod = module_map.get(mod_name)
            if not mod:
                return None
            return getattr(mod, func_name, None)
        return None

    def load(self, module_map):
        """
        Optional external world loader.
        Looks for ./data/world.json (relative to project root).
        Expected JSON structure:
        {
          "place_defs": {...},
          "way_defs": {...},
          "object_defs": {...}
        }
        Any callback fields (apply_f, reveal_f, take_f, prompt_f, place_prompt_f,
        way_prompt_f, obstruction_check) may be strings like "GameApplyFunctions.o_xxx"
        and are resolved to callables.
        Returns (place_defs, way_defs, object_defs) or None if file not present/invalid.
        """
        from utils import GHOSTMODE
        # Compute candidate paths
        candidates = [
            os.path.join("data", "world.json"),
            os.path.join(os.path.dirname(__file__), "data", "world.json"),
        ]
        path = next((p for p in candidates if os.path.exists(p)), None)
        if not path:
            return None

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            dprint(dl.GAMESTATE, f"[world.json] Fehler beim Laden: {e}")
            return None

        place_defs = data.get("place_defs") or {}
        way_defs = data.get("way_defs") or {}
        object_defs = data.get("object_defs") or {}

        # Normalize/resolve callbacks in places
        for _pname, pval in place_defs.items():
            if isinstance(pval, dict):
                if "place_prompt_f" in pval:
                    pval["place_prompt_f"] = self.resolve_func_from_string(pval.get("place_prompt_f"), module_map)

        # Normalize/resolve callbacks in ways, honor GHOSTMODE
        for _wname, wval in way_defs.items():
            if isinstance(wval, dict):
                if "obstruction_check" in wval:
                    wval["obstruction_check"] = self.resolve_func_from_string(wval.get("obstruction_check"), module_map)
                if "way_prompt_f" in wval:
                    wval["way_prompt_f"] = self.resolve_func_from_string(wval.get("way_prompt_f"), module_map)
                if GHOSTMODE:
                    wval["visible"] = True
                    wval["obstruction_check"] = None

        # Normalize/resolve callbacks in objects
        for _oname, oval in object_defs.items():
            if isinstance(oval, dict):
                for key in ("apply_f", "reveal_f", "take_f", "prompt_f"):
                    if key in oval:
                        oval[key] = self.resolve_func_from_string(oval.get(key), module_map)

        return place_defs, way_defs, object_defs

    def validate(self, place_defs, way_defs, object_defs):
        """
        Lightweight validator for loaded world definitions.
        - Checks required fields and simple referential integrity.
        - Warns (does not raise) on problems.
        Call this right after loading JSON and before from_definitions().
        """
        def warn(msg):
            dprint(dl.GAMESTATE, f"[world.json][WARN] {msg}")

        # --- Places ---
        required_place_fields = ("description", "ways", "objects")
        for pname, p in (place_defs or {}).items():
            if not isinstance(p, dict):
                warn(f"Place '{pname}' is not a dict")
                continue
            for f in required_place_fields:
                if f not in p:
                    warn(f"Place '{pname}' missing field '{f}'")
            # Callback type checks
            if "place_prompt_f" in p and p.get("place_prompt_f") not in (None,):
                if not callable(p.get("place_prompt_f")):
                    warn(f"Place '{pname}': place_prompt_f not resolved to callable")
            # Ways / objects should be lists
            if "ways" in p and not isinstance(p.get("ways"), list):
                warn(f"Place '{pname}': 'ways' should be a list of way names")
            if "objects" in p and not isinstance(p.get("objects"), list):
                warn(f"Place '{pname}': 'objects' should be a list of object names")

        # Cross-reference checks for place -> ways / objects
        way_keys = set((way_defs or {}).keys())
        obj_keys = set((object_defs or {}).keys())
        for pname, p in (place_defs or {}).items():
            if not isinstance(p, dict):
                continue
            # Validate referenced ways exist
            if isinstance(p.get("ways"), list):
                for wref in p.get("ways", []):
                    if wref not in way_keys:
                        warn(f"Place '{pname}': unknown way reference '{wref}'")
            # Validate referenced objects exist
            if isinstance(p.get("objects"), list):
                for oref in p.get("objects", []):
                    if oref not in obj_keys:
                        warn(f"Place '{pname}': unknown object reference '{oref}'")

        # --- Ways ---
        required_way_fields = ("source", "destination", "text_direction", "description")
        for wname, w in (way_defs or {}).items():
            if not isinstance(w, dict):
                warn(f"Way '{wname}' is not a dict")
                continue
            for f in required_way_fields:
                if f not in w:
                    warn(f"Way '{wname}' missing field '{f}'")
            src = w.get("source")
            dst = w.get("destination")
            if src and src not in place_defs:
                warn(f"Way '{wname}': unknown source place '{src}'")
            if dst and dst not in place_defs:
                warn(f"Way '{wname}': unknown destination place '{dst}'")
            # Callback checks
            if "obstruction_check" in w and w.get("obstruction_check") not in (None,):
                if not callable(w.get("obstruction_check")):
                    warn(f"Way '{wname}': obstruction_check not resolved to callable")
            if "way_prompt_f" in w and w.get("way_prompt_f") not in (None,):
                if not callable(w.get("way_prompt_f")):
                    warn(f"Way '{wname}': way_prompt_f not resolved to callable")

        # --- Objects ---
        required_object_fields = ("name", "ownedby", "examine", "prompt_f")
        for oname, o in (object_defs or {}).items():
            if not isinstance(o, dict):
                warn(f"Object '{oname}' is not a dict")
                continue
            for f in required_object_fields:
                if f not in o:
                    warn(f"Object '{oname}' missing field '{f}'")
            # Name consistency
            if o.get("name") and o.get("name") != oname:
                warn(f"Object key '{oname}' != object.name '{o.get('name')}'")
            # Place reference
            ob = o.get("ownedby")
            if ob and ob not in place_defs:
                warn(f"Object '{oname}': unknown ownedby place '{ob}'")

            # Callback checks
            for cb in ("apply_f", "reveal_f", "take_f", "prompt_f"):
                if cb in o and o.get(cb) not in (None,):
                    if not callable(o.get(cb)):
                        warn(f"Object '{oname}': {cb} not resolved to callable")
            # callnames type
            if "callnames" in o and o.get("callnames") not in (None,):
                cn = o.get("callnames")
                if not isinstance(cn, list) or not all(isinstance(s, str) for s in cn):
                    warn(f"Object '{oname}': callnames should be list[str]")

    def _init_places(self, defs) -> Dict[str, Place]:
        places = {}

        for place_name, place_data in defs.items():
            place = Place(
                name=place_name,
                description=place_data["description"],
                place_prompt=place_data["place_prompt"],
                place_prompt_f=place_data.get("place_prompt_f",None),
                callnames = place_data.get("callnames",None),
                ways=[],  # Wird später in _init_ways gefüllt
                place_objects=[]  # Wird später in _init_objects gefüllt
            )
            place.callnames = [s.lower() for s in (place.callnames or [])] or [place_name.lower()]
            places[place_name] = place

        return places

    def _init_ways(self, defs: dict, places: Dict[str, Place]) -> Dict[str, Way]:
        ways = {}

        for way_name, way_data in defs.items():
            source_name = way_data["source"]
            dest_name = way_data["destination"]
            v = way_data.get("visible")
            if v is None:
                visible = True
            else:
                visible = v



            source_place = places[source_name]
            dest_place = places[dest_name] if dest_name else None

            obstruction_f = way_data.get("obstruction_check", None)
            if obstruction_f is None:
                obstruction_f = lambda state: "Free"  # Default-Funktion

            way_prompt_f = way_data.get("way_prompt_f", None)

            way = Way(
                name=way_name,
                source=source_place,
                destination=dest_place,
                text_direction=way_data["text_direction"],
                obstruction_check=obstruction_f,
                way_prompt_f = way_prompt_f,
                visible = visible,
                description=way_data["description"]
            )

            # Im source-Place registrieren
            source_place.ways.append(way)

            ways[way_name] = way

        return ways

    def _init_objects(self, defs: dict, places: Dict[str, Place]) -> Dict[str, GameObject]:
        objects = {}
        from game_object import GameObject
        for obj_name, obj_data in defs.items():

            obj = GameObject(
                name=obj_data["name"],
                examine=obj_data["examine"],
                help_text=obj_data.get("help_text", ""),
                fixed=obj_data.get("fixed", False),
                hidden=obj_data.get("hidden", False),
                callnames   = obj_data.get("callnames", None),
                apply_f     = obj_data.get("apply_f", None),
                reveal_f    = obj_data.get("reveal_f", None),
                take_f      = obj_data.get("take_f", None),
                prompt_f    = obj_data.get("prompt_f", None)
            )
            obj.callnames = [s.lower() for s in (obj.callnames or [])] or [obj.name.lower()]
            fn = obj_data.get("apply_f", None)
            obj.apply_f = fn
            ownedby_str = obj_data.get("ownedby", None)
            if ownedby_str in places:
                obj.ownedby = places[ownedby_str]
            else:
                obj.ownedby = None
            # obj.ownedby = obj_data.get("ownedby", None)

            # Füge das Objekt dem passenden Place hinzu
            for place in places.values():
                if ownedby_str == place.name:
                    place.place_objects.append(obj)
                    break

            objects[obj_data["name"]] = obj

        return objects

    def build(self, world, place_defs, way_defs, object_defs):
        """Populate a WorldModel's places/ways/objects from validated defs."""
        world.places = self._init_places(place_defs)
        world.ways = self._init_ways(way_defs, world.places)
        world.objects = self._init_objects(object_defs, world.places)
