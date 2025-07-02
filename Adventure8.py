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

Tipp: sieh dich um oder ersuche um Hilfe!
"""

txt_final_text = """
# An einem weit entfernten Ort

Eine schwarz gekleidete Gestalt lehnt sich in einem Ledersessel zurück und stößt mit einem leisen Hauchen den beißenden Zigarettenrauch aus. Dann drückt sie die Zigarette langsam im Aschenbecher aus und fragt:
„Ist der Bote gekommen?“

„Ich fürchte nicht“, erwidert eine zweite Gestalt, die am anderen Ende des Raumes in einem Sessel der bequemen Sitzecke sitzt und gemächlich an einem Glas mit goldenem Whiskey nippt.

„Das war zu befürchten.“ – „Ja … und nun?“

Die erste Gestalt erhebt sich und verschränkt die Hände hinter dem Rücken. Nach kurzem Überlegen sagt sie ruhig:
„Wie geplant. Es bleibt leider keine andere Wahl.“

Die zweite Gestalt nickt wortlos. Gemeinsam treten sie zu einem Schaltpult in der Ecke des Raumes.
Jeder steckt einen Schlüssel in eines der beiden Schlüssellöcher und beide betätigen gleichzeitig den Schalter in der Mitte des Pultes.

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
        self.game.add_player("Hund", npc=True)

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
            print("\n\n\n")
            tw_print(f"# Spielrunde {round} ")
            round = round + 1
            if round == 200:
                tw_print(txt_final_text)
                self.game.game_over = True
            for pl in self.game.players:

                tw_print(f'{"-" * 30}')
                from PlayerState import PlayerState
                #
                # Warn if dog and players are in the same location
                #
                plf = None
                dgf = None
                for p in self.game.players:
                    if type(p) is PlayerState:
                        plf = p
                    elif type(p) is NPCPlayerState:
                        dgf = p

                if dgf and plf and dgf.location == plf.location:
                    tw_print(f"***Achtung!! {plf.name} und {dgf.name} sind am selben Ort! Da ist Streit vorprogrammiert!***\n\n")

                if (type(pl) is NPCPlayerState):
                    #
                    # Non Player Character
                    #
                    user_input = pl.NPC_game_move(self.game)
                    if  not user_input:
                        raise Exception("should not happen!")

                    dprint(f"**{pl.name}**: {user_input}")
                elif (type(pl) is ExplosionState):

                    user_input = pl.explosion_input(self.game)
                else:
                    user_input = pl.Player_game_move(self.game)



                p=self.game.verb_execute(pl,user_input)
                from PlayerState import PlayerState
                if type(pl) is PlayerState or type(pl) is NPCPlayerState:
                    tw_print(p)



        if not self.game.game_won:
            tw_print(txt_final_text)

        dprint(f"Total tokens used in this game session: {self.game.llm.tokens}")
        dprint(f"Number of API-Calls: {self.game.llm.numcalls}")
        dpprint(self.game.llm.token_details)
        dprint(f"{'*'*80}")
        pprint(self.game.gamelog)
        tw_print("***Auf Wiedersehen!***")
#
# --- Main ---
#
plname = input("Wie willst du im Spiel heissen? ")
a = Adventure([plname])
a.gameloop()