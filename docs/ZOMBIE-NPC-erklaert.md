# Der Zombie-NPC — wie er funktioniert (Erklärung)

Lehrmaterial-Dokument zum **Zombie**, dem zentralen KI-Charakter des Spiels. Der
Zombie wurde ursprünglich **autonom von Claude Code** geschrieben und ist
**LLM-gesteuert**. Alle Verweise zeigen auf `npc_zombie_state.py` (Stand 2026-06-29;
im Zweifel nach den Methodennamen suchen, nicht nach Zeilennummern).

> **Design-Intention (die Leitfrage des Kurses):** Kann ein LLM intelligente
> Spielentscheidungen treffen? Kann es eine Figur steuern, die lernt, eigene
> Entscheidungen trifft und erkennt, dass das Spiel nur in **Kooperation** mit dem
> Spieler lösbar ist? Und dabei eine gute, unterhaltsame Spielfigur sein?
> (siehe `docs/GAMEPLAY-2026-06-27.md`)

> **Hinweis (2026-06-29):** Der Zombie wurde stark **erweitert**, um den Bogen
> dynamischer und das „nur gemeinsam lösbar" weniger binär zu machen. Diese Erklärung
> beschreibt den **neuen** Stand; die frühere Version flippte über **eine** binäre
> Chat-Bewertung von HUNTING direkt nach COOPERATING und lief dann scriptbasiert ab.

---

## 1. Großes Bild: Was für ein Agent ist der Zombie?

Ein **LLM-gesteuerter NPC mit Zustandsautomat + Gedächtnis + Vertrauens-/Energie-Werten**.
Die Bausteine greifen ineinander:

1. **Endlicher Automat** (`ZombieState`) — die groben Phasen.
2. **Pro-Zug-Reasoning** über ein LLM — das „Notizbuch-Pattern" (nur in der Jagd).
3. **Dialog** mit eigenem Gedächtnis und einem **mehrstufigen Bewertungs-Gate**.
4. **Skript-Mechaniken** für Vertrauen (graduell) und Lebensenergie (Tod/Teilen).

Zwei getrennte LLM-Nutzungen mit unterschiedlichen Modellen:

| Zweck | Methode | Modell |
|---|---|---|
| Entscheidung „was tue ich diesen Zug?" (HUNTING/COOPERATIVE/DOUBTING) | `_call_reasoning_llm` | Reasoning-Modell des aktiven Backends |
| Gespräch + Bewertung (`chat` / `end_chat`) | `llm.simple_message` | Text-Modell des aktiven Backends |

→ **Schweres Modell zum Denken, leichtes zum Plaudern.** Die *rein* skriptbasierten
Zustände sind CONVINCED/REDEEMED/PETRIFIED sowie der Handbuch-Quest-Vorrang; die aktiven
Zustände HUNTING/COOPERATIVE/DOUBTING entscheiden pro Zug per Reasoning-LLM.

**Backend-agnostisch** (2026-07-10): `_call_reasoning_llm` war früher fest auf Gemini
verdrahtet (`from google import genai` + `gs.llm._impl.client…`). Unter dem lokalen
Gemma-Backend (`LLM_BACKEND="gemma"`) warf das eine Exception → jeder Zug wurde „nichts";
in HUNTING verdeckte das der Verfolgungs-Fallback, in COOPERATIVE **fror der Zombie ein**.
Jetzt delegiert der Zombie an `gs.llm._impl._call_reasoning_llm` — sowohl `GeminiInterface`
als auch `GemmaInterface` haben diese Methode, der NPC-Code ist damit LLM-unabhängig. Dazu
ein **Folge-dem-Spieler-Nudge** für COOPERATIVE/DOUBTING (empfohlene Richtung zustandsabhängig
gerahmt), damit ein kooperativer Zombie dem Spieler folgt statt passiv stehenzubleiben.

Der NPC erbt von `PlayerState` und stellt `NPC_game_move(gs)` bereit, das die Engine
einmal pro Spielrunde aufruft (`GameState.run_npc_turns`, vom Web-Layer getrieben).

