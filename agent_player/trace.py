"""JSONL-Protokoll eines Agentenspiels: eine Zeile pro Ereignis.

Die Spur ist das Gegenstück zum Panel: das Panel zeigt live, die Spur bleibt für die Auswertung
(und als Kursmaterial). Ordner `agent_runs/` ist git-ignoriert.
"""
import json
import os
import time


class Spur:
    def __init__(self, ordner: str = "agent_runs"):
        os.makedirs(ordner, exist_ok=True)
        self.pfad = os.path.join(ordner, time.strftime("%Y-%m-%d_%H-%M-%S") + ".jsonl")

    def schreibe(self, ereignis: dict) -> None:
        zeile = {"zeit": round(time.time(), 2), **ereignis}
        with open(self.pfad, "a", encoding="utf-8") as f:
            f.write(json.dumps(zeile, ensure_ascii=False) + "\n")
