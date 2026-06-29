"""
Pah-Tum Game Engine — pure logic, no console I/O.
Extracted from PahTum.ipynb, preserving all original rules and scoring.
"""

EMPTY = '.'
WHITE = 'W'
BLACK = 'B'


def make_board(n: int) -> list[list[str]]:
    return [[EMPTY for _ in range(n)] for _ in range(n)]


def board_size(board: list[list[str]]) -> int:
    return len(board)


def in_bounds(board: list[list[str]], r: int, c: int) -> bool:
    n = board_size(board)
    return 0 <= r < n and 0 <= c < n


def generate_scoring_table(n: int) -> dict[int, int]:
    """
    Scoring table for runs of length 1..n:
    - Runs of length 1-2: 0 points
    - Run of 3: 3 points
    - Run of L (L > 3): 2 * score(L-1) + L
    """
    scores = {1: 0, 2: 0, 3: 3}
    for L in range(4, n + 1):
        scores[L] = 2 * scores[L - 1] + L
    return scores


def score_line(scores_for_n: dict[int, int], run_len: int) -> int:
    return scores_for_n.get(run_len, 0)


def score_board(board: list[list[str]], player: str, scores_for_n: dict[int, int]) -> int:
    """Sum scores of all horizontal and vertical contiguous runs of 'player'."""
    n = board_size(board)
    total = 0
    # Horizontal
    for r in range(n):
        run = 0
        for c in range(n):
            if board[r][c] == player:
                run += 1
            else:
                if run > 0:
                    total += score_line(scores_for_n, run)
                run = 0
        if run > 0:
            total += score_line(scores_for_n, run)
    # Vertical
    for c in range(n):
        run = 0
        for r in range(n):
            if board[r][c] == player:
                run += 1
            else:
                if run > 0:
                    total += score_line(scores_for_n, run)
                run = 0
        if run > 0:
            total += score_line(scores_for_n, run)
    return total


def all_empty_cells(board: list[list[str]]):
    n = board_size(board)
    for r in range(n):
        for c in range(n):
            if board[r][c] == EMPTY:
                yield (r, c)


def game_over(board: list[list[str]]) -> bool:
    n = board_size(board)
    return all(board[r][c] != EMPTY for r in range(n) for c in range(n))


def is_legal(board: list[list[str]], r: int, c: int) -> bool:
    return in_bounds(board, r, c) and board[r][c] == EMPTY


def apply_move(board: list[list[str]], r: int, c: int, player: str):
    board[r][c] = player


def copy_board(board: list[list[str]]) -> list[list[str]]:
    return [row[:] for row in board]


def immediate_gain(board, r, c, player, scores_for_n):
    """Evaluate move by placing a stone and measuring player's score increase."""
    before = score_board(board, player, scores_for_n)
    tmp = copy_board(board)
    tmp[r][c] = player
    after = score_board(tmp, player, scores_for_n)
    return after - before


def center_weight(board, r, c):
    n = board_size(board)
    center = (n - 1) / 2.0
    return -abs(r - center) - abs(c - center)


def best_ai_move(board, player, opponent, scores_for_n):
    """Greedy 1-ply: maximize immediate score gain; tiebreak by centrality.
       Lightly penalize giving opponent a big immediate reply."""
    best = None
    best_val = -10**9

    for (r, c) in all_empty_cells(board):
        gain = immediate_gain(board, r, c, player, scores_for_n)

        # Light lookahead: opponent's best immediate reply
        tmp = copy_board(board)
        tmp[r][c] = player
        opp_best = 0
        for (rr, cc) in all_empty_cells(tmp):
            opp_gain = immediate_gain(tmp, rr, cc, opponent, scores_for_n)
            if opp_gain > opp_best:
                opp_best = opp_gain

        value = gain - 0.3 * opp_best + 0.05 * center_weight(board, r, c)

        if value > best_val:
            best_val = value
            best = (r, c)

    return best


# ---------------------------------------------------------------------------
# High-level Game class for the API
# ---------------------------------------------------------------------------

class PahTumGame:
    """Stateful game session wrapping the pure functions above."""

    def __init__(self, board_size_n: int = 7, mode: str = "pvp",
                 player_white: str = "Player 1", player_black: str = "Player 2"):
        if board_size_n < 3 or board_size_n > 25:
            raise ValueError("Board size must be between 3 and 25")
        self.n = board_size_n
        self.board = make_board(board_size_n)
        self.scores_for_n = generate_scoring_table(board_size_n)
        self.mode = mode  # "pvp" or "vs_ai"
        self.player_white = player_white
        self.player_black = player_black
        self.turn = 0
        self.moves: list[dict] = []
        self.is_finished = False
        self.winner = None

    @property
    def current_player(self) -> str:
        return WHITE if self.turn % 2 == 0 else BLACK

    @property
    def current_player_name(self) -> str:
        return self.player_white if self.current_player == WHITE else self.player_black

    def make_move(self, row: int, col: int) -> dict:
        """Place a stone at (row, col). Returns move result dict."""
        if self.is_finished:
            return {"error": "Game is already over"}

        if not is_legal(self.board, row, col):
            return {"error": "Invalid move — cell is occupied or out of bounds"}

        player = self.current_player
        apply_move(self.board, row, col, player)
        self.moves.append({"row": row, "col": col, "player": player})
        self.turn += 1

        finished = game_over(self.board)
        if finished:
            self.is_finished = True
            w = score_board(self.board, WHITE, self.scores_for_n)
            b = score_board(self.board, BLACK, self.scores_for_n)
            if w > b:
                self.winner = "white"
            elif b > w:
                self.winner = "black"
            else:
                self.winner = "draw"

        return {
            "success": True,
            "move": {"row": row, "col": col, "player": player},
            "is_finished": self.is_finished,
            "winner": self.winner,
        }

    def get_ai_move(self) -> dict:
        """Compute and apply AI move. Returns move result dict."""
        if self.is_finished:
            return {"error": "Game is already over"}

        player = self.current_player
        opponent = BLACK if player == WHITE else WHITE
        move = best_ai_move(self.board, player, opponent, self.scores_for_n)

        if move is None:
            return {"error": "No valid moves available"}

        r, c = move
        return self.make_move(r, c)

    def get_state(self) -> dict:
        """Return the full game state as a serializable dict."""
        w_score = score_board(self.board, WHITE, self.scores_for_n)
        b_score = score_board(self.board, BLACK, self.scores_for_n)
        return {
            "board": [row[:] for row in self.board],
            "board_size": self.n,
            "scores_for_n": self.scores_for_n,
            "current_player": self.current_player,
            "current_player_name": self.current_player_name,
            "turn": self.turn,
            "mode": self.mode,
            "player_white": self.player_white,
            "player_black": self.player_black,
            "white_score": w_score,
            "black_score": b_score,
            "is_finished": self.is_finished,
            "winner": self.winner,
            "moves": self.moves,
            "total_cells": self.n * self.n,
            "cells_filled": self.turn,
        }
