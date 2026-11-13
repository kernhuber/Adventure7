# Plan: Agent-Spieler mit Zuschauermodus

Stand: 2026-11-11 · Branch: `Adventure-11-AgentNPC` · Grundlage: `docs/AGENT-SPIELER-AUFTRAG.md`
Status: **Umgesetzt** (Meilensteine 1–6 und Nachträge, Stand 2026-11-11). Dies ist das ursprüngliche Planungsdokument;
wo Code und Plan abweichen, **gilt der Code** — die Abweichungen stehen am Ende („Abweichungen vom Plan“), die
Beschreibung des Ist-Zustands in `docs/AGENT-SPIELER-erklaert.md`.
Achtung: Die Namen im Plan (Dateien, Klassen, Funktionen, Konstanten) sind die **ursprünglichen deutschen**; am 2026-11-13 wurden alle
Bezeichner im Paket ins Englische umbenannt (z. B. `spielstand.py` → `savestate.py`, `AgentKontext` → `AgentContext`,
`spiele_runde` → `play_round`) und die Prompts in `config.py` gesammelt. Die Zuordnung steht in `docs/Agent-overview.md`.

## 0. Entscheidungen aus Phase 0

| Thema | Entscheidung |
|---|---|
| Modell | `gemini-2.5-flash`, konfigurierbar in `agent_player/config.py` |
| Hund | **allein `utils.NODOG`** (False = Hund dabei), wie im normalen Spiel – keine zweite Einstellung in `agent_player/config.py` (so geändert nach Meilenstein 3) |
| Branch | weiter auf `Adventure-11-AgentNPC` |
| Start | Button „Agent spielen lassen“ + URL-Parameter `?mode=agent` (`&player=llm|fake|skript`; `&save=<slot>` lädt Spiel **und** Agentenzustand; ein Spielstand ohne Agentenblock startet den Agenten ohne Gedächtnis – siehe Meilenstein 5), **ein** Browser = Spieloberfläche + Zuschauer |
| Minispiele | im Agentenmodus **entfallen sie**; das Ergebnis wird serverseitig zufällig gezogen (`WON` = Hund gewinnt / `LOST` = Spieler gewinnt / `TIE`), siehe 4.2 |
| Mehrere Zuschauer | nicht im Umfang (kein Sitzungs-Broadcast) |

## 1. Architektur: Weg 2 (Autopilot im Server)

**Wahl: Weg 2**, wie von Chris vorgeschlagen. Begründung nach dem Lesen des Codes:

1. **Die Naht existiert schon.** Alle Stellen, an denen das Spiel auf einen Menschen wartet, laufen über
   `WebDialogs` (`ask_for_playername`, `ask_for_pin`, `do_minigame`, `do_chat`, `do_game_over`), und die Engine
   bekommt dieses Objekt als `dialogs=` übergeben (`async_verb_interact`, `run_npc_turns`). Ein
   `AgentDialogs` mit denselben Methoden ersetzt die fünf Wartestellen, ohne dass Engine oder NPCs es merken.
2. **Der Rundenpfad bleibt identisch.** Der Agent legt `{"function_call": {...}}` in `session["cmd_q"]` und ruft
   `handle_command(ws, {"command": ""})` auf – dieser Aufruf verarbeitet genau das, was auch ein geparster
   Menschenbefehl verarbeitet (`execute_single_command`, Durst, `advance_time`, NPC-Züge, Game Over). Nur der
   LLM-Parser (Schritt 3 in `handle_command`) wird übersprungen.
3. **Zuschauermodus fast geschenkt.** `command_result`, `npc_actions`, `game_state`, Chat-Modal, Biss-Popup,
   Game Over gehen weiter an dieselbe WebSocket – der Browser rendert sie wie bisher. Neu sind nur
   Agenten-Ereignisse (`agent_*`, siehe 3).
4. **Weg 1 verworfen:** bräuchte Sitzungs-Spiegelung (zweite Verbindung sieht dieselbe Sitzung) und würde
   `async for message in self.ws` in `WebDialogs` mit dem Client-Loop um dieselbe Verbindung konkurrieren lassen.

