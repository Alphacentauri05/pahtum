import random
import time

_DEFAULT_N = 7

_TIME_LIMIT   = 0.85
_MAX_DEPTH    = 7
_TT_SIZE      = 1 << 18
_POTENTIAL_WT = 1.5

_ZOBRIST_N = None
ZOBRIST = []
_PIDX = {'X': 0, 'O': 1, 'W': 0, 'B': 1}


_SCORES_FOR_N = {}


def _ensure_tables(n: int):
    global _ZOBRIST_N, ZOBRIST, _SCORES_FOR_N
    if _ZOBRIST_N != n:
        rng = random.Random(0xC0FFEE_DEADBEEF ^ n)
        ZOBRIST = [[[rng.getrandbits(64) for _ in range(2)] for _ in range(n)] for _ in range(n)]
        _ZOBRIST_N = n
    if not _SCORES_FOR_N or _SCORES_FOR_N.get("__n__") != n:
        scores = {1: 0, 2: 0, 3: 3}
        for L in range(4, n + 1):
            scores[L] = 2 * scores[L - 1] + L
        scores["__n__"] = n
        _SCORES_FOR_N = scores


def _score_for_player(board, stone):
    n = len(board)
    _ensure_tables(n)
    total = 0
    # Rows
    for r in range(n):
        run = 0
        for c in range(n):
            if board[r][c] == stone:
                run += 1
            else:
                total += _SCORES_FOR_N.get(run, 0)
                run = 0
        total += _SCORES_FOR_N.get(run, 0)
    # Columns
    for c in range(n):
        run = 0
        for r in range(n):
            if board[r][c] == stone:
                run += 1
            else:
                total += _SCORES_FOR_N.get(run, 0)
                run = 0
        total += _SCORES_FOR_N.get(run, 0)
    return total


def calculate_scores(board, player, opponent):
    return _score_for_player(board, player), _score_for_player(board, opponent)

def _board_hash(board):
    h = 0
    n = len(board)
    _ensure_tables(n)
    for r in range(n):
        for c in range(n):
            p = board[r][c]
            if p != ' ':
                h ^= ZOBRIST[r][c][_PIDX[p]]
    return h

_NEXT_SCORE = {2: 3, 3: 10, 4: 25, 5: 56, 6: 119}

def _calc_threat(board, p):
    n = len(board)
    threat = 0.0
    h_part = [[False] * n for _ in range(n)]
    v_part = [[False] * n for _ in range(n)]
    for r in range(n):
        for c in range(n):
            if board[r][c] != p:
                continue
            for dr, dc, is_h in ((0, 1, True), (1, 0, False)):
                pr, pc = r - dr, c - dc
                if 0 <= pr < n and 0 <= pc < n and board[pr][pc] == p:
                    continue
                run, nr, nc = 0, r, c
                while 0 <= nr < n and 0 <= nc < n and board[nr][nc] == p:
                    run += 1
                    nr += dr
                    nc += dc
                if run >= 2:
                    f_open = 0
                    fr, fc = nr, nc
                    while 0 <= fr < n and 0 <= fc < n and board[fr][fc] == ' ':
                        f_open += 1
                        fr += dr
                        fc += dc
                    b_open = 0
                    br, bc = r - dr, c - dc
                    while 0 <= br < n and 0 <= bc < n and board[br][bc] == ' ':
                        b_open += 1
                        br -= dr
                        bc -= dc
                    if run + f_open + b_open >= 3:
                        openness = int(f_open > 0) + int(b_open > 0)
                        if openness > 0:
                            base = _NEXT_SCORE.get(run, 119)
                            threat += base * (1.5 if openness == 2 else 1.0)
                            for i in range(run):
                                if is_h:
                                    h_part[r + i * dr][c + i * dc] = True
                                else:
                                    v_part[r + i * dr][c + i * dc] = True
    forks = sum(1 for r in range(n) for c in range(n) if h_part[r][c] and v_part[r][c])
    # 3. Reduce fork influence: smaller bonus so scoring chains are preferred
    return threat + forks * 2.0

def _eval(board, player, opponent):
    my_score, opp_score = calculate_scores(board, player, opponent)
    val = float(my_score - opp_score)
    my_threat  = _calc_threat(board, player)
    opp_threat = _calc_threat(board, opponent)
    # 4. Improve evaluation weighting: actual score difference prioritized over threat potential
    return (val * 3.0) + my_threat - (opp_threat * 1.5)

def _order_moves(board, moves, player, opponent):
    scored = []
    # 2. Prioritize chain completion in move ordering
    my_cur, _ = calculate_scores(board, player, opponent)
    for r, c in moves:
        board[r][c] = player
        ev = _eval(board, player, opponent)
        
        my_new, _ = calculate_scores(board, player, opponent)
        if my_new > my_cur:
            # Huge priority for moves that extend a sequence to score immediately
            ev += 10000.0 + (my_new - my_cur)
            
        board[r][c] = ' '
        scored.append((ev, r, c))
    scored.sort(reverse=True)
    return [(r, c) for _, r, c in scored]

_EXACT = 0
_LOWER = 1
_UPPER = 2

