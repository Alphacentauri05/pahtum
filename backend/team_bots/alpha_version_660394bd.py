"""
Combined Pah Tum Bot Entry - Player 1
Includes core logic, smart playing heuristic, and move wrapper.
"""

import random

# ==========================================
# PAHTUM CORE LOGIC
# ==========================================

SIZE = 7
SEQUENCE_POINTS = (3, 10, 25, 56, 119)

def score_board(board, p1, p2):
    size = len(board)
    count_p1 = [0] * size
    count_p2 = [0] * size

    # Horizontal
    for i in range(size):
        run_p1 = run_p2 = 0
        for j in range(size):
            cell = board[i][j]
            if cell == p1:
                run_p1 += 1; run_p2 = 0
            elif cell == p2:
                run_p2 += 1; run_p1 = 0
            else:
                run_p1 = run_p2 = 0
            if run_p1 >= 3:
                count_p1[run_p1 - 3] += 1
            if run_p2 >= 3:
                count_p2[run_p2 - 3] += 1

    # Vertical
    for j in range(size):
        run_p1 = run_p2 = 0
        for i in range(size):
            cell = board[i][j]
            if cell == p1:
                run_p1 += 1; run_p2 = 0
            elif cell == p2:
                run_p2 += 1; run_p1 = 0
            else:
                run_p1 = run_p2 = 0
            if run_p1 >= 3:
                count_p1[run_p1 - 3] += 1
            if run_p2 >= 3:
                count_p2[run_p2 - 3] += 1

    return count_p1, count_p2

def calculate_scores(board, player1, player2):
    count_p1, count_p2 = score_board(board, player1, player2)
    n = min(len(count_p1), len(SEQUENCE_POINTS))
    s1 = sum(count_p1[i] * SEQUENCE_POINTS[i] for i in range(n))
    s2 = sum(count_p2[i] * SEQUENCE_POINTS[i] for i in range(n))
    return s1, s2

def _opponent_of(stone):
    return {'X': 'O', 'O': 'X', 'W': 'B', 'B': 'W'}.get(stone, 'O')

# ==========================================
# SMART PLAYER LOGIC
# ==========================================

def _copy_board(board):
    return [row[:] for row in board]

def _center_distance(row, col, center=3):
    return abs(row - center) + abs(col - center)

def is_valid_move(board, row, col):
    return 0 <= row < len(board) and 0 <= col < len(board) and board[row][col] == '.'

def _get_valid_moves(board):
    return [(r, c) for r in range(len(board)) for c in range(len(board)) if is_valid_move(board, r, c)]

def heuristic_evaluate(board, player, opponent, offense_weight, defense_weight):
    my_score, opp_score = calculate_scores(board, player, opponent)
    return (my_score * offense_weight) - (opp_score * defense_weight)

def get_heuristic_move(board, player, offense_weight, defense_weight):
    opponent = _opponent_of(player)
    valid_moves = _get_valid_moves(board)
    if not valid_moves:
        return 0, 0

    best_score = float('-inf')
    best_moves = []

    for r, c in valid_moves:
        copy = _copy_board(board)
        copy[r][c] = player
        score = heuristic_evaluate(copy, player, opponent, offense_weight, defense_weight)
        if score > best_score:
            best_score = score
            best_moves = [(r, c)]
        elif score == best_score:
            best_moves.append((r, c))

    center = len(board) // 2
    best_moves.sort(key=lambda rc: _center_distance(rc[0], rc[1], center))
    d0 = _center_distance(best_moves[0][0], best_moves[0][1], center)
    best_moves = [rc for rc in best_moves if _center_distance(rc[0], rc[1], center) == d0]
    return random.choice(best_moves)

def get_smart_move(board, player):
    # TWEAK THESE WEIGHTS TO CREATE YOUR PERSONA
    offense_weight = 1.0
    defense_weight = 1.0
    return get_heuristic_move(board, player, offense_weight, defense_weight)

def bot_move(game_state: dict) -> dict:
    board = game_state["board"]
    player = game_state.get("your_stone", "W")
    r, c = get_smart_move(board, player)
    return {"row": r, "col": c}
