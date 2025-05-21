from dataclasses import dataclass, field
from typing import List
from Place import Place

#
# The state of a player. Multiple players - multiple states
#
@dataclass
class PlayerState:
    import GameState
    name: str
    location: Place
    inventory: List[str] = field(default_factory=list)
    last_input: str = "Ich sehe mich erst einmal um."

    def add_to_inventory(self, a: str):
        if a not in self.inventory:
            self.inventory.append(a)
            a.owner = self
            if a in self.location.place_objects:
                self.location.place_objects.remove(a)

    def remove_from_inventory(self, a: str):
        if a in self.inventory:
            self.inventory.remove(a)

    def is_in_inventory(self, s: str) -> bool:
        return s in self.inventory


    def get_inventory(self):
        return self.inventory






