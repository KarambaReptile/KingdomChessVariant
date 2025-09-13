# kingdom_chess_ai.py
# Kingdom Chess: move generator + 3-level AI (Easy/Medium/Hard)
# Built solely from rules defined in this conversation.

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Tuple, Iterable
import math
import random
import time

# -----------------------------------------------------------------------------
# Board coordinates and helpers
# -----------------------------------------------------------------------------

FILES = "abcdefgh"
RANKS = "12345678"
FILE_TO_IDX = {f: i for i, f in enumerate(FILES)}
IDX_TO_FILE = {i: f for f, i in FILE_TO_IDX.items()}

def sq(file_idx: int, rank_idx: int) -> int:
    return rank_idx * 8 + file_idx

def fr_sq(s: str) -> int:
    # e.g., "e4" -> index 4 + (3*8) = 28
    f = FILE_TO_IDX[s[0]]
    r = RANKS.index(s[1])
    return sq(f, r)

def to_algebra(i: int) -> str:
    f = i % 8
    r = i // 8
    return f"{IDX_TO_FILE[f]}{RANKS[r]}"

def on_board(file_idx: int, rank_idx: int) -> bool:
    return 0 <= file_idx < 8 and 0 <= rank_idx < 8

def file_of(i: int) -> int:
    return i % 8

def rank_of(i: int) -> int:
    return i // 8

WHITE = 0
BLACK = 1

# Files 4–7 are zero-indexed: files "e", "f", "g", "h" -> indices 4..7
FILES_4_TO_7 = {4,5,6,7}

# -----------------------------------------------------------------------------
# Pieces and encoding
# -----------------------------------------------------------------------------

# Standard
KING   = "K"
QUEEN  = "Q"
ROOK   = "R"
BISHOP = "B"
KNIGHT = "N"
PAWN   = "P"

# Variant
PRINCESS = "S"   # "S" for "princesS" to avoid clash with "P"
PRINCE   = "U"   # "U" for "prince", unique code
DUKE     = "D"
DRAGON   = "G"   # "G" for draGon
SUBJECT  = "J"   # "J" for subJect
WIZARD   = "W"

ALL_TYPES = {KING, QUEEN, ROOK, BISHOP, KNIGHT, PAWN, PRINCESS, PRINCE, DUKE, DRAGON, SUBJECT, WIZARD}

@dataclass
class Piece:
    color: int         # WHITE or BLACK
    kind: str          # one of ALL_TYPES

EMPTY = None  # empty square marker

# -----------------------------------------------------------------------------
# Moves
# -----------------------------------------------------------------------------

@dataclass
class Move:
    src: int
    dst: int
    capture: Optional[Piece] = None
    special: Optional[str] = None  # e.g., "TELEPORT"

    def __str__(self):
        cap = "x" if self.capture else "-"
        spc = f"({self.special})" if self.special else ""
        return f"{to_algebra(self.src)}{cap}{to_algebra(self.dst)}{spc}"

# -----------------------------------------------------------------------------
# Position
# -----------------------------------------------------------------------------

