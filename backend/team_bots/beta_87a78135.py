import time
import copy

try:
    from flask import Flask, request, jsonify  # optional (not required for local_py bots)
except Exception:  # pragma: no cover
    Flask = None
    request = None
    jsonify = None

app = Flask(__name__) if Flask else None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CORE GAME LOGIC (mirrors the game engine exactly)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def score_board(board, player, scores_for_n):
    """Calculate total score for a player — sum of all horizontal & vertical runs."""
    n = len(board)
    total = 0
    # Horizontal runs
    for r in range(n):
        run = 0
        for c in range(n):
            if board[r][c] == player:
                run += 1
            else:
                if run > 0:
                    total += scores_for_n.get(str(run), 0)
                run = 0
        if run > 0:
            total += scores_for_n.get(str(run), 0)
    # Vertical runs
    for c in range(n):
        run = 0
        for r in range(n):
            if board[r][c] == player:
                run += 1
            else:
                if run > 0:
                    total += scores_for_n.get(str(run), 0)
                run = 0
        if run > 0:
            total += scores_for_n.get(str(run), 0)
    return total


def get_empty_cells(board):
    """Get all empty cells on the board."""
    n = len(board)
    cells = []
    for r in range(n):
        for c in range(n):
            if board[r][c] == '.':
                cells.append((r, c))
    return cells


def copy_board(board):
    return [row[:] for row in board]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# EVALUATION FUNCTION — the brain of the bot
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def count_run_potential(board, player):
    """
    Count 'partial runs' — sequences of 2 of our stones with an adjacent
    empty cell that could become a scoring run of 3+.
    This rewards building up future scoring opportunities.
    """
    n = len(board)
    potential = 0

    # Horizontal potential
    for r in range(n):
        for c in range(n - 2):
            segment = [board[r][c], board[r][c + 1], board[r][c + 2]]
            mine = segment.count(player)
            empty = segment.count('.')
            opponent = 3 - mine - empty
            if opponent == 0 and mine == 2:
                potential += 3  # Close to scoring!
            elif opponent == 0 and mine == 1 and empty == 2:
                potential += 1  # Future opportunity

    # Vertical potential
    for c in range(n):
        for r in range(n - 2):
            segment = [board[r][c], board[r + 1][c], board[r + 2][c]]
            mine = segment.count(player)
            empty = segment.count('.')
            opponent = 3 - mine - empty
            if opponent == 0 and mine == 2:
                potential += 3
            elif opponent == 0 and mine == 1 and empty == 2:
                potential += 1

    return potential


def evaluate(board, my_stone, opp_stone, scores_for_n, turn):
    """
    Full board evaluation combining:
    1. Actual score differential (most important)
    2. Run-building potential (medium importance)
    3. Center control (small importance, decreases as game progresses)
    """
    my_score = score_board(board, my_stone, scores_for_n)
    opp_score = score_board(board, opp_stone, scores_for_n)

    # Primary: score differential
    score_diff = my_score - opp_score

    # Secondary: run-building potential
    my_potential = count_run_potential(board, my_stone)
    opp_potential = count_run_potential(board, opp_stone)
    potential_diff = my_potential - opp_potential

    # Tertiary: center control (matters less as game progresses)
    n = len(board)
    total_cells = n * n
    game_progress = turn / total_cells  # 0.0 (start) to 1.0 (end)
    center = (n - 1) / 2.0
    center_bonus = 0
    for r in range(n):
        for c in range(n):
            if board[r][c] == my_stone:
                dist = abs(r - center) + abs(c - center)
                center_bonus += max(0, center - dist) * 0.1
            elif board[r][c] == opp_stone:
                dist = abs(r - center) + abs(c - center)
                center_bonus -= max(0, center - dist) * 0.1

    # Weight center control less as game progresses
    center_weight = max(0, 1.0 - game_progress * 2) * 0.5

    return score_diff * 10 + potential_diff * 2 + center_bonus * center_weight


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MINIMAX WITH ALPHA-BETA PRUNING
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def immediate_gain(board, r, c, player, scores_for_n):
    """Quick heuristic: how much does placing here increase our score?"""
    before = score_board(board, player, scores_for_n)
    board[r][c] = player
    after = score_board(board, player, scores_for_n)
    board[r][c] = '.'
    return after - before


