"""
Compatibility module for team bots that import `pahtum_core`.

Provides:
- SIZE: default board size (7)
- is_valid_move(board, r, c): True if cell is empty and in bounds
- calculate_scores(board, player, opponent): returns (player_score, opponent_score)

This is a minimal implementation consistent with the Pah-Tum scoring rules:
- Only horizontal and vertical contiguous runs count.
- Runs of length 1–2: 0 points
- Run of 3: 3 points
- Run of L>3: score(L) = 2 * score(L-1) + L
"""

from typing import List, Tuple

SIZE = 7  # Default board size used by some team bots.


def _generate_scoring_table(n: int) -> dict[int, int]:
    scores = {1: 0, 2: 0, 3: 3}
    for L in range(4, n + 1):
        scores[L] = 2 * scores[L - 1] + L
    return scores


_SCORES_CACHE: dict[int, dict[int, int]] = {}


def _scores_for_n(n: int) -> dict[int, int]:
    cached = _SCORES_CACHE.get(n)
    if cached is None:
        cached = _generate_scoring_table(n)
        _SCORES_CACHE[n] = cached
    return cached


def is_valid_move(board: List[List[str]], r: int, c: int) -> bool:
    """A move is valid if it's on the board and the cell is empty ('.')."""
    n = len(board)
    return 0 <= r < n and 0 <= c < n and board[r][c] == "."


def _score_for_player(board: List[List[str]], stone: str) -> int:
    """Score all horizontal and vertical runs for the given stone."""
    total = 0
    n = len(board)
    scores_for_n = _scores_for_n(n)
    # Horizontal
    for r in range(n):
        run = 0
        for c in range(n):
            if board[r][c] == stone:
                run += 1
            else:
                if run > 0:
                    total += scores_for_n.get(run, 0)
                run = 0
        if run > 0:
            total += scores_for_n.get(run, 0)
    # Vertical
    for c in range(n):
        run = 0
        for r in range(n):
            if board[r][c] == stone:
                run += 1
            else:
                if run > 0:
                    total += scores_for_n.get(run, 0)
                run = 0
        if run > 0:
            total += scores_for_n.get(run, 0)
    return total


def calculate_scores(board: List[List[str]], player: str, opponent: str) -> Tuple[int, int]:
    """
    Return (player_score, opponent_score) for the given board.

    This is used by some team bots that work with symbols like 'X'/'O'.
    Any non-empty cells matching `player` or `opponent` are scored.
    """
    return _score_for_player(board, player), _score_for_player(board, opponent)

