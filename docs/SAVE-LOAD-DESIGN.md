# Save / Load — Design (Bauplan)

Stand 2026-07-01. Bauplan für die Ganzspiel-Serialisierung. Noch **nicht implementiert**
— dieses Dokument hält die abgestimmten Entscheidungen und die pro-Klasse-Feldlisten
fest, damit die Umsetzung geradlinig läuft. Lehrmaterial → **Klarheit vor Cleverness**.

## 1. Ziel & harte Anforderungen

Ein Spiel vollständig in **eine JSON-Datei** sichern und wiederherstellen.

- **Vollständigkeit:** nicht nur Flags, sondern der komplette Szenen-Graph (Objekte,
  Wege, Orte), alle NPC-Zustände inkl. **episodischem Gedächtnis** und alle **Caches**.
- **!!! Identisches Verhalten & identische Szene:** nach dem Laden muss das Spiel sich
  genau so verhalten und **exakt dieselbe Szenenbeschreibung** zeigen wie im Moment des
  Speicherns — als wäre nie geladen worden. Alles „History"-Relevante muss mit.
- **Generisch:** alles Sicherbare implementiert dasselbe Interface; auch die LLM-Schicht
  (`GeminiInterface`) — so bleibt ein späterer LLM-Austausch möglich, ohne den Loader zu
  ändern.

## 2. Architektur in einem Satz

Jede sicherbare Klasse implementiert das **`Storable`-Protocol** (`save()`/`load()`);
Instanzen registrieren sich per **Decorator** in einer Registry; der **Saver** läuft die
Registry (gegen den lebenden `GameState`-Graphen gefiltert) ab und schreibt eine Liste
selbstbeschreibender **Envelopes**; der **Loader** rekonstruiert in **zwei Phasen**
(erst instanziieren, dann verlinken) und tauscht `session["game"]`.

## 3. Das `Storable`-Interface (`services/interfaces.py`)

Als `Protocol`, passend zu den vorhandenen `LLMClient`/`PlayerDialogs`.

```python
class Storable(Protocol):
    STORE_TYPE: str                      # z.B. "NPCZombieState" (für Envelope + Registry)
    def store_id(self) -> str: ...       # eindeutige ID je type (name / o_*/p_*/w_* / "gamestate")
    def save(self) -> dict: ...          # NUR der data-Teil (Werte, Refs als IDs)
    def load(self, data: dict, ctx: "LoadContext") -> None: ...  # Werte setzen + Refs auflösen
```

- `save()` liefert **nur `data`** (Werte/IDs). Den Envelope (`type`/`id`) baut der Saver
  drumherum — so muss keine Klasse ihren eigenen Typ doppeln.
- `load(data, ctx)` bekommt einen **`LoadContext`** mit den `id→objekt`-Maps
  (`ctx.place(id)`, `ctx.obj(id)`, `ctx.player(id)`), um Referenzen aufzulösen.
- **Referenzen NIE verschachtelt** serialisieren, immer als **ID**. Das macht Zyklen
  (Place↔GameObject, Way↔Place) harmlos und die Traversierung zu einem DAG.

## 4. Registrierung: Decorator + WeakSet + Klassen-Registry

```python
_SAVABLE_INSTANCES: "weakref.WeakSet" = weakref.WeakSet()
TYPE_REGISTRY: dict[str, type] = {}

def savable(cls):
    TYPE_REGISTRY[cls.__name__] = cls          # (1) Klasse -> für den Loader
    orig_init = cls.__init__
    def __init__(self, *a, **kw):
        orig_init(self, *a, **kw)
        _SAVABLE_INSTANCES.add(self)           # (2) Instanz -> "to be saved"
    cls.__init__ = __init__
    cls.STORE_TYPE = cls.__name__
    return cls
```

- `@savable` an jede Klasse → Konstruktoren bleiben unangetastet.
- **WeakSet** löst das „Löschungs-Drift"-Problem: entfernte Objekte (`o_skelett`,
  zerstörte `o_ec_karte`) fallen bei GC automatisch raus.
