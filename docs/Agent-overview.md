# Agent-Spieler: Überblick (Architektur und Einbindung)

Dieses Dokument beantwortet drei Fragen:

1. Wie funktioniert der Agent?
2. Wie hängt er am Spiel? (Hund und Zombie erben von `PlayerState` – und der Agent?)
3. Wo weicht er von den Konventionen des restlichen Codes ab, und warum?

Tiefer gehende Texte: `docs/AGENT-SPIELER-erklaert.md` (Lehrtext mit kommentierter Spur),
`docs/AGENT-SPIELER-PLAN.md` (ursprünglicher Plan + „Abweichungen vom Plan“),
`docs/AGENT-SPIELER-AUFTRAG.md` (Auftrag). Im Zweifel gilt der Code.

---

## 1. Kurzantwort: Der Agent ist kein NPC

Hund (`NPCDogState`) und Zombie (`NPCZombieState`) sind **Figuren im Spiel**: Unterklassen von `PlayerState`,
stehen in `gs.players`, und die Engine ruft pro Runde ihre Methode `NPC_game_move(gs)` auf
(`GameState.run_npc_turns`, `game_turn.py`).

Der Agent ist **keine Figur**, sondern ein **Fahrer für die Spielerfigur**. Im Spiel gibt es weiterhin genau
einen gewöhnlichen `PlayerState` für „den Spieler“ – nur kommen seine Eingaben nicht von einem Menschen im
Browser, sondern von einem Sprachmodell.

```
Mensch:   Browser-Eingabe ──► LLM-Parser (Gemini) ──► function_call ──► handle_command ──► Engine
Agent:    Modell (Gemini) ──► function_call ─────────────────────────► handle_command ──► Engine
                                                (derselbe Pfad ab hier)
```

| | Hund / Zombie | Agent |
|---|---|---|
| Klasse | Unterklasse von `PlayerState` | **keine** – gewöhnlicher `PlayerState` bleibt der Spieler |
| In `gs.players`? | ja | nein (der Spieler dort wird von ihm gesteuert) |
| Wie kommt er „dran“? | Engine ruft `NPC_game_move(gs)` pro Runde | `AgentRunner` legt einen Zug in `session["cmd_q"]` und ruft `handle_command` auf |
| Liefert | eine Aktion (`dict`) an die Engine | einen `function_call` – wie der Befehls-Parser |
| Sieht | den `GameState` direkt (er ist Teil der Engine) | **nur**, was der Browser auch bekäme (`session["state"]` + mitgeschnittene Nachrichten) |
| Zustand speichern | `@savable`, `save()/load()` der Klasse | eigener optionaler Block `"agent"` im Spielstand |
| Wohnt in | Wurzelverzeichnis (`npc_*_state.py`) | Paket `agent_player/` |

**Warum nicht als NPC-Unterklasse?** Ein NPC ist Teil der Welt und darf alles sehen (IDs, Flags, Karte). Der
Agent soll dasselbe wissen wie ein Mensch – sonst wäre es kein fairer Test, und das Lehrbeispiel („wie arbeitet ein
Agent mit Beobachtung → Werkzeug → Ergebnis?“) wäre verwässert. Zudem soll der Agent **durch dieselbe Tür**
wie der Mensch gehen, damit Durst, Rundenwechsel, NPC-Züge und Game Over unverändert greifen. Der Plan
(`AGENT-SPIELER-PLAN.md`, Abschnitt 1) nennt das „Weg 2: Autopilot im Server“.

---

## 2. Wie der Agent ins Spiel eingebunden ist

Es gibt genau **fünf Nahtstellen**; die Engine selbst (`game_state.py`, `game_verbs.py`, NPC-Klassen)
wurde dafür kaum angefasst.

