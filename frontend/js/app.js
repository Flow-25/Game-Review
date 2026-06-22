// App orchestration: analyze → load game → navigate moves with cues + eval bar.

import {
  getApiBase, setApiBase, analyze, getGame, getMove, getProgress, evaluate,
  getLibrary, loadLibraryGame,
  getToken, setToken, registerAccount, loginAccount, logoutAccount, getMe,
  getSavedGames, saveGame, loadSavedGame, deleteSavedGame,
} from "./api.js";
import { ReviewBoard, FEN, BOOK_ICON_SVG } from "./board.js";
import { Chess } from "chess.js";

const SAMPLE_PGN = `[White "Paul Morphy"]
[Black "Duke Karl / Count Isouard"]
[Result "1-0"]

1. e4 e5 2. Nf3 d6 3. d4 Bg4 4. dxe5 Bxf3 5. Qxf3 dxe5 6. Bc4 Nf6 7. Qb3 Qe7
8. Nc3 c6 9. Bg5 b5 10. Nxb5 cxb5 11. Bxb5+ Nbd7 12. O-O-O Rd8
13. Rxd7 Rxd7 14. Rd1 Qe6 15. Bxd7+ Nxd7 16. Qb8+ Nxb8 17. Rd8# 1-0`;

const BADGE = {
  Genius: "!!!", Brilliant: "!!", Great: "!", Best: "★", Excellent: "✓", Good: "✓",
  Book: "▦", Missed: "−", Inaccuracy: "?!", Mistake: "?", Blunder: "??",
};

// ---- state ----------------------------------------------------------------
const state = {
  game: null,          // /game payload
  startFen: null,      // position before move 0
  moveCache: new Map(),// index -> /move payload
  ply: 0,              // 0 = start position; k = after move (k-1)
  _lastNav: 0,         // timestamp of last navigation (for fast-scroll detection)
  _seq: 0,             // render sequence guard (drops superseded renders)
  mode: "review",      // "review" | "analysis"
  busy: false,         // an analysis job is running
};

// Interactive self-analysis state.
const an = { chess: null, startFen: null, evalSeq: 0 };

let board;

// ---- DOM ------------------------------------------------------------------
const $ = (id) => document.getElementById(id);
const els = {
  apiBase: $("api-base"), drawer: $("pgn-drawer"), pgn: $("pgn-input"),
  time: $("time-input"), brilliant: $("brilliant-input"),
  status: $("status"), movelist: $("movelist-body"),
  evalWhite: $("eval-white"), evalLabel: $("eval-label"),
  moveInfo: $("move-info"),
  nameW: $("name-white"), nameB: $("name-black"),
  acplW: $("acpl-white"), acplB: $("acpl-black"),
  accW: $("acc-white"), accB: $("acc-black"),
  anBar: $("analysis-bar"), anTurn: $("analysis-turn"),
  anLines: $("analysis-lines"), anFen: $("an-fen"),
  progress: $("progress"), progressFill: $("progress-fill"),
  libModal: $("library-modal"), libGrid: $("library-grid"),
  // accounts
  saveBtn: $("save-game"), myGamesBtn: $("open-mygames"), accountBtn: $("open-account"),
  acctModal: $("account-modal"), acctClose: $("account-close"),
  authForm: $("auth-form"), authTitle: $("auth-title"), authUser: $("auth-username"),
  authPass: $("auth-password"), authError: $("auth-error"), authSubmit: $("auth-submit"),
  authToggle: $("auth-toggle"), authToggleText: $("auth-toggle-text"),
  myGamesModal: $("mygames-modal"), myGamesClose: $("mygames-close"), myGamesGrid: $("mygames-grid"),
};

// ---- helpers --------------------------------------------------------------
function setStatus(msg, isError = false) {
  els.status.textContent = msg || "";
  els.status.classList.toggle("error", isError);
}

