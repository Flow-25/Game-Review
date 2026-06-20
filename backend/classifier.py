"""Turn a raw centipawn loss into a human-friendly move-quality label."""

from __future__ import annotations

from .config import ClassificationThresholds, DEFAULT_THRESHOLDS


def classify(
    centipawn_loss: int,
    *,
    is_book: bool = False,
    is_engine_best: bool = False,
    thresholds: ClassificationThresholds = DEFAULT_THRESHOLDS,
) -> str:
    """Map centipawn loss (>= 0) to a label.

    Args:
        centipawn_loss: eval(best) - eval(played), from the mover's POV.
        is_book: True if the move is still within the opening-book window.
        is_engine_best: True if the played move equals the engine's top choice.
                        Such moves are always "Best" regardless of tiny rounding.
    """
    # "Book" only excuses *reasonable* opening moves. A move inside the book
    # window that still loses a lot (e.g. walking into mate on move 3) must be
    # flagged on its merits, not hidden behind the opening label.
    if is_book and centipawn_loss <= thresholds.inaccuracy:
        return "Book"
    if is_engine_best or centipawn_loss <= thresholds.best:
        return "Best"
    if centipawn_loss <= thresholds.excellent:
        return "Excellent"
    if centipawn_loss <= thresholds.good:
        return "Good"
    if centipawn_loss <= thresholds.inaccuracy:
        return "Inaccuracy"
    if centipawn_loss <= thresholds.mistake:
        return "Mistake"
    return "Blunder"