- **Restrisiko Zyklen** (`Place.place_objects ↔ GameObject.ownedby`) verzögern die
  Freigabe. Deshalb **filtert der Saver zusätzlich gegen den lebenden Graphen**: nur
  Objekte speichern, die noch aus `GameState` erreichbar sind (`gs.objects` / `players` /
  `place_objects` / `inventory`). Decorator = Bequemlichkeit, Live-Graph = Korrektheit.
- **`TYPE_REGISTRY`** statt „raffinierter Reflection": der `type`-String im Envelope
  schlägt hier die Klasse nach (klar, sicher, kein `eval`).

## 5. Dateiformat (Envelope)

```jsonc
{
  "version": 1,                    // Schema-Version (Migration)
  "world_json_version": "…",       // optional: Hash/Version der world.json beim Speichern
  "objects": [                     // Liste von Envelopes
    { "type": "GameState",       "id": "gamestate", "data": { … } },
    { "type": "PlayerState",     "id": "Chris",     "data": { … } },
    { "type": "NPCZombieState",  "id": "Zombie",    "data": { … } },
    { "type": "GameObject",      "id": "o_ec_karte","data": { … } },
    { "type": "Way",             "id": "w_ubahn2_kontrollraum", "data": { … } },
    { "type": "GeminiInterface", "id": "llm",       "data": { … } }
  ]
}
```

## 6. Ablauf — Save

1. `version` (+ optional world.json-Hash) setzen.
2. Kandidaten = `_SAVABLE_INSTANCES` **∩ erreichbar aus GameState** (Live-Filter).
3. Je Kandidat: `{type: obj.STORE_TYPE, id: obj.store_id(), data: obj.save()}`.
4. Als eine JSON-Datei schreiben. **Zeitpunkt:** an einer sauberen Rundengrenze
   (Web-`cmd_q`/`pending_llm_input` leer, nicht mitten in einer Chat-/Befehlskette).

## 7. Ablauf — Load (zwei Phasen!)

1. Datei lesen, `version` prüfen (ggf. migrieren).
2. **Basis bauen:** einen **frischen `GameState`** anlegen (nutzt `WorldLoader`, damit
   **Callables & statische Struktur** aus `world.json` vorhanden sind — Callables werden
   nie serialisiert, sie sind Code).
3. **Phase 1 — Instanziieren:** je Envelope die Klasse aus `TYPE_REGISTRY`, Instanz per
   `store_id` anlegen (bzw. die aus der Basis vorhandene nehmen) und in die `ctx`-Maps
   eintragen. **Noch keine Referenzen setzen.**
4. **Phase 2 — Laden & Verlinken:** je Envelope `obj.load(data, ctx)`. Jedes Objekt
   setzt seine Werte **und löst seine Referenzen** über `ctx` auf (location, ownedby,
   inventory, ways, source/destination, `way_home`/`next_loc`).
5. Flags/`time`, `narration_cache`, `way.visible` etc. sind in den jeweiligen `data`
   enthalten und damit gesetzt. Objekt-Set angleichen (im Save fehlende Objekte
   entfernen, zusätzliche — z.B. der zur Laufzeit erzeugte Zombie — anlegen).
