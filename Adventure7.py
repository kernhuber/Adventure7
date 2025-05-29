from collections import deque

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
    from collections import deque
    from typing import List, Deque, Any

    def __init__(self, players):
        self.game = GameState()
        #
        # Interactive Players
        #
        for i in players:
            self.game.add_player(i)
        #
        # Add o_umschlag to first player only
        #

        self.game.players[0].add_to_inventory(self.game.objects["o_umschlag"])
        #
        # Add our Non Player Character (the Dog)
        #
        self.game.add_player("Dog", npc=True)
        #
        # For testing
        #
        self.test_queue = deque([
            "gehe p_schuppen",
            "untersuche o_blumentopf",
            "anwenden o_schluessel o_schuppen",
            "gehe p_innen",
            "untersuche o_skelett",
            "untersuche o_geldboerse",
            "nimm o_ec_karte",
            "nimm o_leiter",
            "gehe p_schuppen",
            "anwenden o_leiter o_schuppen",
            "gehe p_dach",
            "anwenden o_hebel",
            "gehe p_schuppen",
            "anwenden o_ec_karte o_blumentopf",
            "gehe p_geldautomat",
            "anwenden o_ec_karte o_geldautomat",
            "gehe p_warenautomat",
            "gehe p_ubahn",
            "umsehen",
            "untersuche o_muelleimer",
            "untersuche o_geheimzahl",
            "nehme o_geheimzahl",
            "gehe p_warenautomat",
            "gehe p_geldautomat",
            "anwenden o_ec_karte o_geldautomat",
            "nimm o_geld_dollar",
            "gehe p_warenautomat",
            "anwenden o_geld_dollar o_warenautomat",
            "gehe p_schuppen",
            "gehe p_dach",
            "anwenden o_hebel",
            "gehe p_schuppen",
            "gehe p_warenautomat",
            "umsehen",
            "anwenden o_geld_dollar o_warenautomat",
            "untersuche o_warenautomat",
            "nichts"
        ])

    def test_game(self) -> str:
        if self.test_queue:
            c = self.test_queue.popleft()
            print (f'Player: {c}')
            return c
        exit(0)

    def gameloop(self):
        """
        1) Emit initial narrator sequence
        2) Loop until game end state reached
        3)    For all players p
        4)        Get user input (atomic actions to be executed by game logic)
        5)        if user input one of "inventory", "hilfe", "umsehen", "save", execute and go to 4
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
        from NPCPlayerState import NPCPlayerState
        round = 1
        while True:
            # print(f"{'='*20}  Spielrunde {round} {'='*20}")
            print((f" Spielrunde {round} ").center( 60, "-"))
            round = round + 1
            for pl in self.game.players:
                #
                # (3),(4),(5) - commands which  don't count as game moves
                #

                while True:

                    if (isinstance(pl,NPCPlayerState)):
                        #
                        # Non Player Character
                        #
                        print(f'{"-" * 60}')
                        user_input = pl.NPC_game_move(self.game)
                        tw_print(f"**{pl.name}**: {user_input}")
                    else:
                        user_input = ""
                        while user_input=="":
                            # user_input = Prompt.ask(f"Was tust du jetzt, {pl.name}? Deine Eingabe").strip().lower()
                            user_input = self.test_game()
                    tokens = user_input.split()

                    if tokens[0] == "hilfe":
                        tw_print("**hilfe ist noch nicht implementiert**")
                    elif tokens[0] == "inventory":
                        tw_print("**Du trägst bei dir:**")
                        for i in pl.get_inventory():
                            print(f'- "{i.name}" --> {i.examine}')
                    elif tokens[0] == "umsehen":
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

                    if tokens[0] == 'gehe' and len(tokens)>1:
                        r = self.game.verb_walk(pl,tokens[1])
                    elif tokens[0] == 'angreifen' and len(tokens) == 2:
                        tw_print(f'{pl.name} tötet {tokens[1]} nach heldischem Kampf. \n**Game Over!**')
                        exit(0)
                    elif tokens[0] == "untersuche" and len(tokens)>1:
                        r = self.game.verb_examine(pl, tokens[1])
                    elif tokens[0] == "nimm" and len(tokens) == 2:
                        r = self.game.verb_take(pl, tokens[1])
                    elif tokens[0] == "ablegen" and len(tokens) == 2:
                        r = self.game.verb_drop(pl, tokens[1])
                    elif tokens[0]  == "anwenden":
                        if len(tokens) == 2:
                            r = self.game.verb_apply(pl, tokens[1], None)
                        elif len(tokens) == 3:
                            r = self.game.verb_apply(pl,tokens[1], tokens[2])
                        else:
                            r = "**Ich verstehe nicht, was ich wie anwenden soll...**"
                    elif tokens[0] == "nichts":
                        r = ""
                    else:
                        r= "**Die Eingabe habe ich nicht verstanden.**"

                    if r != "":
                        tw_print(r)
#
# --- Main ---
#

a = Adventure(["Chris"])
a.gameloop()