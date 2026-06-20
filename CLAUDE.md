# PROMPT FOR AI AGENT: Chess Game Review System (Part 1 of 4)

## SYSTEM OVERVIEW & ROLE
Act as an experienced Software Architect and Full-Stack Developer. I want to build a local, automated Chess Game Review application (similar to Chess.com's game review) on Arch Linux. 

We will use a hybrid client-server architecture:
- **Backend:** Python + `python-chess` + Stockfish engine (communicating via UCI protocol).
- **Frontend:** HTML + JavaScript + a modern chess board library (e.g., `cm-chessboard` or `chessboardjs`) running in a web browser.

---

## OBJECTIVE FOR PART 1: Environment Setup & Core Engine Logic
We are starting with Phase 1. Do not generate code for the web interface yet. Please provide:

1. **Arch Linux Setup:** Commands to install the necessary system dependencies (including the official `stockfish` package from Arch repositories) and setting up a Python virtual environment (`venv`).
2. **Project Structure:** A clean directory layout for this client-server project.
3. **Core Analysis Script:** A robust Python script using `python-chess` that:
   - Locates and initializes the local Stockfish binary via UCI.
   - Loads a sample game from a PGN string.
   - Iterates through every move, analyzing the position with a time limit (e.g., 0.1s per move).
   - Extracts the evaluation score (in centipawns `cp` or `mate`).
   - Compares the player's move with Stockfish's top recommendation to classify the move quality (e.g., Book, Best, Good, Inaccuracy, Mistake, Blunder) based on the evaluation drop.

Please generate the setup guide and the initial Python script now.