---

## 2. Der Zustandsautomat (`ZombieState`)

```
AWAKENING ──► HUNTING ──Chat: Spieler überzeugt──► COOPERATIVE
                 ▲                                     │  (Vertrauen erodiert: kein
                 │                                     ▼   Kontakt / Feindseligkeit)
                 └───── Vertrauen am Boden ◄──── DOUBTING
                 ▲  (Angriff / sehr feindseliger Chat = sofort)   │ (Kontakt baut auf)
                 │                                                 └──► zurück COOPERATIVE
   jeder aktive Zustand {HUNTING, COOPERATIVE, DOUBTING}
        │
        ├─ liest die Anleitung (Erinnerungs-Route ODER Spieler liest sie ihm vor) ──► CONVINCED
        │                                                                               │
        │                          CONVINCED: verfolgt den Spieler, Dialog zum Überzeugen
        │                          Spieler stimmt zu ──► zwei Schalter (Script) ──► REDEEMED
        │
        └─ Lebensenergie auf 0 ──► PETRIFIED  (EC-Karte zerstört → Spiel verloren)
```

- **AWAKENING** → wechselt sofort zu HUNTING **und** eröffnet das Chat-Modal.
- **HUNTING** → `_do_hunting_move` (der LLM-Kern, Biss).
- **COOPERATIVE / DOUBTING** → `_do_trusting_move` (scriptgesteuert, kein Biss, Vertrauens-Zerfall).
- **CONVINCED** → `_do_convinced_move` (erst Spieler überzeugen, dann Schalter-Endspiel).
- **REDEEMED** / **PETRIFIED** → Endzustände (tun nichts mehr).

🔎 **Lehrbeobachtung:** Im Vergleich zur Erstfassung wurden die **toten Zustände**
DORMANT/STALKING **entfernt** und drei neue eingeführt (COOPERATIVE, DOUBTING,
CONVINCED, PETRIFIED). Der Automat modelliert jetzt nur noch tatsächlich durchlaufene
Zustände — gutes Beispiel dafür, dass man Automaten „ehrlich" hält.

---

## 3. Frage 1 — Intelligente Entscheidungen: das „Notizbuch-Pattern"

Kern bleibt `_do_hunting_move` (nur im Zustand HUNTING):

1. **Biss zuerst** (fest verdrahtet, kein LLM): steht der Spieler am selben Ort →
   beißen (−5 Lebensenergie des Spielers), `zombie_bite`-Action → dramatisches Popup.
2. **Cooldown**: der Zombie handelt nur jeden zweiten Zug (`move_cooldown`).
3. **LLM-Entscheidung**: `compile_zombie_context` → `compile_zombie_prompt`
   (inkl. `self.notes` und letzter Engine-Antwort) → das LLM antwortet strukturiert
   (`<AKTION>…</AKTION><NOTIZBUCH>…</NOTIZBUCH>`); `parse_llm_response` /
   `_action_to_command` übersetzen das in Engine-JSON. Das **Notizbuch wird jeden Zug
   überschrieben** — Scratchpad-/Notebook-Agent-Pattern, Tool-Use per Tag-Konvention
   statt Function-Calling-API.

**Antwort:** Ja — innerhalb eines kleinen Aktionsraums. Die „Intelligenz" der Jagd
steckt in Prompt + Notizbuch.

---

## 4. Frage 2 — Lernen, eigene Entscheidungen, Kooperation erkennen

Der Bogen ist jetzt **mehrschichtig** statt eines einzelnen Umschwungs.

### Zwei Gedächtnisebenen
- **`notes`** — Arbeits-/Strategiegedächtnis, Zug für Zug aktualisiert (Reasoning-Loop).
- **`last_chat`** — **episodisches** Gedächtnis über Gespräche hinweg (`end_chat`).

### Vertrauen als gradueller Wert (statt binär)
- `trust` (0–100) mit benannten Schwellen (`COOP_START_TRUST`, `DOUBT_BELOW`,
  `HUNT_BELOW`) — bewusst als Konstanten zum Balancing.
