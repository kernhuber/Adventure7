""" Zombie NPC Player """
from __future__ import annotations
#from GameState import GameState
from PlayerState import PlayerState

class NPCZombieState(PlayerState):
    def _init_(self):
        self.notes = "Du bist verwirrt."
        self.gameengine_returns = ""

    def NPC_game_move(self, gs:GameState) -> {}:
        """ Zombie Player inputs its actions to the game engine with this method"""
        pass

    def game_engine_answer(self, gs:GameState, r:str):
        """
        Zombie issues commands to game engine like any other player. The game engines
        answers are stored in the Zombie object so it can be processed in subsequent calls
        to NPC_game_move.
        """
        self.gameengine_returns = r