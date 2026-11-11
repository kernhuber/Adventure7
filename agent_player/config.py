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

# --- Modell (ab Meilenstein 2) ----------------------------------------------
AGENT_MODELL = "gemini-2.5-flash"

# --- Grenzen (ab Meilenstein 2) ---------------------------------------------
MAX_AUFRUFE_PRO_RUNDE = 8         # danach: "mach jetzt einen Zug!"
MAX_RUNDEN = 100                  # Rundenlimit pro Spiel
MAX_TOKENS_GESAMT = None          # None = kein Tokenlimit
VERLAUF_RUNDEN = 10               # so viele frühere Runden stehen im Prompt
MAX_CHAT_WORTWECHSEL = 10         # Gesprächslimit (Meilenstein 3)

# --- Zuschauermodus ----------------------------------------------------------
START_TEMPO_MS = 800              # Verzögerung zwischen Schritten (im Panel einstellbar)
