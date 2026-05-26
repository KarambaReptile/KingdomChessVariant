    # kingdom_chess_ai.py
# Kingdom Chess: corrected move generator + 3-level AI (Easy/Medium/Hard)
# 10x10 board, all piece rules per Josef Laspina's official rules (2004)
# Corrections vs original: 10x10 board, correct piece movements (Princess,
# Prince, Dragon, Subject), Duke-King dependency, pawn/subject first-move
# double-step, en passant, promotion, Kingdom castling, wizard zone fix.

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Set
import random
import time

# ---------------------------------------------------------------------------
# Board: 10 files (a-j), 10 ranks (1-10), 100 squares
# Square index = rank_idx * 10 + file_idx  (rank_idx 0=rank1, 9=rank10)
# ---------------------------------------------------------------------------

FILES = "abcdefghij"
RANKS = [str(i) for i in range(1, 11)]          # ["1","2",...,"10"]
FILE_TO_IDX = {f: i for i, f in enumerate(FILES)}
IDX_TO_FILE = {i: f for f, i in FILE_TO_IDX.items()}

NUM_FILES = 10
NUM_RANKS = 10
NUM_SQUARES = 100


def sq(file_idx: int, rank_idx: int) -> int:
    return rank_idx * NUM_FILES + file_idx


def file_of(i: int) -> int:
    return i % NUM_FILES


def rank_of(i: int) -> int:
    return i // NUM_FILES


def on_board(f: int, r: int) -> bool:
    return 0 <= f < NUM_FILES and 0 <= r < NUM_RANKS


def fr_sq(notation: str) -> int:
    """Parse algebraic notation like 'e1' or 'j10' into square index."""
    f = FILE_TO_IDX[notation[0]]
    r = int(notation[1:]) - 1   # rank "1" -> index 0
    return sq(f, r)


def to_algebra(i: int) -> str:
    f = file_of(i)
    r = rank_of(i)
    return f"{IDX_TO_FILE[f]}{r + 1}"


# ---------------------------------------------------------------------------
# Colours
# ---------------------------------------------------------------------------

WHITE = 0
BLACK = 1


def opp(color: int) -> int:
    return 1 - color


# ---------------------------------------------------------------------------
# Piece types
# ---------------------------------------------------------------------------

KING     = "K"
QUEEN    = "Q"
ROOK     = "R"
BISHOP   = "B"
KNIGHT   = "N"
PAWN     = "P"
PRINCESS = "PS"   # moves along rank (unlimited) + forward along file/diagonal
PRINCE   = "PR"   # one square: forward, forward-diag, or sideways
DUKE     = "D"
DRAGON   = "DR"   # moves diag to empty; captures orthogonally adjacent
SUBJECT  = "S"    # moves diag-forward; captures straight-forward
WIZARD   = "W"    # teleports to empty; after opp dragon dead: captures S/P on ranks 4-7


@dataclass(frozen=True)
class Piece:
    color: int
    kind: str

    def symbol(self) -> str:
        base = self.kind if len(self.kind) == 1 else self.kind[0]
        return base.lower() if self.color == BLACK else base.upper()


EMPTY = None


# ---------------------------------------------------------------------------
# Special move tags
# ---------------------------------------------------------------------------

SPECIAL_CASTLE     = "CASTLE"
SPECIAL_EP_PAWN    = "EP_PAWN"      # en passant pawn captures pawn
SPECIAL_EP_SUBJECT = "EP_SUBJECT"   # en passant subject captures subject
SPECIAL_TELEPORT   = "TELEPORT"
SPECIAL_WIZ_CAP    = "WIZ_CAP"
SPECIAL_PROMO_PAWN = "PROMO_PAWN"   # pawn promotes (choice stored in promo_to)
SPECIAL_PROMO_SUBJ = "PROMO_SUBJ"   # subject promotes to pawn first


@dataclass
class Move:
    src: int
    dst: int
    capture: Optional[Piece] = None
    special: Optional[str] = None
    promo_to: Optional[str] = None   # piece kind for promotion
    ep_sq: Optional[int] = None      # square of captured pawn/subject in en passant

    def __str__(self) -> str:
        cap = "x" if self.capture else "-"
        spc = f"({self.special})" if self.special else ""
        promo = f"={self.promo_to}" if self.promo_to else ""
        return f"{to_algebra(self.src)}{cap}{to_algebra(self.dst)}{spc}{promo}"


# ---------------------------------------------------------------------------
# Position
# ---------------------------------------------------------------------------

