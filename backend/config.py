"""Central configuration: engine location, analysis limits, classification thresholds.

Keeping these in one place means the web layer (Phase 2+) and any CLI share the
exact same tuning, so a move classified as a "Blunder" looks the same everywhere.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field

# --------------------------------------------------------------------------- #
# Engine discovery
# --------------------------------------------------------------------------- #
# Common locations for the Stockfish binary. On Arch the official `stockfish`
# package installs to /usr/bin/stockfish. We also honour an env override so the
# user can point at a custom build (e.g. a newer NNUE release) without code edits.
# Path to a binary bundled inside this repo (engines/), used as a fallback when
# Stockfish isn't installed system-wide — handy on distros (e.g. Manjaro) whose
# repos don't ship a `stockfish` package.
import glob

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_BUNDLED = sorted(glob.glob(os.path.join(_REPO_ROOT, "engines", "**", "stockfish*"), recursive=True))

_CANDIDATE_PATHS = (
    os.environ.get("STOCKFISH_PATH"),
    shutil.which("stockfish"),
    "/usr/bin/stockfish",
    "/usr/local/bin/stockfish",
    "/usr/games/stockfish",
    *_BUNDLED,
)


def find_stockfish() -> str:
    """Return the first usable Stockfish path, or raise a helpful error."""
    for path in _CANDIDATE_PATHS:
        if path and os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    raise FileNotFoundError(
        "Could not locate the Stockfish binary.\n"
        "  • On Arch Linux:  sudo pacman -S stockfish\n"
        "  • Or set the STOCKFISH_PATH environment variable to your binary."
    )


# --------------------------------------------------------------------------- #
# Analysis tuning
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class AnalysisConfig:
    """Knobs for how deeply/long each position is examined."""

    # Time budget per position, in seconds. 0.1s is fast and "good enough" for a
    # first pass; bump to 0.3–0.5s for stronger, more stable evaluations.
    time_per_move: float = 0.1

    # Optional fixed depth. If set, it overrides the time limit. Leave None to
    # use time-based search (preferred for consistent wall-clock review times).
    depth: int | None = None

    # Number of UCI threads / hash size (MB) handed to the engine.
    threads: int = 1
    hash_mb: int = 128

    # A score is converted from "mate in N" to this centipawn magnitude so that
    # mates dominate the ranking but never overflow arithmetic.
    mate_score_cp: int = 10_000

    # Plies treated as "opening book" and exempt from quality scoring.
    book_plies: int = 10


# --------------------------------------------------------------------------- #
# Move-quality classification (by centipawn loss vs. the engine's best move)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class ClassificationThresholds:
    """Upper bound (inclusive) of centipawn loss for each label.

    Centipawn loss = eval(best move) − eval(played move), from the mover's POV,
    clamped to be non-negative. Lower loss = better move.
    """

    best: int = 10        # within a hair of the engine's choice
    excellent: int = 25
    good: int = 50
    inaccuracy: int = 100
    mistake: int = 300
    # anything worse than `mistake` is a Blunder

    # "Great" / only-move: a move counts as Great when the player finds the one
    # move that holds — i.e. the engine's best is at least this many centipawns
    # better than its second-best, and the player actually played a top move.
    only_move_gap: int = 120
    # ...but only in a still-contested position. If |eval| already exceeds this,
    # the "only move" is just the obvious continuation of a decided game, not a
    # Great find. (This also excludes forced-mate sequences.)
    only_move_max_eval: int = 600

    labels: tuple[str, ...] = field(
        default_factory=lambda: (
            "Brilliant",   # a sound sacrifice (detected separately, see brilliancy.py)
            "Great",       # the only good move in the position ("!")
            "Book",
            "Best",
            "Excellent",
            "Good",
            "Inaccuracy",
            "Mistake",
            "Blunder",
        )
    )


@dataclass(frozen=True)
class BrilliantConfig:
    """Tuning for Brilliant-move (sound sacrifice) detection.

    The detector works in two stages (see backend/brilliancy.py):
      1. CHEAP static filter — does this move *offer* material? We check, via
         Static Exchange Evaluation, whether the opponent can win material by
         capturing. A real sacrifice often looks like a blunder at shallow
         depth, so this stage does NOT trust the fast base evaluation.
      2. DEEP verification — re-search the position with more time/depth to
         confirm the move is actually best (low centipawn loss) and that we are
         not losing afterwards. If both hold despite having offered material,
         the compensation is real → Brilliant.
    """

    # Stage 1: minimum material the opponent could grab for the move to count as
    # a sacrifice, in centipawns. 150 catches exchange sacs (R for minor ≈ 170)
    # and anything bigger; pawn-only "sacs" (100) are excluded.
    min_sacrifice_cp: int = 150

    # Skip deep verification if the move already looks catastrophically bad at
    # base depth (almost certainly a genuine blunder/mate hang, not a sac). This
    # bounds how many positions get the expensive re-search.
    candidate_max_base_cpl: int = 1000

    # Stage 2: depth (preferred) or time for the verification search. Deeper =
    # more reliable brilliancy calls, at the cost of time on candidate moves.
    verify_depth: int | None = 18
    verify_time: float = 0.5

    # Stage 2 acceptance criteria (all in centipawns, from the mover's POV,
    # using the DEEP evaluation):
    max_cpl: int = 50            # the sacrifice must still be ~the best move
    min_eval_after: int = -75    # we must not be losing after the sac
    already_winning_cp: int = 450  # not "brilliant" if we were already winning big

    mate_score_cp: int = 10_000

    def verify_limit(self):
        """Build the engine search limit used for deep verification."""
        import chess.engine

        if self.verify_depth is not None:
            return chess.engine.Limit(depth=self.verify_depth)
        return chess.engine.Limit(time=self.verify_time)


DEFAULT_ANALYSIS = AnalysisConfig()
DEFAULT_THRESHOLDS = ClassificationThresholds()
DEFAULT_BRILLIANT = BrilliantConfig()
