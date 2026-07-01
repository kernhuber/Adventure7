"""Save / Load foundation — registry, decorator, and the load context.

Step 1 of the plan in ``docs/SAVE-LOAD-DESIGN.md``. This module has **no dependency on
the game classes** (only the stdlib), so any model class can import ``savable`` without
a circular import. The actual saver/loader functions come in a later step and will live
here too.

Two things happen via the ``@savable`` decorator:
  1. the class is put into ``TYPE_REGISTRY`` (name -> class) so the loader can rebuild
     instances from the ``type`` string in a save envelope;
  2. every instance registers itself in a live "to be saved" set on construction, so the
     saver finds it without a hand-maintained registry (constructors stay untouched).

Note on the "to be saved" set: the game's model classes are ``@dataclass`` with value
equality, i.e. **unhashable**, so a plain ``WeakSet`` can't hold them. We use a
``WeakValueDictionary`` keyed by a per-instance token instead — same effect (GC'd
instances drop out automatically), but it does not require hashable values.
"""
from __future__ import annotations

import functools
import itertools
import json
import weakref
from typing import Any, Iterable


# name (STORE_TYPE) -> class. Populated at import time by @savable.
TYPE_REGISTRY: dict[str, type] = {}

# token(int) -> live savable instance. Values are weakly held, so instances that are no
# longer referenced anywhere (removed objects, an old GameState) drop out on GC.
_instances: "weakref.WeakValueDictionary[int, Any]" = weakref.WeakValueDictionary()
_token = itertools.count()


def savable(cls: type) -> type:
    """Class decorator: register the class for loading and auto-register its instances.

    Apply *below* ``@dataclass`` so it wraps the generated ``__init__``::

        @savable
        @dataclass
        class NPCZombieState(PlayerState):
            ...
    """
    TYPE_REGISTRY[cls.__name__] = cls
    cls.STORE_TYPE = cls.__name__  # type: ignore[attr-defined]

    orig_init = cls.__init__

    @functools.wraps(orig_init)
    def __init__(self, *args, **kwargs):
        orig_init(self, *args, **kwargs)
        _instances[next(_token)] = self

    cls.__init__ = __init__  # type: ignore[method-assign]
    return cls


def class_for(store_type: str) -> type | None:
    """Look up the class for a save envelope's ``type`` string (None if unknown)."""
    return TYPE_REGISTRY.get(store_type)


def registered_instances() -> list[Any]:
    """Snapshot of all currently-live savable instances (GC'd ones already dropped).

    De-duplicated by identity. The saver additionally filters these against the live
    ``GameState`` graph (only objects still reachable are actually written), so a stray
    instance from a previous game can never leak into a save.
    """
    seen: dict[int, Any] = {}
    for obj in list(_instances.values()):
        seen[id(obj)] = obj
    return list(seen.values())


class LoadContext:
    """Carries the ``id -> instance`` map across the two load phases.

    Phase 1 (instantiate) calls :meth:`register` for every object; phase 2
    (``obj.load(data, ctx)``) resolves references (``location``, ``ownedby``,
    ``inventory``, way ``source``/``destination``, dog ``way_home`` ...) via the
    lookups below. IDs are globally unique (``p_*`` / ``o_*`` / ``w_*`` / player names /
    ``"gamestate"`` / ``"llm"``), so a single map suffices; the typed accessors are just
    readable sugar over the same lookup.
    """

    def __init__(self) -> None:
        self._by_id: dict[str, Any] = {}

    def register(self, obj_id: str, obj: Any) -> None:
        self._by_id[obj_id] = obj

    def by_id(self, obj_id: str | None) -> Any:
        if obj_id is None:
            return None
        return self._by_id.get(obj_id)

    # readable, typed sugar (same resolution) --------------------------------------
    def place(self, place_id: str | None) -> Any:
        return self.by_id(place_id)

    def obj(self, object_id: str | None) -> Any:
        return self.by_id(object_id)

    def player(self, player_id: str | None) -> Any:
        return self.by_id(player_id)

    def way(self, way_id: str | None) -> Any:
        return self.by_id(way_id)

    def resolve_all(self, ids: Iterable[str]) -> list[Any]:
        """Resolve a list of ids to instances (unknown ids are skipped)."""
        return [self._by_id[i] for i in ids if i in self._by_id]