function formatEval(ev) {
  if (ev.mate !== null && ev.mate !== undefined) {
    return { text: "M" + Math.abs(ev.mate), prob: ev.mate > 0 ? 1 : 0, black: ev.mate < 0 };
  }
  const v = ev.cp / 100;
  return { text: (v > 0 ? "+" : "") + v.toFixed(1), prob: ev.white_win_prob, black: ev.cp < 0 };
}

function setEvalBar(ev) {
  const f = ev ? formatEval(ev) : { text: "0.0", prob: 0.5, black: false };
  els.evalWhite.style.height = (f.prob * 100).toFixed(1) + "%";
  els.evalLabel.textContent = f.text;
  els.evalLabel.classList.toggle("is-black", f.black);
}

// Rough accuracy% from average centipawn loss (lichess-style logistic).
function setAccuracy(accEl, acplEl, avgCpl) {
  const acc = Math.max(0, Math.min(100,
    103.1668 * Math.exp(-0.04354 * (avgCpl / 100)) - 3.1669));
  accEl.textContent = acc.toFixed(1) + "%";
  accEl.dataset.tier = acc >= 80 ? "hi" : acc >= 60 ? "mid" : "low";
  accEl.classList.remove("is-empty");
  acplEl.textContent = "avg loss " + (avgCpl / 100).toFixed(2);
}

function badge(cls) {
  const b = document.createElement("span");
  b.className = "badge";
  b.dataset.c = cls;
  if (cls === "Book") b.innerHTML = BOOK_ICON_SVG;
  else b.textContent = BADGE[cls] ?? "";
  b.title = cls;
  return b;
}

// ---- rendering ------------------------------------------------------------
function buildMoveList() {
  els.movelist.innerHTML = "";
  const moves = state.game.moves;
  for (let i = 0; i < moves.length; i += 2) {
    const tr = document.createElement("tr");
    const num = document.createElement("td");
    num.className = "num";
    num.textContent = moves[i].move_number + ".";
    tr.appendChild(num);
    tr.appendChild(plyCell(moves[i]));
    tr.appendChild(moves[i + 1] ? plyCell(moves[i + 1]) : document.createElement("td"));
    els.movelist.appendChild(tr);
  }
}

function plyCell(m) {
  const td = document.createElement("td");
  const cell = document.createElement("div");
  cell.className = "ply";
  cell.dataset.index = m.index;
  cell.appendChild(badge(m.classification));
  const san = document.createElement("span");
  san.className = "san";
  san.textContent = m.san;
  cell.appendChild(san);
  cell.addEventListener("click", () => {
    if (state.mode === "analysis") exitAnalysis();
    gotoPly(m.index + 1);
  });
  td.appendChild(cell);
  return td;
}

function highlightActive() {
  els.movelist.querySelectorAll(".ply.active").forEach((e) => e.classList.remove("active"));
  if (state.ply === 0) return;
  const cell = els.movelist.querySelector(`.ply[data-index="${state.ply - 1}"]`);
  if (cell) {
    cell.classList.add("active");
    cell.scrollIntoView({ block: "nearest" });
  }
}

function renderMoveInfo(m) {
  els.moveInfo.innerHTML = "";
  if (!m) {
    els.moveInfo.innerHTML = '<span class="move-info__hint">Starting position</span>';
    return;
  }
  els.moveInfo.appendChild(badge(m.classification));
  const wrap = document.createElement("div");
  const side = m.color === "white" ? "White" : "Black";
  let main = `<b>${m.move_number}. ${m.color === "black" ? "… " : ""}${m.san}</b> — ${m.classification}`;
  let sub = `${side}`;
  if (m.best_move?.san && m.best_move.san !== m.san) sub += ` • best was <b>${m.best_move.san}</b>`;
  if (m.centipawn_loss > 0) sub += ` • lost ${(m.centipawn_loss / 100).toFixed(2)}`;
  if ((m.classification === "Brilliant" || m.classification === "Genius") && m.sacrificed_cp) sub += ` • sacrificed ~${(m.sacrificed_cp / 100).toFixed(1)}`;
  wrap.innerHTML = `<div class="mi-text">${main}</div><div class="mi-sub">${sub}</div>`;
  els.moveInfo.appendChild(wrap);
}