- **Aufbau:** ein glaubhaftes, sinnvolles **und nicht feindseliges** Angebot im Chat
  macht HUNTING → COOPERATIVE (`trust = COOP_START_TRUST`).
- **Zerfall:** im Zustand COOPERATIVE/DOUBTING sinkt `trust` Zug für Zug, wenn der
  Spieler **nicht da** ist (`_do_trusting_move` / `_state_from_trust`); ist er da,
  erholt es sich etwas. Unter den Schwellen: COOPERATIVE → DOUBTING → zurück zu HUNTING.
- **Brüche:** ein **feindseliges Gespräch** (`FEINDLICH:JA`) kostet viel Vertrauen;
  ein **Angriff** (`verb_attack` → `gets_attacked`) setzt es sofort auf 0 → HUNTING.
  Ausnahme: **CONVINCED** ist „klebrig" und übersteht einen Angriff.

### Die Anleitung ist der Lösungs-Schlüssel
- **COOPERATIVE** heißt nur: *er vertraut dir* (beißt nicht mehr), **hält aber die
  EC-Karte**. Die eigentliche Lösung (zwei Schalter, synchron) kennt er erst, wenn er
  das **Betriebshandbuch** (`o_manual`, im Kontrollraum) gelesen hat → **CONVINCED**.
- **Zwei Wege zu CONVINCED:**
  1. **Erinnerungs-Route (der Zombie selbst):** betritt er auf seinen Wanderungen die
     **U-Bahn**, erinnert sich Harald Kronstein an den Kontrollraum
     (`remembered_control_room`), läuft per Pfadsuche dorthin und liest die Anleitung
     (`_handle_manual_quest` → `_become_convinced`). Das kann aus **jedem** aktiven
     Zustand passieren — sogar mitten in der Jagd.
  2. **Spieler liefert:** liest der Spieler die Anleitung neben einem **zutraulichen**
     Zombie vor (`o_manual_apply_f`), liest dieser mit → CONVINCED.

### CONVINCED: die Rollen drehen sich um
Jetzt will **er** kooperieren und muss **den Spieler** überzeugen
(`_do_convinced_move`): er verfolgt den Spieler, öffnet bei Begegnung den Dialog und
bittet um Mithilfe. Stimmt der Spieler zu (`EINVERSTANDEN:JA` in `end_chat` →
`cooperation_agreed`), läuft das **Schalter-Endspiel** (`_do_switch_sequence`): zum
Generatorraum, Schalter umlegen; synchron mit dem Spieler-Schalter → `zombie_cooperative`
→ `_do_redemption` → REDEEMED, **EC-Karte fällt**.

### Das Bewertungs-Gate ist jetzt mehrstufig
`end_chat` ruft einen **Richter-LLM-Aufruf**, der **kontextabhängig** bewertet:
`KOOPERATIV` / `SINNVOLL` / `FEINDLICH` immer, dazu `EINVERSTANDEN` (nur im
CONVINCED-Dialog) und `TEILEN` (nur wenn der Zombie um Energie gebeten hat). Der Zombie
wertet jeweils nur die zur Lage passenden Felder aus.

**Antwort:** „Lernt/erinnert sich" — ja, innerhalb einer Partie (zwei Gedächtnisse,
plus Vertrauens-/Energiewerte). „Erkennt Kooperation" — über ein **graduelles**
Vertrauens-Gate **und** eine echte In-Fiction-Erkenntnis (das Lesen der Anleitung),
nicht mehr nur über einen einzelnen binären Judge.

---

## 5. Lebensenergie, Tod und Teilen (neu)

Das frühere `zombie_thirst` ist jetzt die **Lebensenergie** des Zombies (Feldname
beibehalten). Sie sinkt in **jedem** aktiven Zustand um 1 pro Zug (zentral in
`NPC_game_move`):

