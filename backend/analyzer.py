"""Core game-review logic: walk a game move-by-move and score each move.

The algorithm for one move (the standard "centipawn loss" method):

  1. With the position *before* the move, ask the engine for its evaluation and
     its best move. This eval is the best the mover could hope to achieve.
  2. Play the move actually chosen, then ask the engine to evaluate the *new*
     position. Flipped to the mover's point of view, this is what they actually
     got.
  3. centipawn_loss = best_eval − actual_eval  (clamped at 0).
     A small loss means a near-optimal move; a large loss means a blunder.

All evaluations are normalised to centipawns from a single point of view so the
subtraction is always meaningful, and "mate in N" is mapped to a large finite
centipawn value (see AnalysisConfig.mate_score_cp).
"""

from __future__ import annotations

import io
from dataclasses import dataclass, asdict
from typing import Optional

import chess
import chess.pgn

from .classifier import classify
from .brilliancy import detect_brilliant
from .openings import detect_opening
from .config import (
    AnalysisConfig,
    BrilliantConfig,
    ClassificationThresholds,
    DEFAULT_ANALYSIS,
    DEFAULT_BRILLIANT,
    DEFAULT_THRESHOLDS,
)
from .engine import StockfishEngine


@dataclass
class MoveReview:
    """Everything we learned about a single played move."""

    ply: int                 # 1-based half-move index
    move_number: int         # full-move number (1, 1, 2, 2, ...)
    color: str               # "white" | "black"
    san: str                 # the move that was played, e.g. "Nf3"
    uci: str                 # same move in UCI, e.g. "g1f3"
    best_san: str            # engine's recommended move in SAN
    best_uci: str
    eval_before_cp: int      # position eval before the move, mover's POV (cp)
    eval_after_cp: int       # position eval after the move, mover's POV (cp)
    eval_white_cp: int       # eval after the move from White's POV (for graphs)
    mate_in: Optional[int]   # signed mate distance from White's POV, else None
    centipawn_loss: int
    classification: str
    sacrificed_cp: int       # material offered if this was a (Brilliant) sacrifice, else 0
    is_book: bool
    fen_before: str          # FEN of the position before the move (for best-move arrow)
    fen_after: str           # FEN of the position after the move (board to display)


@dataclass
class GameReview:
    """Aggregated result for a whole game."""

    white: str
    black: str
    result: str
    engine_name: str
    moves: list[MoveReview]
    summary: dict  # per-color counts of each classification
    opening: Optional[dict] = None  # {"eco","name","ply"} or None

    def to_dict(self) -> dict:
        return {
            "white": self.white,
            "black": self.black,
            "result": self.result,
            "engine_name": self.engine_name,
            "opening": self.opening,
            "moves": [asdict(m) for m in self.moves],
            "summary": self.summary,
        }


def _pov_cp(score: chess.engine.PovScore, color: chess.Color, mate_score: int) -> int:
    """Centipawn value of `score` from `color`'s point of view."""
    return score.pov(color).score(mate_score=mate_score)


