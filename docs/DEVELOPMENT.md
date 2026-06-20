# Chess Game Review

A local, automated chess game-review tool (think Chess.com's "Game Review")
running on your own machine with [Stockfish](https://stockfishchess.org/).

**Architecture (planned):**

| Layer    | Tech                                            | Status            |
|----------|-------------------------------------------------|-------------------|
| Engine   | Python · `python-chess` · Stockfish (UCI)       | ✅ Phase 1        |
| API      | Python · FastAPI · uvicorn                       | ✅ Phase 2        |
| Frontend | HTML · CSS · JS (ES6) · `cm-chessboard`          | ✅ Phase 3        |

---

## Phase 1 — Environment Setup & Core Engine Logic

### 1. Install system dependencies

**Arch Linux** ships Stockfish in the official `extra` repo:

```bash
sudo pacman -S --needed stockfish python python-pip
stockfish --help    # verify it's on PATH (code auto-detects /usr/bin/stockfish)
```

**Manjaro** (and other distros without a `stockfish` package) — grab the
official prebuilt binary into `engines/`; the code auto-discovers anything under
`engines/stockfish*`, so no `sudo` and no system install needed:

```bash
mkdir -p engines && cd engines
# pick the variant matching your CPU: bmi2 (modern), avx2, sse41-popcnt, or x86-64
curl -L -o sf.tar \
  https://github.com/official-stockfish/Stockfish/releases/download/sf_18/stockfish-ubuntu-x86-64-bmi2.tar
tar xf sf.tar && rm sf.tar && chmod +x stockfish/stockfish-* && cd ..
```

(The AUR `stockfish` package works too if you prefer an AUR helper.)

### 2. Python virtual environment

```bash
cd game_review
python -m venv .venv
source .venv/bin/activate        # bash/zsh
# fish:  source .venv/bin/activate.fish

pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Project structure

```
game_review/
├── CLAUDE.md              # project brief / phased spec
├── README.md             # this file
├── requirements.txt
├── .gitignore
│
├── backend/              # all engine + analysis logic
│   ├── __init__.py
│   ├── config.py         # engine discovery, analysis & classification tuning
│   ├── engine.py         # StockfishEngine: UCI lifecycle wrapper
│   ├── classifier.py     # centipawn loss  ->  Best/Good/Blunder/...
│   ├── analyzer.py       # walks a PGN, scores every move  (the core)
│   └── sample_game.py    # bundled sample PGN (Morphy's Opera Game)
│
├── scripts/
│   └── analyze.py        # CLI entry point
│
└── frontend/             # (Phase 2 — empty for now)
```

### 4. Run it

```bash
# Analyse the bundled sample game (~0.1s/move):
python -m scripts.analyze

# Analyse your own PGN, deeper, and save JSON for later (Phase 2 will consume it):
python -m scripts.analyze mygame.pgn --time 0.3 --output review.json
```

Example output:

```
  [  1/33] white e4      best=e4      cpl=   0  Book
  ...
  [ 33/33] white Rd8#    best=Rd8#    cpl=   0  Best
============================================================
Paul Morphy  vs  Duke Karl / Count Isouard   [1-0]
============================================================

White (Paul Morphy)
  avg centipawn loss: 12.4
  Book:5  Best:9  Good:2  ...
```

---

## How a move is scored

For each move we compute its **centipawn loss**:

1. Evaluate the position **before** the move → the best achievable score
   (and the engine's recommended move).
2. Play the move → evaluate the resulting position from the **same player's**
   point of view.
3. `centipawn_loss = best_eval − actual_eval` (clamped at 0).

"Mate in N" is mapped to a large finite centipawn value so the arithmetic stays
well-behaved. Thresholds for each label (Best / Excellent / Good / Inaccuracy /
Mistake / Blunder) and the opening-book window live in
[`backend/config.py`](backend/config.py) — tune them in one place.

## Phase 2 — Backend API (FastAPI)

The analysis engine is exposed over HTTP so the (Phase 3) browser frontend can
drive it. CORS is wide-open for local development.

```bash
# from the project root, with the venv active
uvicorn backend.api:app --reload --port 8000
# interactive docs: http://127.0.0.1:8000/docs
```

### Endpoints

| Method & path        | Purpose                                                        |
|----------------------|---------------------------------------------------------------|
| `POST /analyze`      | Analyse a PGN and cache the full review in memory.            |
| `GET /game`          | Game metadata + lightweight move list (for a move sidebar).   |
| `GET /move/{index}`  | Full per-move state for the board + overlays (0-based index). |
| `POST /evaluate`     | Evaluate any FEN (interactive self-analysis): eval + top lines.|
| `GET /`              | Health check / whether a game is loaded.                      |

**`POST /evaluate`** body `{ "fen": "...", "time_per_move": 0.3, "multipv": 3 }`
returns the eval-bar data, the best move (with an arrow), and the top-N engine
lines (each with a short SAN principal variation). It is backed by a single
long-lived engine (lock-serialised) so repeated calls from the analysis board
stay responsive.

**`POST /analyze`** body:

```json
{ "pgn": "1. e4 e5 2. Nf3 ...", "time_per_move": 0.1, "depth": null, "detect_brilliancies": true }
```

**`GET /move/{index}`** returns the board position plus ready-to-render visual cues:

```jsonc
{
  "fen": "....",                 // position AFTER the move (board to display)
  "fen_before": "....",          // position before it (best-move arrow context)
  "eval": { "cp": -320, "mate": null, "white_win_prob": 0.13 },  // powers the eval bar
  "classification": "Blunder",
  "marker":    { "square": "f6", "type": "Blunder" },     // badge where it happened
  "best_move": { "san": "g6", "uci": "g7g6", "arrow": ["g7", "g6"] },  // green arrow
  "played_move": { "san": "Nf6", "uci": "g8f6", "arrow": ["g8", "f6"] }
}
```

Errors: `400` (empty/unparseable PGN), `404` (no game loaded, or move index out
of range), `503` (Stockfish binary not found).

---

## Phase 3 — Frontend UI

A dark-themed, responsive single page (pure HTML/CSS/ES6 modules, no build step).
`cm-chessboard` is loaded straight from a CDN via an import map.

Run **both** the API and a static file server, then open the page:

```bash
# terminal 1 — the API
uvicorn backend.api:app --port 8000

# terminal 2 — serve the static frontend
cd frontend && python -m http.server 5500

# then open http://127.0.0.1:5500 in your browser
```

(The API base URL is editable in the top bar and persisted to `localStorage`,
defaulting to `http://127.0.0.1:8000`.)

**Features**
- **Split layout**: left = chessboard with an integrated vertical **eval bar**
  (driven by the API's win-probability); right = scrollable PGN move list with a
  colour-coded classification badge on every move.
- **Board cues**: a marker on the played square (coloured by classification) and
  a green arrow for the engine's best move, pulled from `GET /move/{index}`.
- **Navigation**: `←/→` (and `↑/↓`), `Home`/`End`, **mouse-wheel** over the
  board, on-screen buttons, and click-to-jump on any move in the list.
- Paste any PGN (or **Load sample**), pick time/move, toggle brilliancy
  detection, and hit **Analyze**.

### Self-analysis (interactive board)

Hit **⚄ Analysis** to branch off from the position currently on the board (or
the start) and explore by hand:

- **Drag the pieces** — legality is enforced client-side by `chess.js`; legal
  destinations light up as dots while you drag (castling, en-passant and
  promotion-to-queen are handled).
- Every move is scored live via `POST /evaluate`: the **eval bar** updates and
  the **top engine lines** (with principal variations) are listed below the
  board, plus a blue arrow for the engine's choice.
- **Undo** (or `←`) takes back, **Reset** returns to where you entered, and you
  can paste any **FEN** to evaluate an arbitrary position. **Exit analysis**
  returns to game review.

### Visual annotations (the "Game Review" look)

Driven entirely by the `GET /move/{index}` cue data:

- **Square highlights** — the moved piece's *from* and *to* squares are tinted
  with the move's classification colour (translucent `markerSquare` markers).
- **Engine arrows** — a green arrow to the engine's suggestion is drawn **only
  when the move was an error** (Inaccuracy / Mistake / Blunder).
- **Corner badges** — a stylised glyph (`!!`, `★`, `?!`, `??`, …) sits on the
  top-right corner of the played square. cm-chessboard can't place corner icons,
  so these are an absolutely-positioned DOM overlay that maps board coordinates
  (honouring orientation) and is kept aligned by a `ResizeObserver`.
- **Lag-free scrubbing** — rapid wheel/held-key navigation suppresses the move
  animation and a render-sequence guard drops superseded redraws, so markers and
  badges clear and repaint instantly with no queue build-up.

---

## Brilliant move detection (sound sacrifices)

A **Brilliant** move (`!!`) is a *sound sacrifice*: you offer material the
opponent can capture, but the position stays good for you. Detection
([`backend/brilliancy.py`](backend/brilliancy.py)) runs in two stages so the
common case stays cheap:

1. **Was material offered?** *(cheap, no engine)* — Using **Static Exchange
   Evaluation** we ask whether the opponent can win material by capturing, then
   subtract whatever our own move just captured. Only a *net* give-up of
   ≥ `min_sacrifice_cp` (default 150 cp — exchange sacs and up) counts. This
   alone rejects ordinary trades/recaptures (e.g. `NxN` answered by `bxN`).
2. **Is the sacrifice sound?** *(deep re-search of candidates only)* — A real
   sacrifice often looks like a *blunder* at 0.1 s/move, so candidates are
   re-analysed at higher depth. The move qualifies as Brilliant only if, with
   the deep evaluation, it is still ~the best move, we are not losing
   afterwards, and we were **not already winning** (you don't earn `!!` for a
   flashy finish in a totally won game).

> **A surprising-but-true note on the heuristic:** "a real sacrifice means the
> material is *not* won back" turns out to be false. In Byrne–Fischer 1956,
> after the legendary `17...Be6!!` Fischer ends up *materially even or ahead*
> within a dozen plies — the queen sac wins back plenty of material plus a
> crushing attack. What defines a brilliancy is the *sound offer* of capturable
> material, not a permanent material deficit. The detector is built around that.

Tuning lives in `BrilliantConfig` ([`backend/config.py`](backend/config.py)):
`min_sacrifice_cp`, `verify_depth`/`verify_time`, `max_cpl`, `min_eval_after`,
and `already_winning_cp`.

```bash
# The "Game of the Century" flags 17...Be6 (and other Fischer sacrifices):
python -m scripts.analyze game.pgn -t 0.2
```

### Configuration knobs (env)

| Variable          | Effect                                            |
|-------------------|---------------------------------------------------|
| `STOCKFISH_PATH`  | Use a custom Stockfish binary instead of the auto-detected one. |
