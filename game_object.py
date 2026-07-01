from __future__ import annotations
from typing import Callable, Union, Any, Optional

from services.save_load import savable


#
# Objects which can appear in the game. Special objects like doors etc are derived from this object
#

@savable
class GameObject:
    def __init__(self, name, examine, help_text="", fixed=False, hidden=False, callnames=None, apply_f=None, reveal_f=None, take_f=None, prompt_f=None):
        from player_state import PlayerState
        from game_state import GameState
        from place import Place
        self.name = name
        self.examine = examine      # Text to me emitted when object is examined
        self.help_text = help_text  # Text to be emitted when player asks for help with object
        self.callnames = callnames  # Array with strings the object can be referred to with
        self.ownedby = PlayerState | Place | None         # Which Player or place currently owns this item? Default: None
        self.fixed = fixed          # False bedeutet: Kann aufgenommen werden
        self.hidden = hidden        # True bedeutet: Das Objekt ist nicht sichtbar
        #
        # Apply:
        #
        # Apply myself (for example: "Pull lever" --> apply()
        # myself: lever
        #
        # Apply myself to obj2 (for example "open door with key" --> apply (door)
        # myself: key
        # obj2: door
        #
        #
        # ------- Usage: ------
        # def schluessel_apply(target, player, game) -> str:
        #     if isinstance(target, GameObject) and target.name == "Tuer_Norden":
        #         return "Du schließt die Tür auf – sie ist jetzt offen!"
        #     return "Das funktioniert so nicht."
        #
        # obj = GameObject("schluessel", "Ein rostiger Schlüssel")
        # obj.apply_f = schluessel_apply
        #
        # ... then later ...
        #
        # if obj_a.apply_f:
        #     result = obj_a.apply_f(obj_b, player, game)
        # else:
        #     result = "Du kannst das nicht auf diese Weise anwenden."

        self.apply_f = apply_f      # Optional[Callable[[PlayerState, GameObject, GameObject], str]] = None
        self.reveal_f = reveal_f    # Optional: Funktion, die aufgerufen wird, wenn Objekt untersucht wird
        self.take_f = take_f        # Optional: Funktion, die aufgerufen wird, wenn Objekt genommen wird
        self.prompt_f = prompt_f

    # --- Storable (Save/Load) -----------------------------------------------------------
    # Gespeichert wird der zur Laufzeit veränderliche Zustand + Identität; die Callables
    # (apply_f/…) und statischen Texte (callnames/help_text) kommen beim Laden aus world.json.
    # ``examine`` MUSS mit (kann sich ändern, z.B. o_umschlag nach Tinktur). ``ownedby``
    # (Place/Player/None) wird als ID gespeichert und über den LoadContext aufgelöst.
    def store_id(self) -> str:
        return self.name

    def save(self) -> dict:
        return {
            "examine": self.examine,
            "hidden": self.hidden,
            "fixed": self.fixed,
            "ownedby": getattr(self.ownedby, "name", None),
        }

    def load(self, data, ctx) -> None:
        self.examine = data.get("examine", self.examine)
        self.hidden = data.get("hidden", self.hidden)
        self.fixed = data.get("fixed", self.fixed)
        self.ownedby = ctx.by_id(data.get("ownedby"))

