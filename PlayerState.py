from dataclasses import dataclass, field
from typing import List
from Place import Place
from collections import deque
from SysTest import SysTest
from Utils import dpprint, dprint


#from GameState import GameState
#
# The state of a player. Multiple players - multiple states
#
@dataclass
class PlayerState:
    from GameObject import GameObject
    name: str
    location: Place
    inventory: List[GameObject] = field(default_factory=list)
    last_input: str = "Ich sehe mich erst einmal um."
    thirst_counter: int = 40  # Alle vierzig Spielzüge müssen wir trinken
    cmd_q: deque = field(default_factory = deque)
    systest: SysTest = field(default_factory = SysTest)




    def add_to_inventory(self, a: GameObject):
        if a not in self.inventory:
            self.inventory.append(a)
            a.ownedby = self
            if a in self.location.place_objects:
                self.location.place_objects.remove(a)

    def remove_from_inventory(self, a: GameObject):
        if a in self.inventory:
            self.inventory.remove(a)

    def is_in_inventory(self, s: GameObject) -> bool:

        r = (s in self.inventory)
        return r


    def get_inventory(self):
        return self.inventory


    def Player_game_move(self, gs:"GameState"):
        """
        This function returns user input to the game engine. Two additional features:
        * if there are commands in the systest queue, return these instead of actual user input
        * Commands entered by user are appended to cmd_q, the command queue, and only in a
          subsequent step returned to the game engine. The reason is, that when using an
          LLM to parse user input, multiple commands may be entered into the queue in one
          step
        :return: Command to be executed by game Engine
        """
        from rich.prompt import Prompt
        from Utils import tw_print
        print(f'{self.name} ist nun hier (Ortsname): {self.location.callnames[0]} ')
        self.thirst_counter -= 1
        if self.thirst_counter == 0:
            gs.game_over = True
            tw_print("***Leider bist du verdurstet!***")
            return "nichts"
        if self.thirst_counter == 20:
            tw_print("***Du hast Gottseidank noch keinen Durst***")
        elif self.thirst_counter == 10:
            tw_print("***So langsam bekommst Du Durst. Du solltest etwas zu Trinken suchen!***")
        elif self.thirst_counter <=5:
            tw_print(f"***Du hast jetzt richtig Durst! Es reicht nocht für {self.thirst_counter} Spielrunden, dann verdurstest Du!***")

        user_input = ""
        while user_input == "":
            if self.systest.test_queue:
                user_input = self.systest.test_game().strip().lower()
            elif self.cmd_q:
                user_input = self.cmd_q.popleft()
            else:
                ui = Prompt.ask(f"Was tust du jetzt, {self.name}? Deine Eingabe")
                if ui is not None:
                    if ui == "quit" or ui=="inventory" or ui =="dogstate" or ui=="nichts":
                        self.cmd_q.append(ui.strip().lower())
                    else:
                        cmds = gs.llm.parse_user_input_to_commands(ui,gs.compile_current_game_context(self))
                        dprint(f"LLM made the following atomic commands from user input:")
                        dpprint(cmds)
                        self.cmd_q.extend(cmds)
                else:
                    user_input = ""


        return user_input