**Nebenläufigkeit.** Der Agent läuft als eigener `asyncio.Task` neben der Empfangsschleife `handle_client`.
Dadurch kommen Steuernachrichten (Pause, Einzelschritt, Stopp) an, solange der Agent wartet oder auf Gemini
wartet. Der blockierende Gemini-Aufruf (`google-genai` ist synchron) läuft per `asyncio.to_thread`, damit
der Server nicht blockiert.

## 2. Änderungen im Bestand (möglichst wenige, je ein eigener Commit)

| # | Datei / Stelle | Änderung | Warum |
|---|---|---|---|
| ~~E1~~ *(entfallen: der Mitschnitt aus E2 liefert alle Teilergebnisse)* | `webserver/command_engine.py` – `handle_command` / `execute_single_command` | Ergebnis **zurückgeben** bzw. in `session["last_results"]` sammeln (Ergebnistext je ausgeführtem Kommando, inkl. Folge-Kommandos wie `check_pinpad` aus der Rekursion in Schritt 7). Verhalten für Menschen unverändert. | Der Agent braucht das Ergebnis als Werkzeugergebnis; bisher geht es nur per WebSocket raus. |
| E2 | `command_engine.py` – die Sendestellen für `command_result` und `npc_actions` | kleiner Helfer `_send(session, ws, payload)`: sendet wie bisher und hängt **zusätzlich** eine Kopie an `session["tap"]`, falls gesetzt (`None` bei Menschen). | Der Agent soll genau die NPC-Meldungen sehen, die der Browser bekommt (Fairness, 4.1) – ohne zweite Quelle. |
| E3 | `webserver/server.py` – `register_client` | liest `websocket.request.path` (websockets 15) auf `mode=agent`/`save=`; bei Agentenmodus: Name aus `config` statt `ask_for_playername`, `AgentDialogs` statt `WebDialogs`, optional Spielstand laden, Hund gemäß `config`; neue Nachrichtentypen in `handle_client` (`agent_control`, siehe 3). | Einstiegspunkt. Menschlicher Pfad bleibt Zweig `else`. |
| E4 | `web/websockets.js` + `web/Adventure9.html` | Button „Agent spielen lassen“ (lädt die Seite mit `?mode=agent`), WebSocket-URL mit Query, Eingabezeile im Agentenmodus deaktiviert, neue `case`s für `agent_*` → `agent_panel.js`. | Frontend-Anbindung. |
| E5 | `web/zombie_chat.js` | Chat-Modal bekommt `readonly`-Modus (Eingabefeld aus, Schließen-Knopf nur Anzeige) und nimmt `agentmessage`-Zeilen entgegen. | Zuschauer sehen die Zeilen des Agenten „wie getippt“. |

**Nicht geändert:** `game_state.py`, Verben, NPCs (`whom.chat`, `whom.end_chat`, Trust), `world.json`, Parser.
Wenn sich beim Bauen zeigt, dass eine weitere Engine-Änderung nötig ist, melde ich sie vorher.

## 3. Nachrichten Server ↔ Browser

Bestehende Typen bleiben. Neu:

**Server → Browser**

| Typ | Inhalt | Zweck |
|---|---|---|
| `agent_status` | `{state: idle|running|paused|stopped|finished, round, step, calls_this_round, calls_limit, model, tokens_round, tokens_total, model_calls}` | Kopfzeile des Panels |
| `agent_event` | `{kind: "free"|"move"|"error"|"chat"|"text", tool, args, warum?, result, round, step}` | ein Eintrag im Aufrufprotokoll (Farbe nach `kind`) |
| `agent_notebook` | `{text}` | aktuelles Notizbuch (nach jeder Änderung) |
| `agent_summary` | `{ergebnis, runden, aufrufe, tokens, orte, trace_datei}` | Ende des Spiels |
| `zombie_chat` (bestehend) | + Feld `readonly: true` | Chat-Modal im Zuschauermodus |
| `zombiemessage` (bestehend) / **neu** `agentmessage` | Zeile des Agenten im Chat | Anzeige im Modal |

