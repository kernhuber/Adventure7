"""Alle Einstellungen des Agent-Spielers an EINER Stelle.

LERNPUNKT: Grenzen (Aufrufe pro Runde, Runden pro Spiel, Tokens) gehören in die
Konfiguration und nicht verstreut in den Code. Wer experimentieren will
("Was, wenn der Agent nur 3 Aufrufe pro Runde hat?"), ändert nur diese Datei.
"""

# --- Spiel -------------------------------------------------------------------
AGENT_PLAYER_NAME = "Agent"       # Name der Spielfigur im Agentenmodus
# Hund an/aus: gilt wie im normalen Spiel allein utils.NODOG (False = Hund dabei) – keine zweite Einstellung hier.

# Ausgang des Hundekampfs (ersetzt das Minispiel): Gewichte für (Hund gewinnt = Spiel verloren, Spieler gewinnt, Gleichstand).
# (1, 1, 1) = gleich wahrscheinlich. Z. B. (1, 3, 2) macht eine Niederlage seltener.
MINIGAME_WEIGHTS = (1, 1, 1)
# So lange zeigt der Browser das Kampf-Overlay (3 s Kampf + 3 s Ergebnis + Ausblenden); der Server wartet entsprechend.
DOGFIGHT_DURATION_S = 6.6

# --- Modell (ab Meilenstein 2) ----------------------------------------------
AGENT_MODEL = "gemini-2.5-flash"

# --- Grenzen (ab Meilenstein 2) ---------------------------------------------
MAX_CALLS_PER_ROUND = 8         # danach: "mach jetzt einen Zug!"
MAX_ROUNDS = 100                  # Rundenlimit pro Spiel
MAX_TOKENS_TOTAL = None          # None = kein Tokenlimit
HISTORY_ROUNDS = 10               # so viele frühere Runden stehen im Prompt
MAX_CHAT_EXCHANGES = 10         # Gesprächslimit (Meilenstein 3)

# --- Experience.md: Gedächtnis über Spiele hinweg (experience.py) ---------------------------------
EXPERIENCE_ACTIVE = True                 # False = Agent schreibt/liest keine Erfahrungen (Experiment: "ohne Lernen")
EXPERIENCE_FILE = "Experience.md"      # im Projektordner; man darf sie von Hand bearbeiten
EXPERIENCE_MAX_CHARS = 6000           # so viel (die neuesten Einträge) steht im Prompt
EXPERIENCE_MAX_INSIGHTS = 8         # so viele neue Erkenntnisse pro Spiel
EXPERIENCE_HISTORY_ROUNDS = 25          # so viele letzte Züge sieht der Agent beim Resümee

# --- Zuschauermodus ----------------------------------------------------------
START_TEMPO_MS = 800              # Verzögerung zwischen Schritten (im Panel einstellbar)


# ======================================================================================
# PROMPTS – alle Texte, die das Modell zu lesen bekommt, an EINER Stelle
# ======================================================================================
# LERNPUNKT: Ein Agent besteht zur Hälfte aus Prompts. Wer ihn verbessern will ("Warum folgt er dem Tipp
# nicht?"), ändert meistens Text und nicht Code. Deshalb stehen alle Prompts hier, jeweils mit einem Kommentar:
# WOFÜR sie gebraucht werden und WO im Code sie benutzt werden.
#
# Platzhalter in geschweiften Klammern, z. B. {situation}, füllt der Code mit str.format() – ändern Sie
# die Platzhalter-Namen nicht, sonst fehlt dem Code ein Wert. Geschweifte Klammern sonst bitte verdoppeln ({{ }}).
#
# Nicht hier: die BESCHREIBUNGEN der Werkzeuge (tools.py) – sie sind Teil des Werkzeug-Schemas, das das Modell
# mitbekommt, und stehen deshalb direkt bei den Werkzeugen. Ebenso nicht hier: die Fehlermeldungen, die als
# Werkzeugergebnis zurückgehen (loop.py, chat.py, pin.py), und der Text der Lage selbst (observation.py).

