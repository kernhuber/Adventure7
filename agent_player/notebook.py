"""Das Notizbuch des Agenten.

LERNPUNKT: Der Agent baut seinen Prompt in jeder Runde FRISCH auf (siehe context.py) und
vergisst dadurch alles, was nicht im Prompt steht. Das Notizbuch ist sein einziges
Langzeitgedächtnis – er muss es selbst pflegen. (Der Zombie macht es ähnlich:
`self.notes` in npc_zombie_state.py, nur überschreibt er es jede Runde komplett,
während der Agent Einträge ANHÄNGT.)
"""


class Notizbuch:
    def __init__(self) -> None:
        self.eintraege: list[str] = []

    def schreiben(self, text: str) -> None:
        """Hängt einen Eintrag an (leere Texte werden ignoriert)."""
        text = text.strip()
        if text:
            self.eintraege.append(text)

    def lesen(self) -> str:
        """Alle Einträge als nummerierte Liste – oder ein Hinweis, dass es leer ist."""
        if not self.eintraege:
            return "(Das Notizbuch ist noch leer.)"
        return "\n".join(f"{i}. {e}" for i, e in enumerate(self.eintraege, start=1))