class Position:
    def __init__(self):
        # 8x8 0..63 bottom rank is rank 0 (white home), top rank rank 7 (black home)
        self.board: List[Optional[Piece]] = [EMPTY]*64
        self.turn: int = WHITE
        self.halfmove: int = 0
        self.fullmove: int = 1

        # Setup containers for quick checks
        self.white_king_sq: Optional[int] = None
        self.black_king_sq: Optional[int] = None

    # --------------------- Setup helpers ---------------------

    def copy(self) -> "Position":
        p = Position()
        p.board = self.board[:]
        p.turn = self.turn
        p.halfmove = self.halfmove
        p.fullmove = self.fullmove
        p.white_king_sq = self.white_king_sq
        p.black_king_sq = self.black_king_sq
        return p

    def place(self, sq_idx: int, piece: Piece):
        self.board[sq_idx] = piece
        if piece.kind == KING:
            if piece.color == WHITE:
                self.white_king_sq = sq_idx
            else:
                self.black_king_sq = sq_idx

    def remove(self, sq_idx: int):
        if self.board[sq_idx] and self.board[sq_idx].kind == KING:
            if self.board[sq_idx].color == WHITE:
                self.white_king_sq = None
            else:
                self.black_king_sq = None
        self.board[sq_idx] = EMPTY

    def king_sq(self, color: int) -> int:
        return self.white_king_sq if color == WHITE else self.black_king_sq

    # --------------------- Game logic ---------------------

    def is_enemy(self, at: int, color: int) -> bool:
        pc = self.board[at]
        return pc is not None and pc.color != color

    def is_friend(self, at: int, color: int) -> bool:
        pc = self.board[at]
        return pc is not None and pc.color == color

    def in_bounds(self, i: int) -> bool:
        return 0 <= i < 64

    def enemy_dragon_alive(self, color: int) -> bool:
        # scan for opponent dragon
        for i, pc in enumerate(self.board):
            if pc and pc.kind == DRAGON and pc.color != color:
                return True
        return False

    def make_move(self, m: Move) -> "Position":
        newp = self.copy()
        moving = newp.board[m.src]
        assert moving is not None, "No piece on source"

        # capture
        if m.capture:
            newp.remove(m.dst)

        # move
        newp.board[m.dst] = moving
        newp.board[m.src] = EMPTY

        # update king pos
        if moving.kind == KING:
            if moving.color == WHITE:
                newp.white_king_sq = m.dst
            else:
                newp.black_king_sq = m.dst

        # update turn
        newp.turn = 1 - self.turn
        if newp.turn == WHITE:
            newp.fullmove += 1
        return newp

# -----------------------------------------------------------------------------
# Move generation (per rules from this conversation)
# -----------------------------------------------------------------------------

def generate_moves(pos: Position) -> List[Move]:
    color = pos.turn
    moves: List[Move] = []
    for i, pc in enumerate(pos.board):
        if pc is None or pc.color != color:
            continue
        if pc.kind == KING:
            _gen_king(pos, i, moves)
        elif pc.kind == QUEEN:
            _gen_slides(pos, i, moves, deltas=[(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)], unlimited=True)
        elif pc.kind == ROOK:
            _gen_slides(pos, i, moves, deltas=[(1,0),(-1,0),(0,1),(0,-1)], unlimited=True)
        elif pc.kind == BISHOP:
            _gen_slides(pos, i, moves, deltas=[(1,1),(1,-1),(-1,1),(-1,-1)], unlimited=True)
        elif pc.kind == KNIGHT:
            _gen_knight(pos, i, moves)
        elif pc.kind == PAWN:
            _gen_pawn(pos, i, moves)
        elif pc.kind == PRINCESS:
            _gen_princess(pos, i, moves)
        elif pc.kind == PRINCE:
            _gen_prince(pos, i, moves)
        elif pc.kind == DUKE:
            _gen_duke(pos, i, moves)
        elif pc.kind == DRAGON:
            _gen_dragon(pos, i, moves)
        elif pc.kind == SUBJECT:
            _gen_subject(pos, i, moves)
        elif pc.kind == WIZARD:
            _gen_wizard(pos, i, moves)
    # Filter illegal (king in check)
    legal = []
    for m in moves:
        np = pos.make_move(m)
        if not _king_in_check(np, color):
            legal.append(m)
    return legal

def _add_if_legal_target(pos: Position, src: int, f: int, r: int, moves: List[Move], capture_ok=True, move_ok=True, special=None):
    if not on_board(f, r):
        return
    dst = sq(f, r)
    pc_src = pos.board[src]
    assert pc_src
    pc_dst = pos.board[dst]
    if pc_dst is None:
        if move_ok:
            moves.append(Move(src, dst, None, special))
    else:
        if capture_ok and pc_dst.color != pc_src.color:
            moves.append(Move(src, dst, pc_dst, special))

