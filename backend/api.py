"""FastAPI backend exposing the game-review engine to the frontend (Phase 2).

Endpoints
---------
POST /analyze        Analyse a PGN; store the full review in memory.
GET  /game           Lightweight move list + game metadata.
GET  /move/{index}   Full state for one move: FEN, eval, classification, and
                     visual-cue data (a marker square + a best-move arrow).
POST /evaluate       Evaluate an arbitrary FEN (powers the interactive
                     self-analysis board): eval bar + top engine lines.
GET  /library        Catalogue of pre-reviewed famous games.
GET  /library/{id}   Load one stored review as the active game (like /game).
GET  /                Health check / whether a game is currently loaded.

Multi-user
----------
Several browsers can share one backend. Each sends an opaque ``X-Session-Id``
header (generated client-side); per-session state keeps each user's loaded game
and analysis progress separate. A bounded semaphore (MAX_CONCURRENT_ANALYSES)
caps how many Stockfish reviews run at once so the machine isn't swamped.

Run it:
    uvicorn backend.api:app --reload --port 8000
"""

from __future__ import annotations

import io
import json
import os
import threading
import time
from dataclasses import replace
from typing import Optional

import chess
import chess.engine
import chess.pgn
from fastapi import FastAPI, Header, HTTPException
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
# Per-session state (multi-user)
# --------------------------------------------------------------------------- #
# This is still a small, local tool, but several people can now point their
# browsers at the same backend. Each browser sends an opaque "X-Session-Id"
# header (generated client-side, persisted in localStorage); we keep one slice
# of state per session so users don't clobber each other's loaded game.
class _Progress:
    """Live progress of one session's /analyze job."""
    def __init__(self) -> None:
        self.status: str = "idle"   # idle | queued | running | done | error
        self.done: int = 0
        self.total: int = 0
        self.error: Optional[str] = None


class Session:
    """Everything one connected user is currently looking at."""
    def __init__(self) -> None:
        self.review: Optional[GameReview] = None
        self.pgn: Optional[str] = None
        self.progress = _Progress()
        self.last_seen = time.time()


_DEFAULT_SID = "default"
_MAX_SESSIONS = 200          # cap memory; least-recently-used sessions are evicted
_sessions: dict[str, Session] = {}
_sessions_lock = threading.Lock()
_progress_lock = threading.Lock()


def _get_session(session_id: Optional[str]) -> Session:
    """Fetch (or lazily create) the Session for an X-Session-Id header value."""
    sid = (session_id or "").strip() or _DEFAULT_SID
    now = time.time()
    with _sessions_lock:
        sess = _sessions.get(sid)
        if sess is None:
            if len(_sessions) >= _MAX_SESSIONS:
                # Evict the least-recently-seen session to bound memory.
                oldest = min(_sessions, key=lambda k: _sessions[k].last_seen)
                del _sessions[oldest]
            sess = _sessions[sid] = Session()
        sess.last_seen = now
        return sess


# --------------------------------------------------------------------------- #
# Stockfish concurrency limit
# --------------------------------------------------------------------------- #
# Each /analyze job spawns its own Stockfish process and runs it flat-out for a
# whole game, so letting every user start one at once would swamp the machine.
# A bounded semaphore caps how many reviews run engines simultaneously; extra
# jobs queue (their session shows "queued") until a slot frees up. Tune with the
# MAX_CONCURRENT_ANALYSES env var.
MAX_CONCURRENT_ANALYSES = max(1, int(os.environ.get("MAX_CONCURRENT_ANALYSES", "2")))
_analysis_slots = threading.BoundedSemaphore(MAX_CONCURRENT_ANALYSES)

# A single long-lived engine powers /evaluate so the interactive board feels
# snappy (no per-request process spawn). python-chess engines are not safe for
# concurrent use, so a lock serialises analysis calls (a hard cap of 1 eval at a
# time, independent of the analysis semaphore above).
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


def _require_review(sess: Session) -> GameReview:
    if sess.review is None:
        raise HTTPException(status_code=404, detail="No game loaded. POST a PGN to /analyze first.")
    return sess.review


# --------------------------------------------------------------------------- #
# Pre-reviewed famous-games library (built by backend/build_library.py)
# --------------------------------------------------------------------------- #
_LIBRARY_DIR = os.path.join(os.path.dirname(__file__), "data", "library")


def _review_from_dict(d: dict) -> GameReview:
    """Reconstruct a GameReview from a stored library JSON (inverse of to_dict)."""
    moves = [MoveReview(**m) for m in d["moves"]]
    return GameReview(
        white=d["white"], black=d["black"], result=d["result"],
        engine_name=d["engine_name"], moves=moves,
        summary=d["summary"], opening=d.get("opening"),
    )


