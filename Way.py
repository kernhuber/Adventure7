from __future__ import annotations

from dataclasses import dataclass

# from GameState import GameState
from typing import Callable

#
# Edges within the Room-graph
#

@dataclass
class Way:
    name: str
    source: "Place"            # Edge(Way) originates here
    destination: "Place"              # Edge (Way) ends here
    text_direction: str     # textual short description North, West, South, .. up.. down ...
    visible: True           # Is the way visible after all? It can of course be visible but obstructed
    obstruction_check: Callable[['GameState'], str] = lambda state: "Free" # Checks if edge is obstructed by something
    description: str = ""   # More concise description


