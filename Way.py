from __future__ import annotations

from dataclasses import dataclass

# from GameState import GameState
from typing import Callable

#
# Edges within the Room-graph
#

@dataclass(frozen=True)
class Way:
    name: str
    source: "Place"            # Edge(Way) originates here
    destination: "Place"              # Edge (Way) ends here
    text_direction: str     # textual short description North, West, South, .. up.. down ...
    obstruction_check: Callable[['GameState'], bool] = lambda state: False # Checks if edge is obstructed by something
    description: str = ""   # More concise description