async function fetchMove(index) {
  if (state.moveCache.has(index)) return state.moveCache.get(index);
  const data = await getMove(index);
  state.moveCache.set(index, data);
  return data;
}

// ---- navigation -----------------------------------------------------------
async function gotoPly(ply, animated = true) {
  if (!state.game) return;
  const max = state.game.moves.length;
  state.ply = Math.max(0, Math.min(ply, max));

  // When steps arrive rapidly (wheel flick / held arrow), skip the animation so
  // markers and pieces redraw instantly with no queue build-up.
  const now = performance.now();
  const fast = now - state._lastNav < 180;
  state._lastNav = now;
  const anim = animated && !fast;
  const seq = ++state._seq;

  if (state.ply === 0) {
    await board.render(state.startFen, null, anim);
    if (seq !== state._seq) return;            // a newer navigation superseded us
    setEvalBar(null);
    renderMoveInfo(null);
  } else {
    const m = await fetchMove(state.ply - 1);
    if (seq !== state._seq) return;
    await board.render(m.fen, m, anim);
    if (seq !== state._seq) return;
    setEvalBar(m.eval);
    renderMoveInfo(m);
  }
  highlightActive();
}

const next = (animated = true) => gotoPly(state.ply + 1, animated);
const prev = (animated = true) => gotoPly(state.ply - 1, animated);

// ---- self-analysis (interactive board) ------------------------------------
function currentFen() {
  if (!state.game) return FEN.start;
  if (state.ply === 0) return state.startFen || FEN.start;
  const m = state.moveCache.get(state.ply - 1);
  return m ? m.fen : (state.startFen || FEN.start);
}

function setAnalysisTurn() {
  const t = an.chess.turn() === "w" ? "White" : "Black";
  els.anTurn.textContent = an.chess.isGameOver() ? "Game over" : `${t} to move`;
}

function renderAnalysisLines(r) {
  els.anLines.innerHTML = "";
  if (r.is_game_over) {
    els.anLines.innerHTML = `<div class="mi-sub">Game over — ${r.result}</div>`;
    return;
  }
  for (const l of r.lines) {
    const ev = formatEval(l.eval);
    const div = document.createElement("div");
    div.className = "an-line";
    div.innerHTML =
      `<span class="an-eval ${ev.black ? "neg" : "pos"}">${ev.text}</span>` +
      `<span class="an-pv">${l.pv_san}</span>`;
    els.anLines.appendChild(div);
  }
}

async function evaluateCurrent() {
  setAnalysisTurn();
  const fen = an.chess.fen();
  const seq = ++an.evalSeq;
  els.anLines.innerHTML = '<span class="mi-sub">Evaluating…</span>';
  try {
    const r = await evaluate(fen, { timePerMove: parseFloat(els.time.value) || 0.3 });
    if (seq !== an.evalSeq || state.mode !== "analysis") return;  // superseded
    setEvalBar(r.eval);
    board.showEvalArrow(r.best_move ? r.best_move.arrow : null);
    renderAnalysisLines(r);
  } catch (err) {
    setStatus(err.message, true);
  }
}

function startAnalysisAt(fen) {
  an.startFen = fen;
  an.chess = new Chess(fen);                 // throws on invalid FEN
  board.setInteractive(true, { chess: an.chess, onMove: () => evaluateCurrent() });
  board.setPlain(fen, false);
  evaluateCurrent();
}

function enterAnalysis() {
  if (state.mode === "analysis") { exitAnalysis(); return; }
  state.mode = "analysis";
  els.anBar.classList.remove("hidden");
  els.moveInfo.classList.add("hidden");
  $("analysis-toggle").classList.add("btn--primary");
  startAnalysisAt(currentFen());
}

