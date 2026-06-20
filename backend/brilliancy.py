"""Brilliant-move detection: sound sacrifices.

A "Brilliant" move (chess.com's "!!") is, in essence, a *sound sacrifice*: you
give up material that the opponent can take, but instead of winning it back you
keep an advantage through initiative/attack/compensation.

Two-stage detection (see BrilliantConfig for the knobs):

  Stage 1 — "Is material being offered?"  (cheap, no engine)
      After the move it is the opponent's turn. Using Static Exchange Evaluation
      (SEE) we ask: can the opponent win material by capturing? If the best such
      capture nets them >= `min_sacrifice_cp`, the move offered material.
      Crucially this does NOT rely on the fast base evaluation, because a real
      sacrifice frequently looks like a blunder at shallow depth.

  Stage 2 — "Is the sacrifice sound?"  (deep engine re-search)
      Re-evaluate, deeper, the position before and after the move. If the move is
      still ~the engine's best (small centipawn loss) and we are not losing
      afterwards — yet we were not already winning by a lot — the compensation
      is real. That is a Brilliant move.

SEE here is computed by actually playing out the capture sequence on a board
copy and re-querying attackers each step, so x-ray attackers revealed when a
blocker moves are handled correctly (unlike fast bitboard SEE shortcuts).
"""

from __future__ import annotations

from dataclasses import dataclass

import chess

from .config import BrilliantConfig, DEFAULT_BRILLIANT
from .engine import StockfishEngine

# Material values (centipawns) used only for SEE. King is huge so it is treated
# as the last-resort attacker, never voluntarily traded.
PIECE_VALUES: dict[int, int] = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 20_000,
}


# --------------------------------------------------------------------------- #
# Static Exchange Evaluation
# --------------------------------------------------------------------------- #
def static_exchange_eval(board: chess.Board, move: chess.Move) -> int:
    """Net material (centipawns) the side-to-move wins by playing capture `move`.

    Positive = the capture wins material even after the best recapture sequence.
    Negative = the capture loses material. Assumes `move` is a capture.
    """
    target = move.to_square
    if board.is_en_passant(move):
        captured_value = PIECE_VALUES[chess.PAWN]
    else:
        captured = board.piece_at(target)
        captured_value = PIECE_VALUES[captured.piece_type] if captured else 0

    attacker = board.piece_at(move.from_square)
    if attacker is None:  # defensive; shouldn't happen for a legal capture
        return 0

    board.push(move)
    try:
        # The attacker now sits on `target`; the opponent may recapture.
        gain = captured_value - _recapture_value(board, target, PIECE_VALUES[attacker.piece_type])
    finally:
        board.pop()
    return gain


def _recapture_value(board: chess.Board, square: int, value_on_square: int) -> int:
    """Value gained by the side to move recapturing on `square`, or 0 to stand pat.

    `value_on_square` is the worth of the piece currently sitting on `square`.
    """
    side = board.turn
    attackers = board.attackers(side, square)
    if not attackers:
        return 0

    # Always recapture with the least valuable attacker.
    from_sq = min(attackers, key=lambda s: PIECE_VALUES[board.piece_at(s).piece_type])
    piece = board.piece_at(from_sq)

    # A king cannot recapture onto a square the opponent still defends (illegal
    # move into check); in that case this side has no usable attacker.
    if piece.piece_type == chess.KING and board.attackers(not side, square):
        return 0

    capture = chess.Move(from_sq, square)
    if piece.piece_type == chess.PAWN and chess.square_rank(square) in (0, 7):
        capture = chess.Move(from_sq, square, promotion=chess.QUEEN)

    board.push(capture)
    try:
        # max(0, ...): the side may decline to recapture if it would lose material.
        gain = max(0, value_on_square - _recapture_value(board, square, PIECE_VALUES[piece.piece_type]))
    finally:
        board.pop()
    return gain


def max_opponent_capture_gain(board: chess.Board) -> int:
    """Best material (centipawns) the side-to-move can win via any single capture.

    Applied to the position *after* our move, this is how much material we left
    hanging — i.e. the size of the sacrifice we offered.
    """
    best = 0
    for mv in board.legal_moves:
        if board.is_capture(mv):
            gain = static_exchange_eval(board, mv)
            if gain > best:
                best = gain
    return best


# --------------------------------------------------------------------------- #
# Brilliant detection
# --------------------------------------------------------------------------- #
@dataclass
class BrilliantResult:
    is_brilliant: bool
    sacrificed_cp: int   # material offered (SEE), 0 if none
    reason: str          # human-readable explanation / rejection reason


def _move_capture_value(board_before: chess.Board, move: chess.Move) -> int:
    """Material (centipawns) the move itself captures, 0 for a non-capture."""
    if board_before.is_en_passant(move):
        return PIECE_VALUES[chess.PAWN]
    victim = board_before.piece_at(move.to_square)
    return PIECE_VALUES[victim.piece_type] if victim else 0


def detect_brilliant(
    engine: StockfishEngine,
    board_before: chess.Board,
    board_after: chess.Board,
    move: chess.Move,
    base_cpl: int,
    *,
    config: BrilliantConfig = DEFAULT_BRILLIANT,
) -> BrilliantResult:
    """Decide whether `move` (leading to `board_after`) is Brilliant.

    Args:
        board_before: position with the mover to move (before the move).
        board_after: position after the move (opponent to move).
        move: the move played.
        base_cpl: centipawn loss from the cheap base pass (used only to skip
                  hopeless candidates before paying for a deep search).
    """
    mover = not board_after.turn  # the side that just moved

    # Stage 1: was material *net* offered? The opponent's best capture can win
    # `gross`; but if our move just captured something, that offsets it. A genuine
    # sacrifice gives up more than it grabbed (this rejects ordinary trades and
    # recaptures, e.g. NxN answered by bxN).
    gross = max_opponent_capture_gain(board_after)
    captured = _move_capture_value(board_before, move)
    sac = gross - captured
    if sac < config.min_sacrifice_cp:
        return BrilliantResult(False, max(0, sac), "no net material sacrificed")

    # Don't deep-verify moves that already look like a huge blunder at base depth.
    if base_cpl > config.candidate_max_base_cpl:
        return BrilliantResult(False, sac, "shallow loss too large — likely a real blunder")

    # Stage 2: deep verification of soundness.
    limit = config.verify_limit()
    info_before = engine.analyse(board_before, limit=limit)
    info_after = engine.analyse(board_after, limit=limit)

    eval_before = info_before["score"].pov(mover).score(mate_score=config.mate_score_cp)
    eval_after = info_after["score"].pov(mover).score(mate_score=config.mate_score_cp)
    cpl = max(0, eval_before - eval_after)

    if cpl > config.max_cpl:
        return BrilliantResult(False, sac, f"not best after deep search (cpl={cpl})")
    if eval_after < config.min_eval_after:
        return BrilliantResult(False, sac, f"losing after the sacrifice (eval={eval_after})")
    if eval_before > config.already_winning_cp:
        return BrilliantResult(False, sac, f"already winning before the move (eval={eval_before})")

    return BrilliantResult(True, sac, f"sound sacrifice of ~{sac}cp with compensation")