**Browser → Server**

| Typ | Inhalt |
|---|---|
| `agent_control` | `{action: "start"|"pause"|"resume"|"step"|"round"|"stop", delay_ms?}` |

`step` = genau **ein** Werkzeugaufruf, `round` = bis zum nächsten Zug, `delay_ms` = Pause zwischen Schritten.

## 4. Der Agent selbst – Paket `agent_player/`

```
agent_player/
    config.py        Modell, Limits (Aufrufe/Runde=8, Runden=100, Verlauf=10, Chat-Wortwechsel=10,
                     Token-Limit optional), Spielername "Agent", Hund an/aus, Tempo
    observation.py   Spielersicht als Text (nur Wahrnehmbares, Rufnamen)
    notebook.py      Notizbuch (Text + append/lesen)
    tools.py         Werkzeugdefinitionen – drei getrennte Listen: FREIE_AKTIONEN, ZUEGE, CHAT_WERKZEUGE
    context.py       Prompt je Runde frisch bauen
    llm.py           schmale Schnittstelle AgentLLM + Gemini-Umsetzung
    loop.py          DIE innere Schleife (eine Funktion, ≤ 60 Zeilen ohne Kommentare)
    control.py       Pause/Einzelschritt/Stopp/Tempo (asyncio.Event) – getrennt, damit loop.py lesbar bleibt
    dialogs.py       AgentDialogs: ersetzt WebDialogs (Chat, PIN, Minispiel, Name, Game Over)
    runner.py        Äußere Schleife: Runde für Runde, Spielende, Zusammenfassung
    trace.py         JSONL-Spur nach agent_runs/ (in .gitignore)
web/agent_panel.js   Zuschauer-Panel (plain JS)
```

Jede Datei hat eine Aufgabe; Dataclasses für `Werkzeugaufruf`, `Werkzeugergebnis`, `RundenEintrag`.

### 4.1 Wahrnehmung (Fairness)

`observation.py` baut den Text **aus `session["state"]`** (= `serialize_real_game_state`, dieselbe Quelle wie der
Browser) plus den getappten Meldungen (E2). Enthalten: Ort, Szenentext, Objekte, begehbare/versperrte Wege,
Inventar, Durst, Ergebnis der letzten Aktion, NPC-Meldungen, die auch die GUI einem Menschen zeigt
(`zombie_event`, `zombie_bite`, Explosions-/Timer-Meldungen; Debug-Zeilen wie `zombie_message` **nicht**),
Schalter-Zähler nur, wenn die GUI sie anzeigt. Nicht enthalten: Flags, IDs, `zombie_state`-Enum, NPC-Innenleben,
PIN. Namen sind Rufnamen; die Übersetzung Rufname → ID (`obj_name_from_friendly_name` /
`place_name_from_friendly_name`, case-insensitive) passiert in `tools.py`, nicht im Modell.
*Offener Prüfpunkt:* welche Overlay-Infos die GUI wirklich anzeigt (z. B. „Hund hier“), lese ich beim Bau von
`observation.py` in `websockets.js`/`dog_overlay.js`/`zombie_overlay.js` nach und dokumentiere die Entscheidung.

### 4.2 Werkzeuge

Die Trennung ist im Code sichtbar (drei Listen, je mit `# LERNPUNKT`).

**Freie Aktionen** – kosten keine Runde, NPCs handeln nicht, laufen **nicht** durch die Engine:

| Name | Argumente | Rückgabe |
|---|---|---|
| `situation_lesen` | – | aktuelle Beobachtung erneut |
| `inventar_ansehen` | – | Inventarliste (Rufnamen) |
| `notizbuch_lesen` | – | Notizbuch |
| `notizbuch_schreiben` | `text` | Bestätigung; Text wird angehängt |
| `was_weiss_ich_ueber` | `ort` | Auszug aus **Notizbuch und eigenem Verlauf** zu diesem Ort – nie aus der Welt |

