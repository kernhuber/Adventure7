from collections import deque
from rich.prompt import Prompt
from GameState import GameState
from Utils import dprint, dpprint, tw_print, DEBUG
from pprint import pprint

#
# Nächste Version des Adventures, 2025-05-21
#
#

#
# All kind of text definitions. Texts are in MD-Format
#

txt_initial_text = """
# Willkommen in der Wüste

**Eine komische Situation:** Du radelst mit Deinem Fahrrad als Bote
unter sengender Sonne entlang einer schnurgraden Strasse durch eine
endlose Wüste. Bei Dir hast Du einen Umschlag, den Du an ein Ziel 
bringen musst. Erreicht der Umschlag das Ziel nicht, so geht die Welt 
unter, aber das ist eine andere Geschichte.

Plötzlich reisst Dir die Fahrradkette - das Fahrrad funktioniert ohne
sie nicht mehr. Glücklicherweise bist Du an einem Ort gestrandet, an
dem es Rettung geben könnte. 

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
Überlegen äußert sie: "Wie geplant. Es bleibt leider nichts anderes übrig."

Die zweite Gestalt nickt stumm. Dann gehen beide zu einem Schaltpult, welches in der
Ecke des Raumes steht. Sie stecken je einen Schlüssel in zwei Schlüssellöcher und 
betätigen einen Schalter in der Mitte des Pultes.

Dann geht die Welt unter. 
"""




class Adventure:


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




    def gameloop(self):
        """


        :return:
        """

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
            self.game.gamelog.append({"Game_Round":f"{round}"})
            dprint(f"#Players: {len(self.game.players)}")
            for i in self.game.players:
                dprint(f"* {i.name}")

            tw_print((f" Spielrunde {round} ").center( 60, "-"))
            round = round + 1
            if round == 200:
                tw_print(txt_final_text)
                self.game.game_over = True
            for pl in self.game.players:




                if (type(pl) is NPCPlayerState):
                    #
                    # Non Player Character
                    #
                    print(f'{"-" * 60}')
                    user_input = pl.NPC_game_move(self.game)
                    dprint(f"**{pl.name}**: {user_input}")
                elif (type(pl) is ExplosionState):
                    tw_print(f'{"-" * 60}')
                    user_input = pl.explosion_input(self.game)
                else:
                    user_input = pl.Player_game_move()



                tw_print(self.game.verb_execute(pl,user_input))



        dprint(f"Total tokens used in this game session: {self.game.llm.tokens}")
        dprint(f"Number of API-Calls: {self.game.llm.numcalls}")
        dpprint(self.game.llm.token_details)
        dprint(f"{'*'*80}")
        pprint(self.game.gamelog)
        tw_print("***Auf Wiedersehen!***")
#
# --- Main ---
#

a = Adventure(["Chris"])
a.gameloop()