# --- 1. System-Prompt (gilt für das ganze Spiel) ------------------------------------------
# Wofür:  Rolle, Spielregeln und Werkzeug-Philosophie des Agenten. Er wird bei JEDEM Modellaufruf als
#         System-Anweisung mitgeschickt (Runden, Gespräche, PIN-Pad, Resümee).
# Wo:     agent_player/context.py, AgentContext.system_prompt() -> llm.py (system_instruction).
# Wichtig: Was der Agent über sein Ziel weiß, steht nur hier und entspricht dem, was jeder Spieler zu Beginn
#         liest. Kein Lösungswissen eintragen – dafür gibt es den Tipp-Kanal (siehe PROMPT_ROUND_TIP).
SYSTEM_PROMPT = """Du spielst ein deutschsprachiges Text-Adventure. Deine Spielfigur heißt Agent.

Die Ausgangslage, wie sie jeder Spieler liest: Du radelst als Bote mit deinem Fahrrad unter sengender Sonne
durch eine endlose Wüste. Bei dir hast du einen Umschlag, den du an ein Ziel bringen musst. Erreicht der Umschlag
das Ziel nicht, geht die Welt unter. Plötzlich reißt deine Fahrradkette – das Fahrrad funktioniert ohne sie nicht
mehr. Du bist an einem Ort gestrandet, an dem es Rettung geben könnte.

So funktioniert das Spiel für dich:
- Du hast zwei Arten von Werkzeugen. FREIE AKTIONEN (Lage lesen, Inventar, Notizbuch, Spielstand speichern) kosten keine Spielzeit.
  ZÜGE (gehen, nehmen, anwenden, untersuchen, …) kosten genau eine Spielrunde; danach handeln andere Figuren,
  und dein Durst nimmt zu. Ein Zug beendet deine Runde.
- Jede Runde: bei Bedarf freie Aktionen, dann genau EINEN Zug. Jeder Zug braucht ein 'warum' (ein Satz).
- Verwende Namen genau so, wie sie in der Lage stehen (Objekte hier, Begehbare Wege, Inventar).
- Ein Fehler (z. B. ein unbekannter Name) kostet keine Runde – du siehst die Fehlermeldung und versuchst es neu.
- Wenn dein Durst-Zähler 0 erreicht, verdurstest du, und das Spiel ist verloren.
- WICHTIG: In jeder Runde siehst du nur die aktuelle Lage, dein Notizbuch und eine kurze Liste deiner letzten Züge.
  Alles andere vergisst du. Schreibe deshalb Wichtiges (Zahlen, Codes, Hinweise, Ideen, was du schon probiert hast,
  wo etwas liegt) ins Notizbuch.
- Bevor du etwas Riskantes oder Unumkehrbares tust (z. B. etwas zünden, zerstören oder hergeben), speichere mit
  'spielstand_speichern' und schreibe dir in der 'notiz' eine Warnung für dein späteres Ich.
- Handle selbstständig; du kannst niemanden um Hilfe bitten. Schreibe kurz, was du denkst, und rufe dann ein Werkzeug auf.
"""

# Wofür:  Anhang an den System-Prompt, wenn Experience.md Einträge aus früheren Spielen hat (Lernen von Spiel zu Spiel).
# Wo:     context.py, AgentContext.system_prompt(). {lessons} = die neuesten EXPERIENCE_MAX_CHARS Zeichen der Datei.
PROMPT_LESSONS = """
=== ERFAHRUNGEN AUS FRÜHEREN SPIELEN (Experience.md) ===
Das ist dein Wissen aus früheren Partien. Nutze es, aber prüfe, ob es zur aktuellen Lage passt.

{lessons}
"""

# --- 2. Die Runden-Nachricht (erste Nachricht jeder Spielrunde) ----------------------------
# Wofür:  Der Prompt wird in jeder Runde FRISCH gebaut (siehe context.py): Lage + Notizbuch + letzte Züge.
# Wo:     context.py, round_message(), aufgerufen von loop.py, play_round(). Platzhalter: {situation} (Text aus
#         observation.py), {notebook}, {history} (die letzten HISTORY_ROUNDS Züge).
PROMPT_ROUND = """=== AKTUELLE LAGE ===
{situation}

=== DEIN NOTIZBUCH ===
{notebook}

=== DEINE LETZTEN ZÜGE ===
{history}

"""
PROMPT_NO_HISTORY = "(noch keine)"      # Platzhalter für {history}, solange es noch keinen Zug gab

