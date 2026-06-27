---
name: gameplay-and-npcs
description: "Gameplay/UI phase, NPC architecture (dog FSM vs LLM zombie), and the next step (understand the zombie)"
metadata: 
  node_type: memory
  type: project
  originSessionId: de4a68f5-57c9-4f86-9442-a2d5f29750d7
---

After the refactor (Steps 1-3, see [[webserver-refactor-status]]), work is the
**gameplay & web UI** phase on branch `Adventure-10-2026-06-26-Gameplay`. Summary doc:
`docs/GAMEPLAY-2026-06-27.md`. Project context: [[project-purpose]].

**Changes so far:** Felsnische place rename (`p_felsen`->`p_felsnische`, object
`o_felsen` stays "Felsen"); refillable bottle at the Wasserspender; pretty item names
in take/drop/examine; dog shown as a corner **icon** (`web/dog_overlay.js`, driven by
`dog.here`/`dog.mood` from serialization), yellow blink=angry / red=attack; zombie
awakening opens the chat modal; dramatic **zombie-bite** popup (`web/bite_overlay.js`)
+ Status red flash (life energy == thirst_counter); red zombie chat modal vs green
dog (`web/zombie_chat.js`); **2x2 panel layout**; **"Letzte Aktion" transcript**
(Eingabe + atomic `action_label` + engine response, cleared per input);
`dl.CMDLOG` logs the full user input + per-command debug; `dprint` prefixes lines with
the level name.

**NPCs:** both subclass `PlayerState` with `NPC_game_move(gs)`, run once/turn by
`GameState.run_npc_turns` (called from the web layer). NPC dialog goes
`interaktion` -> `async_verb_interact` -> `do_chat` -> chat modal.
- Dog (`npc_dog_state.py`): hand-written finite state machine (`DogState`
  START/EATING/ATTACK/TRACE/GOHOME); attack -> mini-game. **Author-written.**
- Zombie (`npc_zombie_state.py`): **Claude-authored, LLM-reasoned**
  (`gemini-2.5-flash`); states DORMANT/AWAKENING/HUNTING/STALKING/COOPERATING/REDEEMED;
  awoken by taking the wallet (`game_take_functions._awaken_zombie`).

**NEXT:** understand & document how the zombie works (author's explicit request);
more gameplay polish.
