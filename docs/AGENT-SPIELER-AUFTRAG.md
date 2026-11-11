# Auftrag: Ein KI-Agent spielt das Adventure – mit Zuschauermodus

> **Für Claude Code.** Diese Datei ist dein Arbeitsauftrag. Lies sie vollständig, bevor du etwas tust.
> Arbeite in den Phasen, die unten beschrieben sind, und **halte nach der Planungsphase an**, bis Chris
> den Plan freigegeben hat.

---

## 1. Worum es geht

Das Adventure (dieses Repository) ist **Lehrmaterial**, kein Produkt – siehe `CLAUDE.md`. Bisher spielt ein
Mensch im Browser; die NPCs (Hund, Zombie) handeln pro Runde selbst, der Zombie im Zustand HUNTING sogar per
LLM-Entscheidung mit Notizbuch.

**Neu:** Der menschliche Spieler soll durch einen **KI-Agenten** ersetzt werden können, der versucht, das
Adventure zu lösen – und Chris (und später seine Kursteilnehmer) sollen **im Browser live zusehen** können, wie
das funktioniert.

Das Ziel ist **Verstehen**, nicht Spielstärke. Chris will an diesem Projekt lernen und später zeigen, *wie ein
Agent funktioniert*:

- Ein Agent ist im Kern eine **Schleife**: Modell bekommt Situation + Werkzeugliste → ruft ein Werkzeug auf →
  sieht das Ergebnis → entscheidet erneut … bis es fertig ist.
- Die **Spielwelt wird zur Werkzeug-Umgebung** – so wie bei Claude Code das Repository die Welt ist und Shell
  und Dateizugriff die Werkzeuge sind.
- Es gibt **zwei verschachtelte Schleifen**: die äußere Rundenschleife des Spiels und die innere Denkschleife
  des Agenten innerhalb einer Runde.

Wenn du zwischen „eleganter“ und „leichter zu erklären“ wählen musst: **immer leichter zu erklären.**

---

## 2. Was du zuerst lesen musst

1. `CLAUDE.md` – Architektur, Konventionen, Gotchas. Gilt weiterhin uneingeschränkt (insbesondere:
   kleine, bisektierbare Commits; committen/pushen nur, wenn Chris es sagt; keine Verhaltensänderung beim
   Verschieben von Code).
2. `docs/claude-memory/*` und `docs/ZOMBIE-NPC-erklaert.md` – wie die NPCs arbeiten, besonders das
   Notizbuch-Muster des Zombies.
3. `webserver/command_engine.py` – **hier steckt ein Teil der Rundenlogik** (Befehlswarteschlange, „rest“-
   Fortsetzung, Durst, Rundenwechsel, NPC-Züge, Game Over). Der Agent muss durch **genau denselben Pfad**
   laufen wie ein Mensch.
4. `web_dialogs.py` – die Stellen, an denen das Spiel auf den Menschen wartet:
   `ask_for_playername`, `ask_for_pin`, `do_minigame`, `do_chat`, `do_game_over`.
5. `gemini_interface.py` → `parse_user_input_to_commands` – die vorhandenen Function Declarations der Verben
   (`t_gehen`, `t_nimm`, `t_anwenden`, …). Wiederverwenden, nicht neu erfinden.
6. `webserver/serialization.py` – was der Browser (und damit ein menschlicher Spieler) zu sehen bekommt.
7. `web/websockets.js`, `web/zombie_chat.js`, `web/Adventure9.html` – das Frontend und seine Nachrichtentypen.
8. `sys_test.py` – Chris' früherer Skript-Spieler (Befehlsliste) aus der Textversion.
9. `saves/*.json` – Spielstände an interessanten Punkten (z. B. `05-…-zombie-on-its-way`), ideal zum Testen.

---

## 3. Umfang

Drei Bausteine, alle Pflicht:

| Baustein | Inhalt |
|---|---|
| **A. Agent-Spieler** | Echte Agentenschleife: freie Aktionen (kosten keine Runde), Züge (kosten eine Runde), Notizbuch, mehrere Werkzeugaufrufe pro Runde |
| **B. Gespräche** | Der Agent führt Chats mit Zombie und Hund selbst – zwei Modelle verhandeln miteinander |
| **C. Zuschauermodus** | Im Browser sieht man das Spiel wie gewohnt **plus** das Innenleben des Agenten, live, mit Pause und Einzelschritt |