6. `session["game"] = neuer GameState` (Referenz tauschen — kein „in-place löschen").

## 8. Referenztypen & Nicht-JSON-Werte (Konvention)

| Typ | Serialisierung | Beispiel |
|---|---|---|
| Referenz auf Place/GameObject/Player | **ID-String** (`p_*`/`o_*`/name) | `location`, `ownedby`, `inventory` |
| Enum | **`.name`** (String), Restore per `Enum[name]` | `zombie_state`, `dog_state` |
| Deque | **Liste** (von IDs, wenn Inhalt Refs sind) | `way_home`, `next_loc` (Deque[Place]) |
| Callable (`apply_f`, `obstruction_check`, `*_prompt_f`) | **nicht serialisieren** — kommt aus `WorldLoader`/Klasse | — |
| Live-Ressourcen (LLM-Client) | **nicht serialisieren** — bleibt live | `GeminiInterface.client` |

## 9. `GeminiInterface` implementiert `Storable`

Der Clou für die !!!-Anforderung. Die **Szenenbeschreibungen leben als Cache am
`GeminiInterface`** — nicht das LLM-Objekt speichern, aber seine **Caches** müssen mit.

- `save()` → `{ "narration_cache": self.narration_cache.cache,
  "txt_prev_description": self.txt_prev_description }`. **Nicht** enthalten: `client`
  (Live-SDK-Objekt mit Credentials), Modell-IDs (Config), Token-Stats (`tokens`,
  `numcalls`, `token_details` — spielirrelevant).
- `load(data, ctx)` → `self.narration_cache.cache = data["narration_cache"]`,
  `self.txt_prev_description = data["txt_prev_description"]`. **`self.client` bleibt
  unangetastet** (beim Konstruieren aus dem API-Key gebaut).
- `GameState.save()` ruft `gs.llm.save()` rekursiv auf (DAG, kein Zirkel).
- **Effekt:** `narrate()` findet nach dem Laden den Cache-Treffer → gibt **exakt den
  gespeicherten Text** zurück, statt neu (stochastisch) zu generieren.

### Wichtige Folgerung — der Cache-Key erzwingt Vollständigkeit
`narration_cache.get(room, base_prompt)` trifft nur, wenn der `base_prompt` nach dem
Laden **identisch** ist. Der base_prompt entsteht aus Ortsprompt (Flags!), Objekten,
Inventar … → **fehlt ein zustandsrelevanter Wert, weicht der base_prompt ab → Cache-Miss
→ Neugenerierung → anderer Text.** Damit ist die !!!-Regel zugleich ein eingebauter
**Vollständigkeitstest**: trifft der Cache nach dem Laden, ist der Save komplett.

## 10. Pro-Klasse: was in `data` gehört

**Grundsatz:** Callables und rein statische, aus `world.json` ableitbare Struktur werden
**nicht** gespeichert (kommen aus `WorldLoader`); gespeichert wird der **dynamische /
zur Laufzeit veränderte** Zustand + Identität + Referenzen (als IDs).

### GameState (+ WorldModel/GameFlags)
- **Alle `GameFlags`** (Werte): `schuppentuer, leiter, hebel, geheimzahl(str), felsen,
  hauptschalter, dach, warenautomat_intakt, geldautomat_intakt, schuppen_intakt,
  flasche_voll, falltuer_offen, werbeplakat_offen, korridor_offen, kontrollraum_offen,
  game_over, game_won, **time**, debug_mode, zombie_awake, zombie_cooperative,
  schalter_kontrollraum(+_timer), schalter_generatorraum(+_timer),
  umschlag_geheimbotschaft, …` (die ganze Dataclass).
- **Objekt-Set & Spieler-Set** als Listen von IDs (welche Objekte/Spieler es *aktuell*
  gibt — dynamisch!). Die Einzelobjekte kommen als eigene Envelopes.
- Verweist der Loader auf `WorldLoader` für die statische Struktur, muss GameState
  zusätzlich die **Abweichungen** kennen (entfernte/zusätzliche Objekte).

### PlayerState (Mensch)
`name(id)`, `location`(place-id), `inventory`([obj-ids]), `thirst_counter`,
`pending_llm_input`. *Nicht:* `systest` (Debug-Helfer), `cmd_q` (leer an Rundengrenze).

### NPCZombieState (erbt PlayerState) — **inkl. Gedächtnis!**
`zombie_state`(**Enum→name**), `notes` (**Notizbuch**), `last_chat` (**episodisch**),
`trust`, `zombie_thirst`, `turns_since_player_contact`, `move_cooldown`, `turn_counter`,
`cooperation_agreed`, `awaiting_share_response`, `share_agreed`, `share_cooldown`,
`remembered_control_room`, `gameengine_returns`, `player_last_seen_location`,
`nogo_places`, + geerbte Felder (`location`, `inventory`, …).

### NPCDogState (erbt PlayerState) — **inkl. Gedächtnis!**
`dog_state`(**Enum→name**), `dog_state_message`, `last_chat`, `growl`, `attack_counter`,
`next_loc_wait`, `command_after_fight`, `nogo_places`, **`way_home`/`next_loc`
(Deque[Place] → Liste von place-ids!)**, + geerbte Felder.

### ExplosionState (falls aktiv)
`kaboom_timer`, `location`. (Nur relevant, wenn beim Speichern eine Explosion läuft.)

### GameObject
`name(id)`, **`examine`** (kann sich ändern, z.B. `o_umschlag` nach Tinktur!), `hidden`,
`ownedby`(**id** von Place/Player/None), `fixed`. *Nicht:* `apply_f/reveal_f/take_f/
prompt_f/callnames/help_text` (statisch, aus `world.json`).

### Way
Nur der dynamische Teil: `name(id)`, **`visible`**. Rest (source/destination/obstruction_
check/prompt) statisch aus `world.json`.

### Place
Praktisch statisch. `place_objects` **nicht separat speichern** — beim Laden aus den
`ownedby`-Referenzen der Objekte **neu aufbauen** (eine autoritative Quelle für „wo ist
ein Objekt", sonst drohen inkonsistente Saves).

### GeminiInterface
Siehe §9: `narration_cache.cache`, `txt_prev_description`. Sonst nichts.

## 11. Was NICHT gespeichert wird
- LLM-`client`, Modell-IDs, Token-Statistik.
- Callables (Code, kommen aus `WorldLoader`/Klasse).
- „Letzte Aktion"-Transkript (lebt im Browser/JS, kein Engine-Zustand → nach dem Laden
  leer; Verhalten & Szene sind trotzdem korrekt). Optional separat sicherbar, extra
  Aufwand.
- Web-Session-Zwischenzustand (`cmd_q`, `pending_llm_input`) — an Rundengrenze leer.

## 12. Test (wichtig — keine Testsuite vorhanden)
- **Round-trip-Idempotenz:** `save → load → save`, beide JSONs vergleichen.
- **Szenen-Treffer:** nach `load` muss `narrate()` den **Cache** treffen (kein
  Neugenerieren) — direkter Beweis, dass der Save vollständig ist (§9).
- Ein realistischer Spielstand (Zombie erwacht, Stahltür offen, Wagen verschoben,
  Schalter aktiv) sichern/laden und Verhalten vergleichen.

## 13. Web-Integration
- Speichern/Laden anstoßen über den **`PlayerDialogs`-Port** (Save-Slot-Dialog analog
  pinpad/chat). Der **Kern (Saver/Loader) nimmt nur einen Pfad/Stream** → entkoppelt &
  testbar; „Dateiname interaktiv" ist reine GUI-Sache.
- Nach `load`: `session["game"]` tauschen und ein frisches `game_state` an die GUI
  senden (die dann die (gecachte) Szenenbeschreibung zeigt).

## 14. Offene Entscheidungen
- **Self-contained vs. Overlay:** Callables erzwingen, dass `WorldLoader` beim Laden die
  Struktur baut (Overlay-Ansatz). Empfehlung: Save ist inhaltlich vollständig
  (self-descriptive), beim Laden aber via `WorldLoader` + `resolve_func_from_string`
  rekonstruiert; `world_json_version` prüfen, um Drift zu erkennen.
- **Save-Slots / Dateinamen-Schema.**
- **Speichern nur an Rundengrenzen erzwingen** (Guard) vs. best effort.

## 15. Reihenfolge der Umsetzung (Vorschlag)
1. `Storable`-Protocol + `@savable`-Decorator + `TYPE_REGISTRY` + `LoadContext`.
2. Refactor `GeminiInterface`: `save()`/`load()` (nur die zwei Caches).
3. `Way`/`GameObject`/`PlayerState` save/load (die einfachen).
4. `NPCZombieState`/`NPCDogState` save/load (Enums, Deques, Gedächtnis).
5. `GameState.save()`/`load()` (Orchestrierung, Objekt-/Spieler-Set, Verlinkung).
6. Saver/Loader-Modul (`services/save_load.py`) + Round-trip-Test.
7. Web-Anbindung (Dialog + `session["game"]`-Tausch).
