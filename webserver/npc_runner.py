"""NPC turn handling for the web backend.

NPCRunnerMixin contributes the NPC-facing methods to WebAdventureServer:
- collect_npc_actions: run one move per NPC (dog / zombie / explosion) plus the
  per-turn switch-timer countdown, returning the actions for handle_command to emit.
- handle_minigame_result: apply a finished mini-game result to the dog and reply.

Kept as a mixin so this large, self-referential code can live in its own file while
behaviour stays identical to the original methods. Relies on the host class
providing ``self.game_sessions``.
"""
import json

from Utils import dprint, dl
from webserver.serialization import serialize_real_game_state
from webserver.texts import txt_final_lost_text
from webserver.game_modules import GAME_MODULES_AVAILABLE


class NPCRunnerMixin:

    async def handle_minigame_result(self, websocket, result):
        """Verarbeite Ergebnis eines Mini-Games"""
        session_id = str(id(websocket))
        if session_id not in self.game_sessions:
            await websocket.send(json.dumps({
                "type": "error",
                "message": "Keine aktive Spielsession"
            }))
            return

        session = self.game_sessions[session_id]


        dprint(dl.WEBGUI, f"🎮 Mini-Game Ergebnis:  -> {result}")

        # Markiere Mini-Game als nicht mehr aktiv
        session["minigame_active"] = False

        # Konvertiere Web-Result zu MiniGames.py Format
        if session["type"] == "real" and GAME_MODULES_AVAILABLE:
            try:
                from NPCDogState import DogFight

                # Konvertiere String zu DogFight Enum
                dog_result_map = {
                    'WON': DogFight.WON,  # Hund gewinnt
                    'LOST': DogFight.LOST,  # Hund verliert
                    'TIE': DogFight.TIE  # Unentschieden
                }
                #
                # Wenn der Hund gesiegt hat, ist das Spiel zu Ende
                #
                if result == "WON":
                    txt=f"""Der Hund hat Dich besiegt - du verlierst das Spiel!
  
  {txt_final_lost_text}                  
                    """
                    game = session["game"]
                    # await self.do_game_over(session_id, game.game_won, txt)
                    await session["web_dialogs"].do_game_over(game.game_won, txt)

                dog_fight_result = dog_result_map.get(result, DogFight.TIE)

                # Suche Hund in der Spielerliste und verarbeite Ergebnis
                game = session["game"]
                from NPCDogState import NPCDogState
                dog = next((p for p in game.players if isinstance(p, NPCDogState)), None)

                fight_message = "Mini-Game beendet"

                if dog and hasattr(dog, 'process_fight_result'):
                    # Übergebe Ergebnis direkt an Hund-Logik
                    fight_message_json = dog.process_fight_result(game, dog_fight_result)
                    fight_message = fight_message_json["function_call"]["args"]["message"]
                    dprint(dl.WEBGUI, f"✅ Fight result verarbeitet: {fight_message[:50]}...")

                # Sende Ergebnis an Client
                response = {
                    "type": "minigame_complete",
                    "result": result,
                    "message": fight_message,
                    "game_state": serialize_real_game_state(game, session_id=session_id)
                }

                await websocket.send(json.dumps(response))
                dprint(dl.WEBGUI, f"✅ Mini-Game Ergebnis verarbeitet: {result}")

            except Exception as e:
                dprint(dl.WEBGUI, f"❌ Fehler beim Verarbeiten des Mini-Game Ergebnisses: {e}")
                await websocket.send(json.dumps({
                    "type": "error",
                    "message": f"Fehler beim Verarbeiten des Spielergebnisses: {str(e)}"
                }))
        else:
            # Demo-Modus
            demo_messages = {
                'WON': f"***Hund gewinnt den Kampf! (Demo)***",
                'LOST': f"***Du gewinnst den Kampf! (Demo)***",
                'TIE': f"***Der Kampf endet unentschieden! (Demo)***"
            }

            response = {
                "type": "minigame_complete",
                "result": result,
                "message": demo_messages.get(result, "Mini-Game beendet (Demo)"),
                "game_state": session["state"]
            }

            await websocket.send(json.dumps(response))

    async def collect_npc_actions(self, game, session_id=None):
        """Run NPC turns via the engine, then refresh the session's serialized state.

        The NPC-turn rules now live in GameState.run_npc_turns (Step 3.2); this wrapper
        keeps the web-layer concerns: error handling and updating session["state"]."""
        try:
            # Inject this session's dialogs (PlayerDialogs port) for NPC interactions.
            dialogs = None
            if session_id and session_id in self.game_sessions:
                dialogs = self.game_sessions[session_id].get("web_dialogs")
            npc_actions = await game.run_npc_turns(session_id, dialogs=dialogs)
            # Update game state nach NPC-Aktionen - OHNE Narration (da schon gemacht)
            if session_id and hasattr(self, 'game_sessions') and session_id in self.game_sessions:
                session = self.game_sessions[session_id]
                session["state"] = serialize_real_game_state(game, session_id=session_id)
            return npc_actions
        except Exception as e:
            dprint(dl.WEBGUI, f"⚠️  NPC-Sammeln-Fehler: {e}")
            import traceback
            traceback.print_exc()
            return []
