

from rich.console import Console
from rich.markdown import Markdown
from GameState import GameState


#
# Nächste Version des Adventures, 2025-05-21
#
#

DEBUG = False

def tw_print(x):
    console = Console()
    console.print(Markdown(x))

def dprint(x):
    if DEBUG:
        print(x)

#
# All kind of text definitions
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

    def gameloop(self):
        """
        1) Emit initial narrator sequence
        2) Loop until game end state reached
        3)    For all players p
        4)        Get user input (atomic actions to be executed by game logic)
        5)        if user input one of "inventory", "help", "save" execute and go to 4
        6)        execute user input, and if applicable, generate system response

        :return:
        """
        tw_print(txt_initial_text)


#
# --- Main ---
#

a = Adventure(["Chris"])
a.gameloop()