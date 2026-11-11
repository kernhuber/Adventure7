"""Alle Einstellungen des Agent-Spielers an EINER Stelle.

LERNPUNKT: Grenzen (Aufrufe pro Runde, Runden pro Spiel, Tokens) gehören in die
Konfiguration und nicht verstreut in den Code. Wer experimentieren will
("Was, wenn der Agent nur 3 Aufrufe pro Runde hat?"), ändert nur diese Datei.
"""

# --- Spiel -------------------------------------------------------------------
AGENT_SPIELERNAME = "Agent"       # Name der Spielfigur im Agentenmodus
# Hund an/aus: gilt wie im normalen Spiel allein utils.NODOG (False = Hund dabei) – keine zweite Einstellung hier.

# Ausgang des Hundekampfs (ersetzt das Minispiel): Gewichte für (Hund gewinnt = Spiel verloren, Spieler gewinnt, Gleichstand).
# (1, 1, 1) = gleich wahrscheinlich. Z. B. (1, 3, 2) macht eine Niederlage seltener.
MINISPIEL_GEWICHTE = (1, 1, 1)
# So lange zeigt der Browser das Kampf-Overlay (3 s Kampf + 3 s Ergebnis + Ausblenden); der Server wartet entsprechend.
DOGFIGHT_DAUER_S = 6.6

# --- Modell (ab Meilenstein 2) ----------------------------------------------
AGENT_MODELL = "gemini-2.5-flash"

# --- Grenzen (ab Meilenstein 2) ---------------------------------------------
MAX_AUFRUFE_PRO_RUNDE = 8         # danach: "mach jetzt einen Zug!"
MAX_RUNDEN = 100                  # Rundenlimit pro Spiel
MAX_TOKENS_GESAMT = None          # None = kein Tokenlimit
VERLAUF_RUNDEN = 10               # so viele frühere Runden stehen im Prompt
MAX_CHAT_WORTWECHSEL = 10         # Gesprächslimit (Meilenstein 3)

# --- Experience.md: Gedächtnis über Spiele hinweg (experience.py) ---------------------------------
EXPERIENCE_AKTIV = True                 # False = Agent schreibt/liest keine Erfahrungen (Experiment: "ohne Lernen")
EXPERIENCE_DATEI = "Experience.md"      # im Projektordner; man darf sie von Hand bearbeiten
EXPERIENCE_MAX_ZEICHEN = 6000           # so viel (die neuesten Einträge) steht im Prompt
EXPERIENCE_MAX_ERKENNTNISSE = 8         # so viele neue Erkenntnisse pro Spiel
EXPERIENCE_VERLAUF_RUNDEN = 25          # so viele letzte Züge sieht der Agent beim Resümee

# --- Zuschauermodus ----------------------------------------------------------
START_TEMPO_MS = 800              # Verzögerung zwischen Schritten (im Panel einstellbar)