@dataclass
class Position:
    board: List[Optional[Piece]]
    turn: int = WHITE
    fullmove: int = 1

    # En passant: square that can be captured en passant (None if not available)
    ep_pawn_sq: Optional[int] = None      # square the pawn/subject actually stands on
    ep_subj_sq: Optional[int] = None

    # Has-moved flags for castling and first-move double-steps
    white_king_moved: bool = False
    black_king_moved: bool = False
    white_rook_a_moved: bool = False
    white_rook_j_moved: bool = False
    black_rook_a_moved: bool = False
    black_rook_j_moved: bool = False

    # Track which pawns/subjects have moved (by square index at game start)
    # We use a frozenset of squares that have moved (simpler than per-piece tracking)
    pieces_moved: Set[int] = field(default_factory=set)

    # King squares for fast lookup
    white_king_sq: Optional[int] = None
    black_king_sq: Optional[int] = None

    # ---------------------------------------------------------------------------

    @staticmethod
    def empty_board() -> "Position":
        return Position(board=[EMPTY] * NUM_SQUARES)

    def copy(self) -> "Position":
        p = Position(
            board=self.board[:],
            turn=self.turn,
            fullmove=self.fullmove,
            ep_pawn_sq=self.ep_pawn_sq,
            ep_subj_sq=self.ep_subj_sq,
            white_king_moved=self.white_king_moved,
            black_king_moved=self.black_king_moved,
            white_rook_a_moved=self.white_rook_a_moved,
            white_rook_j_moved=self.white_rook_j_moved,
            black_rook_a_moved=self.black_rook_a_moved,
            black_rook_j_moved=self.black_rook_j_moved,
            pieces_moved=set(self.pieces_moved),
            white_king_sq=self.white_king_sq,
            black_king_sq=self.black_king_sq,
        )
        return p

    def place(self, sq_idx: int, piece: Piece) -> None:
        self.board[sq_idx] = piece
        if piece.kind == KING:
            if piece.color == WHITE:
                self.white_king_sq = sq_idx
            else:
                self.black_king_sq = sq_idx

    def remove_piece(self, sq_idx: int) -> None:
        pc = self.board[sq_idx]
        if pc and pc.kind == KING:
            if pc.color == WHITE:
                self.white_king_sq = None
            else:
                self.black_king_sq = None
        self.board[sq_idx] = EMPTY

    def king_sq(self, color: int) -> Optional[int]:
        return self.white_king_sq if color == WHITE else self.black_king_sq

    # Duke alive check
    def duke_alive(self, color: int) -> bool:
        for pc in self.board:
            if pc and pc.kind == DUKE and pc.color == color:
                return True
        return False

    def dragon_alive(self, color: int) -> bool:
        for pc in self.board:
            if pc and pc.kind == DRAGON and pc.color == color:
                return True
        return False

    def enemy_dragon_alive(self, color: int) -> bool:
        return self.dragon_alive(opp(color))

    # King capture/check rules depend on duke status
    def king_can_capture(self, color: int) -> bool:
        """A king can capture only when the opponent's duke is captured."""
        return not self.duke_alive(opp(color))

    def king_can_be_checked(self, color: int) -> bool:
        """A king can be put in check only when its own duke is captured."""
        return not self.duke_alive(color)

    # ---------------------------------------------------------------------------
    # Make move
    # ---------------------------------------------------------------------------

    def make_move(self, m: Move) -> "Position":
        p = self.copy()
        moving = p.board[m.src]
        assert moving is not None

        # Clear ep state; will be re-set below if double-step
        p.ep_pawn_sq = None
        p.ep_subj_sq = None

        # Handle special moves
        if m.special == SPECIAL_CASTLE:
            _apply_castle(p, m)
            p.turn = opp(self.turn)
            if p.turn == WHITE:
                p.fullmove += 1
            return p

        # En passant captures
        if m.special == SPECIAL_EP_PAWN and m.ep_sq is not None:
            p.remove_piece(m.ep_sq)
        if m.special == SPECIAL_EP_SUBJECT and m.ep_sq is not None:
            p.remove_piece(m.ep_sq)

        # Normal capture
        if m.capture and m.special not in (SPECIAL_EP_PAWN, SPECIAL_EP_SUBJECT):
            p.remove_piece(m.dst)

        # Move piece
        p.board[m.dst] = moving
        p.board[m.src] = EMPTY
        p.pieces_moved.add(m.src)   # mark source as having moved

        # Update king pos
        if moving.kind == KING:
            if moving.color == WHITE:
                p.white_king_sq = m.dst
                p.white_king_moved = True
            else:
                p.black_king_sq = m.dst
                p.black_king_moved = True

        # Rook move tracking for castling
        if moving.kind == ROOK:
            if moving.color == WHITE:
                if m.src == fr_sq("a1"):
                    p.white_rook_a_moved = True
                elif m.src == fr_sq("j1"):
                    p.white_rook_j_moved = True
            else:
                if m.src == fr_sq("a10"):
                    p.black_rook_a_moved = True
                elif m.src == fr_sq("j10"):
                    p.black_rook_j_moved = True

        # En passant availability: pawn double step
        if moving.kind == PAWN and abs(rank_of(m.src) - rank_of(m.dst)) == 2:
            p.ep_pawn_sq = m.dst

        # En passant availability: subject double step
        if moving.kind == SUBJECT and abs(rank_of(m.src) - rank_of(m.dst)) == 2:
            p.ep_subj_sq = m.dst

        # Promotion
        if m.special == SPECIAL_PROMO_PAWN and m.promo_to:
            p.board[m.dst] = Piece(moving.color, m.promo_to)
        if m.special == SPECIAL_PROMO_SUBJ:
            # subject promotes to pawn; pawn promotion happens next move (handled as normal pawn)
            p.board[m.dst] = Piece(moving.color, PAWN)

        p.turn = opp(self.turn)
        if p.turn == WHITE:
            p.fullmove += 1
        return p


def _apply_castle(p: Position, m: Move) -> None:
    """Apply Kingdom castling: king moves 2 squares toward rook, rook jumps over."""
    color = p.board[m.src].color
    king_src = m.src
    king_dst = m.dst

    # Determine rook location
    if file_of(king_dst) > file_of(king_src):
        # Kingside (toward j-file)
        rook_src = sq(9, rank_of(king_src))
        rook_dst = sq(file_of(king_src) + 1, rank_of(king_src))
    else:
        # Queenside (toward a-file)
        rook_src = sq(0, rank_of(king_src))
        rook_dst = sq(file_of(king_src) - 1, rank_of(king_src))

    rook = p.board[rook_src]
    p.board[king_dst] = p.board[king_src]
    p.board[king_src] = EMPTY
    p.board[rook_dst] = rook
    p.board[rook_src] = EMPTY

    if color == WHITE:
        p.white_king_sq = king_dst
        p.white_king_moved = True
        p.white_rook_a_moved = True
        p.white_rook_j_moved = True
    else:
        p.black_king_sq = king_dst
        p.black_king_moved = True
        p.black_rook_a_moved = True
        p.black_rook_j_moved = True