def _gen_king(pos: Position, i: int, moves: List[Move]):
    f, r = file_of(i), rank_of(i)
    for df in (-1,0,1):
        for dr in (-1,0,1):
            if df == 0 and dr == 0:
                continue
            _add_if_legal_target(pos, i, f+df, r+dr, moves)

def _gen_knight(pos: Position, i: int, moves: List[Move]):
    f, r = file_of(i), rank_of(i)
    for df, dr in [(1,2),(2,1),(-1,2),(-2,1),(1,-2),(2,-1),(-1,-2),(-2,-1)]:
        _add_if_legal_target(pos, i, f+df, r+dr, moves)

def _ray(pos: Position, i: int, df: int, dr: int) -> Iterable[Tuple[int,int,int]]:
    f, r = file_of(i), rank_of(i)
    f += df; r += dr
    while on_board(f, r):
        yield (sq(f,r), f, r)
        f += df; r += dr

def _gen_slides(pos: Position, i: int, moves: List[Move], deltas: List[Tuple[int,int]], unlimited: bool):
    for df, dr in deltas:
        for dst, f, r in _ray(pos, i, df, dr):
            if pos.board[dst] is None:
                moves.append(Move(i, dst, None))
                if not unlimited:
                    break
            else:
                if pos.board[dst].color != pos.board[i].color:
                    moves.append(Move(i, dst, pos.board[dst]))
                break

def _forward_dir(color: int) -> int:
    # White moves up (toward higher ranks), Black moves down
    return 1 if color == WHITE else -1

def _gen_pawn(pos: Position, i: int, moves: List[Move]):
    pc = pos.board[i]; assert pc
    f, r = file_of(i), rank_of(i)
    fr = _forward_dir(pc.color)

    # move forward one if empty
    nf, nr = f, r + fr
    if on_board(nf, nr) and pos.board[sq(nf, nr)] is None:
        moves.append(Move(i, sq(nf, nr), None))
    # captures diagonally forward
    for df in (-1, 1):
        nf2, nr2 = f+df, r+fr
        if on_board(nf2, nr2):
            dst = sq(nf2, nr2)
            if pos.board[dst] and pos.board[dst].color != pc.color:
                moves.append(Move(i, dst, pos.board[dst]))

def _gen_princess(pos: Position, i: int, moves: List[Move]):
    # Moves like a queen but ONLY forward (orthogonal forward and forward diagonals).
    pc = pos.board[i]; assert pc
    fr = _forward_dir(pc.color)
    deltas = [(0, fr), (1, fr), (-1, fr)]
    # forward straight and forward diagonals as sliding rays
    for df, dr in deltas:
        for dst, f2, r2 in _ray(pos, i, df, dr):
            if pos.board[dst] is None:
                moves.append(Move(i, dst, None))
            else:
                if pos.board[dst].color != pc.color:
                    moves.append(Move(i, dst, pos.board[dst]))
                break

def _gen_prince(pos: Position, i: int, moves: List[Move]):
    # One square forward OR one square horizontally (left/right); no backward.
    pc = pos.board[i]; assert pc
    f, r = file_of(i), rank_of(i)
    fr = _forward_dir(pc.color)

    # forward one (can move or capture)
    _add_if_legal_target(pos, i, f, r+fr, moves, capture_ok=True, move_ok=True)

    # sideways (left/right) one on same rank; can move or capture
    _add_if_legal_target(pos, i, f-1, r, moves, capture_ok=True, move_ok=True)
    _add_if_legal_target(pos, i, f+1, r, moves, capture_ok=True, move_ok=True)