function exitAnalysis() {
  if (state.mode !== "analysis") return;
  state.mode = "review";
  board.setInteractive(false);
  an.chess = null;
  els.anBar.classList.add("hidden");
  els.moveInfo.classList.remove("hidden");
  $("analysis-toggle").classList.remove("btn--primary");
  if (state.game) gotoPly(state.ply);
  else { board.setPlain(FEN.start, false); setEvalBar(null); }
}

function analysisUndo() {
  if (!an.chess || !an.chess.undo()) return;
  board.setPlain(an.chess.fen(), false);
  evaluateCurrent();
}

function analysisReset() {
  if (!an.chess) return;
  an.chess.load(an.startFen);
  board.setPlain(an.startFen, false);
  evaluateCurrent();
}

function analysisLoadFen() {
  const fen = els.anFen.value.trim();
  if (!fen) return;
  try {
    startAnalysisAt(fen);
    setStatus("");
  } catch {
    setStatus("Invalid FEN.", true);
  }
}

// ---- analysis flow --------------------------------------------------------
function showProgress() { els.progress.classList.remove("hidden"); setProgress(0); }
function hideProgress() { els.progress.classList.add("hidden"); setProgress(0); }
function setProgress(frac) { els.progressFill.style.width = Math.round(frac * 100) + "%"; }

// Poll /progress until the job finishes; resolves on done, rejects on error.
function pollProgress() {
  return new Promise((resolve, reject) => {
    const tick = async () => {
      try {
        const p = await getProgress();
        if (p.total) setProgress(p.done / p.total);
        const pct = p.total ? Math.round((100 * p.done) / p.total) : 0;
        setStatus(`Reviewing… ${p.done}/${p.total} moves (${pct}%)`);
        if (p.status === "done") return resolve(p);
        if (p.status === "error") return reject(new Error(p.error || "Analysis failed"));
        setTimeout(tick, 250);
      } catch (e) {
        reject(e);
      }
    };
    tick();
  });
}

// Populate the whole UI from a /game payload (shared by review + library load).
async function applyLoadedGame(g) {
  state.game = g;
  state.moveCache.clear();
  state.startFen = (await fetchMove(0)).fen_before;

  els.nameW.textContent = g.white || "White";
  els.nameB.textContent = g.black || "Black";
  setAccuracy(els.accW, els.acplW, g.summary.white.avg_centipawn_loss);
  setAccuracy(els.accB, els.acplB, g.summary.black.avg_centipawn_loss);

  buildMoveList();
  const op = g.opening ? `${g.opening.eco} · ${g.opening.name}` : "Unknown opening";
  setStatus(`♟ ${op}  —  ${g.engine_name} • ${g.move_count} moves`);
  await gotoPly(0);
}

// ---- famous-games library -------------------------------------------------
const accTier = (a) => (a >= 80 ? "hi" : a >= 60 ? "mid" : "low");

function libraryCard(g) {
  const card = document.createElement("button");
  card.className = "lib-card";
  card.type = "button";
  const opening = g.opening ? g.opening.name : "—";
  card.innerHTML =
    `<div class="lib-card__title">${g.nickname}</div>` +
    `<div class="lib-card__players">${g.white} <span class="vs">vs</span> ${g.black}</div>` +
    `<div class="lib-card__meta">${g.event} · ${g.year} · ${g.result}</div>` +
    `<div class="lib-card__opening">${opening}</div>` +
    `<div class="lib-card__desc">${g.description}</div>` +
    `<div class="lib-card__foot">` +
      `<span class="lib-acc" data-tier="${accTier(g.accuracy_white)}">♔ ${g.accuracy_white}%</span>` +
      `<span class="lib-acc" data-tier="${accTier(g.accuracy_black)}">♚ ${g.accuracy_black}%</span>` +
      `<span class="grow"></span><span class="lib-card__count">${g.move_count} moves</span>` +
    `</div>`;
  card.addEventListener("click", () => loadLibrary(g.id));
  return card;
}