# ---------------------------------------------------------------------------
# Move generation helpers
# ---------------------------------------------------------------------------

def _forward(color: int) -> int:
    return 1 if color == WHITE else -1


def _ray(pos: Position, f: int, r: int, df: int, dr: int):
    """Generate squares along a ray until blocked or off-board."""
    f += df
    r += dr
    while on_board(f, r):
        yield sq(f, r), f, r
        f += df
        r += dr


def _add_slide(pos: Position, src: int, moves: List[Move],
               deltas: List[Tuple[int, int]], unlimited: bool = True) -> None:
    color = pos.board[src].color
    f0, r0 = file_of(src), rank_of(src)
    for df, dr in deltas:
        for dst, f, r in _ray(pos, f0, r0, df, dr):
            pc = pos.board[dst]
            if pc is None:
                moves.append(Move(src, dst))
                if not unlimited:
                    break
            else:
                if pc.color != color:
                    moves.append(Move(src, dst, pc))
                break


def _add_step(pos: Position, src: int, dst_f: int, dst_r: int,
              moves: List[Move], capture_ok: bool = True,
              move_ok: bool = True, special: Optional[str] = None,
              ep_sq: Optional[int] = None) -> None:
    if not on_board(dst_f, dst_r):
        return
    dst = sq(dst_f, dst_r)
    color = pos.board[src].color
    pc = pos.board[dst]
    if pc is None:
        if move_ok:
            moves.append(Move(src, dst, None, special, ep_sq=ep_sq))
    else:
        if capture_ok and pc.color != color:
            moves.append(Move(src, dst, pc, special, ep_sq=ep_sq))


# ---------------------------------------------------------------------------
# Per-piece move generators
# ---------------------------------------------------------------------------

def _gen_king(pos: Position, i: int, moves: List[Move]) -> None:
    pc = pos.board[i]
    f, r = file_of(i), rank_of(i)
    can_capture = pos.king_can_capture(pc.color)

    for df in (-1, 0, 1):
        for dr in (-1, 0, 1):
            if df == 0 and dr == 0:
                continue
            nf, nr = f + df, r + dr
            if not on_board(nf, nr):
                continue
            dst = sq(nf, nr)
            target = pos.board[dst]
            if target is None:
                moves.append(Move(i, dst))
            elif target.color != pc.color and can_capture:
                moves.append(Move(i, dst, target))

    # Kingdom castling (only when king's own duke is captured → king can be checked)
    # Castling is only legal once the king can be checked (duke captured)
    if pos.king_can_be_checked(pc.color):
        _gen_castling(pos, i, moves)


def _gen_castling(pos: Position, i: int, moves: List[Move]) -> None:
    pc = pos.board[i]
    color = pc.color
    rank = rank_of(i)

    king_moved = pos.white_king_moved if color == WHITE else pos.black_king_moved

    if king_moved:
        return

    rook_a_moved = pos.white_rook_a_moved if color == WHITE else pos.black_rook_a_moved
    rook_j_moved = pos.white_rook_j_moved if color == WHITE else pos.black_rook_j_moved

    f = file_of(i)

    # Kingside: king moves from e→g (file 4→6), rook j→f
    if not rook_j_moved:
        clear = all(pos.board[sq(ff, rank)] is None for ff in range(f + 1, 9))
        rook_sq_j = sq(9, rank)
        if pos.board[rook_sq_j] and pos.board[rook_sq_j].kind == ROOK and clear:
            # squares king passes through must not be attacked
            path_ok = all(
                not _square_attacked(pos, sq(ff, rank), opp(color))
                for ff in range(f, f + 3)
            )
            if path_ok:
                moves.append(Move(i, sq(f + 2, rank), special=SPECIAL_CASTLE))

    # Queenside: king moves from e→c (file 4→2), rook a→d
    if not rook_a_moved:
        clear = all(pos.board[sq(ff, rank)] is None for ff in range(1, f))
        rook_sq_a = sq(0, rank)
        if pos.board[rook_sq_a] and pos.board[rook_sq_a].kind == ROOK and clear:
            path_ok = all(
                not _square_attacked(pos, sq(ff, rank), opp(color))
                for ff in range(f - 2, f + 1)
            )
            if path_ok:
                moves.append(Move(i, sq(f - 2, rank), special=SPECIAL_CASTLE))


def _gen_queen(pos: Position, i: int, moves: List[Move]) -> None:
    _add_slide(pos, i, moves, [
        (1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)
    ])


def _gen_rook(pos: Position, i: int, moves: List[Move]) -> None:
    _add_slide(pos, i, moves, [(1,0),(-1,0),(0,1),(0,-1)])


def _gen_bishop(pos: Position, i: int, moves: List[Move]) -> None:
    _add_slide(pos, i, moves, [(1,1),(1,-1),(-1,1),(-1,-1)])


def _gen_knight(pos: Position, i: int, moves: List[Move]) -> None:
    f, r = file_of(i), rank_of(i)
    for df, dr in [(1,2),(2,1),(-1,2),(-2,1),(1,-2),(2,-1),(-1,-2),(-2,-1)]:
        _add_step(pos, i, f+df, r+dr, moves)


def _gen_princess(pos: Position, i: int, moves: List[Move]) -> None:
    """
    Princess: unlimited along the rank (left and right) + unlimited forward
    along file and forward diagonals. Cannot move backward.
    """
    pc = pos.board[i]
    fwd = _forward(pc.color)
    # Lateral: full rank left and right
    _add_slide(pos, i, moves, [(-1, 0), (1, 0)])
    # Forward file
    _add_slide(pos, i, moves, [(0, fwd)])
    # Forward diagonals
    _add_slide(pos, i, moves, [(-1, fwd), (1, fwd)])


