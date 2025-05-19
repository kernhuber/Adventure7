from __future__ import annotations
from typing import Callable, Union, Any, Optional


#
# Objects which can appear in the game. Special objects like doors etc are derived from this object
#
class GameObject:
    def __init__(self, name, examine, help_text="", fixed=False, hidden=False):
        self.name = name
        self.examine = examine      # Text to me emitted when object is examined
        self.help_text = help_text  # Text to be emitted when player asks for help with object
        self.ownedby = None         # Which Player currently owns this item? Default: None
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
        # Apply something to myself (for example: "enter 8513 into number pad --> "apply ("8513")
        # myself: number pad
        #
        # --> consistency check, execute appropriate action on game_state
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
        from PlayerState import PlayerState
        from GameState import GameState
        self.apply_f: Optional[Callable[[Any, PlayerState, GameState], str]] = None