**Nicht** im Umfang: eine „Ein-Schuss“-Variante (ein LLM-Aufruf = ein Zug). Die gibt es schon in Form des
Zombies und dient als gedankliche Baseline. Ebenfalls nicht: Gemma/Ollama als Agentenmodell.

---

## 4. Anforderungen im Detail

### 4.1 Wahrnehmung – Fairness ist Pflicht

- Der Agent sieht **nur, was ein menschlicher Spieler sieht**: Szene, Umgebung (Objekte, Wege), Status,
  Inventar, Ergebnis der letzten Aktion, NPC-Meldungen, die auch der Mensch sähe.
- Er sieht **nicht**: `data/world.json`, Flags, interne `o_`/`p_`-IDs, Obstruction-Funktionen, den Walkthrough,
  den Zustand der NPCs, die PIN.
- Leite die Beobachtung aus derselben Quelle ab, die auch den Browser füttert (Serialisierung), nicht aus
  einem direkten Griff in `GameState`. Falls dafür eine schmale Funktion „Spielersicht als Text“ nötig ist,
  baue sie so, dass man ihr ansieht, dass sie nichts Verborgenes ausgibt.
- Namen gegenüber dem Agenten sind **Rufnamen** (wie in der GUI). Die Übersetzung Rufname → ID passiert im
  Code, nicht im Modell.

### 4.2 Werkzeuge

Zwei klar getrennte Klassen – diese Trennung ist ein zentraler Lernpunkt und muss im Code sichtbar sein
(eigene Liste/eigener Abschnitt, Kommentar dazu):

**Freie Aktionen** (verbrauchen keine Runde, NPCs handeln nicht):
- aktuelle Situation erneut lesen
- Inventar ansehen
- Notizbuch lesen
- Notizbuch schreiben/ergänzen (z. B. „PIN-Hinweis im Labor gesehen“, „Handrad klemmt – Öl?“)
- ggf. „Was weiß ich über Ort X?“ – nur aus dem eigenen Verlauf/Notizbuch, nie aus der Welt

**Züge** (verbrauchen eine Runde, danach handeln die NPCs):
- die vorhandenen Verben aus `parse_user_input_to_commands` (gehen, nimm, anwenden, untersuche, ablegen, gib,
  umsehen, angreifen, interagieren, …), soweit sinnvoll; Systemverben (quit, hilfe, rest, zurückweisen) nicht
- **Jeder Zug hat ein Pflichtargument `warum`** (ein Satz). Das ist keine Spiellogik, sondern dient dem
  Zuschauermodus und dem Log: Man sieht, *warum* der Agent etwas tut.

**Wichtige Designentscheidung (in der Planung begründen):** Der Agent ruft die Verben **direkt als Werkzeuge**
auf, statt Freitext an den vorhandenen Parser zu schicken. Grund: ein LLM weniger in der Kette, klare
Fehlermeldungen, das Prinzip „Welt = Werkzeuge“ wird sichtbar. Der Zug muss danach aber durch **denselben
Ausführungspfad** wie ein geparster Menschenbefehl laufen (`execute_single_command` o. ä.), damit keine
zweite Regelwelt entsteht.

Ungültige Aufrufe (unbekanntes Objekt, Weg versperrt, falsche Argumente) liefern dem Agenten eine
**verständliche Fehlermeldung als Werkzeugergebnis** und kosten **keine Runde** – so wie das Spiel bei
Systemfehlern schon heute keine Runde abzieht.

### 4.3 Die Schleife

- **Äußere Schleife:** Spielrunden, wie bisher von der Engine/dem Command-Engine-Pfad gesteuert.
- **Innere Schleife:** pro Runde ruft der Agent Werkzeuge auf, bis er einen Zug macht (oder ein Limit greift).
- Diese innere Schleife steht **in einer einzigen, von oben nach unten lesbaren Funktion** (Richtwert:
  ≤ 60 Zeilen ohne Kommentare). Das ist *das* Lehrstück dieses Projekts – sie soll man im Kurs auf eine
  Folie bringen können.
