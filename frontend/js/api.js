// Tiny fetch wrapper around the FastAPI backend.

const STORAGE_KEY = "gr_api_base";
const SESSION_KEY = "gr_session_id";

export function getApiBase() {
  return localStorage.getItem(STORAGE_KEY) || "http://127.0.0.1:8000";
}

export function setApiBase(url) {
  localStorage.setItem(STORAGE_KEY, url.replace(/\/+$/, ""));
}

// A stable per-browser id so this client keeps its own loaded game on a shared
// backend (multi-user). Generated once and persisted in localStorage.
function getSessionId() {
  let id = localStorage.getItem(SESSION_KEY);
  if (!id) {
    id = (crypto.randomUUID && crypto.randomUUID()) ||
      Date.now().toString(36) + Math.random().toString(36).slice(2);
    localStorage.setItem(SESSION_KEY, id);
  }
  return id;
}

async function request(path, options = {}) {
  const headers = { ...(options.headers || {}), "X-Session-Id": getSessionId() };
  const res = await fetch(getApiBase() + path, { ...options, headers });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail || detail;
    } catch (_) { /* non-JSON body */ }
    throw new Error(`${res.status}: ${detail}`);
  }
  return res.json();
}

/** POST /analyze — run Stockfish over a PGN and cache the review server-side. */
export function analyze(pgn, { timePerMove = 0.1, detectBrilliancies = true } = {}) {
  return request("/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      pgn,
      time_per_move: timePerMove,
      detect_brilliancies: detectBrilliancies,
    }),
  });
}

/** GET /game — metadata + lightweight move list. */
export function getGame() {
  return request("/game");
}

/** GET /progress — live progress of the running analysis job. */
export function getProgress() {
  return request("/progress");
}

/** GET /move/{index} — full per-move state (FEN, eval, cues). */
export function getMove(index) {
  return request(`/move/${index}`);
}

/** GET /library — catalogue of pre-reviewed famous games. */
export function getLibrary() {
  return request("/library");
}

/** GET /library/{id} — load a stored review as the active game (returns /game payload). */
export function loadLibraryGame(id) {
  return request(`/library/${encodeURIComponent(id)}`);
}

/** POST /evaluate — score any FEN for the interactive analysis board. */
export function evaluate(fen, { timePerMove = 0.3, multipv = 3 } = {}) {
  return request("/evaluate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ fen, time_per_move: timePerMove, multipv }),
  });
}