# --- Orchestration: whole-game save / load ------------------------------------------
SAVE_VERSION = 1


def _is_savable(obj: Any) -> bool:
    return all(hasattr(obj, a) for a in ("STORE_TYPE", "store_id", "save", "load"))


def save_game(gs: Any) -> dict:
    """Collect the full game into a version'd blob of self-describing envelopes.

    Walks the live GameState graph (ways/objects/players) plus the GameState root and the
    LLM — the live graph is the authoritative "what exists now". Returns a JSON-able dict;
    file I/O is the caller's concern.
    """
    envelopes: list[dict] = []

    def emit(obj: Any) -> None:
        if _is_savable(obj):
            envelopes.append({"type": obj.STORE_TYPE, "id": obj.store_id(), "data": obj.save()})

    emit(gs)                                   # GameState root (type "GameState")
    emit(getattr(gs, "llm", None))             # LLM caches (if it implements Storable)
    for w in gs.ways.values():
        emit(w)
    for o in gs.objects.values():
        emit(o)
    for p in gs.players:                       # non-savable players (e.g. an active explosion) are skipped
        emit(p)

    return {"version": SAVE_VERSION, "envelopes": envelopes}


def load_game(blob: dict, *, llm: Any = None) -> Any:
    """Rebuild a GameState from a save blob and return it (caller swaps session['game']).

    Two phases: (1) build the base world via WorldLoader and instantiate the saved players;
    (2) call load() everywhere so each object restores its values and resolves its refs via
    the LoadContext. GameState is loaded LAST (rebuilds place_objects from ownedby). ``llm``
    is the live LLM instance to reuse (its client stays live); pass None only in the fallback
    where GameState builds its own.
    """
    from game_state import GameState
    from player_state import PlayerState

    if blob.get("version") != SAVE_VERSION:
        raise ValueError(f"Unsupported save version: {blob.get('version')!r}")
    envelopes = blob["envelopes"]

    # Base world (callables + static structure + fresh flags; players == []).
    gs = GameState(llm=llm)
    ctx = LoadContext()
    for p in gs.places.values():
        ctx.register(p.name, p)
    for w in gs.ways.values():
        ctx.register(w.store_id(), w)
    for o in gs.objects.values():
        ctx.register(o.store_id(), o)

    # Phase 1: instantiate the saved players (the base has none) and register them. They are
    # created via the normal constructor (name + resolved location) so @savable registers
    # them; the rest is overlaid in phase 2.
    gs_env = None
    for e in envelopes:
        t = e["type"]
        if t == "GameState":
            gs_env = e
            continue
        cls = class_for(t)
        if cls is not None and issubclass(cls, PlayerState):
            loc = ctx.place(e["data"].get("location"))
            inst = cls(name=e["id"], location=loc)
            ctx.register(e["id"], inst)

    # Phase 2: load everything except the GameState root; the LLM (live singleton) gets its
    # caches restored in place.
    for e in envelopes:
        t, eid = e["type"], e["id"]
        if t == "GameState":
            continue
        if t == "GeminiInterface":
            if hasattr(gs.llm, "load"):
                gs.llm.load(e["data"], ctx)
            continue
        target = ctx.by_id(eid)
        if target is not None and hasattr(target, "load"):
            target.load(e["data"], ctx)

    # GameState last: flags, drop destroyed objects, player order, rebuild place_objects.
    if gs_env is not None:
        gs.load(gs_env["data"], ctx)

    return gs


def save_to_file(gs: Any, path: str) -> None:
    """Write a full game save to ``path`` as JSON."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(save_game(gs), f, ensure_ascii=False, indent=2)


def load_from_file(path: str, *, llm: Any = None) -> Any:
    """Read a game save from ``path`` and rebuild the GameState (caller swaps the ref)."""
    with open(path, encoding="utf-8") as f:
        return load_game(json.load(f), llm=llm)
