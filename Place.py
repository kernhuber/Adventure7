from __future__ import annotations
from dataclasses import dataclass, field
from typing import List
from GameObject import GameObject
from Way import Way


@dataclass
class Place:
    name: str
    description: str
    place_prompt: str
    ways: List[Way] = field(default_factory=list)
    place_objects: List[GameObject] = field(default_factory=list)
    callnames: List[str] = field(default_factory=list)


    def get_objects(self):
            return self.place_objects

    def add_object(self,item):
        if item not in self.place_objects:
            self.place_objects.append(item)

    def rem_object(self,item):
        if item in self.place_objects:
            self.place_objects.remove(item)

    def __contains__(self, item: GameObject) -> bool:
        return item in self.place_objects