- Grenzen (konfigurierbar, mit vernünftigen Standardwerten):
  - max. Werkzeugaufrufe pro Runde (z. B. 8) – danach wird der Agent aufgefordert, jetzt einen Zug zu machen;
    tut er es nicht, gilt ein neutraler Zug (z. B. „umsehen“) und das wird protokolliert
  - max. Runden pro Spiel (z. B. 100)
  - Token-Zähler über das ganze Spiel, sichtbar im Zuschauermodus; optional Abbruch bei Grenze
- **Kontext:** Jede Runde baut den Prompt **frisch** auf: Systemprompt (Rolle, Regeln, Werkzeuge) +
  aktuelle Beobachtung + Notizbuch + kompakter Verlauf der letzten N Runden (z. B. 10: Zug, `warum`,
  Ergebnis). Innerhalb einer Runde wächst der Kontext mit den Werkzeugergebnissen; nach dem Zug wird er
  verworfen. Mach im Code sichtbar, dass das eine bewusste Entscheidung gegen „ein endlos wachsender Chat“
  ist, und warum (Kosten, Fokus, Vergleich zum Notizbuch des Zombies).
- **Ziel des Agenten:** nur das, was der Spieler auch weiß (Einleitungstext: Bote, Umschlag, Fahrradkette
  gerissen …). Kein Wissen über die Lösung im Systemprompt.

### 4.4 Gespräche mit Zombie und Hund (Baustein B)

- Wenn ein Chat startet (vom Agenten per `interagieren` oder vom NPC initiiert, z. B. beim Erwachen des
  Zombies), führt der Agent das Gespräch selbst.
- Eigene, kleine Werkzeugmenge im Chat: `sage(text)`, `gespraech_beenden(zusammenfassung)`; im Chat sind
  Spielzüge nicht erlaubt.
- Das NPC-seitige Verhalten bleibt **unverändert** (`whom.chat`, `whom.end_chat`, Trust-Mechanik). Der
  Agent ersetzt nur die Eingabe des Menschen.
- Gesprächslimit (z. B. 10 Wortwechsel), danach wird beendet.
- Nach dem Gespräch soll der Agent die Gelegenheit bekommen, Wichtiges ins Notizbuch zu schreiben.
- Im Zuschauermodus erscheint der Chat **im vorhandenen Chat-Modal**, die Zeilen des Agenten erscheinen dort,
  als hätte ein Mensch sie getippt.

### 4.5 Weitere Eingabestellen

- **Spielername:** fest konfigurierbar (z. B. „Agent“).
- **PIN-Pad:** Der Agent bekommt ein Werkzeug `pin_eingeben(ziffern)`. Ob die PIN stimmt, prüft der Server
  (MD5 wie heute im Client). Die PIN muss der Agent im Spiel gefunden und sich gemerkt haben – guter Test
  für das Notizbuch.
- **Minispiel (Hundeangriff):** Die Minispiele laufen heute in JavaScript im Browser. Schlage in der Planung
  eine einfache, ehrliche Lösung vor (z. B. Agent entscheidet per Werkzeug, Ergebnis wird serverseitig nach
  den Regeln des jeweiligen Spiels oder per Zufall ermittelt; im Zuschauermodus wird das Ergebnis angezeigt).
  Nicht überbauen – das Minispiel ist nicht der Kern.

### 4.6 Zuschauermodus (Baustein C) – ausdrücklich wichtig

Der Zuschauermodus ist **kein Extra**, sondern der Weg, auf dem man sieht, wie alles zusammenarbeitet. Er ist
gleichzeitig das wichtigste Debugging-Werkzeug. Baue ihn **früh** (siehe Meilensteine), nicht am Ende.

- Start aus der normalen Oberfläche, z. B. Schalter/Button „Agent spielen lassen“ beim Start oder
  `?mode=agent` in der URL. Optional: Start ab einem Spielstand aus `saves/`.
- Die **normale Spieloberfläche** läuft unverändert weiter (Szene, Umgebung, Letzte Aktion, Status,
  Hund-/Zombie-Overlays, Chat-Modal, Biss-Popup, Game Over). Der Zuschauer sieht also exakt das Spiel.