**Züge** – jeder mit Pflichtargument `warum`; laufen als `function_call` durch `handle_command` → `execute_single_command`:

| Name | Argumente | Engine-Verb |
|---|---|---|
| `gehen` | `ziel`, `warum` | `gehe` (`direction`) |
| `nehmen` | `objekt`, `warum` | `nimm` (`whato`) |
| `ablegen` | `objekt`, `warum` | `ablegen` |
| `anwenden` | `objekt`, `auf?`, `warum` | `anwenden` (`what`/`towhat`) |
| `untersuchen` | `objekt`, `warum` | `untersuche` |
| `umsehen` | `warum` | `umsehen` |
| `geben` | `objekt`, `an`, `warum` | `gib` (`what`/`towhom`) |
| `angreifen` | `wen`, `warum` | `angreifen` |
| `ansprechen` | `wen`, `erste_nachricht?`, `warum` | `interagieren` → startet den Chat (Chat-Werkzeuge) |
| `abwarten` | `warum` | `nichts` |

Nicht angeboten: `quit`, `hilfe`, `rest`, `zurueckweisen`, Test-/Debug-Verben (`dogstate`, `zombie_*`, …).

**Chat-Werkzeuge** (nur im Chat; Spielzüge sind dort nicht verfügbar): `sage(text)`, `gespraech_beenden(zusammenfassung)`.

**PIN-Werkzeug** (nur wenn das PIN-Pad offen ist): `pin_eingeben(ziffern)`.

**Begründung „direkte Werkzeuge statt Freitext an den Parser“:** ein LLM weniger in der Kette (kein
Parse-Fehler, kein Parser-„Halluzinieren“ wie der dokumentierte `gehe`-Teleport), klare Fehlermeldungen, und
„Welt = Werkzeuge“ wird sichtbar. Weil die Züge am Ende doch durch **denselben** `handle_command`-Pfad laufen,
entsteht keine zweite Regelwelt. (Die vorhandenen `FunctionDeclaration`s aus `parse_user_input_to_commands`
verwende ich als **Vorlage** für Beschreibungen und Argumentnamen; sie selbst passen nicht 1:1, weil sie
ID-`enum`s pro Ort enthalten und keine `warum`.)

**Ungültige Aufrufe** (unbekanntes Objekt, Weg versperrt, falsche Argumente): `tools.py` prüft vorab gegen die
sichtbare Umgebung und liefert eine verständliche Fehlermeldung als Werkzeugergebnis (`kind: error`) – **ohne**
den Engine-Pfad, also ohne Runde. Was die Engine selbst als Systemfehler markiert
(`last_command_was_system_error`), kostet dort ebenfalls keine Runde.

### 4.3 Die Schleife (`loop.py`)

Pseudocode (so soll die eine Funktion lesbar sein):

```
async def spiele_runde(ctx) -> RundenErgebnis:
    nachrichten = baue_prompt(ctx)                     # frisch: System + Beobachtung + Notizbuch + Verlauf(N)
    for aufruf_nr in range(MAX_AUFRUFE_PRO_RUNDE):
        await ctx.steuerung.vor_schritt()              # Pause / Einzelschritt / Stopp / Tempo
        antwort = await ctx.llm.frage(nachrichten, werkzeuge)   # Text und/oder Werkzeugaufrufe
        ctx.zeige_text(antwort.text)                   # nur echter Modelltext, keine erfundenen „Gedanken“
        for aufruf in antwort.aufrufe:
            ergebnis = await fuehre_aus(ctx, aufruf)   # frei -> sofort; Zug -> handle_command
            nachrichten.append(ergebnis_nachricht(aufruf, ergebnis))
            if aufruf.ist_zug:
                return RundenErgebnis(zug=aufruf, ergebnis=ergebnis)   # Kontext wird verworfen
    return await neutraler_zug(ctx)                    # Limit: „jetzt Zug!“ nachfordern, sonst `umsehen`, protokollieren
```