def _gen_duke(pos: Position, i: int, moves: List[Move]):
    # One or two squares in any direction; cannot jump.
    pc = pos.board[i]; assert pc
    f, r = file_of(i), rank_of(i)
    dirs = [(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]

    # one-step
    for df, dr in dirs:
        _add_if_legal_target(pos, i, f+df, r+dr, moves, capture_ok=True, move_ok=True)

    # two-step with blocking checks
    for df, dr in dirs:
        mf, mr = f+df, r+dr
        if not on_board(mf, mr): continue
        mid = sq(mf, mr)
        if pos.board[mid] is not None:
            continue  # blocked
        tf, tr = f+2*df, r+2*dr
        if not on_board(tf, tr): continue
        dst = sq(tf, tr)
        pc_dst = pos.board[dst]
        if pc_dst is None:
            moves.append(Move(i, dst, None))
        elif pc_dst.color != pc.color:
            moves.append(Move(i, dst, pc_dst))

def _gen_dragon(pos: Position, i: int, moves: List[Move]):
    # One square diagonally in any direction (including backward).
    f, r = file_of(i), rank_of(i)
    for df, dr in [(1,1), (1,-1), (-1,1), (-1,-1)]:
        _add_if_legal_target(pos, i, f+df, r+dr, moves, capture_ok=True, move_ok=True)

def _gen_subject(pos: Position, i: int, moves: List[Move]):
    # Moves diagonally forward one (to empty). Captures straight forward one.
    pc = pos.board[i]; assert pc
    f, r = file_of(i), rank_of(i)
    fr = _forward_dir(pc.color)

    # move diagonally forward into empty
    for df in (-1, 1):
        nf, nr = f+df, r+fr
        if on_board(nf, nr):
            dst = sq(nf, nr)
            if pos.board[dst] is None:
                moves.append(Move(i, dst, None))

    # capture straight forward one
    nf2, nr2 = f, r+fr
    if on_board(nf2, nr2):
        dst2 = sq(nf2, nr2)
        if pos.board[dst2] and pos.board[dst2].color != pc.color:
            moves.append(Move(i, dst2, pos.board[dst2]))

def _gen_wizard(pos: Position, i: int, moves: List[Move]):
    # If opposite-colored Dragon is NOT captured: teleport to any empty square (no capture).
    # If opposite-colored Dragon IS captured: may capture ONLY Subjects or Pawns on files 4..7. No empty-square moves.
    pc = pos.board[i]; assert pc
    enemy_dragon_up = pos.enemy_dragon_alive(pc.color)

    if enemy_dragon_up:
        # teleport to any unoccupied square; cannot capture
        for idx in range(64):
            if pos.board[idx] is None:
                # Preserve parity rules: cannot move if same square
                if idx != i:
                    moves.append(Move(i, idx, None, special="TELEPORT"))
    else:
        # captures only Subjects or Pawns on files 4..7
        for idx, target in enumerate(pos.board):
            if target and target.color != pc.color and target.kind in (SUBJECT, PAWN):
                if file_of(idx) in FILES_4_TO_7:
                    # Wizard "captures" by moving to the target square (no movement constraint otherwise)
                    moves.append(Move(i, idx, target, special="WIZARD_CAPTURE"))

# -----------------------------------------------------------------------------
# Check detection
# -----------------------------------------------------------------------------

def _king_in_check(pos: Position, color: int) -> bool:
    king_sq = pos.king_sq(color)
    if king_sq is None:
        return True  # king captured - illegal state seen as in check

    # Scan enemy moves targeting king (naive but safe)
    opp = 1 - color
    for i, pc in enumerate(pos.board):
        if pc is None or pc.color != opp:
            continue
        tmp_moves: List[Move] = []
        if pc.kind == KING:
            _gen_king(pos, i, tmp_moves)
        elif pc.kind == QUEEN:
            _gen_slides(pos, i, tmp_moves, deltas=[(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)], unlimited=True)
        elif pc.kind == ROOK:
            _gen_slides(pos, i, tmp_moves, deltas=[(1,0),(-1,0),(0,1),(0,-1)], unlimited=True)
        elif pc.kind == BISHOP:
            _gen_slides(pos, i, tmp_moves, deltas=[(1,1),(1,-1),(-1,1),(-1,-1)], unlimited=True)
        elif pc.kind == KNIGHT:
            _gen_knight(pos, i, tmp_moves)
        elif pc.kind == PAWN:
            # For check detection, only their attack squares matter (diagonal forward)
            f, r = file_of(i), rank_of(i)
            fr = _forward_dir(pc.color)
            for df in (-1, 1):
                nf, nr = f+df, r+fr
                if on_board(nf, nr):
                    if sq(nf, nr) == king_sq:
                        return True
        elif pc.kind == PRINCESS:
            _gen_princess(pos, i, tmp_moves)
        elif pc.kind == PRINCE:
            _gen_prince(pos, i, tmp_moves)
        elif pc.kind == DUKE:
            _gen_duke(pos, i, tmp_moves)
        elif pc.kind == DRAGON:
            _gen_dragon(pos, i, tmp_moves)
        elif pc.kind == SUBJECT:
            # Subject attacks straight forward one (for capture), so check that square
            f, r = file_of(i), rank_of(i)
            fr = _forward_dir(pc.color)
            nf, nr = f, r+fr
            if on_board(nf, nr) and sq(nf, nr) == king_sq:
                return True
            continue
        elif pc.kind == WIZARD:
            # Wizard cannot "attack" when enemy dragon alive; when enemy dragon is dead it can
            # capture only Subject/Pawn on files 4..7. It could in principle capture our King?
            # Rules specify ONLY Subjects and Pawns, so Wizard cannot check the King at all.
            tmp_moves = []

        for m in tmp_moves:
            if m.dst == king_sq and m.capture is not None:
                return True
            # also consider king-adjacent moves (king move without capture would also attack)
            if pc.kind in (KING, KNIGHT, DUKE, PRINCE, DRAGON, PRINCESS, QUEEN, ROOK, BISHOP) and m.dst == king_sq:
                # If move generator produced non-captures that land on king square, enemy piece is attacking that square
                return True
    return False

# -----------------------------------------------------------------------------
# Evaluation (material + simple positional)
# -----------------------------------------------------------------------------

PIECE_VALUES = {
    QUEEN:   900,
    ROOK:    500,
    BISHOP:  325,
    KNIGHT:  300,
    PAWN:    100,
    PRINCESS:650,
    PRINCE:  225,
    DUKE:    425,
    DRAGON:  275,
    SUBJECT:  75,
    WIZARD:  350,
    KING:      0,  # not counted
}

def evaluate(pos: Position) -> int:
    # Positive is good for side-to-move
    score = 0
    # material
    for pc in pos.board:
        if pc is None:
            continue
        v = PIECE_VALUES.get(pc.kind, 0)
        score += v if pc.color == pos.turn else -v

    # mobility (small)
    moves = generate_moves(pos)
    score += int(2 * len(moves))

    # wizard dynamic: slight bonus if teleport enabled; otherwise, bonus per eligible target
    for i, pc in enumerate(pos.board):
        if pc and pc.kind == WIZARD:
            if pos.enemy_dragon_alive(pc.color):
                score += 20 if pc.color == pos.turn else -20
            else:
                # count eligible enemy pawns/subjects on files 4..7
                cnt = 0
                for j, t in enumerate(pos.board):
                    if t and t.color != pc.color and t.kind in (SUBJECT, PAWN) and file_of(j) in FILES_4_TO_7:
                        cnt += 1
                delta = 10 * cnt
                score += delta if pc.color == pos.turn else -delta
    return score

# -----------------------------------------------------------------------------
# Search (three levels)
# -----------------------------------------------------------------------------

INF = 10**9

def search_best_move(pos: Position, level: str, time_limit_ms: int = None) -> Optional[Move]:
    if level.lower() == "easy":
        return _search_easy(pos)
    elif level.lower() == "medium":
        return _search_medium(pos, time_limit_ms or 500)
    elif level.lower() == "hard":
        return _search_hard(pos, time_limit_ms or 2500)
    else:
        raise ValueError("Unknown difficulty: choose 'easy', 'medium', or 'hard'")

def _search_easy(pos: Position) -> Optional[Move]:
    # Depth 1 with slight randomness
    moves = generate_moves(pos)
    if not moves:
        return None
    scored = []
    for m in moves:
        np = pos.make_move(m)
        scored.append((evaluate(np), m))
    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:3] if len(scored) >= 3 else scored
    return random.choice(top)[1]