- Zusätzlich ein **Agenten-Panel** (ein- und ausklappbar), das live zeigt:
  - Runde, Schritt innerhalb der Runde, Werkzeugaufrufe dieser Runde / Limit
  - jeden Werkzeugaufruf mit Argumenten und Ergebnis, farblich getrennt nach **freie Aktion** / **Zug** /
    **Fehler** / **Chat**
  - das `warum` jedes Zugs gut lesbar hervorgehoben
  - eventuellen Freitext des Modells zwischen den Aufrufen (das, was es tatsächlich ausgibt – keine erfundene
    „Gedankenwiedergabe“)
  - das aktuelle Notizbuch
  - Token-Zähler (Runde / gesamt) und Anzahl der Modellaufrufe
- **Steuerung:** Start, Pause, **Einzelschritt** (genau ein Werkzeugaufruf), **Runde** (bis zum nächsten Zug),
  Stopp, Tempo (Verzögerung zwischen Schritten). Einzelschritt ist für den Unterricht das Wichtigste.
- Für Kurse: Schrift groß genug für einen Beamer; das Panel soll auch ohne Vorwissen verständlich sein
  (kurze Legende der Farben).
- Frontend in **plain JavaScript** wie der Rest von `web/` (eigene Datei, z. B. `web/agent_panel.js`), kein
  Framework, kein Build-Schritt.

### 4.7 Protokoll und Auswertung

- Jedes Agentenspiel schreibt eine **JSONL-Spur** (eine Zeile pro Ereignis: Runde, Werkzeug, Argumente,
  Ergebnis, Tokens, Zeit) in einen eigenen, git-ignorierten Ordner (z. B. `agent_runs/`).
- Am Ende eine kurze Zusammenfassung: gewonnen/verloren/abgebrochen, Runden, Werkzeugaufrufe, Tokens,
  besuchte Orte, letzter Zustand.
- Optional, aber hilfreich: ein kleines Skript, das eine Spur als lesbaren Text ausgibt (für Kursmaterial).

### 4.8 Modell

- Standard: ein Gemini-Modell über das vorhandene `google-genai`-SDK (der Schlüssel ist vorhanden). Modellname
  konfigurierbar, nicht im Code verstreut.
- Kapsle den Modellaufruf des Agenten hinter einer **kleinen, eigenen Schnittstelle** (eine Funktion „schicke
  Nachrichten + Werkzeuge, bekomme Text und/oder Werkzeugaufrufe zurück“), damit Chris später ein anderes
  Modell (z. B. Claude über die Anthropic-API) vergleichen kann. Baue den zweiten Anbieter **nicht** jetzt,
  aber die Schnittstelle so, dass er eine Datei wäre.
- **Keine Agenten-Frameworks** (kein LangChain, LangGraph, CrewAI, ADK o. ä.). Die Schleife wird von Hand
  geschrieben – genau darum geht es.

---

## 5. Architektur – was in der Planung zu entscheiden ist

Es gibt zwei grundsätzliche Wege. Bewerte beide in der Planung und begründe deine Wahl.

**Weg 1 – Agent als externer WebSocket-Client („falscher Browser“).** Ein separates Programm verbindet sich
wie `websockets.js`, schickt Befehle, beantwortet Chat/PIN/Minispiel. Vorteil: Engine und Server bleiben
nahezu unverändert. Nachteil: Für den Zuschauermodus muss eine zweite Browser-Verbindung dieselbe Sitzung
mitsehen können (Sitzungs-Broadcast nötig), und das Agenten-Panel braucht einen zusätzlichen Kanal.

**Weg 2 – Autopilot im Server, Eingabequellen austauschbar.** Die Browser-Sitzung läuft wie immer, aber die
*Eingaben* (Befehl, Chat-Antworten, PIN, Minispiel, Name) kommen vom Agenten statt aus dem WebSocket. Alles,
was heute an den Browser geht, geht weiterhin an den Browser – der Zuschauermodus ist damit fast geschenkt,
plus Agenten-Ereignisse als neue Nachrichtentypen. Nachteil: Die Wartestellen in `WebDialogs`
(`async for message in self.ws`) und die Befehlsannahme müssen sauber austauschbar gemacht werden.

**Vorläufige Empfehlung von Chris' Seite: Weg 2**, weil der Zuschauermodus zentral ist und so ohne
Sitzungs-Spiegelung auskommt. Wenn du beim Lesen des Codes zu einem anderen Schluss kommst, sag es und
begründe es.

Unabhängig vom Weg gilt:

