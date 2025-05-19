from GameObject import GameObject

#
# Handling doors in the game. Note door != way. A door can obstruct something including, but not limited to ways
#
class Door(GameObject):
    def __init__(self, name, examine, direction, target_room, locked=True, help_text="Eine massive Tür."):
        super().__init__(name, examine, help_text, fixed=True)
        self.locked = locked
        self.direction = direction
        self.target_room = target_room
