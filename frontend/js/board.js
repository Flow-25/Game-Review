// cm-chessboard wrapper + the "Game Review" visual annotation layer:
//   • coloured square highlights on the from/to squares (classification colour)
//   • a green engine arrow — only when the move was an error
//   • a corner badge glyph (!!, ??, ...) drawn as an absolutely-positioned
//     DOM overlay (cm-chessboard can't place corner icons itself)

import { Chessboard, FEN, INPUT_EVENT_TYPE } from "cm-chessboard/src/Chessboard.js";
import { Markers, MARKER_TYPE } from "cm-chessboard/src/extensions/markers/Markers.js";
import { Arrows } from "cm-chessboard/src/extensions/arrows/Arrows.js";

const ASSETS = "https://cdn.jsdelivr.net/npm/cm-chessboard@8/assets/";
const DOT = MARKER_TYPE.dot;                 // legal-move hint dots
const ARROW_EVAL = { class: "arrow-eval" };  // engine arrow in analysis mode

// Glyph shown in the corner badge per classification.
const GLYPH = {
  Brilliant: "!!", Great: "!", Best: "★", Excellent: "✓", Good: "✓",
  Book: "▦", Inaccuracy: "?!", Mistake: "?", Blunder: "??",
};
const ERROR_CLASSES = new Set(["Inaccuracy", "Mistake", "Blunder"]);

// Custom cue types — only `class` is read from the arrow type; the shaft/head
// geometry comes from the extension. Colour both parts via CSS (.arrow-best).
const ARROW_BEST = { class: "arrow-best" };
const squareHighlight = (cls) => ({ class: `sqhl cue-${cls.toLowerCase()}`, slice: "markerSquare" });

export class ReviewBoard {
  constructor(boardEl, overlayEl) {
    this.overlay = overlayEl;
    this.current = null; // remember last cues so we can reposition badges on resize
    this.board = new Chessboard(boardEl, {
      position: FEN.start,
      assetsUrl: ASSETS,
      style: {
        pieces: { file: "pieces/standard.svg" },
        borderType: "none",        // squares fill the element → clean overlay maths
        showCoordinates: true,
        animationDuration: 150,
      },
      extensions: [{ class: Markers }, { class: Arrows }],
    });

    // Keep badges glued to their squares when the board is resized.
    this._ro = new ResizeObserver(() => this._repositionBadges());
    this._ro.observe(boardEl);
  }

  /**
   * Render a position and (optionally) its review cues.
   * @param fen   FEN to display
   * @param cues  a /move payload, or null for the bare starting position
   * @param animated  whether to animate the piece move (off for rapid scrolling)
   */
  async render(fen, cues = null, animated = true) {
    // Clear overlays *immediately* so rapid navigation never shows stale cues.
    this.board.removeMarkers();
    this.board.removeArrows();
    this._clearBadges();
    this.current = cues;

    await this.board.setPosition(fen, animated);
    if (!cues) return;

    const played = cues.played_move?.arrow;     // ['g8','f6']
    const best = cues.best_move?.arrow;
    const cls = cues.classification;

    // 1) Highlight the from/to squares in the classification colour.
    if (played) {
      this.board.addMarker(squareHighlight(cls), played[0]);
      this.board.addMarker(squareHighlight(cls), played[1]);
    }

    // 2) Engine alternative arrow — only when the player erred.
    const sameMove = best && played && best[0] === played[0] && best[1] === played[1];
    if (best && !sameMove && ERROR_CLASSES.has(cls)) {
      this.board.addArrow(ARROW_BEST, best[0], best[1]);
    }

    // 3) Corner badge on the played (key) square.
    const sq = cues.marker?.square || (played && played[1]);
    if (sq) this._addBadge(sq, cls);
  }

  flip() {
    const next = this.board.getOrientation() === "b" ? "w" : "b";
    this.board.setOrientation(next).then(() => this._repositionBadges());
  }