- **Keine Spielregeln ändern.** Engine, NPCs, Rätsel, Flags bleiben, wie sie sind. Wenn du für den Agenten
  etwas in der Engine ändern *musst*, ist das ein eigener, kleiner Commit mit Begründung.
- Der Agent läuft durch **denselben Rundenpfad** wie ein Mensch (Durst, NPC-Züge, Game Over, Fehler ohne
  Rundenverlust …).
- Neuer Code in einem eigenen Paket, z. B.:
  ```
  agent_player/
      __init__.py
      loop.py          # die innere Schleife – DAS Lehrstück
      tools.py         # Werkzeugdefinitionen: freie Aktionen, Züge, Chat – getrennt
      observation.py   # Spielersicht als Text (nur, was ein Mensch sieht)
      notebook.py      # Notizbuch
      context.py       # Prompt-Aufbau pro Runde
      llm.py           # schmale Modellschnittstelle + Gemini-Umsetzung
      trace.py         # JSONL-Protokoll
      config.py        # alle Grenzen und Einstellungen an einer Stelle
  web/agent_panel.js   # Zuschauer-Panel
  ```
  Die Aufteilung ist ein Vorschlag; wichtig ist, dass jede Datei *eine* Aufgabe hat.
- Achte auf die vorhandene async-Struktur (WebSocket, `await`). Pause/Einzelschritt müssen funktionieren,
  ohne den Server zu blockieren.

---

## 6. Verständlichkeit des Codes – nicht verhandelbar

Chris muss jede Zeile verstehen und im Kurs erklären können. Deshalb:

1. **Lesbar vor clever.** Keine Metaprogrammierung, keine Dekorator-Magie, keine verschachtelten
   Comprehensions über drei Ebenen, keine generischen Plugin-Registries. Lieber eine explizite Liste und ein
   `if`, das man sieht.
2. **Die Schleife ist sichtbar.** `loop.py` enthält die innere Schleife als eine Funktion, die man von oben
   nach unten liest. Hilfsfunktionen dürfen ausgelagert werden, aber die Struktur
   „Prompt bauen → Modell fragen → Werkzeug ausführen → Ergebnis anhängen → wiederholen / Zug → fertig“
   muss in dieser einen Funktion stehen.
3. **Kommentare auf Deutsch**, und zwar das *Warum*, nicht das *Was*. Docstrings für jede öffentliche Funktion
   und Klasse.
4. **Lernpunkte markieren.** Wo ein Konzept steckt, das man im Kurs erklären würde, ein Kommentar
   `# LERNPUNKT: …` (z. B. „hier wird aus der Welt ein Werkzeug“, „hier verwerfen wir den Kontext bewusst“,
   „hier verhindern wir, dass der Agent schummelt“). Sparsam, aber an den wichtigen Stellen.
5. **Type Hints** überall, Dataclasses für Datenstrukturen (Werkzeugaufruf, Werkzeugergebnis,
   Rundenprotokoll).
6. **Kleine Dateien, kleine Funktionen**, sprechende Namen (deutsch oder englisch, aber einheitlich – richte
   dich nach dem Bestand: Dateien snake_case, Klassen PascalCase).
7. **Bestehender Stil:** Logging über `dprint(dl.…, …)` aus `utils.py`; ggf. einen eigenen Debug-Level für den
   Agenten anlegen.
8. **Erklärdokument:** `docs/AGENT-SPIELER-erklaert.md` im Stil von `docs/ZOMBIE-NPC-erklaert.md`:
   - Was ist ein Agent? (in fünf Sätzen, ohne Hype)
   - Diagramm der zwei Schleifen (Mermaid oder ASCII)
   - Freie Aktionen vs. Züge, und warum diese Trennung
   - Wahrnehmung und Fairness
   - Kontextaufbau pro Runde vs. wachsender Chat; Vergleich mit dem Notizbuch des Zombies
   - Der Zombie (Ein-Schuss-Entscheidung pro Runde) vs. der Agent-Spieler (Schleife) – Gegenüberstellung
   - Ein **kommentierter Ausschnitt aus einer echten Spur** (ein paar Runden inkl. eines Chats)
   - Wie man den Zuschauermodus bedient
   - Bekannte Grenzen und Ideen für Experimente (anderes Modell, anderes Limit, ohne Notizbuch …)

---

## 7. Vorgehen

