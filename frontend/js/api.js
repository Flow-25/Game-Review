// Tiny fetch wrapper around the FastAPI backend.

const STORAGE_KEY = "gr_api_base";
const TOKEN_KEY = "gr_token";

export function getApiBase() {
  return localStorage.getItem(STORAGE_KEY) || "http://127.0.0.1:8000";
}

export function setApiBase(url) {
  localStorage.setItem(STORAGE_KEY, url.replace(/\/+$/, ""));
}

export function getToken() {
  return localStorage.getItem(TOKEN_KEY) || "";
}

export function setToken(token) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

async function request(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
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

function jsonBody(payload) {
  return { headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) };
}

// ---- accounts -------------------------------------------------------------
/** POST /auth/register — create an account; returns {token, username}. */
export function registerAccount(username, password) {
  return request("/auth/register", { method: "POST", ...jsonBody({ username, password }) });
}

/** POST /auth/login — sign in; returns {token, username}. */
export function loginAccount(username, password) {
  return request("/auth/login", { method: "POST", ...jsonBody({ username, password }) });
}

/** POST /auth/logout — invalidate the current token. */
export function logoutAccount() {
  return request("/auth/logout", { method: "POST" });
}

/** GET /auth/me — current signed-in user (validates token). */
export function getMe() {
  return request("/auth/me");
}

/** GET /games — the user's saved games (catalogue). */
export function getSavedGames() {
  return request("/games");
}

/** POST /games — save the currently-loaded review for the user. */
export function saveGame(name = "") {
  return request("/games", { method: "POST", ...jsonBody({ name }) });
}

/** GET /games/{id} — load a saved game as the active game (returns /game payload). */
export function loadSavedGame(id) {
  return request(`/games/${encodeURIComponent(id)}`);
}

/** DELETE /games/{id} — remove a saved game. */
export function deleteSavedGame(id) {
  return request(`/games/${encodeURIComponent(id)}`, { method: "DELETE" });
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
