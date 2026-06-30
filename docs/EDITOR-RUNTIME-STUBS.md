# Editor → Adventure: Callback-Stubs übernehmen

Dieser Workflow verbindet den **Terrain World Editor** (`../Adventure-Terrain/`) mit
dem Adventure. Der Editor baut/bearbeitet `data/world.json` und kann für die darin
referenzierten Callbacks Python-Stubs erzeugen. `apply_editor_stubs.py` ermittelt
daraus, welche Funktionen im Spiel noch **fehlen**, und schreibt sie einzeln heraus –
fertig zum Einfügen in die echten Module.

```
Editor  ──Export Runtime──►  world.json + python_stubs.zip
                                   │ entpacken
                                   ▼
                          apply_editor_stubs.py  (nutzt missing_functions.py)
                                   │ Vergleich Stub ↔ echtes Modul
                                   ▼
                          missing_<modul>.py  (nur fehlende Funktionen)
                                   │ Bodies implementieren, einfügen
                                   ▼
                          game_*.py / *_prompts.py  im Adventure
```

## Hintergrund

- Callback-Referenzen stehen in `world.json` als `"modul.funktion"` und werden zur
  Laufzeit von `services/world_loader.py` über die `module_map` in `game_state.py`
  aufgelöst. Die Modulnamen sind **snake_case**:
  `game_apply_functions`, `game_take_functions`, `game_reveal_functions`,
  `game_obstruction_check_functions`, `place_prompts`, `object_prompts`, `way_prompts`.
- Eine Referenz, deren Funktion es nicht gibt, löst **still zu `None`** auf (keine
  Fehlermeldung). Genau diese Lücken findet der Workflow.
- Die Funktionsnamen leiten sich aus den IDs ab:
  `p_x_place_prompt_f`, `o_x_apply_f` / `_take_f` / `_reveal_f` / `_prompt_f`,
  `w_x_prompt_f`, `w_x_obstruction_check`.

## Schritt für Schritt

1. **Welt im Editor bearbeiten.** Orte/Wege/Objekte anlegen, Callbacks per Checkbox
   aktivieren. Der Badge „✓ existiert im Spiel“ / „⚠ noch nicht implementiert“ zeigt
   an, ob eine Funktion schon bekannt ist (Snapshot, siehe unten).

2. **Export Runtime** klicken. Der Browser lädt zwei Dateien:
   - `world.json` – die Welt für das Spiel,
   - `python_stubs.zip` – je eine Stub-Datei pro referenziertem Modul
     (`game_apply_functions.py`, `way_prompts.py`, …) mit **korrekten Signaturen**.

3. **`world.json` übernehmen** (falls gewünscht) nach `data/world.json`.

4. **Stubs entpacken**, z. B.:
   ```bash
   unzip ~/Downloads/python_stubs.zip -d stage_editor
   ```

5. **Fehlende Funktionen ermitteln:**
   ```bash
   python3 apply_editor_stubs.py stage_editor
   ```
   Für jedes Modul mit Lücken entsteht `stage_editor/missing_<modul>.py` mit genau den
   Funktionen, die im Spiel noch fehlen. Module ohne Lücken melden „OK“.

   Optionen:
   - `--game-dir PFAD` – Ordner der echten Module (Default: Skript-Verzeichnis).
   - `--out-dir PFAD`  – Ausgabeordner (Default: `stubdir`).

6. **Implementieren & einfügen.** In den `missing_<modul>.py` die `# TODO`-Bodies
   ausfüllen und die Funktionen in das jeweilige echte Modul kopieren. Bestehende
   Funktionen werden nie angefasst.

7. **Spiel starten** und testen.

## Signaturen pro Modul

Die vom Editor erzeugten Stubs verwenden bereits diese Signaturen:

| Modul | Signatur |
|---|---|
| `game_apply_functions` | `(gs, pl=None, what=None, onwhat=None) -> str` |
| `game_reveal_functions` | `(gs, pl=None, what=None, onwhat=None) -> str` |
| `game_take_functions` | `(gs, pl=None) -> str` |
| `place_prompts` / `object_prompts` | `(gs, pl=None) -> str` |
| `way_prompts` | `(gs, pl, w) -> str` |
| `game_obstruction_check_functions` | `(gs) -> str` |

**Wichtig:** Obstruction-Checks müssen `"Free"` zurückgeben, wenn der Weg frei ist –
ein leerer String `""` wird vom Loader als **blockiert** gewertet. Die Stubs liefern
daher `return "Free"`.

## Hinweise

- `apply_editor_stubs.py` ist ein Wrapper um `missing_functions.py` (gleiche
  AST-basierte Logik: Funktionsnamen in Stub vs. echtem Modul vergleichen, fehlende
  Blöcke ausschneiden). Es nutzt dessen Funktionen direkt.
- Der „existiert im Spiel“-Badge im Editor beruht auf einer **statischen Liste**
  (`callbackRegistry` in `src/lib/callbacks.ts`), die einmalig aus den Adventure-Modulen
  erzeugt wurde. Bei größeren Änderungen im Spiel sollte sie neu generiert werden – die
  verlässliche Quelle für „was fehlt wirklich“ ist dieser Stub-Workflow.
- Modul-Dateinamen des Exports entsprechen exakt den echten Modulen (snake_case), damit
  der Vergleich direkt paarweise funktioniert.