def _negamax(pos: Position, depth: int, alpha: int, beta: int, end_time: float) -> Tuple[int, Optional[Move]]:
    if time.time() > end_time:
        return 0, None
    if depth == 0:
        return _quiesce(pos, alpha, beta, end_time), None
    best_score = -INF
    best_move = None
    moves = generate_moves(pos)
    if not moves:
        # Checkmate or stalemate
        if _king_in_check(pos, pos.turn):
            return -50000 - depth, None  # checkmated
        return 0, None  # stalemate

    # Simple MVV-LVA ordering approx: captures first
    def mv_order(m: Move) -> int:
        return (1000 if m.capture else 0)
    moves.sort(key=mv_order, reverse=True)

    for m in moves:
        if time.time() > end_time:
            break
        np = pos.make_move(m)
        score, _ = _negamax(np, depth-1, -beta, -alpha, end_time)
        score = -score
        if score > best_score:
            best_score = score
            best_move = m
        if best_score > alpha:
            alpha = best_score
        if alpha >= beta:
            break
    return best_score, best_move

def _quiesce(pos: Position, alpha: int, beta: int, end_time: float) -> int:
    stand_pat = evaluate(pos)
    if stand_pat >= beta:
        return beta
    if alpha < stand_pat:
        alpha = stand_pat

    # consider only captures for quiescence (plus wizard special captures)
    for m in generate_moves(pos):
        if time.time() > end_time:
            break
        if m.capture is None and m.special not in ("WIZARD_CAPTURE",):
            continue
        np = pos.make_move(m)
        score = -_quiesce(np, -beta, -alpha, end_time)
        if score >= beta:
            return beta
        if score > alpha:
            alpha = score
    return alpha

