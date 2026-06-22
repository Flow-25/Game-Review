<div align="center">

# ♞ Game Review

**A local, Chess.com-style game review tool — powered by Stockfish, running entirely on your machine.**

Paste a PGN, get a move-by-move review with classifications, an evaluation bar,
opening detection, and an interactive analysis board where you can drag the
pieces and see the engine's verdict in real time.

</div>

---

## ✨ Features

- **Full game review** — every move classified as **Genius · Brilliant · Great · Best · Excellent · Good · Book · Missed · Inaccuracy · Mistake · Blunder**.
- **Brilliant move detection** — finds *sound sacrifices* (you give up material but keep the advantage), not just engine-best moves.
- **Great move detection** — flags the *only* move that holds in a critical position.
- **Famous-games library** — browse ~20 of the most celebrated games of all time, **already reviewed** and ready to explore instantly (the Immortal, the Opera Game, Fischer's Game of the Century, Kasparov–Topalov, and more).
- **User accounts** — create a local account to **save your analyzed games** and reopen them any time from your personal collection (passwords are hashed, never stored in plaintext; everything stays on your machine).
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
   Or skip the wait entirely: click **📚 Library** and pick one of ~20 famous
   games that ship **already reviewed**.
2. Step through the game with the **← / →** arrow keys, the **mouse wheel** over
   the board, the on-screen buttons, or by clicking any move in the list.
3. Each move shows its classification badge; when you go wrong, a green arrow
   points to the move the engine preferred.
4. Hit **⚄ Analysis** at any point to branch off: **drag the pieces** to explore
   variations and the engine evaluates live, listing its best lines. Paste a
   **FEN** to analyze any position from scratch. **Undo**, **Reset**, or
   **Exit analysis** to return to the review.
5. Click **👤 Sign in** to create an account or log in. Once signed in, hit
   **💾 Save** to store the game you're viewing, and **🗂 My games** to reopen or
   delete anything you've saved. Click your name to sign out.

> **Tip:** higher **Time/move** in the PGN panel gives stronger, more reliable
> reviews (and better Brilliant/Great detection) — at the cost of longer waits.

### 👥 Accounts

Accounts live entirely on your machine under `backend/data/accounts/`
(git-ignored). Passwords are hashed with PBKDF2-HMAC-SHA256 — never stored in
plaintext. To create a few **test accounts** to try the feature:

```bash
python -m backend.accounts seed
```

This creates **alice / alice123**, **bob / bob123**, and **carol / carol123**.

---

## 🏷️ Move classifications

| Badge | Meaning |
|:-----:|---------|
| `!!!` **Genius** | A Brilliant sacrifice that is *also* the only move that keeps a significant advantage — the rarest call. |
| `!!` **Brilliant** | A sound sacrifice — gives up material for a winning initiative. |
| `!` **Great** | The single move that holds a difficult, contested position. |
| `★` **Best** | The engine's top choice. |
| `✓` **Excellent / Good** | Strong moves, very close to best. |
| 📖 **Book** | A known opening move. |
| `−` **Missed** | A weak move that still leaves you clearly winning — you missed a bigger advantage, not the game. |
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
- **The Library is empty** — the pre-reviewed games ship in
  `backend/data/library/`; regenerate them any time with
  `python -m backend.build_library` (add `--time 0.3` for a stronger review).

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