- **Niedrig** (`≤ LOW_ENERGY`): der Zombie **bittet selbst** im Dialog um geteilte
  Energie (`_ask_for_energy`, `awaiting_share_response`). Sagt der Spieler zu
  (`TEILEN:JA` → `share_agreed`), überträgt `_receive_shared_energy` etwas Energie
  **vom Spieler** (Kosten!) auf den Zombie.
- **Null:** `_do_petrify` → Zustand PETRIFIED, **EC-Karte wird zerstört**, `game_over`
  gesetzt → **Spiel verloren** (ohne Karte nicht mehr lösbar).

So entsteht ein echtes Dilemma: ignoriert man den Zombie zu lange, stirbt er und nimmt
die Lösung mit.

---

## 6. Frage 3 — Gute, unterhaltsame Spielfigur?

- Starke **Persona**: ehemaliger Geschäftsmann **Harald Kronstein**, gebrochenes
  Deutsch, „Grrr…", Geschäftsbegriffe blitzen durch.
- **Zustandsabhängige Präsenz-Beschreibung** (`zombie_prompt`) für die Szenen-Narration.
- Dramatik & Bogen: Erwachen, Biss, Erinnerung, Erkenntnis, Erlösung **oder** Erstarren.

**Antwort:** Ja — die Figur hat Charakter und einen verzweigten Bogen (bedrohlich →
überzeugbar → erkennend → erlöst *oder* tot).

---

## 7. Sichtbarkeit der Zombie-Ereignisse (`zombie_event`)

Damit die Story-Momente beim Spieler ankommen, gibt es eine eigene Aktionsart:

- **`zombie_bite`** → dramatisches Biss-Popup (`bite_overlay.js`).
- **`zombie_event`** → sichtbare Zeile in „Letzte Aktion" (Erinnerung, Erkenntnis,
  Erlösung, Erstarren, geteilte Energie).
- **`zombie_message`** → nur Debug (Status), nicht für den Spieler.
- Dialoge laufen über das **Chat-Modal** (`interaktion` → `do_chat`).

Diese Typen müssen an drei Stellen konsistent sein: erzeugt in `npc_zombie_state.py`
(`json_cmd_simple(...)`), durchgereicht in `game_turn.run_npc_turns` **ohne Typverlust**,
als Token in `utils.game_known_tokens` registriert, weitergeleitet in
`command_engine` und gerendert in `web/websockets.js`. (Genau diese Kette war zuvor für
`zombie_bite` unterbrochen — der Biss kam nicht durch.)

---

## 8. Ablauf einer typischen „Erfolgs"-Partie

1. Spieler nimmt die Geldbörse → `game_take_functions._awaken_zombie` erschafft den
   Zombie (AWAKENING), gibt ihm die EC-Karte.
2. AWAKENING → HUNTING, **Chat-Modal** öffnet sich; in der Jagd entscheidet das LLM,
   am selben Ort **beißt** er.
3. Spieler **überzeugt** ihn im Chat (kein Feindbild) → COOPERATIVE; bleibt der Spieler
   weg oder wird feindselig → DOUBTING → ggf. zurück zu HUNTING.
4. Der Zombie **findet die Anleitung** (U-Bahn-Erinnerung → Kontrollraum) **oder** der
   Spieler liest sie ihm vor → **CONVINCED**.
5. CONVINCED: der Zombie **verfolgt** den Spieler und bittet im Dialog um Mithilfe;
   sagt der Spieler zu → **zwei Schalter synchron** → **REDEEMED**, Karte fällt.
6. Nebenstrang: sinkt seine Lebensenergie zu tief, **bittet er um Energie**; teilt der
   Spieler nicht, **erstarrt** er → Karte zerstört → verloren.

---

## 9. Patterns, die sich gut für den Unterricht eignen

- **Notebook-/Scratchpad-Agent** (selbst aktualisiertes Gedächtnis im Prompt).
- **Strukturierte Ausgabe ohne Tool-API** (`<AKTION>`/`<NOTIZBUCH>` + Regex).
- **Zwei-Ebenen-Gedächtnis** (Arbeits- vs. episodisches Gedächtnis).
- **Kontextabhängiges Judge-Pattern** (KOOPERATIV/SINNVOLL/FEINDLICH/EINVERSTANDEN/TEILEN).
- **Hybrid LLM + Skript**: LLM für Jagd & Gespräch, deterministische Skript-Mechanik
  für Vertrauen, Pfadsuche und Endspiel — bewusste Trennung von „teuer/kreativ" und
  „günstig/vorhersehbar".
