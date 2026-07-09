# Prompt-Optimierung — Plan & Design

*Branch: `Adventure-10-2026-07-08-Prompts` · Stand: 2026-07-08*

Ziel dieses (Unter-)Projekts: den **Token-Verbrauch** der LLM-Aufrufe deutlich senken,
**ohne die Ausgabequalität** zu verschlechtern, und so, dass die Lösungen einen späteren
**Modell-/Anbieterwechsel** überstehen. Dies ist ein *Plan*-Dokument — Referenzpunkt für die
schrittweise Umsetzung; es wird bei Fortschritt aktualisiert.

## 1. Leitplanken (nicht verhandelbar)

1. **Qualität ist heilig.** Die `enum`s im Parser-Tool-Schema, die `compile_*`/ContextBuilder-
   Funktionen und die strukturierte `narrate`-Eingabe sind **qualitätstragend**: ohne sie
   liefert das LLM ungültige IDs (von der Engine abgewiesen) und inkonsistente Erzählung
   (z. B. Warenautomat mal glänzend-modern, mal verrostet; Hund in Szenen hineinfantasiert,
   wo er gar nicht ist). Optimiert wird die **Token-Kosten desselben Inhalts**, nicht der
   Inhalt. Alles, was Qualität gefährden könnte, wird strikt **A/B getestet** (Tokens *und*
   Ausgabequalität).
2. **Provider-agnostisch.** Keine Lösung, die *nur* auf Gemini-spezifischen Features (z. B.
   dessen Caching-API) beruht. Nahtstelle ist die bereits vorhandene **`LLMClient`-Abstraktion**
   (`services/interfaces.py` + `services/adapters.py`). Anbieter-spezifische Optimierungen
   leben hinter diesem Interface; Anbieter, die ein Feature nicht können, fallen weich zurück.
3. **Alles messen.** Instrumentierung (`GeminiInterface._log_prompt_sections`, Debug-Level
   `dl.LLM_TOKENS`) + `tokenstats`-Kommando. Jeder Hebel wird über ein **fixes
   Skript-Playthrough** vorher/nachher verglichen.

## 2. Baseline (Messung 2026-07-08)

Anteil am Gesamt-Tokenverbrauch einer (Teil-)Session (`tokenstats`):

| Quelle | Anteil |
|---|---:|
| `parse_user_input_to_commands` | **~74 %** |
| `narrate` | ~17 % |
| Zombie-Reasoning / Chats / Dog-Chats | ~9 % (zusammen) |

Innerhalb des **Parser-Prompts** (`_log_prompt_sections`, stabil über viele Calls,
~4.450 Input-Tokens/Call):

| Abschnitt | ~Anteil |
|---|---:|
| **Tools-Schema** (13 FunctionDeclarations, `enum`s) | **~58 %** |
| **Instruktionen + Beispiele** (fixer Block) | **~30 %** |
| kompilierter Kontext (`narration_details`) | ~12 % |

**Messvorbehalt:** der Tools-Anteil basiert auf `str(configured_tools)` (verboses Python-Repr)
und ist evtl. um ~20–40 % überzeichnet; an der Rangfolge ändert das nichts.

### Wichtige Erkenntnis
Der pro Eingabe wiederholt gesendete **fixe Overhead (Tools-Schema + Instruktionen ≈ 88 %)**
ist der Elefant — **nicht** der kompilierte Kontext (im Parser nur ~12 %). Die
`compile_*`-Funktionen/Prompts sind ihr größter Kostenfaktor bei **`narrate`**, nicht beim
Parsen. Struktur des Parser-Prompts, der bei **jeder** Eingabe komplett gesendet wird:
generelles Setting/Aufgabe → kompilierte Umgebungsinfos → Zerlegungs-Anweisung →
vollständige Tool-Beschreibungen mit Beispielen für **alle** Tools → dann, klein, die
User-Eingabe.

## 3. Hebel-Katalog

Legende: **Wirkung** / **Risiko** / **provider-agnostisch?**

### Gruppe A — Wiederholung eliminieren (strukturell)
- **A1 — Fixen Prefix cachen.** Setting + Instruktionen + Tool-Beschreibungen einmal voll
  bezahlen, danach zu Cache-Preisen wiederverwenden. Alle großen Anbieter können das (Gemini
  `caches`, Anthropic `cache_control`, OpenAI implizit), aber via **unterschiedlicher APIs**
  → als optionale „cache stable prefix"-Fähigkeit im `LLMClient`-Interface kapseln.
  *Wirkung: sehr hoch · Risiko: mittel (Integration) · Qualität: null Änderung · agnostisch: ja
  (auf Interface-Ebene).*

