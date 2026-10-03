# Persistent best times, one list per grid configuration

from __future__ import annotations

import json
from pathlib import Path

from constants import LEADERBOARD_SIZE

DEFAULT_PATH = Path(__file__).with_name("leaderboard.json")


# Stable string id for a grid type, e.g. '9x9|15|3'
def config_key(rows: int, cols: int, mines: int, decoys: int) -> str:
    return f"{rows}x{cols}|{mines}|{decoys}"


# Split a config key back into rows, cols, mines, decoys
def parse_key(key: str) -> tuple[int, int, int, int]:
    size, mines, decoys = key.split("|")
    rows, cols = size.split("x")
    return int(rows), int(cols), int(mines), int(decoys)


# Readable name for a grid type
def key_label(key: str) -> str:
    rows, cols, mines, decoys = parse_key(key)
    mine_word = "mine" if mines == 1 else "mines"
    decoy_word = "decoy" if decoys == 1 else "decoys"
    return f"{rows}x{cols} · {mines} {mine_word} · {decoys} {decoy_word}"


# Milliseconds as m:ss.t (tenths of a second)
def format_time(ms: int) -> str:
    tenths = max(0, int(ms)) // 100
    minutes = tenths // 600
    seconds = (tenths % 600) / 10
    return f"{minutes}:{seconds:04.1f}"


# Top times per grid type, saved to disk after every win
class Leaderboard:

    def __init__(self, path: Path | None = None):
        self.path = path or DEFAULT_PATH
        self.data: dict[str, list[int]] = {}
        self.load()

    # Loads times from the JSON file (empty if missing)
    def load(self) -> None:
        self.data = {}
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        if not isinstance(raw, dict):
            return
        for key, times in raw.items():
            try:
                parse_key(key)
            except ValueError:
                continue
            if not isinstance(times, list):
                continue
            clean = sorted(int(t) for t in times if isinstance(t, (int, float)) and t >= 0)
            if clean:
                self.data[key] = clean[:LEADERBOARD_SIZE]

    # Saves times to the JSON file
    def save(self) -> None:
        tmp = self.path.with_suffix(".tmp")
        try:
            tmp.write_text(json.dumps(self.data, indent=2), encoding="utf-8")
            tmp.replace(self.path)
        except OSError:
            pass

    # Grid types with times, smallest first
    def keys(self) -> list[str]:
        return sorted((k for k, v in self.data.items() if v), key=parse_key)

    # Best times for one grid type, fastest first
    def times(self, key: str) -> list[int]:
        return list(self.data.get(key, []))

    # Adds a time and returns its rank (None if outside the top list)
    def add(self, key: str, ms: int) -> int | None:
        times = self.data.setdefault(key, [])
        times.append(int(ms))
        times.sort()
        rank = times.index(int(ms)) + 1
        del times[LEADERBOARD_SIZE:]
        self.save()
        return rank if rank <= LEADERBOARD_SIZE else None
