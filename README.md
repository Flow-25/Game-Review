<div align="center">

# ♞ Game Review

**A local, Chess.com-style game review tool — powered by Stockfish, running entirely on your machine.**

Paste a PGN, get a move-by-move review with classifications, an evaluation bar,
opening detection, and an interactive analysis board where you can drag the
pieces and see the engine's verdict in real time.

</div>

---

## ✨ Features

- **Full game review** — every move classified as **Brilliant · Great · Best · Excellent · Good · Book · Inaccuracy · Mistake · Blunder**.
- **Brilliant move detection** — finds *sound sacrifices* (you give up material but keep the advantage), not just engine-best moves.
- **Great move detection** — flags the *only* move that holds in a critical position.
- **Opening detection** — names the opening (ECO code) from a bundled database of 3,700+ lines.
- **Evaluation bar** — a live gauge of who's winning, with mate detection.
- **Annotated board** — colored square highlights, corner badges, and a green arrow showing the engine's suggestion when you slip.
- **Interactive self-analysis** — switch to Analysis mode, **drag pieces** freely (legal moves only), paste any FEN, and get instant evaluations with the top engine lines.
- **Accuracy score** per player and a live **progress bar** while the review runs.
- **100% local & private** — your games never leave your computer.

---

## 📋 Requirements

- **Python 3.10+**
- **Stockfish** (any recent version)
- A modern web browser

---

## 🚀 Quick start

### 1. Get Stockfish

**Arch Linux:**
```bash
sudo pacman -S stockfish
```

**Debian / Ubuntu:**
```bash
sudo apt install stockfish
```

**macOS:**
```bash
brew install stockfish
```

**No package / Manjaro / Windows** — download the official binary from
[stockfishchess.org/download](https://stockfishchess.org/download/) and either
put it on your `PATH` or drop it in an `engines/` folder inside the project
(the app auto-detects `engines/stockfish*`). You can also point the app at a
specific binary with the `STOCKFISH_PATH` environment variable.

### 2. Set up Python

```bash
git clone git@github.com:Flow-25/Game-Review.git
cd Game-Review

python -m venv .venv
source .venv/bin/activate           # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Run it

Open **two terminals** (both with the virtualenv active):

```bash
# Terminal 1 — the analysis server
uvicorn backend.api:app --port 8000

# Terminal 2 — serve the web page
cd frontend && python -m http.server 5500
```

Then open **<http://127.0.0.1:5500>** in your browser. 🎉

---

## 🎮 How to use

1. Click **Paste PGN** (or **Load sample**), paste a game, and hit **Analyze**.
   Watch the progress bar as Stockfish reviews each move.
2. Step through the game with the **← / →** arrow keys, the **mouse wheel** over
   the board, the on-screen buttons, or by clicking any move in the list.
3. Each move shows its classification badge; when you go wrong, a green arrow
   points to the move the engine preferred.
4. Hit **⚄ Analysis** at any point to branch off: **drag the pieces** to explore
   variations and the engine evaluates live, listing its best lines. Paste a
   **FEN** to analyze any position from scratch. **Undo**, **Reset**, or
   **Exit analysis** to return to the review.

> **Tip:** higher **Time/move** in the PGN panel gives stronger, more reliable
> reviews (and better Brilliant/Great detection) — at the cost of longer waits.

---

## 🏷️ Move classifications

| Badge | Meaning |
|:-----:|---------|
| `!!` **Brilliant** | A sound sacrifice — gives up material for a winning initiative. |
| `!` **Great** | The single move that holds a difficult, contested position. |
| `★` **Best** | The engine's top choice. |
| `✓` **Excellent / Good** | Strong moves, very close to best. |
| 📖 **Book** | A known opening move. |
| `?!` **Inaccuracy** | A small slip. |
| `?` **Mistake** | A meaningful error. |
| `??` **Blunder** | A serious, game-changing error. |

---

## ⚙️ Configuration

| What | How |
|------|-----|
| Use a specific Stockfish binary | `STOCKFISH_PATH=/path/to/stockfish uvicorn backend.api:app` |
| Analysis strength / speed | **Time/move** field in the UI (default 0.1 s). |
| Connect UI to a different backend | Edit the **API base URL** field in the top bar (saved in your browser). |

Deeper tuning (classification thresholds, brilliancy/only-move sensitivity,
opening-book depth) lives in [`backend/config.py`](backend/config.py).

---

## 🩺 Troubleshooting

- **"Could not locate the Stockfish binary"** — install Stockfish, put it on your
  `PATH`, drop it in `engines/`, or set `STOCKFISH_PATH`.
- **The page loads but nothing happens on Analyze** — make sure the API server
  (terminal 1) is running and the **API base URL** in the top bar matches it.
- **Opening shows "Unknown opening"** — the position left the book early, or the
  openings database is missing; it ships in `backend/data/openings.json` and can
  be rebuilt with `python -m backend.build_openings`.

---

## 🧰 Command-line use (no browser)

You can review a PGN straight from the terminal:

```bash
python -m scripts.analyze game.pgn --time 0.3 --output review.json
```

---

## 🛠️ For developers

Architecture, the phased build notes, API reference, and the details of how
brilliancy/opening detection work are in
**[docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)**.

Built with [python-chess](https://python-chess.readthedocs.io/),
[FastAPI](https://fastapi.tiangolo.com/),
[cm-chessboard](https://github.com/shaack/cm-chessboard), and
[chess.js](https://github.com/jhlywa/chess.js).
