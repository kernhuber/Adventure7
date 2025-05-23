

from rich.console import Console
from rich.markdown import Markdown
from rich.prompt import Prompt
from GameState import GameState
import textwrap
import regex as re


#
# Nächste Version des Adventures, 2025-05-21
#
#

DEBUG = False
console = Console()

def tw_print(x):
    #print(x)
    console.print(Markdown(x))

def dprint(x):
    if DEBUG:
        print(x)

#
# All kind of text definitions. Texts are in MD-Format
#

txt_initial_text = """
# Willkommen in der Wüste

**Eine alltägliche Situation:** Du radelst mit Deinem Fahrrad als Bote
unter sengender Sonne entlang einer schnurgraden Strasse durch eine
ewige Wüste. Bei Dir hast Du einen Umschlag, den Du ans Ziel bringen
musst. Erreicht der Umschlag das Ziel nicht, so geht die Welt unter,
aber das ist eine andere Geschichte.

Plötzlich reisst Dir die Fahrradkette - das Fahrrad funktioniert ohne
sie nicht mehr. Glücklicherweise bist Du an einem Ort gestrandet, an
dem die Rettung nicht fern scheint. 

**Und nun?**
"""

class Adventure:
    def __init__(self, players):
        self.game = GameState()
        for i in players:
            self.game.add_player(i)
        #
        # Add o_umschlag to first player only
        #

        self.game.players[0].add_to_inventory(self.game.objects["o_umschlag"])

    def gameloop(self):
        """
        1) Emit initial narrator sequence
        2) Loop until game end state reached
        3)    For all players p
        4)        Get user input (atomic actions to be executed by game logic)
        5)        if user input one of "inventory", "hilfe", "umsehen", "save", "untersuche" execute and go to 4
        6)        execute user input,
        7 )       if applicable, generate system response

        :return:
        """
        import PlayerState
        #
        # (1)
        #
        tw_print(txt_initial_text)
        #
        # (2)
        #
        user_input="none"
        while True:
            for pl in self.game.players:

                while True:
                    # user_input = input("Was tust du jetzt? Deine Eingabe: ").strip().lower()
                    user_input = Prompt.ask("Was tust du jetzt? Deine Eingabe: ").strip().lower()
                    if user_input == "hilfe":
                        tw_print("**hilfe ist noch nicht implementiert**")
                    elif user_input == "inventory":
                        tw_print("**Du trägst bei dir:**")
                        for i in pl.get_inventory():
                            print(f'- "{i.name}" --> {i.examine}')
                    elif user_input == "umsehen":
                        r = self.game.verb_lookaround(pl)
                        tw_print(r)
                    else:
                        break
                #
                # user_input is now different from "help" or "inventory"
                #
                # (6)
                # execute user_input
                if user_input == "quit":
                    exit(0)
                else:
                    tokens = user_input.split()
                    if tokens[0] == 'gehe' and len(tokens)>1:
                        r = self.game.verb_walk(pl,tokens[1])
                    elif tokens[0] == "untersuche" and len(tokens)>1:
                        r = self.game.verb_examine(pl, tokens[1])
                    elif tokens[0]  == "anwenden":
                        if len(tokens) == 2:
                            r = self.game.verb_apply(pl, tokens[1], None)
                        elif len(tokens) == 3:
                            r = self.game.verb_apply(pl,tokens[1], tokens[2])
                        else:
                            r = "**Ich verstehe nicht, was ich wie anwenden soll...**"
                    else:
                        r= "**Die Eingabe habe ich nicht verstanden.**"

                    tw_print(r)
#
# --- Main ---
#

a = Adventure(["Chris"])
a.gameloop()