# Wofür:  Wird an die Runden-Nachricht angehängt, wenn der Agent einen Spielstand geladen hat, bei dem er sich
#         selbst eine Notiz hinterlassen hatte ("Vorsicht, gleich zünde ich ..."). Nur in der ersten Runde.
# Wo:     context.py, round_message(); die Notiz setzt savestate.py, import_state(). {memo} = die Notiz.
PROMPT_ROUND_MEMO = """=== ERINNERUNG AUS DEM SPIELSTAND (eine Notiz von dir selbst) ===
{memo}

"""

# Wofür:  Ein Tipp von außen (Zuschauer-Feld im Panel oder &tipp= in der URL). Steht EINMAL im Prompt und
#         dauerhaft im Notizbuch (context.py, remember_tip). Die Formulierung entscheidet, ob der Agent ihn ernst nimmt.
# Wo:     context.py, round_message(). {tip} = der Text des Zuschauers.
PROMPT_ROUND_TIP = """=== TIPP VON EINEM ZUSCHAUER ===
{tip}
Der Tipp kommt von jemandem, der das Spiel kennt. Prüfe ihn und folge ihm, solange du keinen konkreten Gegengrund hast. Er steht jetzt auch in deinem Notizbuch.

"""

# Wofür:  Die Frage am Ende jeder Runden-Nachricht.
# Wo:     context.py, round_message().
PROMPT_ROUND_QUESTION = "Was tust du in dieser Runde?"

# --- 3. Schubser in der Rundenschleife ---------------------------------------------------
# Wofür:  Das Modell hat nur Text geschrieben und kein Werkzeug aufgerufen. Diese Nachricht schickt es zurück an die Arbeit.
# Wo:     loop.py, play_round().
NUDGE_NO_TOOL = "Du hast kein Werkzeug aufgerufen. Rufe jetzt ein Werkzeug auf – am Ende der Runde einen Zug."

# Wofür:  Das Aufruflimit pro Runde (MAX_CALLS_PER_ROUND) ist erreicht: der Agent muss jetzt ziehen.
# Wo:     loop.py, force_move(). {max_calls} = MAX_CALLS_PER_ROUND.
NUDGE_FORCE_MOVE = "Du hast {max_calls} Werkzeugaufrufe in dieser Runde verbraucht. Mache JETZT einen Zug."

# --- 4. Gespräche mit Hund oder Zombie (chat.py) -------------------------------------------
# Wofür:  Erste Nachricht eines Gesprächs. Im Gespräch gibt es nur die Werkzeuge 'sage' und 'gespraech_beenden'.
# Wo:     context.py, chat_message(), aufgerufen von chat.py, run_conversation(). Platzhalter: {situation},
#         {notebook}, {partner} (Hund/Zombie), {partner_upper} (Großbuchstaben, für die Überschrift),
#         {conversation} (bisheriger Verlauf), {max_exchanges} (MAX_CHAT_EXCHANGES).
PROMPT_CHAT = """=== AKTUELLE LAGE ===
{situation}

=== DEIN NOTIZBUCH ===
{notebook}

=== GESPRÄCH MIT {partner_upper} BISHER ===
{conversation}

Du führst gerade ein Gespräch mit {partner}. Jetzt stehen dir nur 'sage' und 'gespraech_beenden' zur Verfügung (keine Spielzüge). Höchstens {max_exchanges} Wortwechsel. Beende das Gespräch, wenn nichts mehr zu besprechen ist, und fasse dabei zusammen, was du dir merken willst."""
PROMPT_CHAT_NOTHING_SAID = "(noch nichts gesagt)"     # Platzhalter für {conversation} zu Beginn
PROMPT_CHAT_YOU = "Du"                                # Sprechername des Agenten im bisherigen Verlauf

# Wofür:  Das Modell hat im Gespräch kein Werkzeug aufgerufen.
# Wo:     chat.py, run_conversation().
NUDGE_CHAT_NO_TOOL = "Rufe 'sage' oder 'gespraech_beenden' auf."