let libLoaded = false;
async function openLibrary() {
  els.libModal.classList.remove("hidden");
  if (libLoaded) return;                          // already populated — keep cards
  els.libGrid.innerHTML = '<p class="library__sub">Loading…</p>';
  try {
    const { games } = await getLibrary();
    els.libGrid.innerHTML = "";
    if (!games.length) { els.libGrid.innerHTML = '<p class="library__sub">No games found — run <code>python -m backend.build_library</code>.</p>'; return; }
    games.forEach((g) => els.libGrid.appendChild(libraryCard(g)));
    libLoaded = true;
  } catch (err) {
    els.libGrid.innerHTML = `<p class="library__sub">Could not load library: ${err.message}</p>`;
  }
}

function closeLibrary() { els.libModal.classList.add("hidden"); }

async function loadLibrary(id) {
  if (state.busy) return;
  if (state.mode === "analysis") exitAnalysis();
  state.busy = true;
  setStatus("Loading game…");
  try {
    const g = await loadLibraryGame(id);   // server-side becomes the active game
    await applyLoadedGame(g);
    closeLibrary();
    els.drawer.classList.add("hidden");
  } catch (err) {
    setStatus(err.message, true);
  } finally {
    state.busy = false;
  }
}

// ---- accounts -------------------------------------------------------------
let currentUser = null;
let authMode = "login";   // "login" | "register"

function setAuthUI() {
  if (currentUser) {
    els.accountBtn.textContent = `👤 ${currentUser}`;
    els.accountBtn.title = "Sign out";
    els.saveBtn.hidden = false;
    els.myGamesBtn.hidden = false;
  } else {
    els.accountBtn.textContent = "👤 Sign in";
    els.accountBtn.title = "Sign in / create account";
    els.saveBtn.hidden = true;
    els.myGamesBtn.hidden = true;
  }
}

function setAuthMode(mode) {
  authMode = mode;
  const register = mode === "register";
  els.authTitle.textContent = register ? "Create account" : "Sign in";
  els.authSubmit.textContent = register ? "Create account" : "Sign in";
  els.authToggleText.textContent = register ? "Already have an account?" : "Need an account?";
  els.authToggle.textContent = register ? "Sign in" : "Create one";
  els.authPass.autocomplete = register ? "new-password" : "current-password";
  els.authError.textContent = "";
}

function openAccount() {
  setAuthMode("login");
  els.authError.textContent = "";
  els.acctModal.classList.remove("hidden");
  els.authUser.focus();
}

function closeAccount() { els.acctModal.classList.add("hidden"); }

async function submitAuth(e) {
  e.preventDefault();
  const username = els.authUser.value.trim();
  const password = els.authPass.value;
  els.authError.textContent = "";
  els.authSubmit.disabled = true;
  try {
    const fn = authMode === "register" ? registerAccount : loginAccount;
    const { token, username: who } = await fn(username, password);
    setToken(token);
    currentUser = who;
    setAuthUI();
    closeAccount();
    els.authForm.reset();
    setStatus(`Signed in as ${who}.`);
  } catch (err) {
    els.authError.textContent = err.message.replace(/^\d+:\s*/, "");
  } finally {
    els.authSubmit.disabled = false;
  }
}

async function signOut() {
  try { await logoutAccount(); } catch (_) { /* token may already be gone */ }
  setToken("");
  currentUser = null;
  setAuthUI();
  setStatus("Signed out.");
}

async function refreshAuth() {
  setAuthUI();
  if (!getToken()) return;
  try {
    const { username } = await getMe();
    currentUser = username;
  } catch (_) {
    setToken("");          // stale/expired token (e.g. server restarted)
    currentUser = null;
  }
  setAuthUI();
}

async function doSaveGame() {
  if (!currentUser) { openAccount(); return; }
  if (!state.game) { setStatus("Analyze or open a game first.", true); return; }
  const suggested = `${state.game.white || "White"} vs ${state.game.black || "Black"}`;
  const name = window.prompt("Save game as:", suggested);
  if (name === null) return;                 // cancelled
  try {
    const { saved } = await saveGame(name.trim());
    setStatus(`Saved “${saved.name}” to your games.`);
  } catch (err) {
    setStatus(err.message, true);
  }
}