### 2.1 Start – `webserver/server.py`
Der Browser verbindet sich mit `?mode=agent[&player=llm|fake|skript][&save=<slot>][&tipp=<text>]`
(der Welcome-Screen baut diese URL). `_agent_request` liest sie. Im Agentenmodus
- wird statt `WebDialogs` ein `AgentDialogs` angelegt (2.2),
- bekommt die Session `session["agent"] = AgentRunner(...)` und `session["tap"] = None` (2.3).

Ohne `?mode=agent` läuft alles wie vorher.

### 2.2 Dialog-Port – `agent_player/dialogs.py`
Die Engine fragt den Spieler nur über das Protokoll `PlayerDialogs` (`services/interfaces.py`): Name, PIN,
Minispiel, Chat, Game Over. `AgentDialogs` erbt von `WebDialogs` und ersetzt davon: Name (fest), Minispiel
(würfeln + Overlay), Chat und PIN (an den Agenten weitergereicht). Alles andere (Game-Over-Popup) bleibt wie im Browser.
Das ist der „Hexagon-Port“ aus Step 3 des Refactorings – hier zahlt er sich aus.

### 2.3 Zugpfad + Mitschnitt – `webserver/command_engine.py`
- `AgentRunner.run_move` stellt den `function_call` in `session["cmd_q"]` und ruft `handle_command` auf.
  Nur der LLM-Parser (Schritt 3 dort) wird übersprungen, alles danach ist der normale Pfad.
- `CommandEngineMixin._send` kopiert jede an den Browser gesendete Nachricht zusätzlich in `session["tap"]`
  (nur wenn ein Agent mitliest). So bekommt der Agent **exakt** die Meldungen, die auch ein Mensch sähe.
  `npc_runner.py` sendet das Minispiel-Ergebnis ebenfalls über `_send`.

### 2.4 Spielstände – `services/save_load.py`
`save_game(gs, agent=None)` kennt einen optionalen Top-Level-Block `"agent"` (eigenes Formatkennzeichen
und eigene Version, geprüft in `agent_player/savestate.py`). `SAVE_VERSION` des Spiels blieb bei 1.
Menschen-Spielstände ohne Block laden unverändert.

### 2.5 Browser – `web/`
`agent_panel.js` (Zuschauer-Panel: Steuerung, Notizbuch, Tokens, Tipp-Feld, Legende), `agent_overlay.js`
(Agent-Icon), `dogfight_overlay.js` (Kampf-Overlay), `welcome.js` (Wahl: selbst spielen / Agent / laden),
dazu Fälle in `websockets.js`. Der Chat-Dialog mit Hund/Zombie läuft schreibgeschützt (`readonly`).

Außerdem: `utils.py` bekam `dl.AGENT` (Debug-Level); `.gitignore` ignoriert `agent_runs/` und `Experience.md`.

---

## 3. Der Agent von innen: zwei verschachtelte Schleifen

```
Äußere Schleife (runner._play_agent)         = die Spielrunden
 └─ pro Runde: Innere Schleife (loop.play_round) = die Agentenschleife
      Modell fragen → Werkzeug ausführen → Ergebnis zurückgeben → wiederholen … bis ein ZUG gewählt wird
 └─ Zug ausführen (run_move) → Engine rechnet Runde, NPCs ziehen → Ergebnis in Notizbuch/Verlauf
```

**Der Kern** ist `loop.play_round`: bewusst eine einzige, lesbare Funktion. Der Rest des Pakets ist Zubehör.

