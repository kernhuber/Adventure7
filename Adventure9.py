from collections import deque
from rich.prompt import Prompt
from GameState import GameState
from services.adapters import LLMClientGemini
from EnhancedUI import EnhancedUI

import Utils
Utils.ADV_LOGGER = Utils.dlogger()

from Utils import tw_print, dprint, dpprint, dl
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

***Dann geht die Welt unter. ***
"""

txt_final_won_text = """
# An einem weit entfernten Ort

Eine schwarz gekleidete Gestalt lehnt sich in einem Ledersessel zurück.
„Der Bote hat den Umschlag gebracht“, sagt sie und wedelt mit dem Umschlag.

„Das sind großartige Neuigkeiten!“, erwidert eine zweite Gestalt und erhebt sich aus einer bequemen Sitzecke am anderen Ende des Raumes.
Einen Moment lang starren beide den Umschlag an. Dann öffnet ihn die erste Gestalt und zieht einen vergilbten Notizzettel hervor.
Auf diesem sind in krakeliger Handschrift einige Zeichen gekritzelt.

Lange betrachten sie schweigend den Zettel.
Dann entspannen sich ihre Gesichtszüge.

„Damit ist die Bedrohung endgültig vorbei.“
„Gott sei Dank“, murmelt die erste Gestalt, zerknüllt den Zettel und wirft ihn in einen Papierkorb neben der Sitzecke.
Anschließend verlassen beide den Raum durch eine schwere, mit Leder gepolsterte Tür.

***Die Welt ist gerettet!***
"""




class Adventure:


    def __init__(self, players):
        llm = LLMClientGemini()
        self.game = GameState(llm=llm)
        self.ui = EnhancedUI()
        # Rest der Initialisierung.
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
        from NPCDogState import NPCDogState
        from ExplosionState import ExplosionState

        round = 1
        auto_mode = True
        while not self.game.game_over:
            if not self.game.players:
                self.game.game_over = True
                tw_print("***Keine Spieler mehr übrig***")
                break
            self.game.gamelog.append({"Game_Round":f"{round}"})
            dprint(dl.GAMELOOP,f"#Players: {len(self.game.players)}")
            for i in self.game.players:
                dprint(dl.GAMELOOP,f"* {i.name}")
            print("\n\n\n")
            tw_print(f"# Spielrunde {round} ")
            dprint(dl.GAMELOOP,f"# Spielrunde {round} ")
            round = round + 1
            if round == 200:
                tw_print(txt_final_text)
                self.game.game_over = True
            for pl in self.game.players:

                # tw_print(f'{"-" * 30}')
                from PlayerState import PlayerState
                #
                # Warn if dog and players are in the same location
                #
                plf = None
                dgf = None
                for p in self.game.players:
                    if type(p) is PlayerState:
                        plf = p
                    elif type(p) is NPCDogState:
                        dgf = p

                if dgf and plf and dgf.location == plf.location and not dgf.command_after_fight:
                    tw_print(f"\n***Achtung {plf.name}!! {dgf.name} steht neben Dir! Da ist Streit vorprogrammiert!***\n\n")

                if (type(pl) is NPCDogState):
                    #
                    # Non Player Character
                    #

                    user_input = pl.NPC_game_move(self.game)
                    if  not user_input:
                        raise Exception("should not happen!")


                    #tw_print(f"**Spielzug {pl.name}**: {user_input}")

                elif (type(pl) is ExplosionState):

                    user_input = pl.explosion_input(self.game)
                else:
                    no_game_move = True
                    while no_game_move:
                        user_input_json = pl.Player_game_move(self.game)
                        if user_input_json["function_call"]["name"] in ["hilfe","umsehen","dogstate","context"]:
                            dprint(dl.GAMELOOP,f"###Executing non playround command {user_input_json["function_call"]["name"]}")
                            tw_print(self.game.verb_execute_json(pl, user_input_json))
                            print()
                        else:
                            no_game_move = False

                    dprint(dl.GAMELOOP,f"**Spielzug {pl.name}**: {user_input_json}")

                if type(pl) is not PlayerState:
                    p=self.game.verb_execute(pl,user_input)
                else:
                    # pprint(user_input_json)
                    p = self.game.verb_execute_json(pl, user_input_json)

                # p=self.game.verb_execute_llm(pl,user_input)
                from PlayerState import PlayerState
                if type(pl) is PlayerState or type(pl) is NPCDogState:
                    tw_print(p)
                    print(f"{'-'*30}")



        if not self.game.game_won:
            tw_print(txt_final_text)
        else:
            tw_print(txt_final_won_text)

        dprint(dl.GAMELOOP,f"Total tokens used in this game session: {self.game.llm.tokens}")
        dprint(dl.GAMELOOP,f"Number of API-Calls: {self.game.llm.numcalls}")
        dpprint(dl.GAMELOOP,self.game.llm.token_details)
        dprint(dl.GAMELOOP,f"{'*'*80}")
        dpprint(dl.GAMELOOP,self.game.gamelog)
        tw_print("***Auf Wiedersehen!***")

    def gameloop(self):
        """Gameloop mit verbesserter UI"""
        from PlayerState import PlayerState
        from NPCDogState import NPCDogState
        self.ui.display_long_text(txt_initial_text, "Spielbeginn")

        round = 1

        while not self.game.game_over:
            current_player = self.game.players[0]

            # Sammle alle Aktionen dieser Runde
            round_actions = []

            for pl in self.game.players:
                if type(pl) is PlayerState:
                    # Zeige UI vor Eingabe
                    self.ui.display_game_screen_v2(current_player, self.game)

                    user_input_json = pl.Player_game_move(self.game)

                    # Spezielle Befehle
                    if user_input_json["function_call"]["name"] == "hilfe":
                        self.ui.display_help()
                        continue
                    elif user_input_json["function_call"]["name"] == "toggle_layout":
                        result = self.ui.toggle_layout_mode()
                        self.ui.add_action_to_history(result, "system")
                        continue

                    # Normale Befehle ausführen
                    result = self.game.verb_execute_json(pl, user_input_json)

                    # Zur Historie hinzufügen
                    command_name = user_input_json["function_call"]["name"]
                    self.ui.add_action_to_history(f"Du: {command_name}", "input")
                    self.ui.add_action_to_history(result, "output")

                    round_actions.append(f"Du: {command_name}")
                    round_actions.append(result)

                elif type(pl) is NPCDogState:
                    # NPC-Aktionen
                    npc_action = pl.NPC_game_move(self.game)
                    if npc_action and npc_action != "nichts":
                        npc_result = self.game.verb_execute(pl, npc_action)
                        self.ui.add_action_to_history(f"{pl.name}: {npc_action}", "npc")
                        if npc_result:
                            self.ui.add_action_to_history(npc_result, "npc_result")
                        round_actions.extend([f"{pl.name}: {npc_action}", npc_result])

            # Finale Anzeige der Runde
            self.ui.display_game_screen_v2(current_player, self.game, round_actions)

            round += 1

        # Spiel-Ende
        end_text = txt_final_won_text if self.game.game_won else txt_final_text
        self.ui.display_long_text(end_text, "Spielende")


#
# --- Main ---
#

plname = input("Wie willst du im Spiel heissen? ")

a = Adventure([plname])
a.gameloop()