function savedGameCard(g) {
  const card = document.createElement("div");
  card.className = "lib-card lib-card--saved";
  const opening = g.opening ? g.opening.name : "—";
  const when = g.saved_at ? new Date(g.saved_at * 1000).toLocaleDateString() : "";
  card.innerHTML =
    `<button class="lib-card__del" type="button" title="Delete" aria-label="Delete">✕</button>` +
    `<div class="lib-card__title">${g.name}</div>` +
    `<div class="lib-card__players">${g.white} <span class="vs">vs</span> ${g.black}</div>` +
    `<div class="lib-card__meta">${g.result} · ${opening}${when ? " · saved " + when : ""}</div>` +
    `<div class="lib-card__foot">` +
      `<span class="lib-acc" data-tier="${accTier(g.accuracy_white)}">♔ ${g.accuracy_white}%</span>` +
      `<span class="lib-acc" data-tier="${accTier(g.accuracy_black)}">♚ ${g.accuracy_black}%</span>` +
      `<span class="grow"></span><span class="lib-card__count">${g.move_count} moves</span>` +
    `</div>`;
  card.querySelector(".lib-card__del").addEventListener("click", (e) => {
    e.stopPropagation();
    deleteMyGame(g.id, g.name);
  });
  card.addEventListener("click", () => loadMyGame(g.id));
  return card;
}

async function openMyGames() {
  if (!currentUser) { openAccount(); return; }
  els.myGamesModal.classList.remove("hidden");
  els.myGamesGrid.innerHTML = '<p class="library__sub">Loading…</p>';
  try {
    const { games } = await getSavedGames();
    els.myGamesGrid.innerHTML = "";
    if (!games.length) {
      els.myGamesGrid.innerHTML = '<p class="library__sub">No saved games yet — open a game and hit 💾 Save.</p>';
      return;
    }
    games.forEach((g) => els.myGamesGrid.appendChild(savedGameCard(g)));
  } catch (err) {
    els.myGamesGrid.innerHTML = `<p class="library__sub">Could not load your games: ${err.message}</p>`;
  }
}

function closeMyGames() { els.myGamesModal.classList.add("hidden"); }

async function loadMyGame(id) {
  if (state.busy) return;
  if (state.mode === "analysis") exitAnalysis();
  state.busy = true;
  setStatus("Loading game…");
  try {
    const g = await loadSavedGame(id);
    await applyLoadedGame(g);
    closeMyGames();
    els.drawer.classList.add("hidden");
  } catch (err) {
    setStatus(err.message, true);
  } finally {
    state.busy = false;
  }
}

async function deleteMyGame(id, name) {
  if (!window.confirm(`Delete “${name}”? This can't be undone.`)) return;
  try {
    await deleteSavedGame(id);
    openMyGames();              // refresh the list
  } catch (err) {
    setStatus(err.message, true);
  }
}

async function runAnalysis() {
  if (state.busy) return;                       // ignore double-clicks
  const pgn = els.pgn.value.trim();
  if (!pgn) { setStatus("Paste a PGN first.", true); els.drawer.classList.remove("hidden"); return; }
  if (state.mode === "analysis") exitAnalysis();

  state.busy = true;
  showProgress();
  setStatus("Starting review…");
  try {
    await analyze(pgn, {
      timePerMove: parseFloat(els.time.value) || 0.1,
      detectBrilliancies: els.brilliant.checked,
    });
    await pollProgress();                        // wait for the engine to finish

    await applyLoadedGame(await getGame());
    els.drawer.classList.add("hidden");
  } catch (err) {
    setStatus(err.message, true);
  } finally {
    hideProgress();
    state.busy = false;
  }
}