| Datei | Aufgabe |
|---|---|
| `config.py` | alle Einstellungen (Modell `gemini-2.5-flash`, Limits, Würfelgewichte, Experience) **und alle Prompts**, jeweils mit Kommentar, wofür und wo sie gebraucht werden |
| `runner.py` | `AgentRunner`: äußere Schleife, Start/Ende, Zug ausführen, Speichern, Resümee |
| `loop.py` | `play_round`: die innere Agentenschleife; `force_move` bei Aufruflimit |
| `context.py` | `AgentContext` (Zustand) und die Funktionen, die aus den Prompts in `config.py` die Nachrichten bauen (`round_message`, `chat_message`, `pin_message`, `remember_tip`) |
| `tools.py` | Werkzeugliste: **freie Aktionen** (kosten keine Runde) und **Züge** (eine Runde, Pflichtfeld `warum`) |
| `observation.py` | baut die Sicht des Agenten **nur** aus `session["state"]` und den mitgeschnittenen Nachrichten |
| `llm.py` | Schnittstelle `AgentLLM.frage(...)`, `GeminiAgentLLM` (synchrones SDK via `asyncio.to_thread`) |
| `notebook.py` | Notizbuch = einziges Langzeitgedächtnis (der Prompt wird jede Runde frisch gebaut) |
| `chat.py`, `pin.py` | Gespräche mit Hund/Zombie, PIN-Pad (NPC-Seite unverändert) |
| `dialogs.py` | `AgentDialogs` (2.2) |
| `control.py` | Start/Pause/Einzelschritt/Stopp/Tempo aus dem Panel |
| `savestate.py` | Agentenblock in Spielständen: prüfen, importieren, speichern, laden, auflisten |
| `experience.py` | Lernen von Spiel zu Spiel: `Experience.md` (nur Text, kein Training) |
| `trace.py` | schreibt `agent_runs/*.jsonl` (jede Aktion zum Nachlesen) |
| `fake_llm.py`, `fake_run.py`, `script_player.py` | kostenlose Testspieler ohne Gemini |

Regeln, die man kennen sollte:
- **Fairness:** Der Agent sieht nie `GameState`, interne IDs (`o_…`) oder Flags – nur Anzeigenamen („call-names“).
- **Fehlerhafte Aufrufe kosten keine Runde:** Ungültiges kommt als Fehlertext zurück, der Agent versucht es erneut.
- **Gedächtnis:** nur Notizbuch + die letzten 10 Züge + Sicht der Lage. Tipps von außen (`&tipp=` / Panel) landen
  einmal im Prompt **und** im Notizbuch.
- **Hund** (`utils.NODOG`) und die **Minispiel-Würfel** sind die einzigen Spielregel-nahen Einstellungen;
  Spielregeln selbst wurden nicht geändert.
- **Keine Agenten-Frameworks** (kein LangChain/ADK): die Schleife ist von Hand geschrieben, damit man sie erklären kann.

---

## 4. Wo der Agent von den Konventionen des Adventure-Codes abweicht

Ehrlich aufgelistet – manches ist Absicht (Lehrzweck), manches Preis der Entkopplung:

| Abweichung | Grund / Bewertung |
|---|---|
| Eigenes **Paket** statt Dateien im Wurzelverzeichnis | Das Spiel ist flach (`npc_*_state.py`); der Agent ist größer (~1800 Zeilen) und soll als Ganzes lesbar und entfernbar sein. Entspricht dem Muster `webserver/`. |
| ~~Deutsche Bezeichner~~ → **angeglichen (2026-11-13)** | Klassen, Funktionen, Variablen und Modulnamen sind jetzt englisch wie im Engine-Code (`AgentController`, `play_round`, `run_move`, `Notebook`, `savestate.py`, `script_player.py`). **Bewusst deutsch geblieben:** Kommentare und Docstrings (Lehrtext), Prompts, die **Werkzeugnamen und -parameter**, die das Modell sieht (`untersuchen`, `warum`, ...), die Schlüssel im Agentenblock der Spielstände und im Spur-Protokoll (damit alte Spielstände/Spuren lesbar bleiben) und die Nachrichtentypen zum Browser. |
| `# LERNPUNKT:`-Kommentare und lange Modul-Doku | Unterrichtsfokus; im Engine-Code sind Kommentare sparsamer. |
| **`asyncio`-Task** neben der Empfangsschleife | Nötig für Pause/Stopp, solange der Agent wartet; die Engine ist ohnehin `async`. |
| Kopplung über **`session`-Dict** (`session["tap"]`, `session["agent"]`, `web_dialogs.ctx`) | Die Session ist im Web-Layer bereits ein untypisiertes Dict; ein getypter `GameSession` steht im Backlog. Dieses Muster erbt den Mangel. |
| Eigener Spielstand-Block statt `@savable`-Klasse | Der Agent ist keine Spielobjekt-Klasse; sein Zustand (Notizbuch, Verlauf) gehört nicht ins Weltmodell und soll Menschen-Saves nicht verändern. |
| **Kein Test-Suite**, nur Fake-Modell + Skripte | Wie im restlichen Projekt (siehe CLAUDE.md); `fake_run.py` ersetzt hier ein bisschen Testinfrastruktur. |
| Eigene `AgentLLM`-Schnittstelle neben `LLMClient` | `LLMClient` kennt Befehlsparser/Narration, der Agent braucht *Tool-Calling-Dialog*; eine zweite Schnittstelle war einfacher. Ein Kandidat für spätere Zusammenführung. |
| `AgentDialogs` **erbt** von `WebDialogs` | Spart Doppelcode (Game-Over-Popup etc.), koppelt aber an die konkrete Web-Klasse statt nur an das Protokoll. |