  // ---- interactive (self-analysis) mode ------------------------------- //
  /**
   * Enable/disable piece dragging. When enabled, `chess` (a chess.js instance)
   * provides legality; `onMove(fen, move)` fires after each accepted move.
   */
  setInteractive(enabled, { chess = null, onMove = null } = {}) {
    if (!enabled) {
      this.board.disableMoveInput();
      this._chess = this._onMove = null;
      return;
    }
    this._chess = chess;
    this._onMove = onMove;
    this.board.enableMoveInput((e) => this._handleInput(e));
  }

  _handleInput(e) {
    if (e.type === INPUT_EVENT_TYPE.moveInputStarted) {
      const moves = this._chess.moves({ square: e.squareFrom, verbose: true });
      moves.forEach((m) => this.board.addMarker(DOT, m.to));
      return moves.length > 0;            // only pick up pieces that can move
    }
    if (e.type === INPUT_EVENT_TYPE.validateMoveInput) {
      this.board.removeMarkers(DOT);
      // chess.js v1 throws on an illegal move (instead of returning null).
      let mv;
      try {
        mv = this._chess.move({ from: e.squareFrom, to: e.squareTo, promotion: "q" });
      } catch {
        return false;
      }
      if (!mv) return false;
      // Sync the board to the true new FEN (handles castling/en-passant/promotion)
      // after cm-chessboard finishes its own from→to animation.
      queueMicrotask(() => {
        this.board.setPosition(this._chess.fen(), false);
        this.board.removeArrows();
        if (this._onMove) this._onMove(this._chess.fen(), mv);
      });
      return true;
    }
    if (e.type === INPUT_EVENT_TYPE.moveInputCanceled) {
      this.board.removeMarkers(DOT);
    }
    return true;
  }

  /** Show/refresh the engine's suggested move as an arrow (analysis mode). */
  showEvalArrow(arrow) {
    this.board.removeArrows();
    if (arrow) this.board.addArrow(ARROW_EVAL, arrow[0], arrow[1]);
  }

  /** Render a plain position (no review cues) — used by analysis undo/reset/FEN. */
  async setPlain(fen, animated = true) {
    this.board.removeMarkers();
    this.board.removeArrows();
    this._clearBadges();
    await this.board.setPosition(fen, animated);
  }

  // ---- badge overlay -------------------------------------------------- //
  _clearBadges() {
    this.overlay.replaceChildren();
  }

  _addBadge(square, cls) {
    const b = document.createElement("div");
    b.className = "review-badge";
    b.dataset.c = cls;
    b.dataset.square = square;
    b.textContent = GLYPH[cls] ?? "";
    b.title = cls;
    this.overlay.appendChild(b);
    this._placeBadge(b);
  }

  _repositionBadges() {
    this.overlay.querySelectorAll(".review-badge").forEach((b) => this._placeBadge(b));
  }

  _placeBadge(b) {
    const size = this.overlay.clientWidth;
    if (!size) return;
    const sq = size / 8;
    const { col, row } = this._squareToGrid(b.dataset.square);
    const x = col * sq, y = row * sq;
    const bs = Math.max(15, sq * 0.46);
    b.style.width = b.style.height = `${bs}px`;
    b.style.fontSize = `${bs * 0.5}px`;
    // top-right corner of the square, nudged to overlap like chess.com
    b.style.left = `${x + sq - bs * 0.62}px`;
    b.style.top = `${y - bs * 0.38}px`;
  }

  /** file/rank -> grid column/row honouring board orientation. */
  _squareToGrid(square) {
    const file = square.charCodeAt(0) - 97;          // a..h -> 0..7
    const rank = parseInt(square[1], 10) - 1;        // 1..8 -> 0..7
    const flipped = this.board.getOrientation() === "b";
    return {
      col: flipped ? 7 - file : file,
      row: flipped ? rank : 7 - rank,
    };
  }
}

export { FEN };