def analyse_game(
    pgn: str,
    engine: StockfishEngine,
    *,
    config: AnalysisConfig = DEFAULT_ANALYSIS,
    thresholds: ClassificationThresholds = DEFAULT_THRESHOLDS,
    brilliant_config: BrilliantConfig = DEFAULT_BRILLIANT,
    detect_brilliancies: bool = True,
    progress: bool = True,
    progress_cb=None,
) -> GameReview:
    """Analyse a full game given as a PGN string. Engine must already be open."""

    game = chess.pgn.read_game(io.StringIO(pgn))
    if game is None:
        raise ValueError("Could not parse a game from the provided PGN.")

    board = game.board()
    reviews: list[MoveReview] = []

    moves_list = list(game.mainline_moves())
    total_plies = len(moves_list)
    if total_plies == 0:
        # python-chess parses unrecognised text into an empty game rather than
        # failing, so guard against "no moves" explicitly.
        raise ValueError("No moves found — the PGN is empty or could not be parsed.")

    # Opening (ECO) detection is a cheap, engine-free position lookup.
    opening = detect_opening(moves_list)

    ply = 0
    for move in moves_list:
        ply += 1
        mover = board.turn  # color to move = the player making THIS move
        is_book = ply <= config.book_plies

        # 1) Evaluate the position *before* the move. multipv=2 also gives us the
        #    second-best line, so we can tell when only one move holds ("Great").
        legal_count = board.legal_moves.count()
        infos = engine.analyse(board, multipv=2)
        info_before = infos[0]
        best_eval = _pov_cp(info_before["score"], mover, config.mate_score_cp)
        second_eval = (
            _pov_cp(infos[1]["score"], mover, config.mate_score_cp) if len(infos) > 1 else None
        )
        pv = info_before.get("pv") or []
        best_move = pv[0] if pv else None
        best_san = board.san(best_move) if best_move else "—"
        best_uci = best_move.uci() if best_move else "—"

        # "Only move": a real choice exists, the best is much better than the
        # rest, and the position is still contested (not an already-decided game
        # or a forced mate). (One legal move = forced, not Great.)
        is_only_move = (
            legal_count > 1
            and second_eval is not None
            and (best_eval - second_eval) >= thresholds.only_move_gap
            and abs(best_eval) <= thresholds.only_move_max_eval
        )

        # Record the played move in SAN *before* pushing it (SAN needs context).
        san = board.san(move)
        uci = move.uci()
        is_engine_best = best_move is not None and move == best_move

        # Snapshot the pre-move position (FEN for the best-move arrow; full copy
        # only when we may need brilliancy deep-verification).
        fen_before = board.fen()
        board_before = board.copy(stack=False) if detect_brilliancies and not is_book else None

        # 2) Play the move, evaluate the resulting position.
        board.push(move)
        fen_after = board.fen()
        info_after = engine.analyse(board)
        actual_eval = _pov_cp(info_after["score"], mover, config.mate_score_cp)
        eval_white = _pov_cp(info_after["score"], chess.WHITE, config.mate_score_cp)
        score_white = info_after["score"].white()
        mate_in = score_white.mate() if score_white.is_mate() else None

        # 3) Centipawn loss (never negative — the played move can't beat "best").
        cpl = max(0, best_eval - actual_eval)

        label = classify(
            cpl,
            is_book=is_book,
            is_engine_best=is_engine_best,
            thresholds=thresholds,
        )

        # 4) Brilliant? A sound sacrifice can override the base label. We only
        #    pay for the deep-verification search on real sacrifice candidates.
        sacrificed_cp = 0
        if board_before is not None:
            result = detect_brilliant(
                engine, board_before, board, move, cpl, config=brilliant_config
            )
            if result.is_brilliant:
                label = "Brilliant"
                sacrificed_cp = result.sacrificed_cp

        # 5) Great move: found the single move that holds. Doesn't override a
        #    Brilliant, and only applies when the player actually played a top
        #    move (small loss) outside of book.
        if (
            label not in ("Brilliant", "Book")
            and is_only_move
            and cpl <= thresholds.excellent
        ):
            label = "Great"

        reviews.append(
            MoveReview(
                ply=ply,
                move_number=(ply + 1) // 2,
                color="white" if mover == chess.WHITE else "black",
                san=san,
                uci=uci,
                best_san=best_san,
                best_uci=best_uci,
                eval_before_cp=best_eval,
                eval_after_cp=actual_eval,
                eval_white_cp=eval_white,
                mate_in=mate_in,
                centipawn_loss=cpl,
                classification=label,
                sacrificed_cp=sacrificed_cp,
                is_book=is_book,
                fen_before=fen_before,
                fen_after=fen_after,
            )
        )

        if progress:
            marker = "  <<< BRILLIANT (!!)" if label == "Brilliant" else ""
            print(
                f"  [{ply:>3}/{total_plies}] "
                f"{reviews[-1].color:>5} {san:<7} "
                f"best={best_san:<7} cpl={cpl:>4}  {label}{marker}"
            )

        if progress_cb is not None:
            progress_cb(ply, total_plies)

    headers = game.headers
    summary = _summarise(reviews, thresholds)

    return GameReview(
        white=headers.get("White", "?"),
        black=headers.get("Black", "?"),
        result=headers.get("Result", "*"),
        engine_name=engine.name,
        moves=reviews,
        summary=summary,
        opening=opening,
    )


def _summarise(
    reviews: list[MoveReview],
    thresholds: ClassificationThresholds,
) -> dict:
    """Count classifications per color and compute average centipawn loss."""
    summary: dict = {"white": {}, "black": {}}
    cpl_totals = {"white": 0, "black": 0}
    cpl_counts = {"white": 0, "black": 0}

    for label in thresholds.labels:
        summary["white"][label] = 0
        summary["black"][label] = 0

    for r in reviews:
        summary[r.color][r.classification] += 1
        if r.classification != "Book":  # genuine book moves shouldn't skew accuracy
            cpl_totals[r.color] += r.centipawn_loss
            cpl_counts[r.color] += 1

    for color in ("white", "black"):
        n = cpl_counts[color]
        summary[color]["avg_centipawn_loss"] = round(cpl_totals[color] / n, 1) if n else 0.0

    return summary
