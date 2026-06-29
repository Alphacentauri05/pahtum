import math
import time
import random

TEAM_NAME = "AlphaZero_PahTum"
TIME_LIMIT = 0.92  # Safety margin for 1.0s limit

# Transposition Table to store evaluated positions
transposition_table = {}


def _get_board_hash(board):
    """Simple hash for fast state lookup."""
    return hash(tuple(tuple(row) for row in board))


def _generate_scoring_table(n: int) -> dict[int, int]:
    scores = {1: 0, 2: 0, 3: 3}
    for L in range(4, n + 1):
        scores[L] = 2 * scores[L - 1] + L
    return scores


def _score_for_player(board, stone: str, scores_for_n: dict[int, int]) -> int:
    """Score all horizontal and vertical runs for the given stone."""
    n = len(board)
    total = 0

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


def _calculate_scores(board, me: str, opponent: str) -> tuple[int, int]:
    """Pah-Tum style scoring using the current board size."""
    n = len(board)
    scores_for_n = _generate_scoring_table(n)
    return (
        _score_for_player(board, me, scores_for_n),
        _score_for_player(board, opponent, scores_for_n),
    )


def _evaluate_strategic(board, me, opponent):
    """
    Advanced Evaluation:
    - Base: score(me) - score(opponent)
    - Positional bonus: pieces closer to center are better.
    """
    my_score, opp_score = _calculate_scores(board, me, opponent)
    score = (my_score - opp_score) * 100

    n = len(board)
    center = n // 2
    for r in range(n):
        for c in range(n):
            if board[r][c] == me:
                dist = abs(r - center) + abs(c - center)
                score += (6 - dist) * 2
            elif board[r][c] == opponent:
                dist = abs(r - center) + abs(c - center)
                score -= (6 - dist) * 2
    return score


def _is_valid_move(board, r, c) -> bool:
    """Legal if on board and currently empty ('.')."""
    n = len(board)
    return 0 <= r < n and 0 <= c < n and board[r][c] == "."


def _minimax(board, depth, maximizing, me, opponent, alpha, beta, start_time):
    if time.time() - start_time > TIME_LIMIT:
        raise TimeoutError

    state_hash = _get_board_hash(board)
    if state_hash in transposition_table:
        entry = transposition_table[state_hash]
        if entry["depth"] >= depth:
            return entry["val"], None

    n = len(board)
    valid_moves = [
        (r, c)
        for r in range(n)
        for c in range(n)
        if _is_valid_move(board, r, c)
    ]

    if depth == 0 or not valid_moves:
        return _evaluate_strategic(board, me, opponent), None

    # Move ordering: prioritize center moves (Manhattan distance)
    center = n // 2
    valid_moves.sort(key=lambda rc: abs(rc[0] - center) + abs(rc[1] - center))

    best_move = None
    if maximizing:
        best_val = -math.inf
        for r, c in valid_moves:
            original = board[r][c]
            board[r][c] = me
            val, _ = _minimax(
                board, depth - 1, False, me, opponent, alpha, beta, start_time
            )
            board[r][c] = original  # UNDO: restore the original value
            if val > best_val:
                best_val, best_move = val, (r, c)
            alpha = max(alpha, val)
            if beta <= alpha:
                break
    else:
        best_val = math.inf
        for r, c in valid_moves:
            original = board[r][c]
            board[r][c] = opponent
            val, _ = _minimax(
                board, depth - 1, True, me, opponent, alpha, beta, start_time
            )
            board[r][c] = original  # UNDO: restore the original value
            if val < best_val:
                best_val, best_move = val, (r, c)
            beta = min(beta, val)
            if beta <= alpha:
                break

    transposition_table[state_hash] = {"val": best_val, "depth": depth}
    return best_val, best_move


def _choose_move(board, player, opponent):
    """Iterative deepening driver, returns (row, col)."""
    global transposition_table
    transposition_table = {}  # Refresh table each turn

    start_time = time.time()
    best_overall_move = None
    depth = 1

    try:
        while True:
            _, move = _minimax(
                board,
                depth,
                True,
                player,
                opponent,
                -math.inf,
                math.inf,
                start_time,
            )
            if move:
                best_overall_move = move
            depth += 1
    except TimeoutError:
    # Stop when time is up
        pass

    # Fallback to ensure a legal move is always returned
    if not best_overall_move:
        n = len(board)
        for r in range(n):
            for c in range(n):
                if _is_valid_move(board, r, c):
                    return r, c

    return best_overall_move


def bot_move(game_state: dict) -> dict:
    """
    Tournament entrypoint, same shape as team_example1.bot_move.

    Expects game_state to contain:
    - "board": 2D list with '.' for empty
    - "board_size": int
    - "your_stone" / "opponent_stone" or "current_player"
    """
    raw_board = game_state["board"]
    board = [row[:] for row in raw_board]  # work on a copy

    # Determine our stone
    player = (
        game_state.get("your_stone")
        or game_state.get("current_player")
        or "X"
    )
    opponent = game_state.get("opponent_stone")
    if not opponent:
        opponent = "O" if player == "X" else "X"

    row, col = _choose_move(board, player, opponent)
    return {"row": row, "col": col}