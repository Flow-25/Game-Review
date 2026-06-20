"""FastAPI backend exposing the game-review engine to the frontend (Phase 2).

Endpoints
---------
POST /analyze        Analyse a PGN; store the full review in memory.
GET  /game           Lightweight move list + game metadata.
GET  /move/{index}   Full state for one move: FEN, eval, classification, and
                     visual-cue data (a marker square + a best-move arrow).
POST /evaluate       Evaluate an arbitrary FEN (powers the interactive
                     self-analysis board): eval bar + top engine lines.
GET  /                Health check / whether a game is currently loaded.

Run it:
    uvicorn backend.api:app --reload --port 8000
"""

from __future__ import annotations

import io
import threading
from dataclasses import replace
from typing import Optional

import chess
import chess.engine
import chess.pgn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .analyzer import GameReview, MoveReview, analyse_game
from .config import DEFAULT_ANALYSIS
from .engine import StockfishEngine

app = FastAPI(title="Chess Game Review API", version="0.3.0")

# Allow the local frontend (any origin during development) to call us. For a
# local-only tool wide-open CORS is fine; tighten allow_origins for deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------------------------------- #
# In-memory store (single current game — this is a local single-user tool)
# --------------------------------------------------------------------------- #
class _Store:
    review: Optional[GameReview] = None
    pgn: Optional[str] = None


STATE = _Store()


class _Progress:
    """Live progress of the current /analyze job (single-user tool)."""
    status: str = "idle"   # idle | running | done | error
    done: int = 0
    total: int = 0
    error: Optional[str] = None


PROGRESS = _Progress()
_progress_lock = threading.Lock()

# A single long-lived engine powers /evaluate so the interactive board feels
# snappy (no per-request process spawn). python-chess engines are not safe for
# concurrent use, so a lock serialises analysis calls.
_eval_engine: Optional[StockfishEngine] = None
_eval_lock = threading.Lock()
_eval_init_lock = threading.Lock()


def _eval_engine_instance() -> StockfishEngine:
    global _eval_engine
    if _eval_engine is None:
        with _eval_init_lock:
            if _eval_engine is None:
                _eval_engine = StockfishEngine().open()
    return _eval_engine


@app.on_event("shutdown")
def _shutdown_engine() -> None:
    global _eval_engine
    if _eval_engine is not None:
        _eval_engine.close()
        _eval_engine = None


# --------------------------------------------------------------------------- #
# Request / response models
# --------------------------------------------------------------------------- #
class AnalyzeRequest(BaseModel):
    pgn: str = Field(..., description="A PGN string for a single game.")
    time_per_move: float = Field(
        DEFAULT_ANALYSIS.time_per_move, gt=0, le=5,
        description="Seconds of engine time per move.",
    )
    depth: Optional[int] = Field(
        None, gt=0, le=40,
        description="Fixed search depth (overrides time_per_move if set).",
    )
    detect_brilliancies: bool = Field(
        True, description="Run the (slower) sacrifice/brilliancy detection."
    )


class EvaluateRequest(BaseModel):
    fen: str = Field(..., description="Position to evaluate, in FEN.")
    time_per_move: float = Field(0.3, gt=0, le=5, description="Engine time (s).")
    depth: Optional[int] = Field(None, gt=0, le=40, description="Fixed depth (overrides time).")
    multipv: int = Field(3, ge=1, le=5, description="How many candidate lines to return.")


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _uci_to_squares(uci: str) -> Optional[list[str]]:
    """Turn 'e2e4'/'e7e8q' into ['e2', 'e4'] (for drawing arrows). None if N/A."""
    if not uci or uci == "—" or len(uci) < 4:
        return None
    return [uci[0:2], uci[2:4]]


def _win_probability(cp: int) -> float:
    """Map a White-POV centipawn eval to White's win probability in [0, 1].

    Logistic curve (the standard ~1/400 scaling) — handy for rendering an eval
    bar as a simple percentage instead of raw centipawns.
    """
    return round(1.0 / (1.0 + 10 ** (-cp / 400.0)), 4)


