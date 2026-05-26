# Kingdom Chess

**A chess variant by Josef Laspina · MotoHov Industries (Malta)**
Rules: https://kingdomchessvariant.wordpress.com

---

## What is Kingdom Chess?

Kingdom Chess is an original 10×10 chess variant featuring 12 piece types
including the Princess, Prince, Duke, Dragon, Subject, and Wizard.
The most distinctive feature is the **Duke-King dependency**: while both Dukes
are alive, Kings cannot capture and cannot be put in check. Capturing an
opponent's Duke is the key strategic trigger that opens the King to attack.

---

## Files in this repository

| File | Purpose |
|---|---|
| `kingdom_chess_ai.py` | Complete game engine: 10×10 board, all 12 piece types, 3-level AI |
| `kingdom_server.py` | Flask REST server — connects the React frontend to the engine |
| `KingdomChess.jsx` | React frontend — visual board, clickable pieces, game panel |

---

## Quick Start — Terminal (no install beyond Python)

```bash
python kingdom_chess_ai.py
```

Type moves in algebraic notation:
- `e2e3` — move piece from e2 to e3
- `a3b4` — subject diagonal move
- `ai` — ask the AI to play the current side
- `level easy` / `level medium` / `level hard` — change difficulty
- `moves` — list all legal moves
- `quit` — exit

---

## Full Setup — Visual Browser Interface

### Requirements

- Python 3.9 or newer
- Node.js 18 or newer (for the React frontend)

### Step 1 — Install Python dependencies

```bash
pip install flask flask-cors
```

### Step 2 — Start the game server

```bash
python kingdom_server.py
```

You should see:
```
Kingdom Chess Server starting on http://localhost:5000
```

Leave this terminal open.

### Step 3 — Set up the React frontend

In a new terminal:

```bash
# If you don't have a React project yet:
npx create-react-app kingdom-chess
cd kingdom-chess

# Copy KingdomChess.jsx into src/
cp /path/to/KingdomChess.jsx src/KingdomChess.jsx

# Edit src/App.js to use the component:
```

Replace the contents of `src/App.js` with:

```jsx
import KingdomChess from './KingdomChess';
export default function App() { return <KingdomChess />; }
```

Then run:

```bash
npm start
```

Open your browser at **http://localhost:3000**

---

## How to Play

### Selecting and moving pieces

1. Click any of your pieces — legal destination squares are highlighted
2. Click a highlighted square to move there
3. If a pawn reaches the last rank, a promotion dialog appears

### The AI

- Click **AI Move** to make the AI play the current side
- Or set yourself as Black and the AI plays White automatically
- Change difficulty with the dropdown before starting a new game

---

## Piece Reference

| Symbol | Name | Movement |
|---|---|---|
| ♔ K | King | One square any direction. Cannot capture or be checked while own Duke is alive. |
| ♕ Q | Queen | Unlimited any direction |
| ♖ R | Rook | Unlimited along ranks and files |
| ♗ B | Bishop | Unlimited diagonally |
| ♘ N | Knight | Standard L-shape |
| ♙ P | Pawn | Forward 1 (or 2 on first move); captures diagonally. Promotes on last rank. |
| ⚜ PS | Princess | Unlimited along full rank + unlimited forward (file and diagonals) |
| ⚡ PR | Prince | One square: forward, forward-diagonal, or sideways |
| 🛡 D | Duke | 1 or 2 squares any direction (no jumping). Protecting it shields your King. |
| 🐉 DR | Dragon | Moves diagonally to empty square; captures orthogonally adjacent |
| ⬡ S | Subject | Moves diagonally forward; captures straight forward. En passant with subjects. |
| ✦ W | Wizard | While enemy Dragon alive: teleports to any empty square. After enemy Dragon captured: captures Subjects/Pawns in the battlefield (ranks 4–7). |

---

## Duke-King Dependency (the core rule)

This is what makes Kingdom Chess unique:

- **Both Dukes alive**: Neither King can capture pieces or be put in check
- **Your Duke captured**: Your King becomes vulnerable — it can now be checked and checkmated
- **Opponent's Duke captured**: Your King gains full capturing power
- **Both Dukes captured**: Both Kings function as in standard chess

Protecting your Duke is therefore as important as protecting your King.

---

## Starting Position

```
  a   b   c   d   e   f   g   h   i   j
10 br  bn  bb  bps bk  bq  bpr bb  bn  br
 9 bp  bp  bp  bp  bd  bw  bp  bp  bp  bp
 8 bs  bs  bs  bs  bs  bdr bs  bs  bs  bs
 7 .   .   .   .   .   .   .   .   .   .
 6 .   .   .   .   .   .   .   .   .   .
 5 .   .   .   .   .   .   .   .   .   .
 4 .   .   .   .   .   .   .   .   .   .
 3 WS  WS  WS  WS  WS  WDR WS  WS  WS  WS
 2 WP  WP  WP  WP  WD  WW  WP  WP  WP  WP
 1 WR  WN  WB  WPS WK  WQ  WPR WB  WN  WR
```

Ranks 4–7 are the battlefield — the Wizard's capture zone.

---

## AI Levels

| Level | Behaviour |
|---|---|
| Easy | Evaluates 1 ply, picks randomly among top third of moves |
| Medium | Iterative deepening negamax with alpha-beta, ~600ms time limit |
| Hard | Aspiration windows + deeper iterative deepening, ~3000ms time limit |

---

## Smartphone

**Android:** Install **Pydroid 3** from the Play Store, paste `kingdom_chess_ai.py`,
run it — text terminal game, no server needed.

**iPhone:** Install **Pyto** from the App Store, same process.

For the visual interface on mobile, run the server on a PC and open
`http://<your-pc-ip>:3000` in the phone's browser on the same Wi-Fi network.

---

## Known limitations

- No draw by repetition or 50-move rule detection yet
- No persistent game save/load
- Wizard teleport on Hard difficulty adds significant branching — expect slightly
  longer think times in opening positions

---

## Credits

- **Rules and game design**: Josef Laspina, MotoHov Industries, Malta (2004)
  https://kingdomchessvariant.wordpress.com
- **Engine and interface**: Generated with Claude (Anthropic), May 2026
- **Original repository**: https://github.com/KarambaReptile/KingdomChessVariant