def _gen_prince(pos: Position, i: int, moves: List[Move]) -> None:
    """
    Prince: one square forward (file), one square forward-diagonal (2 dirs),
    or one square sideways (left/right). No backward movement.
    """
    pc = pos.board[i]
    fwd = _forward(pc.color)
    f, r = file_of(i), rank_of(i)
    # Forward along file
    _add_step(pos, i, f, r + fwd, moves)
    # Forward diagonals
    _add_step(pos, i, f - 1, r + fwd, moves)
    _add_step(pos, i, f + 1, r + fwd, moves)
    # Sideways
    _add_step(pos, i, f - 1, r, moves)
    _add_step(pos, i, f + 1, r, moves)


def _gen_duke(pos: Position, i: int, moves: List[Move]) -> None:
    """
    Duke: one or two squares in any direction; cannot jump over pieces.
    """
    pc = pos.board[i]
    f, r = file_of(i), rank_of(i)
    dirs = [(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]

    for df, dr in dirs:
        # One step
        nf, nr = f + df, r + dr
        if not on_board(nf, nr):
            continue
        dst1 = sq(nf, nr)
        pc1 = pos.board[dst1]
        if pc1 is None:
            moves.append(Move(i, dst1))
            # Two steps (only if first square clear)
            nf2, nr2 = nf + df, nr + dr
            if on_board(nf2, nr2):
                dst2 = sq(nf2, nr2)
                pc2 = pos.board[dst2]
                if pc2 is None:
                    moves.append(Move(i, dst2))
                elif pc2.color != pc.color:
                    moves.append(Move(i, dst2, pc2))
        elif pc1.color != pc.color:
            moves.append(Move(i, dst1, pc1))
            # blocked after capture: no two-step


def _gen_dragon(pos: Position, i: int, moves: List[Move]) -> None:
    """
    Dragon:
    - Move to any immediately diagonal square that is EMPTY (no capture diagonally)
    - Capture any piece immediately in front or behind (same file, 1 sq)
    - Capture any piece immediately left or right (same rank, 1 sq)
    """
    pc = pos.board[i]
    f, r = file_of(i), rank_of(i)

    # Diagonal movement (to empty only)
    for df, dr in [(1,1),(1,-1),(-1,1),(-1,-1)]:
        nf, nr = f + df, r + dr
        if on_board(nf, nr) and pos.board[sq(nf, nr)] is None:
            moves.append(Move(i, sq(nf, nr)))

    # Orthogonal capture (adjacent file-direction and rank-direction)
    for df, dr in [(0,1),(0,-1),(-1,0),(1,0)]:
        nf, nr = f + df, r + dr
        if on_board(nf, nr):
            dst = sq(nf, nr)
            target = pos.board[dst]
            if target and target.color != pc.color:
                moves.append(Move(i, dst, target))


def _gen_subject(pos: Position, i: int, moves: List[Move]) -> None:
    """
    Subject:
    - Move forward diagonally to empty square (1 or 2 squares on first move)
    - Capture straight forward (same file, 1 sq ahead)
    En passant subject-to-subject also handled here.
    """
    pc = pos.board[i]
    fwd = _forward(pc.color)
    f, r = file_of(i), rank_of(i)
    first_move = i not in pos.pieces_moved

    # Diagonal forward movement (to empty)
    for df in (-1, 1):
        nf, nr = f + df, r + fwd
        if on_board(nf, nr):
            dst = sq(nf, nr)
            if pos.board[dst] is None:
                moves.append(Move(i, dst))
                # Double diagonal step on first move
                if first_move:
                    nf2, nr2 = nf + df, nr + fwd
                    if on_board(nf2, nr2) and pos.board[sq(nf2, nr2)] is None:
                        moves.append(Move(i, sq(nf2, nr2)))

    # Straight forward capture
    nf_cap, nr_cap = f, r + fwd
    if on_board(nf_cap, nr_cap):
        dst_cap = sq(nf_cap, nr_cap)
        target = pos.board[dst_cap]
        if target and target.color != pc.color:
            moves.append(Move(i, dst_cap, target))

    # En passant: subject captures opponent subject
    if pos.ep_subj_sq is not None:
        ep_s = pos.ep_subj_sq
        ep_f, ep_r = file_of(ep_s), rank_of(ep_s)
        # Opponent subject is on same rank, adjacent file; we capture to the
        # diagonal-forward square of our subject that is "behind" ep subject
        if ep_r == r and abs(ep_f - f) == 1:
            # The capture landing square is diagonally forward toward ep subject
            land_f = ep_f
            land_r = r + fwd
            if on_board(land_f, land_r) and pos.board[sq(land_f, land_r)] is None:
                moves.append(Move(i, sq(land_f, land_r),
                                  pos.board[ep_s],
                                  special=SPECIAL_EP_SUBJECT,
                                  ep_sq=ep_s))


def _gen_pawn(pos: Position, i: int, moves: List[Move]) -> None:
    """
    Pawn:
    - Move forward 1 square (to empty)
    - Move forward 2 squares on first move (both empty)
    - Capture diagonally forward
    - En passant
    - Promotion on reaching last rank
    """
    pc = pos.board[i]
    fwd = _forward(pc.color)
    f, r = file_of(i), rank_of(i)
    first_move = i not in pos.pieces_moved
    promo_rank = 9 if pc.color == WHITE else 0

    def add_pawn_move(dst: int, cap: Optional[Piece] = None,
                      special: Optional[str] = None,
                      ep_sq: Optional[int] = None) -> None:
        if rank_of(dst) == promo_rank:
            # Generate promotion choices (not pawn, not subject, not king)
            for kind in [QUEEN, ROOK, BISHOP, KNIGHT, PRINCESS, PRINCE,
                         DUKE, DRAGON, WIZARD]:
                moves.append(Move(i, dst, cap, SPECIAL_PROMO_PAWN,
                                  promo_to=kind, ep_sq=ep_sq))
        else:
            moves.append(Move(i, dst, cap, special, ep_sq=ep_sq))

    # Forward 1
    nr = r + fwd
    if on_board(f, nr):
        dst1 = sq(f, nr)
        if pos.board[dst1] is None:
            add_pawn_move(dst1)
            # Forward 2 on first move
            if first_move:
                nr2 = nr + fwd
                if on_board(f, nr2):
                    dst2 = sq(f, nr2)
                    if pos.board[dst2] is None:
                        moves.append(Move(i, dst2))  # double step (no promo from here)

    # Diagonal captures
    for df in (-1, 1):
        nf, nr_d = f + df, r + fwd
        if on_board(nf, nr_d):
            dst = sq(nf, nr_d)
            target = pos.board[dst]
            if target and target.color != pc.color:
                add_pawn_move(dst, target)

    # En passant pawn-to-pawn
    if pos.ep_pawn_sq is not None:
        ep_p = pos.ep_pawn_sq
        ep_f, ep_r = file_of(ep_p), rank_of(ep_p)
        if ep_r == r and abs(ep_f - f) == 1:
            land = sq(ep_f, r + fwd)
            if on_board(ep_f, r + fwd) and pos.board[land] is None:
                moves.append(Move(i, land,
                                  pos.board[ep_p],
                                  special=SPECIAL_EP_PAWN,
                                  ep_sq=ep_p))

    # Subject promotion (when subject reaches last rank it becomes pawn, handled separately)


def _gen_subject_promotion(pos: Position, i: int, moves: List[Move]) -> None:
    """Subject reaching last rank promotes to pawn."""
    pc = pos.board[i]
    fwd = _forward(pc.color)
    f, r = file_of(i), rank_of(i)
    promo_rank = 9 if pc.color == WHITE else 0
    first_move = i not in pos.pieces_moved

    # diagonal forward to empty
    for df in (-1, 1):
        nf, nr = f + df, r + fwd
        if on_board(nf, nr):
            dst = sq(nf, nr)
            if pos.board[dst] is None:
                if nr == promo_rank:
                    moves.append(Move(i, dst, None, SPECIAL_PROMO_SUBJ))
                else:
                    moves.append(Move(i, dst))
                if first_move:
                    nf2, nr2 = nf + df, nr + fwd
                    if on_board(nf2, nr2) and pos.board[sq(nf2, nr2)] is None:
                        if nr2 == promo_rank:
                            moves.append(Move(i, sq(nf2, nr2), None, SPECIAL_PROMO_SUBJ))
                        else:
                            moves.append(Move(i, sq(nf2, nr2)))

    # straight forward capture
    nf_c, nr_c = f, r + fwd
    if on_board(nf_c, nr_c):
        dst_c = sq(nf_c, nr_c)
        target = pos.board[dst_c]
        if target and target.color != pc.color:
            if nr_c == promo_rank:
                moves.append(Move(i, dst_c, target, SPECIAL_PROMO_SUBJ))
            else:
                moves.append(Move(i, dst_c, target))


def _gen_wizard(pos: Position, i: int, moves: List[Move]) -> None:
    """
    Wizard:
    - Opponent dragon alive: teleport to any empty square (no capture).
    - Opponent dragon dead: capture only subjects or pawns on ranks 4-7
      (0-indexed: ranks 3,4,5,6 = rank indices for ranks 4,5,6,7).
    Wizard cannot capture opponent wizard, royalty, nobility, knights, clergy.
    """
    pc = pos.board[i]
    enemy_dragon_up = pos.enemy_dragon_alive(pc.color)

    # Battlefield ranks: 4,5,6,7 (1-based) -> indices 3,4,5,6
    BATTLEFIELD = {3, 4, 5, 6}

    if enemy_dragon_up:
        # Teleport to any empty square
        for idx in range(NUM_SQUARES):
            if idx != i and pos.board[idx] is None:
                moves.append(Move(i, idx, special=SPECIAL_TELEPORT))
    else:
        # Capture subjects or pawns in the battlefield
        for idx, target in enumerate(pos.board):
            if (target and target.color != pc.color
                    and target.kind in (SUBJECT, PAWN)
                    and rank_of(idx) in BATTLEFIELD):
                moves.append(Move(i, idx, target, special=SPECIAL_WIZ_CAP))


# ---------------------------------------------------------------------------
# Legal move generation
# ---------------------------------------------------------------------------

def generate_pseudo_moves(pos: Position) -> List[Move]:
    color = pos.turn
    moves: List[Move] = []

    for i, pc in enumerate(pos.board):
        if pc is None or pc.color != color:
            continue
        if pc.kind == KING:
            _gen_king(pos, i, moves)
        elif pc.kind == QUEEN:
            _gen_queen(pos, i, moves)
        elif pc.kind == ROOK:
            _gen_rook(pos, i, moves)
        elif pc.kind == BISHOP:
            _gen_bishop(pos, i, moves)
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
            _gen_subject_promotion(pos, i, moves)
        elif pc.kind == WIZARD:
            _gen_wizard(pos, i, moves)

    return moves


def generate_moves(pos: Position) -> List[Move]:
    """Return only fully legal moves."""
    color = pos.turn
    legal = []
    for m in generate_pseudo_moves(pos):
        np = pos.make_move(m)
        # Only filter for check if king can be checked
        if np.king_can_be_checked(color):
            if _king_in_check(np, color):
                continue
        legal.append(m)
    return legal


# ---------------------------------------------------------------------------
# Attack / check detection
# ---------------------------------------------------------------------------

def _square_attacked(pos: Position, target_sq: int, by_color: int) -> bool:
    """Is target_sq attacked by any piece of by_color?"""
    for i, pc in enumerate(pos.board):
        if pc is None or pc.color != by_color:
            continue
        if _piece_attacks_square(pos, i, target_sq):
            return True
    return False


def _piece_attacks_square(pos: Position, src: int, target: int) -> bool:
    pc = pos.board[src]
    if pc is None:
        return False
    f, r = file_of(src), rank_of(src)
    tf, tr = file_of(target), rank_of(target)
    df, dr = tf - f, tr - r

    kind = pc.kind

    if kind == KING:
        return max(abs(df), abs(dr)) == 1

    if kind == KNIGHT:
        return sorted([abs(df), abs(dr)]) == [1, 2]

    if kind == QUEEN:
        return _ray_attacks(pos, src, target)

    if kind == ROOK:
        if df != 0 and dr != 0:
            return False
        return _ray_attacks(pos, src, target)

    if kind == BISHOP:
        if abs(df) != abs(dr):
            return False
        return _ray_attacks(pos, src, target)

    if kind == PAWN:
        fwd = _forward(pc.color)
        return dr == fwd and abs(df) == 1

    if kind == PRINCESS:
        # Rank movement (left/right) or forward along file/diag
        fwd = _forward(pc.color)
        if dr == 0:  # lateral
            return _ray_attacks(pos, src, target)
        if df == 0 and dr * fwd > 0:  # forward file
            return _ray_attacks(pos, src, target)
        if abs(df) == abs(dr) and dr * fwd > 0:  # forward diag
            return _ray_attacks(pos, src, target)
        return False

    if kind == PRINCE:
        fwd = _forward(pc.color)
        # one step forward, forward-diag, or sideways
        if abs(df) <= 1 and abs(dr) <= 1:
            if dr == fwd:  # forward or forward-diag
                return True
            if dr == 0 and abs(df) == 1:  # sideways
                return True
        return False

    if kind == DUKE:
        # 1 or 2 steps any direction, no jump
        if max(abs(df), abs(dr)) > 2:
            return False
        if abs(df) > 0 and abs(dr) > 0 and abs(df) != abs(dr):
            return False
        step_f = (1 if df > 0 else -1) if df != 0 else 0
        step_r = (1 if dr > 0 else -1) if dr != 0 else 0
        mid = sq(f + step_f, r + step_r)
        if abs(df) == 2 or abs(dr) == 2:
            return pos.board[mid] is None
        return True

    if kind == DRAGON:
        # Attacks orthogonally adjacent (capture squares)
        if abs(df) + abs(dr) == 1:
            return True
        # Attacks diagonally adjacent (movement squares, but does attack them)
        if abs(df) == 1 and abs(dr) == 1:
            return True
        return False

    if kind == SUBJECT:
        # Captures straight forward
        fwd = _forward(pc.color)
        return df == 0 and dr == fwd

    if kind == WIZARD:
        # Wizard cannot check the king (only captures S/P in battlefield)
        return False

    return False


def _ray_attacks(pos: Position, src: int, target: int) -> bool:
    """Check if src attacks target along a clear ray."""
    sf, sr = file_of(src), rank_of(src)
    tf, tr = file_of(target), rank_of(target)
    df = tf - sf
    dr = tr - sr

    # Determine unit step
    if df != 0 and dr != 0 and abs(df) != abs(dr):
        return False
    step_f = (1 if df > 0 else -1) if df != 0 else 0
    step_r = (1 if dr > 0 else -1) if dr != 0 else 0

    f, r = sf + step_f, sr + step_r
    while on_board(f, r):
        s = sq(f, r)
        if s == target:
            return True
        if pos.board[s] is not None:
            return False
        f += step_f
        r += step_r
    return False


def _king_in_check(pos: Position, color: int) -> bool:
    """Is the king of `color` in check? (Only meaningful when king can be checked.)"""
    ksq = pos.king_sq(color)
    if ksq is None:
        return True
    return _square_attacked(pos, ksq, opp(color))


# ---------------------------------------------------------------------------
# Starting position
# ---------------------------------------------------------------------------

def create_start_position() -> Position:
    """
    Official Kingdom Chess starting position on 10x10 board.
    White rank 1: R N B PS K Q PR B N R
                  a b  c  d e f  g h i j
    White rank 2: W  (f2) and D (e2)
    White rank 3: nine Subjects (a3-j3 except f3 which has DR)
    Actually per rules:
      Rank 1: a1-R, b1-N, c1-B, d1-PS, e1-K, f1-Q, g1-PR, h1-B, i1-N, j1-R
      Rank 2: a2-P, b2-P, c2-P, d2-P, e2-D, f2-W, g2-P, h2-P, i2-P, j2-P
      Rank 3: a3-S, b3-S, c3-S, d3-S, e3-S, f3-DR, g3-S, h3-S, i3-S, j3-S
    Black mirrors on ranks 10, 9, 8.
    """
    pos = Position.empty_board()

    # White rank 1
    for file_letter, kind in [
        ("a", ROOK), ("b", KNIGHT), ("c", BISHOP), ("d", PRINCESS),
        ("e", KING), ("f", QUEEN), ("g", PRINCE), ("h", BISHOP),
        ("i", KNIGHT), ("j", ROOK)
    ]:
        pos.place(fr_sq(f"{file_letter}1"), Piece(WHITE, kind))

    # White rank 2: pawns except e2=Duke, f2=Wizard
    for file_letter in "abcdhij":
        pos.place(fr_sq(f"{file_letter}2"), Piece(WHITE, PAWN))
    pos.place(fr_sq("e2"), Piece(WHITE, DUKE))
    pos.place(fr_sq("f2"), Piece(WHITE, WIZARD))
    pos.place(fr_sq("g2"), Piece(WHITE, PAWN))

    # White rank 3: subjects except f3=Dragon
    for file_letter in "abcdeghij":
        pos.place(fr_sq(f"{file_letter}3"), Piece(WHITE, SUBJECT))
    pos.place(fr_sq("f3"), Piece(WHITE, DRAGON))

    # Black rank 10
    for file_letter, kind in [
        ("a", ROOK), ("b", KNIGHT), ("c", BISHOP), ("d", PRINCESS),
        ("e", KING), ("f", QUEEN), ("g", PRINCE), ("h", BISHOP),
        ("i", KNIGHT), ("j", ROOK)
    ]:
        pos.place(fr_sq(f"{file_letter}10"), Piece(BLACK, kind))

    # Black rank 9: pawns except e9=Duke, f9=Wizard
    for file_letter in "abcdhij":
        pos.place(fr_sq(f"{file_letter}9"), Piece(BLACK, PAWN))
    pos.place(fr_sq("e9"), Piece(BLACK, DUKE))
    pos.place(fr_sq("f9"), Piece(BLACK, WIZARD))
    pos.place(fr_sq("g9"), Piece(BLACK, PAWN))

    # Black rank 8: subjects except f8=Dragon
    for file_letter in "abcdeghij":
        pos.place(fr_sq(f"{file_letter}8"), Piece(BLACK, SUBJECT))
    pos.place(fr_sq("f8"), Piece(BLACK, DRAGON))

    return pos


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

PIECE_VALUES = {
    QUEEN:    900,
    ROOK:     500,
    BISHOP:   330,
    KNIGHT:   310,
    PRINCESS: 680,
    PRINCE:   240,
    DUKE:     700,   # high value: losing it triggers king vulnerability
    DRAGON:   290,
    SUBJECT:  85,
    PAWN:     100,
    WIZARD:   360,
    KING:     0,
}

BATTLEFIELD = {3, 4, 5, 6}   # rank indices for ranks 4-7 (0-based)


def evaluate(pos: Position) -> int:
    """Positive = good for side to move."""
    score = 0
    stm = pos.turn

    for pc in pos.board:
        if pc is None:
            continue
        v = PIECE_VALUES.get(pc.kind, 0)
        score += v if pc.color == stm else -v

    # Duke bonus/penalty: losing duke is catastrophic (king becomes vulnerable)
    for color in (WHITE, BLACK):
        if not pos.duke_alive(color):
            # Our duke captured: bad for us (king now vulnerable)
            penalty = -800
            score += penalty if color == stm else 800

    # Mobility (small weight)
    score += 2 * len(generate_moves(pos))

    # Wizard dynamic bonus
    for i, pc in enumerate(pos.board):
        if pc and pc.kind == WIZARD:
            if pos.enemy_dragon_alive(pc.color):
                delta = 25
            else:
                cnt = sum(
                    1 for j, t in enumerate(pos.board)
                    if t and t.color != pc.color
                    and t.kind in (SUBJECT, PAWN)
                    and rank_of(j) in BATTLEFIELD
                )
                delta = 12 * cnt
            score += delta if pc.color == stm else -delta

    return score


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

INF = 10 ** 9


def search_best_move(pos: Position, level: str,
                     time_limit_ms: int = None) -> Optional[Move]:
    level = level.lower()
    if level == "easy":
        return _search_easy(pos)
    elif level == "medium":
        return _search_medium(pos, time_limit_ms or 600)
    elif level == "hard":
        return _search_hard(pos, time_limit_ms or 3000)
    raise ValueError(f"Unknown difficulty: {level}")


def _search_easy(pos: Position) -> Optional[Move]:
    moves = generate_moves(pos)
    if not moves:
        return None
    scored = []
    for m in moves:
        np = pos.make_move(m)
        scored.append((evaluate(np), m))
    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:max(3, len(scored) // 3)]
    return random.choice(top)[1]


def _move_order_key(m: Move) -> int:
    score = 0
    if m.capture:
        score += 1000 + PIECE_VALUES.get(m.capture.kind, 0)
    if m.special in (SPECIAL_WIZ_CAP, SPECIAL_TELEPORT):
        score += 500
    if m.special == SPECIAL_PROMO_PAWN:
        score += 900
    return score


def _negamax(pos: Position, depth: int, alpha: int, beta: int,
             end_time: float) -> Tuple[int, Optional[Move]]:
    if time.time() > end_time:
        return 0, None

    if depth == 0:
        return _quiesce(pos, alpha, beta, end_time), None

    moves = generate_moves(pos)

    if not moves:
        # Check if king can be checked first
        if pos.king_can_be_checked(pos.turn) and _king_in_check(pos, pos.turn):
            return -50000 - depth, None  # checkmate
        return 0, None  # stalemate or no moves without check

    moves.sort(key=_move_order_key, reverse=True)

    best_score = -INF
    best_move = None

    for m in moves:
        if time.time() > end_time:
            break
        np = pos.make_move(m)
        score, _ = _negamax(np, depth - 1, -beta, -alpha, end_time)
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

    for m in generate_moves(pos):
        if time.time() > end_time:
            break
        if m.capture is None and m.special not in (SPECIAL_WIZ_CAP,):
            continue
        np = pos.make_move(m)
        score = -_quiesce(np, -beta, -alpha, end_time)
        if score >= beta:
            return beta
        if score > alpha:
            alpha = score

    return alpha


def _search_medium(pos: Position, time_limit_ms: int) -> Optional[Move]:
    end_time = time.time() + time_limit_ms / 1000.0
    best_move = None
    for depth in range(1, 7):
        if time.time() >= end_time:
            break
        _, move = _negamax(pos, depth, -INF, INF, end_time)
        if move is not None:
            best_move = move
    return best_move


def _search_hard(pos: Position, time_limit_ms: int) -> Optional[Move]:
    end_time = time.time() + time_limit_ms / 1000.0
    best_move = None
    guess = 0
    window = 60
    for depth in range(1, 10):
        if time.time() >= end_time:
            break
        alpha, beta = guess - window, guess + window
        score, move = _negamax(pos, depth, alpha, beta, end_time)
        if move is None:
            score, move = _negamax(pos, depth, -INF, INF, end_time)
        if move is not None:
            best_move = move
            guess = score
    return best_move


# ---------------------------------------------------------------------------
# UCI-style helpers
# ---------------------------------------------------------------------------

def move_from_uci(pos: Position, uci: str) -> Optional[Move]:
    """Parse 'e2e4' or 'e2e4Q' (promotion) into a Move."""
    if len(uci) < 4:
        return None
    try:
        src = fr_sq(uci[:2])
        # Destination may be 2 or 3 chars (e.g. 'j10')
        # Try to split: remaining is dest + optional promo letter
        rest = uci[2:]
        promo_kind = None
        # Check for trailing promotion letter
        if rest[-1].upper() in (QUEEN, ROOK, BISHOP, KNIGHT, PRINCESS[0],
                                 PRINCE[0], DUKE, DRAGON[0], WIZARD):
            promo_kind = rest[-1].upper()
            rest = rest[:-1]
        dst = fr_sq(rest)
    except (KeyError, ValueError):
        return None

    for m in generate_moves(pos):
        if m.src == src and m.dst == dst:
            if promo_kind:
                if m.promo_to == promo_kind:
                    return m
            else:
                if m.promo_to is None or m.special == SPECIAL_PROMO_SUBJ:
                    return m
    return None


def apply_uci(pos: Position, uci: str) -> Position:
    m = move_from_uci(pos, uci)
    if not m:
        raise ValueError(f"Illegal move: {uci}")
    return pos.make_move(m)


def best_move_uci(pos: Position, level: str = "medium",
                  time_limit_ms: int = None) -> Optional[str]:
    m = search_best_move(pos, level, time_limit_ms)
    return str(m) if m else None


# ---------------------------------------------------------------------------
# Board display
# ---------------------------------------------------------------------------

PIECE_DISPLAY = {
    (WHITE, KING):     "K ",
    (WHITE, QUEEN):    "Q ",
    (WHITE, ROOK):     "R ",
    (WHITE, BISHOP):   "B ",
    (WHITE, KNIGHT):   "N ",
    (WHITE, PAWN):     "P ",
    (WHITE, PRINCESS): "PS",
    (WHITE, PRINCE):   "PR",
    (WHITE, DUKE):     "D ",
    (WHITE, DRAGON):   "DR",
    (WHITE, SUBJECT):  "S ",
    (WHITE, WIZARD):   "W ",
    (BLACK, KING):     "k ",
    (BLACK, QUEEN):    "q ",
    (BLACK, ROOK):     "r ",
    (BLACK, BISHOP):   "b ",
    (BLACK, KNIGHT):   "n ",
    (BLACK, PAWN):     "p ",
    (BLACK, PRINCESS): "ps",
    (BLACK, PRINCE):   "pr",
    (BLACK, DUKE):     "d ",
    (BLACK, DRAGON):   "dr",
    (BLACK, SUBJECT):  "s ",
    (BLACK, WIZARD):   "w ",
}


def print_board(pos: Position) -> None:
    print()
    print("   " + "  ".join(FILES))
    print("   " + "--" * 10 + "-" * 9)
    for r in range(9, -1, -1):
        rank_label = str(r + 1).rjust(2)
        row = []
        for f in range(10):
            pc = pos.board[sq(f, r)]
            if pc is None:
                row.append(". ")
            else:
                row.append(PIECE_DISPLAY.get((pc.color, pc.kind), "??"))
        print(f"{rank_label} | " + " ".join(row))
    print()
    # Status
    wd = "alive" if pos.duke_alive(WHITE) else "CAPTURED"
    bd = "alive" if pos.duke_alive(BLACK) else "CAPTURED"
    wdr = "alive" if pos.dragon_alive(WHITE) else "captured"
    bdr = "alive" if pos.dragon_alive(BLACK) else "captured"
    print(f"   White Duke: {wd}  |  Black Duke: {bd}")
    print(f"   White Dragon: {wdr}  |  Black Dragon: {bdr}")
    if pos.king_can_be_checked(pos.turn):
        if _king_in_check(pos, pos.turn):
            print("   *** CHECK ***")
    print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    random.seed(42)
    pos = create_start_position()
    level = "medium"

    print("Kingdom Chess AI — 10x10 board")
    print("Commands: <move> (e.g. e2e3), 'ai', 'level easy|medium|hard', 'quit'")
    print("Promotion: append piece letter, e.g. e9e10Q")

    while True:
        print_board(pos)
        turn_str = "White" if pos.turn == WHITE else "Black"

        moves = generate_moves(pos)
        if not moves:
            if pos.king_can_be_checked(pos.turn) and _king_in_check(pos, pos.turn):
                print(f"Checkmate! {turn_str} loses.")
            else:
                print("Stalemate — draw.")
            break

        line = input(f"{turn_str} to move [{level}] > ").strip()

        if line == "quit":
            break

        if line.startswith("level"):
            parts = line.split()
            if len(parts) == 2:
                level = parts[1].lower()
                print(f"Level set to {level}")
            continue

        if line == "ai":
            bm = search_best_move(pos, level)
            if bm is None:
                print("No legal moves.")
                break
            print(f"AI plays: {bm}")
            pos = pos.make_move(bm)
            continue

        if line == "moves":
            print(f"{len(moves)} legal moves:")
            print("  " + "  ".join(str(m) for m in moves[:40]))
            continue

        try:
            pos = apply_uci(pos, line)
        except Exception as e:
            print(f"Error: {e}")

