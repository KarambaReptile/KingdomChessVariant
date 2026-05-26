# kingdom_server.py
# Flask REST server — bridges KingdomChess.jsx to kingdom_chess_ai.py
# Run: python kingdom_server.py
# Default port: 5000

from __future__ import annotations
from flask import Flask, request, jsonify
from flask_cors import CORS
import uuid
import threading

from kingdom_chess_ai import (
    Position, Piece, Move,
    WHITE, BLACK,
    KING, QUEEN, ROOK, BISHOP, KNIGHT, PAWN,
    PRINCESS, PRINCE, DUKE, DRAGON, SUBJECT, WIZARD,
    create_start_position, generate_moves, search_best_move,
    _king_in_check, to_algebra, fr_sq, rank_of, file_of,
    SPECIAL_PROMO_PAWN, SPECIAL_PROMO_SUBJ,
    PIECE_VALUES,
)

app = Flask(__name__)
CORS(app)

# In-memory game store  { game_id: { pos, level, player_color } }
GAMES: dict = {}
LOCK = threading.Lock()

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def color_char(c: int) -> str:
    return "W" if c == WHITE else "B"


def piece_code(pc: Piece) -> str:
    """Returns e.g. 'WK', 'BPS', 'WDR'"""
    return color_char(pc.color) + pc.kind


def board_to_dict(pos: Position) -> dict:
    """Convert board array to { 'e1': 'WK', ... } for the frontend."""
    out = {}
    for i, pc in enumerate(pos.board):
        if pc is not None:
            f = file_of(i)
            r = rank_of(i)
            sq_str = "abcdefghij"[f] + str(r + 1)
            out[sq_str] = piece_code(pc)
    return out


def move_to_dict(m: Move, pos: Position) -> dict:
    """Serialize a Move for the frontend."""
    return {
        "notation": str(m),
        "src": to_algebra(m.src),
        "dst": to_algebra(m.dst),
        "capture": m.capture.kind if m.capture else None,
        "special": m.special,
        "promo_to": m.promo_to,
    }


def game_response(game_id: str, pos: Position, level: str,
                  player_color: int,
                  ai_move: dict = None,
                  captured_code: str = None) -> dict:
    """Build the standard API response object."""
    color = pos.turn
    legal = generate_moves(pos)
    in_check = pos.king_can_be_checked(color) and _king_in_check(pos, color)

    game_over = False
    result = None

    if not legal:
        if in_check:
            winner = color_char(1 - color)
            result = f"Checkmate — {winner} wins!"
        else:
            result = "Stalemate — draw."
        game_over = True

    return {
        "game_id": game_id,
        "board": board_to_dict(pos),
        "turn": color_char(pos.turn),
        "fullmove": pos.fullmove,
        "in_check": in_check,
        "game_over": game_over,
        "result": result,
        "duke_W": pos.duke_alive(WHITE),
        "duke_B": pos.duke_alive(BLACK),
        "dragon_W": pos.dragon_alive(WHITE),
        "dragon_B": pos.dragon_alive(BLACK),
        "ai_move": ai_move,
        "captured": captured_code,
    }


def parse_move_notation(pos: Position, notation: str) -> Move | None:
    """Find a legal move matching the given notation string."""
    for m in generate_moves(pos):
        if str(m) == notation:
            return m
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/ping")
def ping():
    return jsonify({"status": "ok"})


@app.route("/new_game", methods=["POST"])
def new_game():
    data = request.json or {}
    level = data.get("level", "medium").lower()
    player_color_str = data.get("player_color", "W").upper()
    player_color = WHITE if player_color_str == "W" else BLACK

    pos = create_start_position()
    game_id = str(uuid.uuid4())[:8]

    with LOCK:
        GAMES[game_id] = {
            "pos": pos,
            "level": level,
            "player_color": player_color,
        }

    resp = game_response(game_id, pos, level, player_color)

    # If player is Black, AI (White) moves first
    if player_color == BLACK:
        bm = search_best_move(pos, level)
        if bm:
            new_pos = pos.make_move(bm)
            with LOCK:
                GAMES[game_id]["pos"] = new_pos
            ai_dict = move_to_dict(bm, pos)
            resp = game_response(game_id, new_pos, level, player_color,
                                 ai_move=ai_dict)

    return jsonify(resp)


@app.route("/legal_moves", methods=["POST"])
def legal_moves_for_square():
    """Return all legal moves from a given square."""
    data = request.json or {}
    game_id = data.get("game_id")
    square = data.get("square", "").lower()

    with LOCK:
        game = GAMES.get(game_id)
    if not game:
        return jsonify({"error": "Game not found"}), 404

    pos = game["pos"]

    # Parse square
    try:
        src = fr_sq(square)
    except (KeyError, ValueError):
        return jsonify({"error": "Invalid square"}), 400

    pc = pos.board[src]
    if pc is None or pc.color != pos.turn:
        return jsonify({"moves": []})

    moves = [m for m in generate_moves(pos) if m.src == src]
    return jsonify({
        "moves": [move_to_dict(m, pos) for m in moves]
    })


@app.route("/make_move", methods=["POST"])
def make_move():
    data = request.json or {}
    game_id = data.get("game_id")
    notation = data.get("move", "")

    with LOCK:
        game = GAMES.get(game_id)
    if not game:
        return jsonify({"error": "Game not found"}), 404

    pos = game["pos"]
    level = game["level"]
    player_color = game["player_color"]

    m = parse_move_notation(pos, notation)
    if m is None:
        return jsonify({"error": f"Illegal or unrecognised move: {notation}"}), 400

    captured_code = m.capture.kind if m.capture else None
    new_pos = pos.make_move(m)

    with LOCK:
        GAMES[game_id]["pos"] = new_pos

    resp = game_response(game_id, new_pos, level, player_color,
                         captured_code=captured_code)
    return jsonify(resp)


@app.route("/ai_move", methods=["POST"])
def ai_move():
    data = request.json or {}
    game_id = data.get("game_id")

    with LOCK:
        game = GAMES.get(game_id)
    if not game:
        return jsonify({"error": "Game not found"}), 404

    pos = game["pos"]
    level = game["level"]
    player_color = game["player_color"]

    bm = search_best_move(pos, level)
    if bm is None:
        return jsonify({"error": "No legal moves for AI"}), 400

    captured_code = bm.capture.kind if bm.capture else None
    ai_dict = move_to_dict(bm, pos)
    new_pos = pos.make_move(bm)

    with LOCK:
        GAMES[game_id]["pos"] = new_pos

    resp = game_response(game_id, new_pos, level, player_color,
                         ai_move=ai_dict,
                         captured_code=captured_code)
    return jsonify(resp)


@app.route("/game_state", methods=["GET"])
def game_state():
    game_id = request.args.get("game_id")
    with LOCK:
        game = GAMES.get(game_id)
    if not game:
        return jsonify({"error": "Game not found"}), 404
    pos = game["pos"]
    return jsonify(game_response(game_id, pos, game["level"], game["player_color"]))


# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Kingdom Chess Server starting on http://localhost:5000")
    print("Make sure kingdom_chess_ai.py is in the same directory.")
    app.run(debug=False, port=5000, threaded=True)