Die **äußere Schleife** (`runner.py`): solange nicht Spielende/Rundenlimit/Tokenlimit/Stopp → `spiele_runde`, Verlauf
fortschreiben, `agent_status` senden; am Ende `agent_summary` + JSONL-Zusammenfassung.

**Kontext:** je Runde frisch (Systemprompt + Beobachtung + Notizbuch + die letzten N=10 Runden als Zeilen
„Zug · warum · Ergebnis“). Innerhalb der Runde wächst er mit den Werkzeugergebnissen, nach dem Zug wird er verworfen
– bewusst gegen einen endlos wachsenden Chat (Kosten, Fokus; Vergleich: das Notizbuch des Zombies). Im Code mit
`# LERNPUNKT` begründet. **Ziel im Systemprompt:** nur das, was der Spieler weiß (Bote, Umschlag, gerissene
Fahrradkette …) – ich übernehme den Einleitungstext aus der GUI/`texts.py`; kein Lösungswissen.

### 4.4 Gespräche (Baustein B)

`AgentDialogs.do_chat(gs, pl, whom, firstmessage)` spiegelt `WebDialogs.do_chat`: sendet `zombie_chat` mit
`readonly: true`, führt einen **Chat-Mini-Loop** (gleicher Aufbau wie `loop.py`, nur mit `sage` /
`gespraech_beenden`), pflegt wie das Modal das `chatArray` (`{zombiemessage}` / `{playermessage}`), ruft
`whom.chat(gs.llm, array)` und am Ende `whom.end_chat(gs.llm, array)` – NPC-Seite unverändert. Der Zombie-Befehl
`quit` beendet den Chat wie im Browser. Limit: 10 Wortwechsel. Danach bekommt der Agent einen Notizbuch-Aufruf frei.
Funktioniert für vom Agenten gestartete Chats und für NPC-initiierte (Erwachen des Zombies), da beide über
`dialogs.do_chat` laufen. Der Chat-Mini-Loop läuft im selben Task wie die Runde und nutzt dieselbe `control`-Steuerung
(Pause/Einzelschritt gelten auch im Chat).

### 4.5 PIN und Minispiel

- **PIN:** `check_pinpad` wird wie heute von der Engine in die Queue gelegt; `execute_single_command` ruft
  `ask_for_pin(hash)`. `AgentDialogs.ask_for_pin` startet einen kurzen Mini-Loop mit `pin_eingeben(ziffern)` (+ freie
  Aktionen, um das Notizbuch zu lesen). Der Server prüft `md5(ziffern) == hash` (dieselbe Prüfung wie `pinpad.js`) und
  gibt `"OK"`/`"FAIL"` zurück. **Ein** Versuch pro Karteneinsatz (wie beim Menschen: das Browser-Pad schließt erst nach vier Ziffern); Formatfehler (nicht genau vier Ziffern) sind kostenlos. Im Browser erscheint
  der Ablauf im Panel (und optional als Einblendung des Pads – Option, kein Muss). Die PIN steht nirgends im
  Systemprompt – der Agent muss sie finden und ins Notizbuch schreiben.
- **Minispiel:** `AgentDialogs.do_minigame()` zieht serverseitig `random.choice(["WON","LOST","TIE"])` (WON = Hund
  gewinnt, wie in `handle_minigame_result`), sendet nur eine `info`/`agent_event`-Meldung („Hundekampf: …“) und gibt
  das Ergebnis zurück. `handle_minigame_result` bleibt unverändert; die JS-Minispiele werden im Agentenmodus nie
  gestartet. Hinweis für die Doku: Die Gewinnchance ist damit nicht mehr von Geschick abhängig – ein bewusst
  einfacher Platzhalter.

### 4.6 Zuschauermodus (`web/agent_panel.js`)

