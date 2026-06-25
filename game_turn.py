"""Per-turn game rules for GameState.

GameTurnMixin owns the rule logic that drives a single turn. It starts with the
switch-timer countdown and grows (in later Step 3 sub-steps) to include NPC turns
and the thirst / turn-advance / game-over effects. These rules previously lived in
the web layer (webserver/command_engine.py, webserver/npc_runner.py); moving them
here makes GameState the home of game rules, testable without the web GUI.

Relies on the host class (GameState) for get_flags(), players, the verb engine, etc.
"""
from __future__ import annotations

from Utils import dprint, dl


class GameTurnMixin:
    def tick_switch_timers(self):
        """Per-turn countdown of the control-room / generator-room switch timers.

        When a timer reaches zero the corresponding switch flips back off, unless the
        zombie is cooperative. Runs once per turn, after all NPCs have acted.
        """
        f = self.get_flags()
        if f.schalter_kontrollraum_timer > 0:
            f.schalter_kontrollraum_timer -= 1
            if f.schalter_kontrollraum_timer <= 0 and not f.zombie_cooperative:
                f.schalter_kontrollraum = False
        if f.schalter_generatorraum_timer > 0:
            f.schalter_generatorraum_timer -= 1
            if f.schalter_generatorraum_timer <= 0 and not f.zombie_cooperative:
                f.schalter_generatorraum = False

    async def run_npc_turns(self, session_id=None):
        """Run one move for each NPC (dog / zombie / explosion), tick the switch
        timers, and remove expired explosions. Returns the list of NPC action dicts
        for the caller to render. Moved verbatim from the web layer
        (webserver/npc_runner.collect_npc_actions) in Step 3.2."""
        from NPCDogState import NPCDogState
        from Utils import json_cmd_simple
        # Versuche auch ExplosionState zu importieren
        try:
            from ExplosionState import ExplosionState
            EXPLOSION_AVAILABLE = True
        except ImportError:
            EXPLOSION_AVAILABLE = False
            dprint(dl.WEBGUI, "⚠️  ExplosionState nicht verfügbar")

        npc_actions = []
        players_to_remove = []  # Für Spieler die durch Explosion eliminiert werden

        from NPCZombieState import NPCZombieState

        for npc in self.players:
            if isinstance(npc, NPCDogState):
                # Normaler NPC (Hund)
                #
                # Der NPCDogState ("Hund") liefert ergebnisse, die erst durch
                # verb_execute ausgeführt werden müssen (z.B: er geht irgendwo hin)
                # Die verb_execute-Funktion liefert Strings, die erst in dog_messages
                # umgewandelt werden müssen. (Dies ist notwendig, weil die gleichen
                # execute-Methoden für alle NPC aufgerufen werden, egal ob PlayerState
                # oder NPNCPlayerState)
                #
                npc_input = npc.NPC_game_move(self)
                command = npc_input.get("function_call",{}).get("name",None)
                args = npc_input.get("function_call",{}).get("args",{})

                if npc_input and command != "nichts":
                    if command != "minigame":
                        if command  in ["interaktion", "interagiere", "interagieren"]:

                            whom = npc_input["function_call"]["args"]["who"]
                            firstmessage = npc_input["function_call"]["args"]["firstmessage"]
                            npc_result = await self.async_verb_interact(npc, session_id, whom, firstmessage)
                        else:
                            npc_result = self.verb_execute_json(npc, npc_input, session_id)
                        if npc_result and npc_result.strip():
                            npc_actions.append(json_cmd_simple("dog_message",f"**{npc.name}:** {npc_result}"))
                    else:
                        #
                        # Initiate Minigame in web GUI
                        #
                        npc_actions.append(npc_input)

            elif isinstance(npc, NPCZombieState):
                # Zombie NPC
                npc_input = npc.NPC_game_move(self)
                command = npc_input.get("function_call", {}).get("name", None)
                args = npc_input.get("function_call", {}).get("args", {})

                if npc_input and command != "nichts":
                    if command in ["interaktion", "interagiere", "interagieren"]:
                        whom = args.get("who", "")
                        firstmessage = args.get("firstmessage", "")
                        npc_result = await self.async_verb_interact(npc, session_id, whom, firstmessage)
                    elif command == "zombie_message":
                        # Direct message, no self engine processing needed
                        npc_result = args.get("message", "")
                    else:
                        npc_result = self.verb_execute_json(npc, npc_input, session_id)

                    npc.game_engine_answer(self, npc_result)

                    if npc_result and npc_result.strip():
                        npc_actions.append(json_cmd_simple("zombie_message", f"**{npc.name}:** {npc_result}"))

            elif EXPLOSION_AVAILABLE and isinstance(npc, ExplosionState):
                # Explosion-NPC - VEREINFACHT
                dprint(dl.WEBGUI, f"💥 Sammle Explosion: Timer={npc.kaboom_timer}")

                # ExplosionState.explosion_input() macht ALLES und gibt Nachrichten zurück
                #explosion_messages = npc.explosion_input(self)
                #
                # ExplosionState liefert immer Ergebnisse vom Typ
                # explosion_message oder do_explosion, die nicht weiter
                # von verb_execute interpretiert werden müssen, sondern
                # direkt zur Ausgabe an das GUI übergeben werden können
                #
                npc_input = npc.explosion_input(self)
                command = npc_input.get("function_call", {}).get("name", None)
                args = npc_input.get("function_call", {}).get("args", {})

                # Verwende die Nachrichten direkt (keine verb_execute nötig!)
                if npc_input and command != "nichts":
                    npc_actions.append(npc_input)
                    dprint(dl.WEBGUI, f"💥 Explosion-Messages gesammelt!")

                # Prüfe ob die Explosion abgelaufen ist (kaboom_timer = 0 nach explosion_input)
                if npc.kaboom_timer <= 0:
                    dprint(dl.WEBGUI, "💥 Explosion ist abgelaufen - entferne ExplosionState")
                    players_to_remove.append(npc)

        # Switch timer countdown — runs once per turn, after all NPCs have acted
        self.tick_switch_timers()

        # Entferne abgelaufene Explosionen
        for player in players_to_remove:
            if player in self.players:
                self.players.remove(player)
                dprint(dl.WEBGUI, f"🗑️  {player.name} aus Spielerliste entfernt")
        return npc_actions