def _search_medium(pos: Position, time_limit_ms: int) -> Optional[Move]:
    end_time = time.time() + (time_limit_ms / 1000.0)
    best_move = None
    best_score = -INF
    depth = 1
    while time.time() < end_time:
        score, move = _negamax(pos, depth, -INF, INF, end_time)
        if move is not None:
            best_move = move
            best_score = score
        depth += 1
        if depth > 6:  # cap for medium
            break
    return best_move

def _search_hard(pos: Position, time_limit_ms: int) -> Optional[Move]:
    end_time = time.time() + (time_limit_ms / 1000.0)
    best_move = None
    best_score = -INF
    depth = 1
    # simple aspiration
    window = 50
    guess = 0
    while time.time() < end_time:
        alpha, beta = guess - window, guess + window
        score, move = _negamax(pos, depth, alpha, beta, end_time)
        if move is None and time.time() < end_time:
            # widen window or fallback full
            score, move = _negamax(pos, depth, -INF, INF, end_time)
        if move is not None:
            best_move = move
            best_score = score
            guess = score
        depth += 1
        if depth > 9:  # reasonable cap for hard
            break
    return best_move

# -----------------------------------------------------------------------------
# Simple API
# -----------------------------------------------------------------------------

def create_start_position() -> Position:
    # Placeholder: you can place your custom setup here.
    # By default, set kings and a few variants for testing.
    p = Position()

    # Example mini-setup for testing (feel free to replace with your full setup):
    # White
    p.place(fr_sq("e1"), Piece(WHITE, KING))
    p.place(fr_sq("d1"), Piece(WHITE, QUEEN))
    p.place(fr_sq("c1"), Piece(WHITE, BISHOP))
    p.place(fr_sq("b1"), Piece(WHITE, KNIGHT))
    p.place(fr_sq("a1"), Piece(WHITE, ROOK))
    p.place(fr_sq("e2"), Piece(WHITE, PAWN))
    p.place(fr_sq("b2"), Piece(WHITE, SUBJECT))
    p.place(fr_sq("c2"), Piece(WHITE, PRINCE))
    p.place(fr_sq("d2"), Piece(WHITE, PRINCESS))
    p.place(fr_sq("f2"), Piece(WHITE, DUKE))
    p.place(fr_sq("g2"), Piece(WHITE, DRAGON))
    p.place(fr_sq("h2"), Piece(WHITE, WIZARD))

    # Black
    p.place(fr_sq("e8"), Piece(BLACK, KING))
    p.place(fr_sq("d8"), Piece(BLACK, QUEEN))
    p.place(fr_sq("c8"), Piece(BLACK, BISHOP))
    p.place(fr_sq("b8"), Piece(BLACK, KNIGHT))
    p.place(fr_sq("a8"), Piece(BLACK, ROOK))
    p.place(fr_sq("e7"), Piece(BLACK, PAWN))
    p.place(fr_sq("b7"), Piece(BLACK, SUBJECT))
    p.place(fr_sq("c7"), Piece(BLACK, PRINCE))
    p.place(fr_sq("d7"), Piece(BLACK, PRINCESS))
    p.place(fr_sq("f7"), Piece(BLACK, DUKE))
    p.place(fr_sq("g7"), Piece(BLACK, DRAGON))
    p.place(fr_sq("h7"), Piece(BLACK, WIZARD))

    return p