def minimax(board, depth, alpha, beta, is_maximizing,
            my_stone, opp_stone, scores_for_n, turn, deadline):
    """
    Minimax search with alpha-beta pruning.
    - is_maximizing=True: our turn (maximize eval)
    - is_maximizing=False: opponent's turn (minimize eval)
    """
    # Time check — don't exceed deadline
    if time.time() > deadline:
        return evaluate(board, my_stone, opp_stone, scores_for_n, turn)

    empty = get_empty_cells(board)

    # Terminal: no moves left or depth reached
    if depth == 0 or len(empty) == 0:
        return evaluate(board, my_stone, opp_stone, scores_for_n, turn)

    # Move ordering: sort by immediate gain for better pruning
    current_stone = my_stone if is_maximizing else opp_stone
    scored_moves = []
    for (r, c) in empty:
        g = immediate_gain(board, r, c, current_stone, scores_for_n)
        scored_moves.append((-g, r, c))  # Negative for descending sort
    scored_moves.sort()

    if is_maximizing:
        max_eval = float('-inf')
        for (_, r, c) in scored_moves:
            board[r][c] = my_stone
            val = minimax(board, depth - 1, alpha, beta, False,
                          my_stone, opp_stone, scores_for_n, turn + 1, deadline)
            board[r][c] = '.'
            max_eval = max(max_eval, val)
            alpha = max(alpha, val)
            if beta <= alpha:
                break  # Beta cutoff — opponent won't allow this
        return max_eval
    else:
        min_eval = float('inf')
        for (_, r, c) in scored_moves:
            board[r][c] = opp_stone
            val = minimax(board, depth - 1, alpha, beta, True,
                          my_stone, opp_stone, scores_for_n, turn + 1, deadline)
            board[r][c] = '.'
            min_eval = min(min_eval, val)
            beta = min(beta, val)
            if beta <= alpha:
                break  # Alpha cutoff — we won't choose this path
        return min_eval


def find_best_move(board, my_stone, opp_stone, scores_for_n, turn):
    """
    Iterative deepening minimax:
    1. Always compute depth-1 as fast fallback
    2. Try depth-2 for strong play
    3. Try depth-3 on small boards if time permits
    """
    start_time = time.time()
    deadline = start_time + 1.7  # keep under 2s server move limit

    empty = get_empty_cells(board)
    if not empty:
        return (0, 0)

    n = len(board)

    # Sort moves by immediate gain for first pass
    scored_moves = []
    for (r, c) in empty:
        g = immediate_gain(board, r, c, my_stone, scores_for_n)
        # Also penalize opponent's gain if we DON'T play here
        opp_g = immediate_gain(board, r, c, opp_stone, scores_for_n)
        scored_moves.append((-(g + opp_g * 0.7), r, c))
    scored_moves.sort()

    best_move = (scored_moves[0][1], scored_moves[0][2])  # Greedy fallback

    # Determine max depth based on board state
    remaining = len(empty)
    if remaining <= 8:
        max_depth = 4
    elif remaining <= 15:
        max_depth = 3
    elif remaining <= 30:
        max_depth = 2
    else:
        max_depth = 2

    # Iterative deepening
    for depth in range(1, max_depth + 1):
        if time.time() > deadline:
            break

        current_best_val = float('-inf')
        current_best_move = best_move

        for (_, r, c) in scored_moves:
            if time.time() > deadline:
                break

            board[r][c] = my_stone
            val = minimax(board, depth - 1, float('-inf'), float('inf'), False,
                          my_stone, opp_stone, scores_for_n, turn + 1, deadline)
            board[r][c] = '.'

            if val > current_best_val:
                current_best_val = val
                current_best_move = (r, c)

        best_move = current_best_move

    return best_move


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# HTTP API ENDPOINT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if app:
    @app.route('/', methods=['POST'])
    def make_move():
        data = request.get_json() or {}

        board = data.get("board", [])
        my_stone = data.get("your_stone") or data.get("current_player") or "W"
        opp_stone = data.get("opponent_stone") or ("B" if my_stone == "W" else "W")
        scores_for_n = data.get("scores_for_n", {})
        turn = data.get("turn", 0)

        # Convert scores_for_n keys to strings (this bot uses string keys)
        scores = {}
        for k, v in scores_for_n.items():
            scores[str(k)] = int(v)

        row, col = find_best_move(board, my_stone, opp_stone, scores, turn)
        return jsonify({"row": row, "col": col})


    @app.route('/', methods=['GET'])
    def health():
        return jsonify({
            "name": "Team7",
            "status": "online",
            "strategy": "Minimax + Alpha-Beta Pruning (2-ply) with positional scoring",
        })


if __name__ == '__main__' and app:
    print("=" * 60)
    print("  TEAM7 PAH-TUM BOT")
    print("  Strategy: Minimax + Alpha-Beta Pruning")
    print("  Depth: Adaptive (2-4 ply)")
    print("  Port: 5001")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5001, debug=False)


def bot_move(game_state: dict) -> dict:
    """
    Entry point for the tournament server.

    Expects the standard game_state payload and returns {"row", "col"}.
    """
    board = game_state["board"]
    my_stone = game_state.get("your_stone") or game_state.get("current_player") or "W"
    opp_stone = game_state.get("opponent_stone") or ("B" if my_stone == "W" else "W")
    scores_for_n = game_state.get("scores_for_n", {})
    turn = game_state.get("turn", 0)

    # Convert scores_for_n keys to strings (this bot uses string keys)
    scores = {}
    for k, v in scores_for_n.items():
        scores[str(k)] = int(v)

    row, col = find_best_move(board, my_stone, opp_stone, scores, turn)
    return {"row": row, "col": col}
