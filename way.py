from __future__ import annotations

from dataclasses import dataclass

# from GameState import GameState
from typing import Callable

from services.save_load import savable

#
# Edges within the Room-graph
#

@savable
@dataclass
class Way:
    name: str
    source: "Place"            # Edge(Way) originates here
    destination: "Place"              # Edge (Way) ends here
    text_direction: str     # textual short description North, West, South, .. up.. down ...
    visible: True           # Is the way visible after all? It can of course be visible but obstructed
    description: str = ""  # More concise description
    obstruction_check: Callable[['GameState'], str] = lambda state: "Free" # Checks if edge is obstructed by something
    way_prompt_f: Callable[['GameState','PlayerState','Way'], str] = lambda state: "** Wenn dieser Weg frei ist kann man ihn gehen, laufen , rennen, wandern **"

    # --- Storable (Save/Load) -------------------------------------------------------
    # Dynamisch ist nur ``visible`` (wird von Türen/Wagen/Plakat verändert). Struktur
    # (source/destination/text_direction) und Callables kommen beim Laden aus world.json.
    def store_id(self) -> str:
        return self.name

    def save(self) -> dict:
        return {"visible": self.visible}

    def load(self, data, ctx=None) -> None:
        self.visible = data["visible"]



