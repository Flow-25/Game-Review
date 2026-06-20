// App orchestration: analyze → load game → navigate moves with cues + eval bar.

import { getApiBase, setApiBase, analyze, getGame, getMove, getProgress, evaluate } from "./api.js";
import { ReviewBoard, FEN } from "./board.js";
import { Chess } from "chess.js";

const SAMPLE_PGN = `[White "Paul Morphy"]
[Black "Duke Karl / Count Isouard"]
[Result "1-0"]

1. e4 e5 2. Nf3 d6 3. d4 Bg4 4. dxe5 Bxf3 5. Qxf3 dxe5 6. Bc4 Nf6 7. Qb3 Qe7
8. Nc3 c6 9. Bg5 b5 10. Nxb5 cxb5 11. Bxb5+ Nbd7 12. O-O-O Rd8
13. Rxd7 Rxd7 14. Rd1 Qe6 15. Bxd7+ Nxd7 16. Qb8+ Nxb8 17. Rd8# 1-0`;

const BADGE = {
  Brilliant: "!!", Great: "!", Best: "★", Excellent: "✓", Good: "✓",
  Book: "▦", Inaccuracy: "?!", Mistake: "?", Blunder: "??",
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
  b.textContent = BADGE[cls] ?? "";
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
  if (m.classification === "Brilliant" && m.sacrificed_cp) sub += ` • sacrificed ~${(m.sacrificed_cp / 100).toFixed(1)}`;
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

    const g = (state.game = await getGame());
    state.moveCache.clear();
    state.startFen = (await fetchMove(0)).fen_before;

    els.nameW.textContent = g.white || "White";
    els.nameB.textContent = g.black || "Black";
    setAccuracy(els.accW, els.acplW, g.summary.white.avg_centipawn_loss);
    setAccuracy(els.accB, els.acplB, g.summary.black.avg_centipawn_loss);

    buildMoveList();
    els.drawer.classList.add("hidden");
    const op = g.opening ? `${g.opening.eco} · ${g.opening.name}` : "Unknown opening";
    setStatus(`♟ ${op}  —  ${g.engine_name} • ${g.move_count} moves`);
    await gotoPly(0);
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