def _negamax(board, depth, alpha, beta, player, opponent, tt, deadline, hash_val):
    if time.perf_counter() >= deadline:
        return _eval(board, player, opponent), True
    tt_slot = hash_val & (_TT_SIZE - 1)
    entry = tt.get(tt_slot)
    if entry and entry[0] == hash_val and entry[1] >= depth:
        _, _, stored_val, flag = entry
        if flag == _EXACT:
            return stored_val, False
        elif flag == _LOWER:
            alpha = max(alpha, stored_val)
        elif flag == _UPPER:
            beta = min(beta, stored_val)
        if alpha >= beta:
            return stored_val, False
    n = len(board)
    has_empty = next((True for r in range(n) for c in range(n) if board[r][c] == ' '), False)
    if depth == 0 or not has_empty:
        return _eval(board, player, opponent), False
    empty = [(r, c) for r in range(n) for c in range(n) if board[r][c] == ' ' ]
    ordered = _order_moves(board, empty, player, opponent)
    best_val  = float('-inf')
    orig_alpha = alpha
    timed_out  = False
    for r, c in ordered:
        board[r][c] = player
        new_hash = hash_val ^ ZOBRIST[r][c][_PIDX[player]]
        child_val, child_to = _negamax(board, depth - 1, -beta, -alpha, opponent, player, tt, deadline, new_hash)
        val = -child_val
        board[r][c] = ' '
        if child_to:
            timed_out = True
            break
        if val > best_val:
            best_val = val
        if val > alpha:
            alpha = val
        if alpha >= beta:
            break
    if not timed_out and best_val != float('-inf'):
        if best_val <= orig_alpha:
            flag = _UPPER
        elif best_val >= beta:
            flag = _LOWER
        else:
            flag = _EXACT
        tt[tt_slot] = (hash_val, depth, best_val, flag)
    return best_val, timed_out

def bot_move(game_state: dict) -> dict:
    raw_board = game_state["board"]
    n         = game_state["board_size"]
    _ensure_tables(n)
    # Derive player/opponent from multiple possible keys
    player = (
        game_state.get("your_stone")
        or game_state.get("current_player")
        or game_state.get("player")
        or "X"
    )
    opponent = (
        game_state.get("opponent_stone")
        or game_state.get("opponent")
        or ("O" if player == "X" else "X")
    )
    has_dot = any(raw_board[r][c] == '.' for r in range(n) for c in range(n))
    if has_dot:
        board = [[' ' if raw_board[r][c] == '.' else raw_board[r][c] for c in range(n)] for r in range(n)]
    else:
        board = [row[:] for row in raw_board]
    empty = [(r, c) for r in range(n) for c in range(n) if board[r][c] == ' ']
    if not empty:
        return {"row": 0, "col": 0}
    if len(empty) == 1:
        return {"row": empty[0][0], "col": empty[0][1]}
        
    if len(empty) == n * n:
        return {"row": n // 2, "col": n // 2}
    if len(empty) == n * n - 1:
        cr, cc = n // 2, n // 2
        return {"row": cr, "col": cc - 1} if board[cr][cc] != ' ' else {"row": cr, "col": cc}
        
    # 1. Immediate scoring move detection & Urgent Blocking
    my_cur_score, opp_cur_score = calculate_scores(board, player, opponent)
    best_imm = None
    best_imm_val = 0
    best_blk = None
    best_blk_val = 0
    
    for r, c in empty:
        board[r][c] = player
        m_new, _ = calculate_scores(board, player, opponent)
        board[r][c] = ' '
        diff = m_new - my_cur_score
        if diff > best_imm_val:
            best_imm_val = diff
            best_imm = (r, c)
            
        board[r][c] = opponent
        _, o_new = calculate_scores(board, player, opponent)
        board[r][c] = ' '
        o_diff = o_new - opp_cur_score
        if o_diff > best_blk_val:
            best_blk_val = o_diff
            best_blk = (r, c)

    # 1b. Urgent blocking: If the opponent can score MORE than we can immediately, block them!
    if best_blk_val > best_imm_val and best_blk_val > 0:
        return {"row": best_blk[0], "col": best_blk[1]}
        
    # 1a. Immediate scoring: If we can score immediately and it's equal or better, play it!
    if best_imm is not None and best_imm_val > 0:
        return {"row": best_imm[0], "col": best_imm[1]}

    tt       = {}
    deadline = time.perf_counter() + _TIME_LIMIT
    h0       = _board_hash(board)
    ordered_moves = _order_moves(board, empty, player, opponent)
    best_move     = ordered_moves[0]
    for depth in range(1, _MAX_DEPTH + 1):
        if time.perf_counter() >= deadline:
            break
        depth_best_val  = float('-inf')
        depth_best_move = None
        alpha           = float('-inf')
        beta            = float('inf')
        timed_out       = False
        for r, c in ordered_moves:
            if time.perf_counter() >= deadline:
                timed_out = True
                break
            board[r][c] = player
            child_hash  = h0 ^ ZOBRIST[r][c][_PIDX[player]]
            val, child_to = _negamax(board, depth - 1, -beta, -alpha, opponent, player, tt, deadline, child_hash)
            val = -val
            board[r][c] = ' '
            if child_to:
                timed_out = True
                break
            val += random.uniform(0.0, 0.01)
            if val > depth_best_val:
                depth_best_val  = val
                depth_best_move = (r, c)
            if val > alpha:
                alpha = val
        if not timed_out and depth_best_move:
            best_move = depth_best_move
            ordered_moves = [best_move] + [m for m in ordered_moves if m != best_move]
    return {"row": best_move[0], "col": best_move[1]}

def play_move_2(board, player):
    game_state = {
        "board":      board,
        "board_size": SIZE,
        "player":     player,
        "opponent":   "O" if player == "X" else "X",
    }
    result = bot_move(game_state)
    return result["row"], result["col"]