Ein- und ausklappbares Panel neben der unveränderten 2×2-Oberfläche: Kopfzeile (Runde, Schritt, Aufrufe/Limit, Status),
Aufrufprotokoll (Farben: freie Aktion / Zug / Fehler / Chat; `warum` hervorgehoben; Modell-Freitext kursiv),
Notizbuch, Tokens (Runde/gesamt) und Modellaufrufe, Steuerleiste (Start, Pause, **Einzelschritt**, Runde, Stopp,
Tempo), Legende der Farben, große Schrift (Beamer). Kein Framework, kein Build.

### 4.7 Protokoll

`agent_runs/<zeitstempel>.jsonl` (git-ignoriert): eine Zeile je Ereignis (Runde, Werkzeug, Argumente, Ergebnis,
Tokens, Zeit); letzte Zeile = Zusammenfassung (gewonnen/verloren/abgebrochen, Runden, Aufrufe, Tokens, besuchte
Orte, letzter Zustand). Optional: `agent_player/spur_anzeigen.py` gibt eine Spur als lesbaren Text aus.

### 4.8 Modell-Schnittstelle (`llm.py`)

Eine Klasse `AgentLLM` mit einer Methode `frage(nachrichten, werkzeuge) -> Antwort(text, aufrufe, tokens)`;
`GeminiAgentLLM` setzt sie mit `google-genai` um (Modellname aus `config`). Ein zweiter Anbieter (z. B. Claude über
die Anthropic-API) wäre eine weitere Datei. **Fake-Modell** `FakeAgentLLM` (liefert vorgegebene Aufrufe, kein Netz)
liegt in `agent_player/fake_llm.py` – Test für die Schleife und Lehrstück („Schleife ohne KI“). Tokenzählung über
`usage_metadata`, getrennt vom bestehenden `_log_tokens` der Spiel-LLMs; ich lese aber, wie dieses dort arbeitet,
und nutze dasselbe Muster. Keine Agenten-Frameworks.

### 4.9 Logging

`dprint(dl.AGENT, …)` mit neuem Flag `dl.AGENT` in `utils.py` (kleine Ergänzung; Chris' manuelle Debug-Einstellungen
dort fasse ich nicht an).

## 5. Meilensteine und Prüfschritte

Alles ohne Commit, bis Chris es sagt. Ich liefere je Meilenstein eine kurze Testanleitung; Netz-/SDK-Pfade teste ich
in meiner Sandbox nicht (Google-SDK-Import hängt dort) – nur `py_compile` und Blattmodule.

1. **Naht + Skript-Spieler im Zuschauermodus** (E1–E5, `control.py`, `dialogs.py`, `runner.py`, Skript statt LLM,
   Befehlsliste wie `sys_test.py`, aber direkt als Verb-Aufrufe; Panel mit Start/Pause/Einzelschritt/Runde/Stopp).
   - *Prüfung:* `./start.sh`, Browser `…/?mode=agent`, Button „Start“: Der Spieler läuft die Liste ab; „Einzelschritt“
     löst genau einen Befehl aus (Letzte Aktion, Szene und Umgebung aktualisieren sich wie bei Menschen); „Pause“
     hält an; Zurück ohne `?mode=agent` spielt der Mensch unverändert (Regression).
2. **Agentenschleife** (`tools`, `observation`, `notebook`, `context`, `llm`, `loop`, `trace`; Fake-Modell).
   - *Prüfung ohne Netz:* `./venv/bin/python3 -m agent_player.fake_run` – Spur mit freien Aktionen, Zügen, einem
     Fehlerfall (keine Runde), Limit→neutraler Zug. *Mit Gemini:* `?mode=agent` + Spielstand `02-gemma-nodog-höhle`:
     Panel zeigt Aufrufe, `warum`, Notizbuch, Tokens; Spur in `agent_runs/`.
3. **Gespräche** (`AgentDialogs.do_chat`, E5). *Prüfung:* Spielstand `05-…zombie-on-its-way` oder Wallet nehmen:
   Zombie erwacht → Chat-Modal öffnet read-only, Zeilen des Agenten erscheinen, `quit`/Limit beenden, `end_chat`
   aktualisiert Vertrauen (im Log sichtbar), Agent schreibt danach ins Notizbuch.
