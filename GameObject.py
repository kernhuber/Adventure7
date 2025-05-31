from __future__ import annotations
from typing import Callable, Union, Any, Optional


#
# Objects which can appear in the game. Special objects like doors etc are derived from this object
#
class GameObject:
    def __init__(self, name, examine, help_text="", fixed=False, hidden=False, apply_f=None, reveal_f=None):
        from PlayerState import PlayerState
        from GameState import GameState
        from Place import Place
        self.name = name
        self.examine = examine      # Text to me emitted when object is examined
        self.help_text = help_text  # Text to be emitted when player asks for help with object
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

        self.apply_f = apply_f # Optional[Callable[[PlayerState, GameObject, GameObject], str]] = None
        self.reveal_f = reveal_f