### Phase 0 – Lesen und Fragen
Lies alles aus Abschnitt 2. Stelle Chris **gesammelt** die Fragen, die du wirklich nicht aus dem Code
beantworten kannst. Keine Fragen, deren Antwort im Repo steht.

### Phase 1 – Plan (dann anhalten!)
Schreibe `docs/AGENT-SPIELER-PLAN.md` mit:
- Entscheidung Weg 1/Weg 2 mit Begründung
- konkreten Änderungspunkten im Bestand (Datei, Funktion, was und warum) – möglichst wenige
- Werkzeugliste (Name, Argumente, frei/Zug, Rückgabe)
- Nachrichtentypen zwischen Server und Browser für den Zuschauermodus
- Lösung für Minispiel und PIN
- Meilensteine (siehe unten, gern verfeinert) mit jeweils einem **Prüfschritt**, den Chris selbst ausführen kann
- Risiken und offene Punkte

**Dann anhalten und auf Freigabe warten.** Nichts implementieren, bevor Chris „go“ sagt.

### Phase 2 – Umsetzung in Meilensteinen
Neuer Branch, abgezweigt vom aktuellen (Namensschema wie bisher, z. B. `Adventure-11-<Datum>-Agent`).
Pro Meilenstein kleine, bisektierbare Commits – committen erst, wenn Chris es sagt (siehe `CLAUDE.md`).

1. **Naht + Skript-Spieler im Zuschauermodus.** Eingaben austauschbar machen; ein Skript-Spieler (Befehle aus
   einer Liste wie in `sys_test.py`) spielt im Browser sichtbar, mit Start/Pause/Einzelschritt. *Noch kein
   LLM.* Beweist, dass die Pipeline End-to-End trägt und dass der Agent denselben Rundenpfad nutzt.
2. **Agentenschleife.** Freie Aktionen, Züge mit `warum`, Notizbuch, Grenzen, JSONL-Spur. Panel zeigt
   Werkzeugaufrufe und Ergebnisse.
3. **Gespräche.** Chat mit Zombie und Hund, Anzeige im vorhandenen Modal und im Panel.
4. **PIN und Minispiel.**
5. **Panel vollständig** (Notizbuch, Tokens, Legende, Beamer-Tauglichkeit), Start ab Spielstand.
6. **Erklärdokument** inkl. kommentierter echter Spur; `CLAUDE.md` um einen kurzen Abschnitt zum
   Agent-Spieler ergänzen.

### Prüfen
- Es gibt keine automatische Testsuite (siehe `CLAUDE.md`). Prüfe mit `./venv/bin/python3 -m py_compile …`
  und Importen der Blattmodule.
- **Achtung:** In deiner Sandbox hängt der Import des Google-SDK. LLM-Pfade und den Browser kannst du dort
  nicht selbst testen. Gib Chris für jeden Meilenstein eine **kurze, konkrete Testanleitung** (was starten,
  was klicken, was er sehen sollte, welcher Spielstand sich eignet).
- Wo möglich, baue so, dass die Schleife mit einem **Fake-Modell** (liefert vorgegebene Werkzeugaufrufe)
  ohne Netz läuft – das macht Meilenstein 2 auch ohne Google-SDK prüfbar und ist gleichzeitig gutes
  Lehrmaterial („so sieht die Schleife ohne KI aus“).

---

## 8. Fertig ist es, wenn …

- Chris im Browser „Agent spielen lassen“ wählen und zusehen kann, wie der Agent Runde für Runde spielt,
  inkl. Gesprächen mit dem Zombie im Chat-Modal,
- er jederzeit pausieren, einzeln schrittweise weiterschalten und im Panel jeden Werkzeugaufruf samt `warum`,
  Ergebnis, Notizbuch und Tokenverbrauch sehen kann,
- ein Spiel mit einer JSONL-Spur und Zusammenfassung endet (gewonnen, verloren oder an einer Grenze
  abgebrochen),
- das menschliche Spiel unverändert funktioniert,
- `docs/AGENT-SPIELER-erklaert.md` existiert und die Schleife so erklärt, dass Chris sie im Kurs zeigen kann,
- Chris den Code in `agent_player/` lesen und erklären kann, ohne nachfragen zu müssen.

Ob der Agent das Adventure tatsächlich löst, ist **kein** Abnahmekriterium. Wo er hängen bleibt, ist
mindestens so lehrreich.