# --------------------------------------------------------------------------- #
# Endpoints
# --------------------------------------------------------------------------- #
@app.get("/")
def root(x_session_id: Optional[str] = Header(None)) -> dict:
    sess = _get_session(x_session_id)
    loaded = sess.review is not None
    return {
        "status": "ok",
        "game_loaded": loaded,
        "move_count": len(sess.review.moves) if loaded else 0,
        "active_sessions": len(_sessions),
        "max_concurrent_analyses": MAX_CONCURRENT_ANALYSES,
    }


def _run_analysis_job(req: AnalyzeRequest, sess: Session) -> None:
    """Background worker: wait for an engine slot, then analyse the game."""
    prog = sess.progress
    config = replace(DEFAULT_ANALYSIS, time_per_move=req.time_per_move, depth=req.depth)

    def on_progress(done: int, total: int) -> None:
        prog.done = done   # plain int assignment is atomic enough for polling

    # Block here until a Stockfish slot is free — this caps total engine load
    # no matter how many users hit Analyze at once.
    _analysis_slots.acquire()
    try:
        with _progress_lock:
            prog.status = "running"
        with StockfishEngine(config=config) as engine:
            review = analyse_game(
                req.pgn, engine, config=config,
                detect_brilliancies=req.detect_brilliancies,
                progress=False, progress_cb=on_progress,
            )
        sess.review = review
        sess.pgn = req.pgn
        with _progress_lock:
            prog.done = prog.total
            prog.status = "done"
    except Exception as exc:  # noqa: BLE001 — surface any failure via /progress
        with _progress_lock:
            prog.status = "error"
            prog.error = str(exc)
    finally:
        _analysis_slots.release()


@app.post("/analyze")
def analyze(req: AnalyzeRequest, x_session_id: Optional[str] = Header(None)) -> dict:
    """Kick off a background review of a PGN; poll GET /progress for status."""
    sess = _get_session(x_session_id)

    # Cheap up-front validation so obviously-bad input fails fast with 400.
    game = chess.pgn.read_game(io.StringIO(req.pgn))
    total = sum(1 for _ in game.mainline_moves()) if game else 0
    if total == 0:
        raise HTTPException(status_code=400, detail="No moves found — the PGN is empty or could not be parsed.")

    with _progress_lock:
        if sess.progress.status in ("queued", "running"):
            raise HTTPException(status_code=409, detail="An analysis is already in progress for this session.")
        # "queued" until the job thread acquires a Stockfish slot; it flips to
        # "running" once the engine actually starts.
        sess.progress.status = "queued"
        sess.progress.done = 0
        sess.progress.total = total
        sess.progress.error = None

    threading.Thread(target=_run_analysis_job, args=(req, sess), daemon=True).start()
    return {"status": "started", "total_plies": total}


@app.get("/progress")
def progress(x_session_id: Optional[str] = Header(None)) -> dict:
    """Live progress of this session's current/last analysis job."""
    prog = _get_session(x_session_id).progress
    return {
        "status": prog.status,
        "done": prog.done,
        "total": prog.total,
        "error": prog.error,
    }


@app.get("/game")
def get_game(x_session_id: Optional[str] = Header(None)) -> dict:
    """Return game metadata and a lightweight list of moves."""
    review = _require_review(_get_session(x_session_id))
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
def get_move(index: int, x_session_id: Optional[str] = Header(None)) -> dict:
    """Full per-move state, including visual-cue data for the board overlay."""
    review = _require_review(_get_session(x_session_id))
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


@app.get("/library")
def list_library() -> dict:
    """Catalogue of pre-reviewed famous games (built by backend/build_library.py)."""
    path = os.path.join(_LIBRARY_DIR, "index.json")
    if not os.path.isfile(path):
        return {"games": []}
    with open(path) as fh:
        return json.load(fh)


@app.get("/library/{game_id}")
def load_library_game(game_id: str, x_session_id: Optional[str] = Header(None)) -> dict:
    """Load a stored review into the session's active game and return it like GET /game."""
    # Guard against path traversal — ids are lowercase slug + digits + hyphens.
    if not game_id.replace("-", "").replace("_", "").isalnum():
        raise HTTPException(status_code=400, detail="Invalid game id.")
    path = os.path.join(_LIBRARY_DIR, f"{game_id}.json")
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail=f"Unknown library game '{game_id}'.")
    with open(path) as fh:
        data = json.load(fh)
    sess = _get_session(x_session_id)
    sess.review = _review_from_dict(data)
    sess.pgn = None
    return get_game(x_session_id)


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