def move_from_uci(pos: Position, uci: str) -> Optional[Move]:
    # uci "e2e4" basic finder
    if len(uci) < 4:
        return None
    src = fr_sq(uci[:2])
    dst = fr_sq(uci[2:4])
    for m in generate_moves(pos):
        if m.src == src and m.dst == dst:
            return m
    return None

def apply_uci(pos: Position, uci: str) -> Position:
    m = move_from_uci(pos, uci)
    if not m:
        raise ValueError(f"Illegal move: {uci}")
    return pos.make_move(m)

def best_move_uci(pos: Position, level: str = "medium", time_limit_ms: int = None) -> Optional[str]:
    m = search_best_move(pos, level, time_limit_ms)
    return str(m) if m else None

# -----------------------------------------------------------------------------
# Example CLI usage
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    random.seed(42)
    pos = create_start_position()
    print("Kingdom Chess AI demo. Side to move:", "White" if pos.turn == WHITE else "Black")
    print("Enter moves like e2e4 or type 'ai' to let engine play one move.")
    level = "medium"

    while True:
        print("\nBoard:")
        for r in range(7, -1, -1):
            row = []
            for f in range(8):
                pc = pos.board[sq(f, r)]
                if pc is None:
                    row.append(".")
                else:
                    sym = pc.kind
                    row.append(sym.lower() if pc.color == BLACK else sym)
            print(RANKS[r], " ".join(row))
        print("  a b c d e f g h")

        if _king_in_check(pos, pos.turn):
            print("Check!")

        line = input(f"{'White' if pos.turn==WHITE else 'Black'} to move (move/ai/level [easy|medium|hard]/quit): ").strip()
        if line == "quit":
            break
        if line.startswith("level"):
            _, lv = line.split()
            level = lv.lower()
            print("Level set to", level)
            continue
        if line == "ai":
            bm = search_best_move(pos, level)
            if bm is None:
                print("No legal moves. Game over.")
                break
            print("AI plays:", bm)
            pos = pos.make_move(bm)
            continue
        try:
            pos = apply_uci(pos, line)
        except Exception as e:
            print("Error:", e)
            continue
