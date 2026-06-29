def bot_move(game_state: dict) -> dict:
    """
    Pah-Tum AI bot using iterative deepening alpha-beta search with:
    - Aspiration windows
    - Null move pruning
    - Killer move heuristic
    - History heuristic
    - Transposition table
    - Open-ended run scoring
    - Lazy eval in ordered_moves (no board copy for scoring)
    - Incremental board scoring (avoid full rescan)
    - Time-based cutoff instead of fixed depth
    - Late Move Reduction (LMR)
    """
    import random
    import time

    # ─── Config ──────────────────────────────────────────────
    SIZE = game_state["board_size"]
    MAX_DEPTH = 12
    MAX_CANDS = 16
    INF = 1e8
    TIME_LIMIT = 2.0  # seconds
    start_time = time.time()
    time_up = [False]

    SCORE_OPEN = [0, 0, 4,  18,  60, 200, 800, 2000]
    SCORE_HALF = [0, 0, 1,   5,  18,  60, 200,  800]
    SCORE_DEAD = [0, 0, 0,   1,   4,  12,  40,  160]

    # ─── Parse Board ─────────────────────────────────────────
    raw_board = game_state["board"]
    symbol_map = {".": 0, "X": 1, "O": -1, "x": 1, "o": -1, "W": 1, "B": -1}

    board = []
    for r in range(SIZE):
        row = []
        for c in range(SIZE):
            cell = raw_board[r][c]
            row.append(cell if isinstance(cell, int) else symbol_map.get(cell, 0))
        board.append(row)

    _stone = (game_state.get("your_stone")
              or game_state.get("current_player")
              or game_state.get("player"))
    if _stone in ("X", "W"):
        player = 1
    elif _stone in ("O", "B"):
        player = -1
    else:
        count_1  = sum(board[r][c] == 1  for r in range(SIZE) for c in range(SIZE))
        count_m1 = sum(board[r][c] == -1 for r in range(SIZE) for c in range(SIZE))
        player   = 1 if count_1 <= count_m1 else -1
    OPP = -player

    # ─── Zobrist Hashing ─────────────────────────────────────
    def _build_zobrist():
        rng_state = [0xA5521A]
        def rand():
            rng_state[0] = (rng_state[0] + 0x6D2B79F5) & 0xFFFFFFFF
            s = rng_state[0]
            t = ((s ^ (s >> 15)) * (1 | s)) & 0xFFFFFFFF
            t = (t + ((t ^ (t >> 7)) * (61 | t))) & 0xFFFFFFFF
            t = (t ^ (t >> 14)) & 0xFFFFFFFF
            return t
        z = {}
        for r in range(SIZE):
            for c in range(SIZE):
                for p in [1, -1]:
                    z[(r, c, p)] = rand() ^ (rand() * 0x10000)
        return z

    ZOB = _build_zobrist()

    # ─── Board Utilities ─────────────────────────────────────
    def copy_board(b):
        return [row[:] for row in b]

    def is_empty(b, r, c):
        return b[r][c] == 0

    def is_full(b):
        return all(b[r][c] != 0 for r in range(SIZE) for c in range(SIZE))

    def cdist(r, c):
        m = SIZE // 2
        return abs(r - m) + abs(c - m)

    def hash_board(b):
        h = 0
        for r in range(SIZE):
            for c in range(SIZE):
                if b[r][c] != 0:
                    h ^= ZOB[(r, c, b[r][c])]
        return h

    # ─── Incremental Run Scoring (single row or col) ──────────
    def score_line(line, length):
        """Score a single line (list of ints). Returns (s_me, s_opp)."""
        s_me = s_opp = 0
        run = 0
        who = 0
        run_start = 0
        for i in range(length + 1):
            cell = line[i] if i < length else 0
            if cell != 0 and cell == who:
                run += 1
            else:
                if who != 0 and run != 0:
                    left_open  = run_start > 0 and line[run_start - 1] == 0
                    right_open = i < length    and line[i] == 0
                    if left_open and right_open:
                        tbl = SCORE_OPEN
                    elif left_open or right_open:
                        tbl = SCORE_HALF
                    else:
                        tbl = SCORE_DEAD
                    pts = tbl[min(run, 7)]
                    if who == player:
                        s_me += pts
                    else:
                        s_opp += pts
                who = cell
                run = 1
                run_start = i
        return s_me, s_opp

    # ─── Incremental board_scores: only rescan affected lines ─
    def board_scores_full(b):
        s_me = s_opp = 0
        for r in range(SIZE):
            m, o = score_line(b[r], SIZE)
            s_me += m; s_opp += o
        for c in range(SIZE):
            col = [b[r][c] for r in range(SIZE)]
            m, o = score_line(col, SIZE)
            s_me += m; s_opp += o
        return s_me, s_opp

    def board_scores_incremental(b, prev_scores, move_r, move_c):
        """Recompute only the row and col affected by (move_r, move_c)."""
        old_me, old_opp = prev_scores

        # subtract old row score
        row_line = [b[move_r][c] for c in range(SIZE)]
        row_line[move_c] = 0  # pretend move not yet made
        old_row_me, old_row_opp = score_line(row_line, SIZE)

        # subtract old col score
        col_line = [b[r][move_c] for r in range(SIZE)]
        col_line[move_r] = 0
        old_col_me, old_col_opp = score_line(col_line, SIZE)

        # new row score
        new_row_me, new_row_opp = score_line(b[move_r], SIZE)

        # new col score
        col_line_new = [b[r][move_c] for r in range(SIZE)]
        new_col_me, new_col_opp = score_line(col_line_new, SIZE)

        new_me   = old_me   - old_row_me   - old_col_me   + new_row_me   + new_col_me
        new_opp  = old_opp  - old_row_opp  - old_col_opp  + new_row_opp  + new_col_opp
        return new_me, new_opp

    # ─── Urgency ─────────────────────────────────────────────
    def urgency(b):
        threat = 0
        for r in range(SIZE):
            run, who, run_start = 0, 0, 0
            for c in range(SIZE + 1):
                cell = b[r][c] if c < SIZE else 0
                if cell != 0 and cell == who:
                    run += 1
                else:
                    if who == OPP and run >= 4:
                        lo = run_start > 0 and b[r][run_start - 1] == 0
                        ro = c < SIZE      and b[r][c] == 0
                        if lo or ro:
                            threat += SCORE_OPEN[min(run, 7)] * 2.5
                    who = cell; run = 1; run_start = c
        for c in range(SIZE):
            run, who, run_start = 0, 0, 0
            for r in range(SIZE + 1):
                cell = b[r][c] if r < SIZE else 0
                if cell != 0 and cell == who:
                    run += 1
                else:
                    if who == OPP and run >= 4:
                        lo = run_start > 0 and b[run_start - 1][c] == 0
                        ro = r < SIZE      and b[r][c] == 0
                        if lo or ro:
                            threat += SCORE_OPEN[min(run, 7)] * 2.5
                    who = cell; run = 1; run_start = r
        return threat

    # ─── Density Bonus ───────────────────────────────────────
    def density(b, p):
        bonus = 0.0
        for r in range(SIZE):
            for c in range(SIZE):
                if b[r][c] == p:
                    if r > 0      and b[r-1][c] == p: bonus += 1.2
                    if r < SIZE-1 and b[r+1][c] == p: bonus += 1.2
                    if c > 0      and b[r][c-1] == p: bonus += 1.2
                    if c < SIZE-1 and b[r][c+1] == p: bonus += 1.2
        return bonus

    # ─── Full Evaluation ─────────────────────────────────────
    def eval_board(b, scores=None):
        if scores is None:
            scores = board_scores_full(b)
        s_me, s_opp = scores
        urg = urgency(b)
        den = density(b, player) - density(b, OPP) * 0.9
        centre = 0.0
        for r in range(SIZE):
            for c in range(SIZE):
                if b[r][c] == player:
                    centre -= cdist(r, c) * 0.08
                elif b[r][c] == OPP:
                    centre += cdist(r, c) * 0.08
        return (s_me - s_opp) - urg + den + centre

    # ─── Lazy Move Scoring (no board copy) ───────────────────
    def lazy_move_score(b, r, c, p, base_scores):
        """Estimate move value using incremental scoring only — no copy."""
        b[r][c] = p
        inc_scores = board_scores_incremental(b, base_scores, r, c)
        b[r][c] = 0  # undo
        s_me, s_opp = inc_scores
        raw = (s_me - s_opp) if p == player else -(s_me - s_opp)
        return raw

    # ─── Move Ordering ───────────────────────────────────────
    def ordered_moves(b, p, killers=None, hist_table=None, base_scores=None):
        if killers is None:
            killers = []
        if hist_table is None:
            hist_table = {}
        if base_scores is None:
            base_scores = board_scores_full(b)

        cands = []
        killer_set = set((r * SIZE + c) for r, c in killers)

        for r in range(SIZE):
            for c in range(SIZE):
                if not is_empty(b, r, c):
                    continue
                sc = lazy_move_score(b, r, c, p, base_scores)
                hist = hist_table.get(r * SIZE + c, 0)
                killer_bonus = 8000 if (r * SIZE + c) in killer_set else 0
                cands.append((sc + hist * 0.01 + killer_bonus, -cdist(r, c), r, c))

        cands.sort(key=lambda x: (-x[0], -x[1]))
        return [(r, c) for (_, _, r, c) in cands[:MAX_CANDS]]

    # ─── Transposition Table & Killers & History ─────────────
    tt = {}
    killers = [[] for _ in range(MAX_DEPTH + 4)]
    hist_table = {}

    # ─── Alpha-Beta with LMR ──────────────────────────────────
    NULL_R = 2
    LMR_MIN_DEPTH = 3
    LMR_MIN_MOVE  = 4   # start reducing after this many moves searched

    def ab(b, depth, alpha, beta, maximizing, allow_null, cur_scores=None):
        if time_up[0]:
            return 0

        if time.time() - start_time >= TIME_LIMIT:
            time_up[0] = True
            return 0

        if cur_scores is None:
            cur_scores = board_scores_full(b)

        bh = hash_board(b)
        tte = tt.get(bh)
        if tte and tte['d'] >= depth:
            if tte['flag'] == 'e':
                return tte['val']
            if tte['flag'] == 'l':
                alpha = max(alpha, tte['val'])
            if tte['flag'] == 'u':
                beta  = min(beta,  tte['val'])
            if alpha >= beta:
                return tte['val']

        if depth == 0 or is_full(b):
            v = eval_board(b, cur_scores)
            tt[bh] = {'d': 0, 'flag': 'e', 'val': v}
            return v

        # Null Move Pruning
        if allow_null and maximizing and depth >= NULL_R + 1:
            null_val = ab(b, depth - NULL_R - 1, beta - 1, beta, False, False, cur_scores)
            if null_val >= beta:
                tt[bh] = {'d': depth, 'flag': 'l', 'val': beta}
                return beta

        cur = player if maximizing else OPP
        kl  = killers[depth] if depth < len(killers) else []
        moves = ordered_moves(b, cur, kl, hist_table, cur_scores)

        if not moves:
            v = eval_board(b, cur_scores)
            tt[bh] = {'d': depth, 'flag': 'e', 'val': v}
            return v

        orig_alpha = alpha
        best = -INF if maximizing else INF
        best_rc = None

        for move_idx, (r, c) in enumerate(moves):
            nb = copy_board(b)
            nb[r][c] = cur
            child_scores = board_scores_incremental(nb, cur_scores, r, c)

            # ─── Late Move Reduction ──────────────────────────
            use_depth = depth - 1
            if (depth >= LMR_MIN_DEPTH
                    and move_idx >= LMR_MIN_MOVE
                    and not time_up[0]):
                reduction = 1 + (move_idx - LMR_MIN_MOVE) // 3
                use_depth = max(0, depth - 1 - reduction)

            v = ab(nb, use_depth, alpha, beta, not maximizing, True, child_scores)

            # Re-search at full depth if LMR move beats alpha
            if use_depth < depth - 1 and v > alpha and not time_up[0]:
                v = ab(nb, depth - 1, alpha, beta, not maximizing, True, child_scores)

            if time_up[0]:
                break

            if maximizing:
                if v > best:
                    best = v
                    best_rc = (r, c)
                alpha = max(alpha, best)
            else:
                if v < best:
                    best = v
                    best_rc = (r, c)
                beta = min(beta, best)

            if alpha >= beta:
                if best_rc:
                    k_arr = killers[depth]
                    if not any(kr == best_rc[0] and kc == best_rc[1] for kr, kc in k_arr):
                        k_arr.insert(0, best_rc)
                        if len(k_arr) > 2:
                            k_arr.pop()
                key = r * SIZE + c
                hist_table[key] = hist_table.get(key, 0) + (1 << depth)
                break

        if time_up[0]:
            return best if best != (-INF if maximizing else INF) else 0

        flag = 'u' if best <= orig_alpha else ('l' if best >= beta else 'e')
        tt[bh] = {'d': depth, 'flag': flag, 'val': best}
        return best

    # ─── Iterative Deepening ──────────────────────────────────
    WINDOW = 50

    def iterative_deepening(b):
        base_scores = board_scores_full(b)
        first_moves = ordered_moves(b, player, [], {}, base_scores)
        if not first_moves:
            return None

        best_move  = first_moves[0]
        prev_score = 0

        for depth in range(1, MAX_DEPTH + 1):
            if time_up[0]:
                break
            if time.time() - start_time >= TIME_LIMIT:
                break

            for i in range(len(killers)):
                killers[i] = []

            alpha = (prev_score - WINDOW) if depth >= 3 else -INF
            beta  = (prev_score + WINDOW) if depth >= 3 else  INF

            iter_best  = -INF
            iter_moves = []
            root_moves = ordered_moves(b, player, killers[depth] if depth < len(killers) else [], hist_table, base_scores)

            for r, c in root_moves:
                if time_up[0]:
                    break
                nb = copy_board(b)
                nb[r][c] = player
                child_scores = board_scores_incremental(nb, base_scores, r, c)
                v = ab(nb, depth - 1, alpha, beta, False, True, child_scores)

                if time_up[0]:
                    break

                if depth >= 3 and (v <= prev_score - WINDOW or v >= prev_score + WINDOW):
                    v = ab(nb, depth - 1, -INF, INF, False, True, child_scores)

                if v > iter_best:
                    iter_best  = v
                    iter_moves = [(r, c)]
                    alpha = max(alpha, v)
                elif v == iter_best:
                    iter_moves.append((r, c))

            if iter_moves and not time_up[0]:
                prev_score = iter_best
                best_move  = random.choice(iter_moves)

        return best_move

    # ─── Entry Point ─────────────────────────────────────────
    all_empty = [
        (r, c)
        for r in range(SIZE)
        for c in range(SIZE)
        if board[r][c] == 0
    ]

    if not all_empty:
        return {"row": 0, "col": 0}

    result = iterative_deepening(board)
    if result is None:
        r, c = all_empty[0]
        return {"row": r, "col": c}

    row, col = result
    return {"row": row, "col": col}