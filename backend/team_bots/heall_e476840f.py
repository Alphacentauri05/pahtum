import random


def bot_move(game_state):
    """
    Random bot for Pah-Tum.
    Chooses any valid empty cell.
    """

    board = game_state["board"]

    valid_moves = []

    n = len(board)

    for r in range(n):
        for c in range(n):
            if board[r][c] == ".":
                valid_moves.append((r, c))

    if not valid_moves:
        return {
            "row": 0,
            "col": 0
        }

    row, col = random.choice(valid_moves)

    return {
        "row": row,
        "col": col
    }