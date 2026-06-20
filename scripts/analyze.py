#!/usr/bin/env python3
"""CLI entry point for Phase 1 — analyse a PGN and print a move-by-move review.

Usage:
    python -m scripts.analyze                 # analyse the bundled sample game
    python -m scripts.analyze game.pgn        # analyse a PGN file
    python -m scripts.analyze game.pgn -t 0.3 # 0.3s per move
    python -m scripts.analyze game.pgn -o out.json
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

# Allow running as `python scripts/analyze.py` from the project root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.analyzer import analyse_game  # noqa: E402
from backend.config import DEFAULT_ANALYSIS  # noqa: E402
from backend.engine import StockfishEngine  # noqa: E402
from backend.sample_game import SAMPLE_PGN  # noqa: E402


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Chess game review (Phase 1 core).")
    p.add_argument("pgn", nargs="?", help="Path to a PGN file (default: bundled sample game).")
    p.add_argument("-t", "--time", type=float, default=DEFAULT_ANALYSIS.time_per_move,
                   help="Seconds of analysis per move (default: %(default)s).")
    p.add_argument("-d", "--depth", type=int, default=None,
                   help="Fixed search depth (overrides --time if set).")
    p.add_argument("-o", "--output", type=str, default=None,
                   help="Write the full review as JSON to this file.")
    p.add_argument("--quiet", action="store_true", help="Suppress per-move progress lines.")
    return p.parse_args()


def main() -> int:
    args = _parse_args()

    if args.pgn:
        pgn_text = Path(args.pgn).read_text(encoding="utf-8")
        source = args.pgn
    else:
        pgn_text = SAMPLE_PGN
        source = "bundled sample (Morphy 'Opera Game', 1858)"

    config = replace(DEFAULT_ANALYSIS, time_per_move=args.time, depth=args.depth)

    print(f"Analysing: {source}")
    print(f"Settings : {'depth ' + str(config.depth) if config.depth else str(config.time_per_move) + 's'}/move\n")

    with StockfishEngine(config=config) as engine:
        print(f"Engine   : {engine.name}\n")
        review = analyse_game(pgn_text, engine, config=config, progress=not args.quiet)

    # -- summary -------------------------------------------------------------
    print("\n" + "=" * 60)
    print(f"{review.white}  vs  {review.black}   [{review.result}]")
    print("=" * 60)
    for color in ("white", "black"):
        s = review.summary[color]
        name = review.white if color == "white" else review.black
        counts = "  ".join(f"{k}:{v}" for k, v in s.items() if k != "avg_centipawn_loss" and v)
        print(f"\n{color.capitalize():<6} ({name})")
        print(f"  avg centipawn loss: {s['avg_centipawn_loss']}")
        print(f"  {counts}")

    if args.output:
        Path(args.output).write_text(json.dumps(review.to_dict(), indent=2), encoding="utf-8")
        print(f"\nFull review written to {args.output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
