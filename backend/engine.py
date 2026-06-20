"""Thin, safe wrapper around a Stockfish UCI process.

Why a wrapper instead of calling python-chess directly everywhere?
  • One place owns the engine lifecycle (open/configure/close) so we never leak
    a process — important when the web server analyses many games.
  • Usable as a context manager:  `with StockfishEngine() as eng: ...`
"""

from __future__ import annotations

from typing import Optional

import chess
import chess.engine

from .config import AnalysisConfig, DEFAULT_ANALYSIS, find_stockfish


class StockfishEngine:
    """Manages a single Stockfish UCI engine instance."""

    def __init__(
        self,
        config: AnalysisConfig = DEFAULT_ANALYSIS,
        path: Optional[str] = None,
    ) -> None:
        self.config = config
        self.path = path or find_stockfish()
        self._engine: Optional[chess.engine.SimpleEngine] = None

    # -- lifecycle ---------------------------------------------------------- #
    def open(self) -> "StockfishEngine":
        if self._engine is not None:
            return self
        self._engine = chess.engine.SimpleEngine.popen_uci(self.path)
        # Apply only options the engine actually advertises, so we stay
        # compatible across Stockfish versions.
        opts = {}
        if "Threads" in self._engine.options:
            opts["Threads"] = self.config.threads
        if "Hash" in self._engine.options:
            opts["Hash"] = self.config.hash_mb
        if opts:
            self._engine.configure(opts)
        return self

    def close(self) -> None:
        if self._engine is not None:
            self._engine.quit()
            self._engine = None

    def __enter__(self) -> "StockfishEngine":
        return self.open()

    def __exit__(self, *_exc) -> None:
        self.close()

    # -- analysis ----------------------------------------------------------- #
    @property
    def _limit(self) -> chess.engine.Limit:
        if self.config.depth is not None:
            return chess.engine.Limit(depth=self.config.depth)
        return chess.engine.Limit(time=self.config.time_per_move)

    def analyse(
        self,
        board: chess.Board,
        limit: Optional[chess.engine.Limit] = None,
        multipv: Optional[int] = None,
    ):
        """Analyse a position and return the engine's info line(s).

        With the default ``multipv=None`` a single InfoDict is returned (cheap,
        one line). Pass ``multipv=N`` to get a list of the top-N lines — used to
        measure the gap between the best and second-best move for "Great"/only-
        move detection.

        The returned dict(s) include 'score' (a PovScore) and, when a move
        exists, 'pv' whose first element is the engine's recommended move.

        Pass `limit` to override the default search budget for one call — used by
        the brilliancy detector to deep-verify sacrifice candidates.
        """
        if self._engine is None:
            raise RuntimeError("Engine is not open. Call open() or use a 'with' block.")
        return self._engine.analyse(board, limit or self._limit, multipv=multipv)

    @property
    def name(self) -> str:
        if self._engine is None:
            return "Stockfish (closed)"
        return self._engine.id.get("name", "Stockfish")