### Gruppe B — Fixen Overhead verkleinern (qualitätsneutral, provider-agnostisch)
- **B1 — Instruktions-/Beispielblock straffen** (~30 %). Regeln behalten, Redundanz raus;
  Inline-Beispiele reduzieren (Semantik steckt bereits in den Tool-`description`s).
  *Wirkung: mittel · Risiko: niedrig.*
- **B1b — Prompt-Reordering.** Fixes nach vorn, Variables (Kontext + User-Eingabe) ans Ende →
  ermöglicht Prefix-Caching und macht klar, was cachebar ist. *Wirkung: (Voraussetzung für A1)
  · Risiko: niedrig · Qualität: null Änderung.*
- **B2 — Tool-Schema verschlanken** (~58 %). Beschreibungen kürzen; prüfen, ob wirklich alle
  13 Tools in jedem Call nötig sind (selten genutzte situativ weglassen). **`enum`s bleiben.**
  *Wirkung: hoch · Risiko: niedrig–mittel (A/B).*

### Gruppe D — Architektur/Modell
- **D1** — Parsen läuft bereits auf dem günstigsten Modell (`gemini-2.5-flash-lite`). Bei
  Austauschbarkeit: pro Aufgabe das billigste fähige Modell wählen — Entscheidung hinter dem
  `LLMClient`-Interface.

## 4. Umsetzungs-Reihenfolge & Fortschritt

- [x] **B1 + B1b — ERLEDIGT (Token-Win).** Instruktions-/Beispielblock entrümpelt (nur Dedup +
  Formatierung, kein Beispiel inhaltlich entfernt) und fix/variabel getrennt (fixer Prefix vorn,
  Kontext + User-Eingabe hinten). Gemessen (kontrolliert, gleiche Räume): `instruktionen+bsp`
  ~8.410 → ~4.470 Zeichen (−47 %); Parse Ø/Call **4.613 → 3.823 tok (−17 %)**; `narrate` unverändert
  (Kontrolle); null Fehlparses. Commit `f33428f`.
