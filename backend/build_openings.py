#!/usr/bin/env python3
"""Build backend/data/openings.json from the lichess ECO dataset.

The lichess `chess-openings` repo ships five TSVs (a–e) with columns
`eco`, `name`, `pgn`. We replay each line and key the *resulting position's*
EPD (board layout + side + castling + en-passant, no move clocks) to the
opening name, so detection is a simple per-position lookup at review time.

Run once:  python -m backend.build_openings
"""

from __future__ import annotations

import json
import os
import urllib.request

import chess

BASE = "https://raw.githubusercontent.com/lichess-org/chess-openings/master"
FILES = ["a.tsv", "b.tsv", "c.tsv", "d.tsv", "e.tsv"]
OUT = os.path.join(os.path.dirname(__file__), "data", "openings.json")


def _epd_for(pgn: str) -> str | None:
    board = chess.Board()
    for token in pgn.split():
        if token[0].isdigit() or token in ("1-0", "0-1", "1/2-1/2", "*"):
            continue  # move numbers / results
        try:
            board.push_san(token)
        except ValueError:
            return None
    return board.epd()


def main() -> None:
    table: dict[str, list[str]] = {}
    for fname in FILES:
        url = f"{BASE}/{fname}"
        print(f"Downloading {url}")
        with urllib.request.urlopen(url) as resp:
            text = resp.read().decode("utf-8")
        for line in text.splitlines()[1:]:  # skip header
            if not line.strip():
                continue
            eco, name, pgn = line.split("\t")
            epd = _epd_for(pgn)
            if epd and epd not in table:
                table[epd] = [eco, name]

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(table, fh, ensure_ascii=False)
    print(f"Wrote {len(table)} openings to {OUT}")


if __name__ == "__main__":
    main()