Stand 2026-11-13: Die englischen Bezeichner sind umgesetzt, die Prompts liegen gesammelt in `config.py`.
Offen (bewusst nicht angefasst, weil es die technische Trennung berühren würde): den Agentenzustand typisieren
(statt `session`-Dict) und `AgentLLM` mit `LLMClient` zusammenführen.

---

## 6. Namen vor und nach der Angleichung (2026-11-13)

Für alle, die ältere Texte (Plan, Spuren, Gesprächsprotokolle) lesen. Dateien: `spielstand.py` → `savestate.py`,
`skript_spieler.py` → `script_player.py`; alle anderen Dateinamen blieben.

| früher | jetzt | | früher | jetzt |
|---|---|---|---|---|
| `AgentKontext` | `AgentContext` | | `spiele_runde` | `play_round` |
| `AgentSteuerung` | `AgentController` | | `fuehre_werkzeug_aus` | `run_tool` |
| `AgentGestoppt` | `AgentStopped` | | `zug_ausfuehren` | `execute_move` |
| `Werkzeug` | `ToolSpec` | | `erzwinge_zug` | `force_move` |
| `Aufruf` / `AufrufErgebnis` | `ToolCall` / `ToolResult` | | `fuehre_zug_aus` | `run_move` |
| `Antwort` / `Nachricht` | `ModelReply` / `Message` | | `zug_vorbereiten` | `prepare_move` |
| `Notizbuch` | `Notebook` | | `frage` / `frage_modell` | `ask` / `ask_model` |
| `RundenEintrag` / `RundenErgebnis` | `RoundEntry` / `RoundResult` | | `runden_nachricht` | `round_message` |
| `Spur` | `Trace` | | `resuemee_ziehen` | `write_summary` |
| `FREIE_AKTIONEN` / `ZUEGE` | `FREE_ACTIONS` / `MOVES` | | `hinweis_merken` | `remember_tip` |
| `MAX_AUFRUFE_PRO_RUNDE` | `MAX_CALLS_PER_ROUND` | | `behandle_kommando` | `handle_control_command` |

Felder im Kontext: `notizbuch` → `notebook`, `verlauf` → `history`, `runde` → `round_number`, `schritt` → `step`,
`hinweis` → `tip`, `erfahrungen` → `lessons`, `letztes_ergebnis` → `last_result`, `npc_meldungen` → `npc_messages`.
**Unverändert** (Datenformate, nicht Code): Schlüssel im Agentenblock der Spielstände (`notizbuch`, `verlauf`, `notiz_an_mich`, …),
Spur-Zeilen, Werkzeugnamen/-parameter für das Modell, Nachrichtentypen zum Browser (`agent_event`, …).