- [x] **B2 — ERLEDIGT (Quality, ~token-neutral).** `enum`-Scoping pro Verb: `nimm` nur Objekte am
  Ort (`available_object_ids_here`), `ablegen` nur Inventar (`player_inventory_ids`); Fallback auf
  die volle Liste bei leerer Teil-Liste. Ergebnis: **weniger ungültige Tool-Calls** (subjektiv
  „viel weniger Fehler"), Token-Effekt aber **vernachlässigbar (~−0,5 % Tools-Schema)** — das Schema
  ist fast nur qualitätstragende, *fixe* Struktur.
- [x] **A1 — GEMESSEN & (vorerst) GESTOPPT.** Implizites Caching ist bei Gemini 2.5
  standardmäßig an; `_log_tokens`/`token_report`/`tokenstats` messen jetzt die gecachten Tokens
  (`cached_content_token_count`, Commit `da88681`). Befund (Playthrough): **nur 3/34 Parse-Calls
  mit Cache-Hit**, dann aber je ~80 % des Calls gecacht (~2.700 tok) — Caching ist **binär**
  (ganzer fixer Block trifft oder nichts). Gesamt-Cache-Quote **~4 %**. Ursache: die **pro-Ort-
  `enum`s** im Tools-Schema stehen vorn im Request und **brechen den gemeinsamen Prefix** bei fast
  jedem Orts-/Kontextwechsel. **Fazit:** Caching zahlt sich nur aus, wenn das Tools-Schema
  *orts-invariant* wird — d.h. die `enum`s sind der Blocker für Größe **und** Cacheability. Ohne
  Qualitätsänderung an den `enum`s bringt A1 nichts → Token-Teil des Projekts hier **abgeschlossen**
  mit den Gewinnen B1 (−17 %/Call) + B2 (Quality). Idee für später siehe §5.

**Erkenntnis nach B1/B2:** Der Parser-Prompt teilt sich jetzt in grob ~19 % Instruktionen /
~13 % Kontext / **~68 % Tools-Schema** auf. Das Tools-Schema ist **fix + qualitätstragend**
(13 Tool-Defs + Beschreibungen + Orts-/Objekt-`enum`s) → nicht sinnvoll trimmbar → **A1 (Caching)**
ist der einzige große verbleibende Hebel dafür. B2 zeigte: `enum`-Scoping bringt Qualität, kaum
Tokens.

## 5. Weitere Möglichkeiten — **NICHT jetzt umsetzen**

Bewusst zurückgestellt (später neu bewerten):

- **A2 — `rest`-Schleife entstopfen.** Idee war, die Mehrfach-Übertragung bei langen Eingaben
  zu vermeiden. **Problem / Grund für die Zurückstellung:** der `rest`-Mechanismus ist
  *absichtlich* so gebaut, weil sich der Kontext **zwischen** den Teilschritten ändert und
  „die Zukunft" berücksichtigt werden muss. Beispiel:

  > „untersuche den blumentopf und schliesse mit dem schlüssel den schuppen auf"
  > → `(1: untersuche blumentopf)  (2: rest "schliesse mit schlüssel den schuppen auf")`

  Bei Eingabe des Satzes **weiß das System noch gar nichts vom Schlüssel**. Erst *nachdem*
  Schritt 1 ausgeführt wurde, kennt die Game-Engine den Schlüssel, liefert ihn über eine
  `compile_*`-Funktion in den nächsten LLM-Aufruf, und „schliesse den schuppen mit dem
  schlüssel auf" wird überhaupt auflösbar. Ein Zerlegen des ganzen Satzes in **einem** Call
  würde diese Zustandsabhängigkeit brechen. → Nur mit großer Vorsicht und ausführlichem Test
  angehen, nicht in der aktuellen Runde.

- **C1 — Object-/Location-/Way-Prompts entschlacken + Parser/`narrate`-Kontext entdoppeln.**
  Größter Effekt bei `narrate`; im Parser klein (~12 %). Qualitätssensibel (Konsistenz der
  Erzählung, Disambiguierung beim Parsen) → erst nach den sicheren Hebeln und nur mit striktem
  A/B. Vorher `narrate` analog zum Parser instrumentieren.

- **A1' — Orts-invariante `enum`s für bessere Cache-Hits (Gemini-spezifisch, Idee für später).**
  Aus der A1-Messung: implizites Caching greift nur, wenn das Tools-Schema call-übergreifend
  identisch ist. Ansatz: statt der lokalen IDs die **komplette Welt-ID-Liste** ins `enum` legen →
  statischer Teil sieht immer gleich aus → ~80 % des Parse-Calls würden gecacht (75 % billiger).
  Qualität bliebe größtenteils erhalten (`enum` verhindert weiterhin *erfundene* IDs; die
  *Lokalität* sichern wie heute der Kontext + die Engine-Abweisung). Risiko: bei Cache-*Miss*
  ist das Schema größer, die Lokalitäts-Bindung minimal weicher → messbar per A/B (Tokens +
  Ungültig-Call-Rate). **Achtung:** rein Gemini-/impliziter-Cache-spezifisch — passt nur bedingt
  zum Ziel „provider-agnostisch"; daher bewusst zurückgestellt.

## 6. Mess-/Validierungsmethode

- **Instrumentierung:** `_log_prompt_sections` (Parser; `narrate` bei Bedarf nachrüsten) +
  `tokenstats` für die Session-Aggregation nach Quelle.
- **A/B-Harness:** ein **fixes Skript-Playthrough** (Kandidat: `sys_test.py` mit vordefinierten
  Sätzen) — identische Eingaben vor/nach jedem Hebel.
- **Zwei Kriterien pro Hebel:** (1) Token-Delta (`tokenstats`), (2) Ausgabequalität stichprobe
  (gültige Tool-Calls beim Parsen; Konsistenz/keine Fantasie bei `narrate`).
- Sandbox-Hinweis: die google-SDK lädt im Sandbox nicht (hängt) → Änderungen per `py_compile`
  + Lesen prüfen; Token-/Qualitätsmessung im echten Browser-Playthrough.

## 7. Provider-Austauschbarkeit (Designprinzip)

Alles, was Prompt-Aufbau, Tool-Schema und Caching betrifft, wird so gebaut, dass es hinter der
`LLMClient`-Abstraktion liegt. Ein späterer Wechsel (z. B. Anthropic/OpenAI/lokal) soll nur
einen neuen Adapter erfordern, nicht Änderungen in der Spiel-Engine. Caching (A1) wird als
**optionale Fähigkeit** modelliert: nutzbar, wenn der Adapter sie anbietet; sonst weicher
Fallback auf den vollen Prompt.

---

**Verwandte Doku/Notizen:** Token-Logging-Setup (`_log_tokens`/`dl.LLM_TOKENS`/`token_report`);
Qualitätsrationale der enums/Compile-Funktionen (siehe CLAUDE.md „Status & next steps" und die
Projekt-Memory).