// ---- wiring ---------------------------------------------------------------
function wire() {
  els.apiBase.value = getApiBase();
  els.apiBase.addEventListener("change", () => setApiBase(els.apiBase.value));

  $("analyze").addEventListener("click", runAnalysis);
  $("analyze-2").addEventListener("click", runAnalysis);
  $("open-library").addEventListener("click", openLibrary);
  $("library-close").addEventListener("click", closeLibrary);
  els.libModal.addEventListener("click", (e) => { if (e.target === els.libModal) closeLibrary(); });

  // Accounts
  els.accountBtn.addEventListener("click", () => (currentUser ? signOut() : openAccount()));
  els.acctClose.addEventListener("click", closeAccount);
  els.acctModal.addEventListener("click", (e) => { if (e.target === els.acctModal) closeAccount(); });
  els.authForm.addEventListener("submit", submitAuth);
  els.authToggle.addEventListener("click", () => setAuthMode(authMode === "login" ? "register" : "login"));
  els.saveBtn.addEventListener("click", doSaveGame);
  els.myGamesBtn.addEventListener("click", openMyGames);
  els.myGamesClose.addEventListener("click", closeMyGames);
  els.myGamesModal.addEventListener("click", (e) => { if (e.target === els.myGamesModal) closeMyGames(); });
  $("open-pgn").addEventListener("click", () => els.drawer.classList.toggle("hidden"));
  $("load-sample").addEventListener("click", () => {
    els.pgn.value = SAMPLE_PGN;
    els.drawer.classList.remove("hidden");
  });

  $("nav-start").addEventListener("click", () => gotoPly(0));
  $("nav-prev").addEventListener("click", () => prev());
  $("nav-next").addEventListener("click", () => next());
  $("nav-end").addEventListener("click", () => gotoPly(state.game ? state.game.moves.length : 0));
  $("flip").addEventListener("click", () => board.flip());

  // Analysis mode
  $("analysis-toggle").addEventListener("click", enterAnalysis);
  $("an-exit").addEventListener("click", exitAnalysis);
  $("an-undo").addEventListener("click", analysisUndo);
  $("an-reset").addEventListener("click", analysisReset);
  $("an-loadfen").addEventListener("click", analysisLoadFen);
  els.anFen.addEventListener("keydown", (e) => { if (e.key === "Enter") analysisLoadFen(); });

  // Keyboard navigation
  window.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      if (!els.libModal.classList.contains("hidden")) { closeLibrary(); return; }
      if (!els.acctModal.classList.contains("hidden")) { closeAccount(); return; }
      if (!els.myGamesModal.classList.contains("hidden")) { closeMyGames(); return; }
    }
    if (e.target.tagName === "TEXTAREA" || e.target.tagName === "INPUT") return;
    if (state.mode === "analysis") {       // analysis: ← takes back, no review nav
      if (e.key === "ArrowLeft") { e.preventDefault(); analysisUndo(); }
      return;
    }
    switch (e.key) {
      case "ArrowRight": case "ArrowDown": e.preventDefault(); next(); break;
      case "ArrowLeft":  case "ArrowUp":   e.preventDefault(); prev(); break;
      case "Home": e.preventDefault(); gotoPly(0); break;
      case "End":  e.preventDefault(); gotoPly(state.game ? state.game.moves.length : 0); break;
    }
  });

  // Mouse-wheel navigation over the board pane — instant (no animation),
  // lightly throttled so a single flick doesn't skip the whole game.
  let wheelLock = false;
  document.querySelector(".board-pane").addEventListener("wheel", (e) => {
    if (state.mode === "analysis") return;   // don't hijack scroll during analysis
    e.preventDefault();
    if (wheelLock) return;
    wheelLock = true;
    setTimeout(() => (wheelLock = false), 80);
    (e.deltaY > 0 ? next : prev)(false);
  }, { passive: false });
}

board = new ReviewBoard(
  document.getElementById("board"),
  document.getElementById("board-overlay"),
);
wire();
setEvalBar(null);
refreshAuth();
