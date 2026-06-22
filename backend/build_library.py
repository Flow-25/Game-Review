"""Pre-review the famous-games base into ready-to-browse JSON.

Usage:
    python -m backend.build_library --check          # validate PGNs only (no engine)
    python -m backend.build_library                  # full review (default 0.2s/move)
    python -m backend.build_library --time 0.3       # slower, stronger review

Outputs (under backend/data/library/):
    <id>.json        full GameReview.to_dict() + display metadata
    index.json       lightweight catalogue the frontend lists
"""

from __future__ import annotations

import argparse
import io
import json
import os

import chess.pgn

from .analyzer import analyse_game
from .config import DEFAULT_ANALYSIS, find_stockfish
from .engine import StockfishEngine
from .famous_games import FAMOUS_GAMES

_DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "library")


def build_pgn(game: dict) -> str:
    """Assemble a full PGN (headers + movetext + result) from a library entry."""
    headers = (
        f'[Event "{game["event"]}"]\n'
        f'[Date "{game["year"]}.??.??"]\n'
        f'[White "{game["white"]}"]\n'
        f'[Black "{game["black"]}"]\n'
        f'[Result "{game["result"]}"]\n'
    )
    return f"{headers}\n{game['moves']} {game['result']}\n"


def validate(game: dict) -> tuple[bool, str]:
    """Parse the movetext and confirm it is fully legal (no truncation)."""
    pgn = build_pgn(game)
    parsed = chess.pgn.read_game(io.StringIO(pgn))
    if parsed is None:
        return False, "could not parse"
    if parsed.errors:
        return False, f"illegal move(s): {parsed.errors[0]}"
    plies = sum(1 for _ in parsed.mainline_moves())
    if plies == 0:
        return False, "no moves"
    return True, f"{plies} plies"


def _accuracy(avg_cpl: float) -> float:
    """Lichess-style accuracy% from average centipawn loss (mirrors the frontend)."""
    import math

    acc = 103.1668 * math.exp(-0.04354 * (avg_cpl / 100)) - 3.1669
    return round(max(0.0, min(100.0, acc)), 1)


def main() -> None:
    ap = argparse.ArgumentParser(description="Build the pre-reviewed famous-games library.")
    ap.add_argument("--check", action="store_true", help="Validate PGNs only; skip the engine.")
    ap.add_argument("--time", type=float, default=0.2, help="Engine time per move (seconds).")
    args = ap.parse_args()

    # 1) Validate every game first so transcription errors surface immediately.
    print(f"Validating {len(FAMOUS_GAMES)} games…")
    valid: list[dict] = []
    for g in FAMOUS_GAMES:
        ok, msg = validate(g)
        flag = "OK " if ok else "FAIL"
        print(f"  [{flag}] {g['id']:<32} {msg}")
        if ok:
            valid.append(g)
    print(f"{len(valid)}/{len(FAMOUS_GAMES)} games valid.")

    if args.check:
        return
    if not valid:
        print("Nothing to build.")
        return

    os.makedirs(_DATA_DIR, exist_ok=True)
    config = DEFAULT_ANALYSIS.__class__(time_per_move=args.time)
    find_stockfish()  # fail fast with a helpful message if missing

    index: list[dict] = []
    with StockfishEngine(config=config) as engine:
        for i, g in enumerate(valid, 1):
            print(f"\n[{i}/{len(valid)}] Reviewing {g['nickname']} ({g['white']} vs {g['black']})…")
            pgn = build_pgn(g)
            review = analyse_game(pgn, engine, config=config, progress=False)
            out = review.to_dict()
            out.update({
                "id": g["id"], "nickname": g["nickname"], "event": g["event"],
                "year": g["year"], "description": g["description"],
            })
            with open(os.path.join(_DATA_DIR, f"{g['id']}.json"), "w") as fh:
                json.dump(out, fh)

            sw, sb = review.summary["white"], review.summary["black"]
            index.append({
                "id": g["id"],
                "white": review.white,
                "black": review.black,
                "result": review.result,
                "nickname": g["nickname"],
                "event": g["event"],
                "year": g["year"],
                "description": g["description"],
                "opening": review.opening,
                "move_count": len(review.moves),
                "accuracy_white": _accuracy(sw["avg_centipawn_loss"]),
                "accuracy_black": _accuracy(sb["avg_centipawn_loss"]),
            })

    with open(os.path.join(_DATA_DIR, "index.json"), "w") as fh:
        json.dump({"games": index}, fh, indent=2)
    print(f"\nWrote {len(index)} reviewed games + index to {_DATA_DIR}")


if __name__ == "__main__":
    main()
