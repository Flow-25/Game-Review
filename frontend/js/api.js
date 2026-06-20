// Tiny fetch wrapper around the FastAPI backend.

const STORAGE_KEY = "gr_api_base";

export function getApiBase() {
  return localStorage.getItem(STORAGE_KEY) || "http://127.0.0.1:8000";
}

export function setApiBase(url) {
  localStorage.setItem(STORAGE_KEY, url.replace(/\/+$/, ""));
}

async function request(path, options = {}) {
  const res = await fetch(getApiBase() + path, options);
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

/** POST /evaluate — score any FEN for the interactive analysis board. */
export function evaluate(fen, { timePerMove = 0.3, multipv = 3 } = {}) {
  return request("/evaluate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ fen, time_per_move: timePerMove, multipv }),
  });
}