4. **PIN und Minispiel.** *Prüfung:* Spielstand vor dem Geldautomaten (Hund an, Zettel gelesen): Agent gibt die PIN
   ein, Panel zeigt Versuch/Ergebnis; Hundangriff liefert zufälliges Ergebnis ohne Minispiel-Overlay.
5. **Panel vollständig** (Notizbuch, Tokens, Legende, Beamer-Größe), Start ab Spielstand (`&save=`). *Prüfung:*
   Fenster auf Beamer-Zoom, alle Steuerungen, Spielende → `agent_summary`.
6. **Erklärdokument** `docs/AGENT-SPIELER-erklaert.md` (inkl. kommentierter echter Spur) und kurzer Abschnitt in
   `CLAUDE.md`. *Prüfung:* Chris liest es und kann die Schleife erklären.

## 6. Risiken und offene Punkte

- **`handle_command` ist rekursiv** (Schritt 7) und verarbeitet Folgekommandos (z. B. `check_pinpad`) im selben Aufruf.
  E1 muss daher *alle* Teilergebnisse einsammeln; der Zug-Pfad des Agenten darf nicht von einem einzigen Rückgabewert
  ausgehen. Fallstrick bei der Umsetzung.
- **Ein WebSocket-Leser pro Verbindung:** `WebDialogs` liest mit `async for message in self.ws` selbst; im Agentenmodus
  darf **nur** `handle_client` lesen, deshalb `AgentDialogs` ohne eigene Leseschleife. Die Steuernachrichten gehen
  an `control`.
- **Zombie-Chat vom NPC initiiert** läuft innerhalb `run_npc_turns` und damit im Rundenpfad – dort muss der
  Chat-Loop denselben `control`-Zugriff haben (Pause mitten im Chat). Einplant in Meilenstein 3.
- **Synchrone SDK-Aufrufe** (`google-genai`) blockieren den Event-Loop ohne `to_thread`; ebenso blockiert das
  bestehende `game.llm.narrate(...)` in `serialize_real_game_state` – schon heute, aber im Agentenmodus fällt es
  stärker auf, weil Pause-Nachrichten dann verzögert ankommen. Gegebenenfalls in Meilenstein 1 per `to_thread`
  umhüllen (kleine Engine-/Webserver-Änderung, eigener Commit, ich melde sie vorher).
- **Kosten:** ≈ 2–8 Gemini-Aufrufe je Runde × 100 Runden + Narration/NPC-Reasoning; deshalb Token-Zähler und
  optionales Limit. Der Agent kann sich außerdem in Schleifen verrennen (immer dasselbe untersuchen) – das ist
  Lehrmaterial, kein Fehler; das Rundenlimit begrenzt es.
- **Narration ist LLM-erzeugt** und kann Dinge ausschmücken; der Mensch sieht dasselbe. Der Agent bekommt sie
  deshalb **zusammen** mit der strukturierten Umgebungsliste (Objekte/Wege), die verlässlich ist.
- **Fairness-Kante:** `untersuche` und Lesetexte (Betriebshandbuch-Popup `manual_popup`) – Inhalte, die der Mensch im
  Popup liest, müssen auch beim Agenten ankommen (Tap von `manual_popup` in E2 ergänzen).
- **Spielstände mit `nodog`** (alle in `saves/`) laufen ohne Hund; für Meilenstein 4 brauche ich einen Spielstand mit Hund
  (ich erzeuge einen neuen aus einem Neustart, oder Chris speichert einen).
- **Offen für Chris:** Soll der Agent den Namen „Agent“ tragen (Default) oder soll das aus der URL kommen
  (`&name=`)? – ich nehme „Agent“, außer du sagst etwas anderes.


## Nachtrag Meilenstein 5 (2026-11-11): Spielstände mit Agentenzustand

- Das Save-Framework (`services/save_load.py`) bekommt einen optionalen, eigens versionierten Block `"agent"`
  (additiv, `SAVE_VERSION` bleibt 1; Details in `docs/SAVE-LOAD-DESIGN.md`).
