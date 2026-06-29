"""
Combined Pah Tum Bot Entry - Player 1
Includes core logic, smart playing heuristic, and move wrapper.
"""

import random

# ==========================================
# PAHTUM CORE LOGIC (from pahtum_core.py)
# ==========================================

SIZE = 7
# Points for sequences of 3, 4, 5, 6, 7
SEQUENCE_POINTS = (3, 10, 25, 56, 119)



def score_board(board, p1, p2):
    """
    Count sequences of 3+ for stones p1 and p2.
    Returns (count_p1, count_p2) where each is a list of counts for lengths 3..size.
    """
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


def get_scores_from_counts(count_p1, count_p2, size):
    """Compute total scores from sequence counts."""
    pts = SEQUENCE_POINTS
    n = min(len(count_p1), len(pts))
    score_p1 = sum(count_p1[i] * pts[i] for i in range(n))
    score_p2 = sum(count_p2[i] * pts[i] for i in range(n))
    return score_p1, score_p2


def _opponent_of(stone):
    """Return the opponent stone for both X/O and W/B symbol sets."""
    return {'X': 'O', 'O': 'X', 'W': 'B', 'B': 'W'}.get(stone, 'O')


def calculate_scores(board, player1, player2):
    """Return (player1_score, player2_score) for the given board."""
    count_p1, count_p2 = score_board(board, player1, player2)
    return get_scores_from_counts(count_p1, count_p2, len(board))



# ==========================================
# SMART PLAYER LOGIC (from smart_player.py)
# ==========================================

def _copy_board(board):
    return [row[:] for row in board]

def _center_distance(row, col, center=3):
    """Prefer moves closer to the board center. Smaller is better."""
    return abs(row - center) + abs(col - center)

def is_valid_move(board, row, col):
    """Return True if (row, col) is within bounds and empty."""
    size = len(board)
    return (
        0 <= row < size
        and 0 <= col < size
        and board[row][col] == '.'
    )

def _get_valid_moves(board):
    size = len(board)
    return [(r, c) for r in range(size) for c in range(size) if is_valid_move(board, r, c)]

def heuristic_evaluate(board, player, opponent, offense_weight, defense_weight):
    """
    Evaluates the board state based on the persona's weights.
    Higher score is better for the `player`.
    """
    my_score, opp_score = calculate_scores(board, player, opponent)
    return (my_score * offense_weight) - (opp_score * defense_weight)

def get_heuristic_move(board, player, offense_weight, defense_weight):
    """
    Algorithm 1: Weighted Heuristic Engine.
    Evaluates all valid moves 1-ply deep based on persona weights.
    Returns (row, col) of the best move.
    """
    opponent = _opponent_of(player)
    valid_moves = _get_valid_moves(board)
    if not valid_moves:
        raise ValueError("no valid moves")

    best_score = float('-inf')
    best_moves = []

    for r, c in valid_moves:
        copy = _copy_board(board)
        copy[r][c] = player
        
        # Evaluate board using the persona's weighted scoring
        score = heuristic_evaluate(copy, player, opponent, offense_weight, defense_weight)
        
        if score > best_score:
            best_score = score
            best_moves = [(r, c)]
        elif score == best_score:
            best_moves.append((r, c))

    # Tie-break: prefer center
    center = len(board) // 2
    best_moves.sort(key=lambda rc: _center_distance(rc[0], rc[1], center))
    d0 = _center_distance(best_moves[0][0], best_moves[0][1], center)
    best_moves = [rc for rc in best_moves if _center_distance(rc[0], rc[1], center) == d0]
    return random.choice(best_moves)

def minimax(board, depth, alpha, beta, is_maximizing, player, opponent, offense_weight, defense_weight):
    """
    Minimax with Alpha-Beta Pruning.
    """
    valid_moves = _get_valid_moves(board)
    
    # Terminal node or depth limit reached
    if depth == 0 or not valid_moves:
        score = heuristic_evaluate(board, player, opponent, offense_weight, defense_weight)
        # Add a slight center-bonus to the evaluation leaf nodes so Minimax naturally climbs towards the center.
        return score, None

    best_move = None
    if is_maximizing:
        max_eval = float('-inf')
        for r, c in valid_moves:
            copy = _copy_board(board)
            copy[r][c] = player
            
            # Recurse (opponent's turn)
            eval_score, _ = minimax(copy, depth - 1, alpha, beta, False, player, opponent, offense_weight, defense_weight)
            
            # Tiny center bonus
            eval_score -= (_center_distance(r, c) * 0.1) 

            if eval_score > max_eval:
                max_eval = eval_score
                best_move = (r, c)
            
            alpha = max(alpha, eval_score)
            if beta <= alpha:
                break
        return max_eval, best_move
    else:
        min_eval = float('inf')
        for r, c in valid_moves:
            copy = _copy_board(board)
            copy[r][c] = opponent
            
            # Recurse (player's turn)
            eval_score, _ = minimax(copy, depth - 1, alpha, beta, True, player, opponent, offense_weight, defense_weight)
            
            if eval_score < min_eval:
                min_eval = eval_score
                best_move = (r, c)
            
            beta = min(beta, eval_score)
            if beta <= alpha:
                break
        return min_eval, best_move

def get_strategic_move(board, player, offense_weight, defense_weight, depth=2):
    """
    Algorithm 2: Minimax (Depth 2).
    Burns computation time for a strategic, multi-ply lookahead.
    """
    opponent = _opponent_of(player)
    valid_moves = _get_valid_moves(board)
    if not valid_moves:
        raise ValueError("no valid moves")
        
    _, best_move = minimax(board, depth, float('-inf'), float('inf'), True, player, opponent, offense_weight, defense_weight)
    
    # Fallback to heuristic if minimax returns None (e.g. at the very end of the game with 1 move left)
    if best_move is None:
        return get_heuristic_move(board, player, offense_weight, defense_weight)
        
    return best_move

def get_smart_move(board, player, persona="mastermind", move_type="standard"):
    """
    Persona & Move Dispatcher.
    Combines the selected Persona configuration with the requested Algorithm (standard vs strategic).
    """
    persona = persona.lower()
    move_type = move_type.lower()
    
    # Configure weights based on Persona
    if persona == "builder":
        offense_weight = 1.0
        defense_weight = 0.0
    elif persona == "blocker":
        offense_weight = 0.0
        defense_weight = 1.0
    else: # mastermind or default
        offense_weight = 1.0
        defense_weight = 1.0

    # Dispatch to Algorithm based on Move Type
    if move_type == "strategic":
        # Hard cap depth at 2 for performance in Python without C extensions
        return get_strategic_move(board, player, offense_weight, defense_weight, depth=2)
    else:
        return get_heuristic_move(board, player, offense_weight, defense_weight)




def bot_move(game_state: dict) -> dict:
    """
    Competition wrapper matching team_example1.py format.
    Accepts game_state and returns {"row": r, "col": c}.
    """
    board = game_state["board"]
    player = (game_state.get("your_stone")
              or game_state.get("current_player")
              or game_state.get("player")
              or "W")
    
    # Get the best move using the mastermind heuristic
    best_r, best_c = get_smart_move(board, player, persona="mastermind", move_type="standard")
    
    return {"row": best_r, "col": best_c}
