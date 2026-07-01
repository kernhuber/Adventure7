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
