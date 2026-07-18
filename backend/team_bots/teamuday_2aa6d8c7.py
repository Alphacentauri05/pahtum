import time

def bot_move(game_state: dict) -> dict:
    """
    Ultimate pure-Python engine:
    Iterative Deepening + Alpha-Beta Pruning + Transposition Tables + Dynamic Move Ordering.
    """
    board = game_state["board"]
    n = game_state.get("board_size", len(board))
    my_id = (game_state.get("your_stone")
             or game_state.get("current_player")
             or game_state.get("player")
             or "W")
    opp_id = {'X': 'O', 'O': 'X', 'W': 'B', 'B': 'W'}.get(my_id, 'B')
    
    time_limit = 0.93  # Slightly tighter to ensure we return safely
    start_time = time.time()

    # ---------- PRECOMPUTED GLOBALS ---------- #
    precomputed_lines = []
    for i in range(n):
        precomputed_lines.append([i * n + j for j in range(n)])  # Rows
        precomputed_lines.append([j * n + i for j in range(n)])  # Columns

    base_move_order = sorted(range(n * n), key=lambda x: abs((x // n) - (n // 2)) + abs((x % n) - (n // 2)))
    score_table = {0: 0, 1: 0, 2: 0, 3: 3, 4: 10, 5: 25, 6: 56, 7: 119}

    # Transposition Table: stores tuples of (depth, flag, score, best_move)
    # Flags: 0 = EXACT, 1 = LOWERBOUND, 2 = UPPERBOUND
    tt = {}

    # ---------- CORE EVALUATION ---------- #
    def _fast_eval_speed(board_tuple):
        my_score, opp_score = 0, 0
        
        for line in precomputed_lines:
            my_streak, opp_streak = 0, 0
            
            for idx in line:
                piece = board_tuple[idx]
                if piece == my_id:
                    my_streak += 1
                    if opp_streak > 0:
                        opp_score += score_table.get(opp_streak, 0)
                        opp_streak = 0
                elif piece == opp_id:
                    opp_streak += 1
                    if my_streak > 0:
                        my_score += score_table.get(my_streak, 0)
                        my_streak = 0
                else:
                    if my_streak > 0:
                        my_score += score_table.get(my_streak, 0)
                        my_streak = 0
                    if opp_streak > 0:
                        opp_score += score_table.get(opp_streak, 0)
                        opp_streak = 0
            
            if my_streak > 0: my_score += score_table.get(my_streak, 0)
            if opp_streak > 0: opp_score += score_table.get(opp_streak, 0)

        return my_score - opp_score

    # ---------- TT-ENHANCED MINIMAX ---------- #
    def _minimax(board_list, depth, alpha, beta, is_max):
        if time.time() - start_time > time_limit:
            raise TimeoutError

        board_tuple = tuple(board_list)
        
        # 1. Transposition Table Lookup
        tt_entry = tt.get(board_tuple)
        if tt_entry and tt_entry[0] >= depth:
            tt_flag, tt_score, tt_move = tt_entry[1], tt_entry[2], tt_entry[3]
            if tt_flag == 0: return tt_score, tt_move
            if tt_flag == 1: alpha = max(alpha, tt_score)
            if tt_flag == 2: beta = min(beta, tt_score)
            if alpha >= beta: return tt_score, tt_move

        if depth == 0:
            val = _fast_eval_speed(board_tuple)
            return val, -1

        # 2. Dynamic Move Ordering (Try TT's best move first)
        ordered_moves = []
        if tt_entry and tt_entry[3] != -1:
            ordered_moves.append(tt_entry[3])
        for m in base_move_order:
            if board_list[m] == 0 and (not tt_entry or m != tt_entry[3]):
                ordered_moves.append(m)

        if not ordered_moves:
            return _fast_eval_speed(board_tuple), -1

        best_move = -1
        original_alpha = alpha

        if is_max:
            max_eval = -100000
            for move in ordered_moves:
                board_list[move] = my_id
                score, _ = _minimax(board_list, depth - 1, alpha, beta, False)
                board_list[move] = 0
                
                if score > max_eval:
                    max_eval = score
                    best_move = move
                alpha = max(alpha, max_eval)
                if beta <= alpha:
                    break
            
            # Save to TT
            flag = 0 if max_eval > original_alpha and max_eval < beta else (1 if max_eval >= beta else 2)
            tt[board_tuple] = (depth, flag, max_eval, best_move)
            return max_eval, best_move
            
        else:
            min_eval = 100000
            for move in ordered_moves:
                board_list[move] = opp_id
                score, _ = _minimax(board_list, depth - 1, alpha, beta, True)
                board_list[move] = 0
                
                if score < min_eval:
                    min_eval = score
                    best_move = move
                beta = min(beta, min_eval)
                if beta <= alpha:
                    break
            
            # Save to TT
            flag = 0 if min_eval > original_alpha and min_eval < beta else (1 if min_eval <= original_alpha else 2)
            tt[board_tuple] = (depth, flag, min_eval, best_move)
            return min_eval, best_move

    # ---------- MAIN EXECUTION ---------- #
    board_1d = [0] * (n * n)
    for r in range(n):
        for c in range(n):
            if board[r][c] != ".":
                board_1d[r * n + c] = board[r][c]

    best_move_1d = -1
    depth = 1
    
    try:
        while True:
            _, move = _minimax(board_1d, depth, -100000, 100000, True)
            if move != -1:
                best_move_1d = move
            depth += 1
    except TimeoutError:
        pass

    # Failsafes
    if best_move_1d == -1:
        for m in base_move_order:
            if board_1d[m] == 0:
                best_move_1d = m
                break
    
    if best_move_1d == -1:
        return {"row": 0, "col": 0}
        
    return {"row": best_move_1d // n, "col": best_move_1d % n}