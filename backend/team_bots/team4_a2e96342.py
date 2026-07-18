import random

EMPTY = "."


def _is_valid_move(board, r, c):
    return board[r][c] == EMPTY


def _calculate_scores(board, player, opponent):
    """Count total stones on board for each player."""
    my_score = sum(cell == player for row in board for cell in row)
    opp_score = sum(cell == opponent for row in board for cell in row)
    return my_score, opp_score


def _copy_board(board):
    return [row[:] for row in board]


def _center_distance(row, col, size):
    return abs(row - size // 2) + abs(col - size // 2)


def bot_move(game_state: dict) -> dict:
    board = game_state["board"]
    n = game_state["board_size"]

    me = (game_state.get("your_stone")
          or game_state.get("current_player")
          or game_state.get("player")
          or "W")
    opp = {'X': 'O', 'O': 'X', 'W': 'B', 'B': 'W'}.get(me, 'B')

    valid_moves = [
        (r, c)
        for r in range(n)
        for c in range(n)
        if _is_valid_move(board, r, c)
    ]
    if not valid_moves:
        return {"row": 0, "col": 0}

    best_score_diff = None
    best_moves = []

    for r, c in valid_moves:
        copy = _copy_board(board)
        copy[r][c] = me
        my_score, opp_score = _calculate_scores(copy, me, opp)
        diff = my_score - opp_score

        if best_score_diff is None or diff > best_score_diff:
            best_score_diff = diff
            best_moves = [(r, c)]
        elif diff == best_score_diff:
            best_moves.append((r, c))

    best_moves.sort(key=lambda rc: _center_distance(rc[0], rc[1], n))
    d0 = _center_distance(best_moves[0][0], best_moves[0][1], n)
    best_moves = [rc for rc in best_moves if _center_distance(rc[0], rc[1], n) == d0]

    chosen = random.choice(best_moves)
    return {"row": chosen[0], "col": chosen[1]}