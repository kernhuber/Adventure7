from collections import deque

from rich.console import Console
from rich.markdown import Markdown
from rich.prompt import Prompt
from GameState import GameState
from Utils import dprint, tw_print, DEBUG
import textwrap
import regex as re


#
# Nächste Version des Adventures, 2025-05-21
#
#

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

txt_final_text = """
# An einem weit entfernten Ort

Eine schwarz gekleidete Gestalt in einem Ledersessel stößt hauchend den beissenden 
Zigarrettenrauch aus. Dann drückt sie die Zigarrette im Aschenbecher aus und fragt:
"Ist der Bote gekommen?"
"Ich fürchte nein", antwortet eine andere Gestalt, die am Ende des Raums im Sessel
einer bequemen Sitzecke sitzt, und langsam an einem Glas mit goldenem Whiskey nippt.

"Das war zu befürchten!"
"Ja, und nun?"

Die erste Gestalt steht auf und verschränkt ihre Hände hinter dem Rücken. Nach kurzem
Üerlegen äußert sie: "Wie geplant. Es bleibt leider nichts anderes übrig."

Die zweite Gestalt nickt stumm. Dann gehen beide zu einem Schaltpult, welches in der
Ecke des Raumes steht. Sie stecken je einen Schlüssel in zwei Schlüssellöcher und 
betätigen einen Schalter in der Mitte des Pultes.

Dann geht die Welt unter. 
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
            "gehe Schuppen",
            "untersuche Blumentopf",
            "anwenden Schlüssel Schuppen",
            "gehe p_innen",
            "nimm sprengladung",
            "gehe schuppen",
            "gehe felsen",
            "anwenden sprengladung",
            "ablegen sprengladung",
            "gehe schuppen",
            "gehe innen",
            "nichts",
            "gehe schuppen",
            "gehe felsen",
            "gehe höhle",
            "anwenden breaker",
            "gehe felsen",
            "gehe p_schuppen",
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
            "nimm o_geheimzahl",
            "gehe p_warenautomat",
            "gehe p_geldautomat",
            "anwenden o_ec_karte o_geldautomat",
            "gehe p_warenautomat",
            "gehe p_ubahn",
            "gehe p_wagen",
            "umsehen",
            "nimm o_salami",
            "gehe p_ubahn",
            "gehe p_warenautomat",
            "gehe p_schuppen",
            "ablegen o_salami",
            "umsehen",
            "gehe p_innen",
            "nichts",
            "nichts",
            "gehe p_schuppen"
            "gehe p_geldautomat",
            "nimm o_geld_dollar",
            "gehe p_warenautomat",
            "anwenden o_geld_dollar o_warenautomat",
            "gehe p_schuppen",
            "nichts",
            "nichts",
            "nichts",
            "gehe p_dach",
            "anwenden o_hebel",
            "gehe p_schuppen",
            "gehe p_warenautomat",
            "umsehen",
            "anwenden o_geld_dollar o_warenautomat",
            "untersuche o_warenautomat",
            "nichts",
            "gehe schuppen",
            "gehe dach",
            "anwenden hebel",
            "gehe schuppen",
            "gehe warenautomat",
            "gehe u-bahn",
            "gehe wagen",
            "anwenden turschliesser",
            "gehe p_ubahn2",
            "umsehen",
            "anwenden o_geld_dollar o_pizzaautomat",
            "umsehen",
            "nimm pizza",
            "nimm lire",
            "gehe wagen",
            "anwenden tuerschliesser",
            "gehe ubahn",
            "gehe warenautomat",
            "anwenden lire warenautomat",
            "gehe schuppen",
            "gehe dach",
            "anwenden hebel",
            "gehe schuppen",
            "gehe warenautomat",
            "nichts"

        ])

    def test_game(self) -> str:
        if self.test_queue:
            c = self.test_queue.popleft()
            print (f'Player: {c}')
            return c
        else:
            return None

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
        from ExplosionState import ExplosionState

        round = 1
        auto_mode = True
        while not self.game.game_over:
            if not self.game.players:
                self.game.game_over = True
                tw_print("***Keine Spieler mehr übrig***")
                break
            dprint(f"#Players: {len(self.game.players)}")
            for i in self.game.players:
                dprint(f"* {i.name}")
            # print(f"{'='*20}  Spielrunde {round} {'='*20}")
            tw_print((f" Spielrunde {round} ").center( 60, "-"))
            round = round + 1
            if round == 200:
                tw_print(txt_final_text)
                exit(0)
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
                    elif (isinstance(pl, ExplosionState)):
                        tw_print(f'{"-" * 60}')
                        user_input = pl.explosion_input(self.game)
                    else:

                        print(f'Du bist hier: {pl.location.name}')
                        user_input = ""
                        while user_input=="":
                            if self.test_queue:
                                user_input = self.test_game().strip().lower()
                            else:
                                user_input = Prompt.ask(f"Was tust du jetzt, {pl.name}? Deine Eingabe").strip().lower()
                    if self.game.game_over:
                        tw_print("***Auf Wiedersehen!***")
                        exit(0)
                    tokens = user_input.split()

                    if tokens[0] == "hilfe":
                        r = self.game.verb_help(pl)
                        tw_print(r)
                    elif tokens[0] == "inventory":
                        tw_print("**Du trägst bei dir:**")
                        for i in pl.get_inventory():
                            tw_print(f'- "{i.name}" --> {i.examine}')
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
                        dprint(f" --> gehe {tokens[1]} --> {self.game.place_name_from_friendly_name(tokens[1])}")
                        r = self.game.verb_walk(pl,self.game.place_name_from_friendly_name(tokens[1]))
                    elif tokens[0] == 'angreifen' and len(tokens) == 2:
                        tw_print(f'{pl.name} tötet {tokens[1]} nach heldischem Kampf. \n**Game Over!**')
                        exit(0)
                    elif tokens[0] == "untersuche" and len(tokens)>1:
                        r = self.game.verb_examine(pl, self.game.obj_name_from_friendly_name(tokens[1]))
                    elif tokens[0] == "nimm" and len(tokens) == 2:
                        r = self.game.verb_take(pl, self.game.obj_name_from_friendly_name(tokens[1]))
                    elif tokens[0] == "ablegen" and len(tokens) == 2:
                        r = self.game.verb_drop(pl, self.game.obj_name_from_friendly_name(tokens[1]))
                    elif tokens[0]  == "anwenden":
                        if len(tokens) == 2:
                            r = self.game.verb_apply(pl, self.game.obj_name_from_friendly_name(tokens[1]), None)
                            # r = self.game.verb_apply(pl,tokens[1], None)
                        elif len(tokens) == 3:
                            r = self.game.verb_apply(pl, self.game.obj_name_from_friendly_name(tokens[1]),
                                                     self.game.obj_name_from_friendly_name(tokens[2]))
                        else:
                            r = "**Ich verstehe nicht, was ich wie anwenden soll...**"
                    elif tokens[0] == "nichts":
                        r = ""
                    else:
                        r= "**Die Eingabe habe ich nicht verstanden.**"

                    if r != "":
                        tw_print(r)
                if self.game.game_over:
                    break


        tw_print("***Auf Wiedersehen!***")
#
# --- Main ---
#

a = Adventure(["Chris"])
a.gameloop()