def _eval_payload(m: MoveReview) -> dict:
    """Eval-bar data for one move, from White's point of view."""
    return {
        "cp": m.eval_white_cp,                 # centipawns, White POV (mate -> ±10000)
        "mate": m.mate_in,                     # signed mate-in-N (White POV) or null
        "white_win_prob": _win_probability(m.eval_white_cp),
    }


def _line_payload(board: chess.Board, info: chess.engine.InfoDict) -> Optional[dict]:
    """Build one candidate-line payload (first move + short PV + eval) from an info."""
    pv = info.get("pv") or []
    if not pv:
        return None
    first = pv[0]
    sans, tmp = [], board.copy()
    for mv in pv[:6]:
        sans.append(tmp.san(mv))
        tmp.push(mv)
    sw = info["score"].white()
    cp = sw.score(mate_score=10000)
    uci = first.uci()
    return {
        "uci": uci,
        "san": board.san(first),
        "pv_san": " ".join(sans),
        "arrow": [uci[0:2], uci[2:4]],
        "eval": {"cp": cp, "mate": sw.mate() if sw.is_mate() else None, "white_win_prob": _win_probability(cp)},
    }


def _require_review() -> GameReview:
    if STATE.review is None:
        raise HTTPException(status_code=404, detail="No game loaded. POST a PGN to /analyze first.")
    return STATE.review


# --------------------------------------------------------------------------- #
# Endpoints
# --------------------------------------------------------------------------- #
@app.get("/")
def root() -> dict:
    loaded = STATE.review is not None
    return {
        "status": "ok",
        "game_loaded": loaded,
        "move_count": len(STATE.review.moves) if loaded else 0,
    }


def _run_analysis_job(req: AnalyzeRequest) -> None:
    """Background worker: analyse the game, updating PROGRESS as it goes."""
    config = replace(DEFAULT_ANALYSIS, time_per_move=req.time_per_move, depth=req.depth)

    def on_progress(done: int, total: int) -> None:
        PROGRESS.done = done   # plain int assignment is atomic enough for polling

    try:
        with StockfishEngine(config=config) as engine:
            review = analyse_game(
                req.pgn, engine, config=config,
                detect_brilliancies=req.detect_brilliancies,
                progress=False, progress_cb=on_progress,
            )
        STATE.review = review
        STATE.pgn = req.pgn
        with _progress_lock:
            PROGRESS.done = PROGRESS.total
            PROGRESS.status = "done"
    except Exception as exc:  # noqa: BLE001 — surface any failure via /progress
        with _progress_lock:
            PROGRESS.status = "error"
            PROGRESS.error = str(exc)


@app.post("/analyze")
def analyze(req: AnalyzeRequest) -> dict:
    """Kick off a background review of a PGN; poll GET /progress for status."""
    # Cheap up-front validation so obviously-bad input fails fast with 400.
    game = chess.pgn.read_game(io.StringIO(req.pgn))
    total = sum(1 for _ in game.mainline_moves()) if game else 0
    if total == 0:
        raise HTTPException(status_code=400, detail="No moves found — the PGN is empty or could not be parsed.")

    with _progress_lock:
        if PROGRESS.status == "running":
            raise HTTPException(status_code=409, detail="An analysis is already in progress.")
        PROGRESS.status = "running"
        PROGRESS.done = 0
        PROGRESS.total = total
        PROGRESS.error = None

    threading.Thread(target=_run_analysis_job, args=(req,), daemon=True).start()
    return {"status": "started", "total_plies": total}


@app.get("/progress")
def progress() -> dict:
    """Live progress of the current/last analysis job (for the progress bar)."""
    return {
        "status": PROGRESS.status,
        "done": PROGRESS.done,
        "total": PROGRESS.total,
        "error": PROGRESS.error,
    }


