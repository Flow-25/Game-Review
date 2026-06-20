"""Opening (ECO) detection by position lookup against the bundled lichess data."""

from __future__ import annotations

import functools
import json
import os
from typing import Optional

import chess

_PATH = os.path.join(os.path.dirname(__file__), "data", "openings.json")

# Openings essentially never run past ~30 plies; cap the scan for speed.
_MAX_PLIES = 40


@functools.lru_cache(maxsize=1)
def _table() -> dict:
    try:
        with open(_PATH, encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        # Dataset not built — detection simply returns None (see build_openings.py).
        return {}


def detect_opening(moves: list[chess.Move]) -> Optional[dict]:
    """Return the deepest matching opening for a move list, or None.

    Result: {"eco": "C41", "name": "Philidor Defense", "ply": 6}
    """
    table = _table()
    if not table:
        return None

    board = chess.Board()
    best: Optional[dict] = None
    for i, mv in enumerate(moves[:_MAX_PLIES], start=1):
        board.push(mv)
        entry = table.get(board.epd())
        if entry:
            best = {"eco": entry[0], "name": entry[1], "ply": i}
    return best
