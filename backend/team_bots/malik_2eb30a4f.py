import random
from pahtum_core import get_valid_moves

def bot_move(game_state):
    moves = get_valid_moves(game_state)

    if not moves:
        return {"row": -1, "col": -1}

    row, col = random.choice(moves)

    return {
        "row": row,
        "col": col
    }