- **Benannte Stellschrauben** (Schwellen-Konstanten) statt Magic Numbers.
- **Modellwahl nach Aufgabe** (Reasoning- vs. Text-Modell).
- **Prompt-Injection-Härtung** in der Persona (`chat`).

## 10. Schwachstellen / Diskussionspunkte (bewusst offen, gut für den Kurs)

- Der Reasoning-Prompt bietet auch Aktionen an (nimm/anwenden/untersuche), die in der
  Jagd selten sinnvoll sind → das LLM könnte „komische" Aktionen wählen.
- **Token-Kosten**: Reasoning-Call (~jeden 2. Zug in den aktiven Zuständen) + Chat-Call je
  Nachricht + `end_chat`. Die Endzustände (CONVINCED/REDEEMED/PETRIFIED) sparen den LLM-Call.
- Direkter Zugriff `gs.llm._impl` (statt über den Adapter) — die Kopplung ist inzwischen aber
  backend-**neutral**: `_call_reasoning_llm` existiert auf beiden Impls (`GeminiInterface`/
  `GemmaInterface`), der Zombie läuft also mit Gemini wie mit lokalem Gemma. Sauberer wäre,
  `_call_reasoning_llm` auch auf dem `LLMClient`-Adapter zu exponieren (Backlog).
- Die **Übergabe-Route** der Anleitung ist pragmatisch („neben dem Zombie lesen");
  ein eigener `gib <Objekt> an <NPC>`-Befehl wäre sauberer (Backlog).
- Vertrauens-/Energie-Schwellen sind nur grob abgestimmt — Balancing-Aufgabe.

## 11. Zentrale Stellen im Code (`npc_zombie_state.py`)

- `NPC_game_move` — Dispatcher: Energie-Tick, Teilen/Erstarren/Bitten, Erinnerungs-Quest,
  dann Zustands-Switch.
- `_do_hunting_move` — Biss, Cooldown, LLM-Entscheidung (Notizbuch-Loop).
- `_do_trusting_move` / `_state_from_trust` — Vertrauens-Zerfall, COOPERATIVE/DOUBTING/HUNTING.
- `gets_attacked` — Angriff bricht Vertrauen (CONVINCED bleibt bestehen).
- `_handle_manual_quest` / `_become_convinced` — Erinnerungs-Route zur Anleitung → CONVINCED.
- `_do_convinced_move` / `_do_switch_sequence` / `_do_redemption` — Spieler überzeugen,
  dann Schalter-Endspiel und Erlösung.
- `_ask_for_energy` / `_receive_shared_energy` / `_do_petrify` — Lebensenergie-Mechanik.
- `compile_zombie_context` / `compile_zombie_prompt` — Kontext + Reasoning-Prompt.
- `parse_llm_response` / `_action_to_command` — strukturierte Ausgabe → Engine-Befehl.
- `chat` — In-Character-Antwort (Text-Modell) + Injection-Schutz.
- `end_chat` — kontextabhängiger Richter + episodisches Gedächtnis + Übergänge.
- `zombie_prompt` — Präsenz-Text für die Szenen-Narration des Spielers.

Außerhalb dieser Datei:
- Erwachen: `game_take_functions._awaken_zombie`.
- Anleitung: `game_apply_functions.o_manual_apply_f` (+ `object_prompts.o_manual_prompt_f`,
  `data/world.json` `o_manual` im `p_kontrollraum`).
- Angriff: `game_verbs.verb_attack` (findet Hund **oder** Zombie).
- Sichtbarkeit/Game-Over: `game_turn.run_npc_turns`, `utils.json_cmd_simple`,
  `webserver/command_engine.py`, `web/websockets.js`, `web/text_popup.js`.