- `agent_player/spielstand.py`: `exportieren`, `pruefen` (Format-/Versionsanalyse beim Laden), `importieren`,
  `speichern`, `laden`, `auflisten`.
- Neue freie Aktion **`spielstand_speichern(notiz)`**: der Agent legt vor einer riskanten Entscheidung selbst einen
  Spielstand an; seine Notiz erinnert ihn nach dem Laden daran. Zusätzlich speichert der Zuschauer per Panel-Knopf.
- Laden: Panel-Knopf „📂 Laden“ (🤖 = Spielstand mit Agentengedächtnis) oder URL `?mode=agent&save=<name>`.
- Gespeichert wird nur zwischen Zügen (nicht mitten in einem laufenden Zug der Engine).
- Panel: Beamer-Zoom (A−/A+), Tooltips in der Legende.


## Abweichungen vom Plan (Stand der Umsetzung, 2026-11-11)

Geprüft gegen den Code; der Plan oben ist in diesen Punkten überholt:

- **E1 entfällt.** `handle_command` gibt nichts zurück; der Agent liest alles aus `session["tap"]` (E2). E2 deckt zusätzlich
  `manual_popup` und das Minispiel-Ergebnis ab (`webserver/npc_runner.py` sendet über `_send`).
- **Start/URL.** Zusätzlich zu `?mode=agent`: `&player=llm|fake|skript`, `&save=<slot>`, `&tipp=<text>`; für Menschen
  `?load=<slot>` (kein Namensdialog). `web/index.html` reicht die Query durch. Der Welcome-Screen bietet die Auswahl
  (selbst spielen / Agent / laden); die Spielstandliste kommt über `/slots.json` (`webserver/http_server.py`).
- **Paket.** Zusätzlich zur Liste in Abschnitt 4: `chat.py`, `pin.py`, `spielstand.py`, `experience.py`, `control.py`, `dialogs.py`,
  `runner.py`, `skript_spieler.py`, `fake_llm.py`, `fake_run.py`. Nicht gebaut: das optionale Skript `spur_anzeigen.py`.
- **Werkzeuge.** Neu gegenüber der Liste: freie Aktion `spielstand_speichern(notiz)`, Ergebnis-Werkzeug `erfahrung_notieren`
  (nur beim Resümee), PIN-Werkzeuge (`notizbuch_lesen`, `pin_eingeben`). Nach einem Gespräch gibt es keinen eigenen
  Notizbuch-Aufruf; die `zusammenfassung` von `gespraech_beenden` wird automatisch ins Notizbuch übernommen.
- **PIN.** Ein Versuch pro Karteneinsatz (wie beim Menschen), nicht drei.
- **Minispiel.** Gewürfelt mit Gewichten (`config.MINISPIEL_GEWICHTE`); der Browser zeigt den Kampf als Overlay
  (`agent_dogfight`, `web/dogfight_overlay.js`), der Server wartet `config.DOGFIGHT_DAUER_S`.
- **Hund.** Allein `utils.NODOG` entscheidet (keine zweite Einstellung im Agenten-Paket).
- **Nachrichten.** Statt `agentmessage`: `agent_chat_line` und `agent_chat_end`; `zombie_chat` trägt `readonly: true`.
  Weitere Typen: `agent_slots`, `agent_dogfight`. `agent_event.kind`: `free`, `move`, `error`, `chat`, `pin`, `text`, `exp`.
  `agent_control.action`: `start`, `pause`, `resume`, `step`, `round`, `stop`, `tempo`, `hint`, `save`, `slots`.
- **Zusätzlich gebaut (nicht im Plan):** Zuschauer-Hinweisfeld, Spielstände mit Agentenzustand (siehe Nachtrag Meilenstein 5),
  `Experience.md` (Lernen von Spiel zu Spiel, git-ignoriert), Agent-Icon und Kampf-Overlay, Beamer-Zoom.
