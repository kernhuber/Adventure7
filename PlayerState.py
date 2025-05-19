from dataclasses import dataclass, field
from typing import List


#
# The state of a player. Multiple players - multiple states
#
@dataclass
class PlayerState:
    location: "Room"
    inventory: List[str] = field(default_factory=list)
    last_input: str = "Ich sehe mich erst einmal um."

    def add_to_inventory(self, a: str):
        if a not in self.inventory:
            self.inventory.append(a)

    def remove_from_inventory(self, a: str):
        if a in self.inventory:
            self.inventory.remove(a)

    def is_in_inventory(self, s: str) -> bool:
        return s in self.inventory


    def get_inventory(state):
        return state.get("inventory", [])






