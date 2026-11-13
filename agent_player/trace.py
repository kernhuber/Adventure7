"""JSONL-Protokoll eines Agentenspiels: eine Zeile pro Ereignis.

Die Spur ist das Gegenstück zum Panel: das Panel zeigt live, die Spur bleibt für die Auswertung
(und als Kursmaterial). Ordner `agent_runs/` ist git-ignoriert.
"""
import json
import os
import time


class Trace:
    def __init__(self, folder: str = "agent_runs"):
        os.makedirs(folder, exist_ok=True)
        self.file_path = os.path.join(folder, time.strftime("%Y-%m-%d_%H-%M-%S") + ".jsonl")

    def write(self, event: dict) -> None:
        line = {"zeit": round(time.time(), 2), **event}
        with open(self.file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")