@app.get("/game")
def get_game() -> dict:
    """Return game metadata and a lightweight list of moves."""
    review = _require_review()
    moves = [
        {
            "index": i,
            "ply": m.ply,
            "move_number": m.move_number,
            "color": m.color,
            "san": m.san,
            "classification": m.classification,
            "eval_white_cp": m.eval_white_cp,
        }
        for i, m in enumerate(review.moves)
    ]
    return {
        "white": review.white,
        "black": review.black,
        "result": review.result,
        "engine_name": review.engine_name,
        "opening": review.opening,
        "move_count": len(moves),
        "summary": review.summary,
        "moves": moves,
    }


@app.get("/move/{index}")
def get_move(index: int) -> dict:
    """Full per-move state, including visual-cue data for the board overlay."""
    review = _require_review()
    if index < 0 or index >= len(review.moves):
        raise HTTPException(
            status_code=404,
            detail=f"Move index {index} out of range (0..{len(review.moves) - 1}).",
        )

    m = review.moves[index]
    played_squares = _uci_to_squares(m.uci)
    # The marker (e.g. a blunder badge) sits on the square the moved piece landed
    # on — that's "where it happened".
    marker_square = played_squares[1] if played_squares else None

    return {
        "index": index,
        "ply": m.ply,
        "move_number": m.move_number,
        "color": m.color,
        "san": m.san,
        "uci": m.uci,
        # Board state: position AFTER the move (what the user looks at), plus the
        # pre-move FEN so the frontend can draw the best-move arrow on the
        # position where that choice was actually available.
        "fen": m.fen_after,
        "fen_before": m.fen_before,
        "eval": _eval_payload(m),
        "classification": m.classification,
        "centipawn_loss": m.centipawn_loss,
        "sacrificed_cp": m.sacrificed_cp,
        "is_book": m.is_book,
        # ---- Visual cues -------------------------------------------------- #
        "played_move": {
            "san": m.san,
            "uci": m.uci,
            "arrow": played_squares,          # ['e7', 'e5']
        },
        "marker": {
            "square": marker_square,          # 'e5'
            "type": m.classification,         # 'Blunder' / 'Brilliant' / ...
        },
        "best_move": {
            "san": m.best_san,
            "uci": m.best_uci,
            "arrow": _uci_to_squares(m.best_uci),   # ['e2', 'e4']
        },
    }


@app.post("/evaluate")
def evaluate(req: EvaluateRequest) -> dict:
    """Evaluate any position (for the interactive self-analysis board)."""
    try:
        board = chess.Board(req.fen)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid FEN.")

    turn = "white" if board.turn == chess.WHITE else "black"

    # Terminal positions: report the result directly, no search needed.
    if board.is_game_over():
        if board.is_checkmate():
            white_lost = board.turn == chess.WHITE
            cp = -10000 if white_lost else 10000
            ev = {"cp": cp, "mate": 0, "white_win_prob": 0.0 if white_lost else 1.0}
        else:  # stalemate / draw
            ev = {"cp": 0, "mate": None, "white_win_prob": 0.5}
        return {
            "fen": req.fen, "turn": turn, "is_game_over": True,
            "result": board.result(), "eval": ev, "best_move": None, "lines": [],
        }

    limit = (
        chess.engine.Limit(depth=req.depth) if req.depth
        else chess.engine.Limit(time=req.time_per_move)
    )
    engine = _eval_engine_instance()
    try:
        with _eval_lock:
            infos = engine.analyse(board, limit=limit, multipv=req.multipv)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    lines = [lp for info in infos if (lp := _line_payload(board, info))]
    best = lines[0] if lines else None
    return {
        "fen": req.fen,
        "turn": turn,
        "is_game_over": False,
        "result": "*",
        "eval": best["eval"] if best else {"cp": 0, "mate": None, "white_win_prob": 0.5},
        "best_move": best,
        "lines": lines,
    }