# Wofür:  Das Gespräch ist zu Ende, ohne dass der Agent es selbst beendet hat: einmal nach der Zusammenfassung
#         fragen (sie kommt ins Notizbuch). {reason} ist einer der beiden folgenden Sätze.
# Wo:     chat.py, _wrap_up().
PROMPT_CHAT_WRAP_UP = "{reason} Rufe jetzt 'gespraech_beenden' mit deiner Zusammenfassung auf."
CHAT_REASON_PARTNER_ENDED = "{partner} hat das Gespräch beendet."
CHAT_REASON_LIMIT = "Das Gesprächslimit ist erreicht."

# --- 5. PIN-Pad des Geldautomaten (pin.py) --------------------------------------------------
# Wofür:  Erste Nachricht, sobald das PIN-Pad offen ist: dieselben Regeln, die auch ein Mensch am Pad erfährt.
#         Die Zahl selbst steht NICHT im Prompt – der Agent muss sie im Spiel gefunden und notiert haben.
# Wo:     context.py, pin_message(), aufgerufen von pin.py, solve_pinpad(). Platzhalter: {situation}, {notebook}.
PROMPT_PIN = """=== AKTUELLE LAGE ===
{situation}

=== DEIN NOTIZBUCH ===
{notebook}

Du hast die EC-Karte in den Geldautomaten gesteckt. Auf dem Bildschirm steht: 'Bitte Geheimzahl eingeben.' Die Geheimzahl hat vier Ziffern. Das Pad lässt sich nur durch Eingabe von vier Ziffern verlassen. Ist die Zahl falsch, musst du die Karte erneut einstecken (das kostet eine weitere Spielrunde). Du kannst dein Notizbuch lesen und die Zahl mit 'pin_eingeben' eintippen."""

# Wofür:  Das Modell hat am PIN-Pad kein Werkzeug aufgerufen.
# Wo:     pin.py, solve_pinpad().
NUDGE_PIN_NO_TOOL = "Rufe 'pin_eingeben' mit vier Ziffern auf."

# --- 6. Resümee am Spielende (Experience.md) ---------------------------------------------
# Wofür:  Letzter Modellaufruf eines Spiels: Der Agent soll festhalten, was er für künftige Spiele gelernt hat
#         (Werkzeug 'erfahrung_notieren'). Das Ergebnis landet in Experience.md und steht beim nächsten Start
#         im System-Prompt (PROMPT_LESSONS).
# Wo:     experience.py, write_summary(). Platzhalter: {result_upper} (GEWONNEN/VERLOREN/...), {round_number},
#         {ending} (letzte Meldungen), {notebook}, {history} (die letzten EXPERIENCE_HISTORY_ROUNDS Züge),
#         {max_insights} (EXPERIENCE_MAX_INSIGHTS).
PROMPT_SUMMARY = """=== DAS SPIEL IST ZU ENDE: {result_upper} (Runde {round_number}) ===

=== LETZTE MELDUNGEN ===
{ending}

=== DEIN NOTIZBUCH ===
{notebook}

=== DEINE LETZTEN ZÜGE ===
{history}

Ziehe jetzt Resümee – so, wie ein menschlicher Spieler sich nach dem Spiel etwas fürs nächste Mal merkt. Was hast du über die Spielwelt gelernt (Orte, Wege, Objekte und was man damit tun kann, Gefahren, Figuren)? Was würdest du beim nächsten Mal anders machen? Formuliere jede Erkenntnis als einen kurzen, konkreten, allgemeingültigen Satz, z. B. 'Vorsicht: <Aktion> am Ort <X> hat <Folge>.' oder '<Objekt> kann man <Verb> – dann passiert <Wirkung>.' Nur, was du in diesem Spiel selbst erlebt oder gelesen hast – nichts erfinden, nichts wiederholen, was schon unter 'Erfahrungen aus früheren Spielen' steht. Rufe für jede Erkenntnis 'erfahrung_notieren' auf (höchstens {max_insights})."""
PROMPT_SUMMARY_NO_MOVES = "(keine Züge)"      # Platzhalter für {history}
PROMPT_SUMMARY_NO_MESSAGES = "(nichts)"       # Platzhalter für {ending}
