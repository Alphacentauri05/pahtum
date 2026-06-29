import random
import time

def bot_move(game_state: dict) -> dict:
    board  = game_state["board"]
    SIZE   = game_state["board_size"]
    player = (game_state.get("your_stone")
              or game_state.get("current_player")
              or game_state.get("player")
              or _infer_player(board, SIZE))

    row, col = _choose_move(board, player, SIZE)
    return {"row": row, "col": col}


# ── constants ────────────────────────────────────────────────────────────────

EMPTY      = '.'
INF        = 10_000_000
ASP_WINDOW = 30.0

LINE_SCORE = {3: 3, 4: 10, 5: 25, 6: 56, 7: 119}

OPENING_BOOK = [
    (3, 3), (3, 5), (1, 3), (3, 1), (5, 3),
    (1, 1), (5, 5), (1, 5), (5, 1),
]

W_ATK = dict(completed=1.00, potential=0.50, threats=0.80,
             centrality=0.20, intersection=0.35, tempo=0.25)
W_DEF = dict(completed=0.80, potential=0.55, threats=0.95,
             centrality=0.15, intersection=0.30, tempo=0.20)

_TT:        dict = {}
_killers:   dict = {}
_last_score: dict = {'X': 0.0, 'O': 0.0}


# ── helpers ──────────────────────────────────────────────────────────────────

def _infer_player(board, SIZE) -> str:
    p1 = sum(board[r][c] in ('X', 'W') for r in range(SIZE) for c in range(SIZE))
    p2 = sum(board[r][c] in ('O', 'B') for r in range(SIZE) for c in range(SIZE))
    if p1 == 0 and p2 == 0:
        return 'W'
    return 'W' if p1 <= p2 else 'B'

def _opp(player: str) -> str:
    return {'X': 'O', 'O': 'X', 'W': 'B', 'B': 'W'}.get(player, 'B')

def _copy(board):
    return [row[:] for row in board]

def _board_key(board) -> str:
    return ''.join(''.join(row) for row in board)

def _get_turn(board, SIZE) -> int:
    return sum(cell != EMPTY for row in board for cell in row)

def _get_phase(board, SIZE) -> str:
    t = _get_turn(board, SIZE)
    return 'early' if t < 10 else ('mid' if t < 32 else 'late')

def _is_first_player(board, player, SIZE) -> bool:
    mine   = sum(cell == player              for row in board for cell in row)
    theirs = sum(cell not in (EMPTY, player) for row in board for cell in row)
    return mine > theirs


# ── transposition table ───────────────────────────────────────────────────────

def _tt_store(key, depth, flag, score, best_move):
    ex = _TT.get(key)
    if ex and ex[0] > depth:
        return
    _TT[key] = (depth, flag, score, best_move)

def _tt_lookup(key, depth, alpha, beta):
    entry = _TT.get(key)
    if not entry:
        return None
    d, flag, score, move = entry
    if d < depth:
        return None
    if flag == 0:
        return score, True, move
    if flag == 1 and score >= beta:
        return score, False, move
    if flag == 2 and score <= alpha:
        return score, False, move
    return None

def _add_killer(depth, move):
    bucket = _killers.setdefault(depth, [])
    if move not in bucket:
        _killers[depth] = ([move] + bucket)[:2]


# ── evaluation ────────────────────────────────────────────────────────────────

def _calc_scores(board, player, opponent, SIZE):
    ps = os = 0
    def scan(get_cell):
        nonlocal ps, os
        for i in range(SIZE):
            run = 0; who = None
            for j in range(SIZE + 1):
                cell = get_cell(i, j) if j < SIZE else None
                if cell and cell == who:
                    run += 1
                else:
                    if who and who != EMPTY and run >= 3:
                        pts = LINE_SCORE.get(run, 0)
                        if who == player: ps += pts
                        else:             os += pts
                    who = cell; run = 1
    scan(lambda i, j: board[i][j])
    scan(lambda i, j: board[j][i])
    return ps, os

def _longest_line(board, player, SIZE) -> int:
    best = 0
    for r in range(SIZE):
        run = 0
        for c in range(SIZE):
            run = run + 1 if board[r][c] == player else 0
            best = max(best, run)
    for c in range(SIZE):
        run = 0
        for r in range(SIZE):
            run = run + 1 if board[r][c] == player else 0
            best = max(best, run)
    return best

def _intersection_bonus(board, player, opponent, SIZE) -> float:
    bonus = 0.0
    for r in range(SIZE):
        for c in range(SIZE):
            if board[r][c] != EMPTY:
                continue
            left = right = up = down = 0
            for d in range(1, SIZE):
                if c - d < 0 or board[r][c - d] == opponent: break
                if board[r][c - d] == player: left += 1
            for d in range(1, SIZE):
                if c + d >= SIZE or board[r][c + d] == opponent: break
                if board[r][c + d] == player: right += 1
            for d in range(1, SIZE):
                if r - d < 0 or board[r - d][c] == opponent: break
                if board[r - d][c] == player: up += 1
            for d in range(1, SIZE):
                if r + d >= SIZE or board[r + d][c] == opponent: break
                if board[r + d][c] == player: down += 1
            row_s = left + right
            col_s = up + down
            if row_s >= 1 and col_s >= 1:
                bonus += (LINE_SCORE.get(row_s + 1, 0) +
                          LINE_SCORE.get(col_s + 1, 0))
    return bonus

def _adv_potential(board, player, opponent, SIZE) -> float:
    total = 0.0

    def score_run(cells, left_open, right_open):
        n = len(cells)
        if n < 3: return 0.0
        mine = sum(1 for c in cells if c == player)
        if mine == 0: return 0.0
        has_gap = any(cells[k] == EMPTY for k in range(1, n - 1))
        base = LINE_SCORE.get(n, 0) * (mine / n) ** 2
        if left_open and right_open:
            base *= 1.4
        elif not left_open and not right_open:
            base *= 0.5
        if has_gap:
            base *= 0.6
        max_len = n + (1 if left_open else 0) + (1 if right_open else 0)
        if max_len <= 4: base *= 0.7
        if max_len <= 3: base *= 0.5
        return base

    def scan(get_cell):
        nonlocal total
        for i in range(SIZE):
            j = 0
            while j < SIZE:
                if get_cell(i, j) == opponent:
                    j += 1; continue
                start = j; cells = []
                while j < SIZE and get_cell(i, j) != opponent:
                    cells.append(get_cell(i, j)); j += 1
                lo = start > 0 and get_cell(i, start - 1) != opponent
                hi = j < SIZE  and get_cell(i, j)         != opponent
                total += score_run(cells, lo, hi)

    scan(lambda i, j: board[i][j])
    scan(lambda i, j: board[j][i])
    return total

def _count_threats(board, player, opponent, SIZE) -> float:
    total = 0.0

    def check(cells):
        n = len(cells)
        if n < 3: return 0.0
        mine    = sum(1 for c in cells if c == player)
        empties = sum(1 for c in cells if c == EMPTY)
        if empties == 1 and mine == n - 1:
            return LINE_SCORE.get(n, 0)
        return 0.0

    def scan(get_cell):
        nonlocal total
        for i in range(SIZE):
            run = []
            for j in range(SIZE):
                cell = get_cell(i, j)
                if cell != opponent:
                    run.append(cell)
                else:
                    total += check(run); run = []
            total += check(run)

    scan(lambda i, j: board[i][j])
    scan(lambda i, j: board[j][i])
    return total

def _tempo_bonus(board, player, opponent, is_my_turn, SIZE) -> float:
    my_thr  = _count_threats(board, player,   opponent, SIZE)
    opp_thr = _count_threats(board, opponent, player,   SIZE)
    if is_my_turn:
        return  my_thr * 0.5 - opp_thr * 0.3
    else:
        return -opp_thr * 0.5 + my_thr * 0.3

def _centrality(board, player, SIZE) -> float:
    total = 0.0
    for r in range(SIZE):
        for c in range(SIZE):
            if board[r][c] == player:
                total += min(r, SIZE - 1 - r) + min(c, SIZE - 1 - c)
    return total

def _eval_board(board, player, opponent, weights, SIZE, is_my_turn=True) -> float:
    my_s,  th_s  = _calc_scores(board,   player,   opponent, SIZE)
    my_pot       = _adv_potential(board,  player,   opponent, SIZE)
    th_pot       = _adv_potential(board,  opponent, player,   SIZE)
    my_thr       = _count_threats(board,  player,   opponent, SIZE)
    th_thr       = _count_threats(board,  opponent, player,   SIZE)
    my_cen       = _centrality(board,     player,   SIZE)
    th_cen       = _centrality(board,     opponent, SIZE)
    my_int       = _intersection_bonus(board, player,   opponent, SIZE)
    th_int       = _intersection_bonus(board, opponent, player,   SIZE)
    tempo        = _tempo_bonus(board,    player,   opponent, is_my_turn, SIZE)
    return (
        (my_s   - th_s)   * weights['completed']    +
        (my_pot - th_pot) * weights['potential']     +
        (my_thr - th_thr) * weights['threats']       +
        (my_cen - th_cen) * weights['centrality']    +
        (my_int - th_int) * weights['intersection']  +
        tempo             * weights['tempo']
    )


# ── move generation ───────────────────────────────────────────────────────────

def _get_moves(board, player, weights, SIZE, top_n=10):
    opponent = _opp(player)
    scored = []
    for r in range(SIZE):
        for c in range(SIZE):
            if board[r][c] != EMPTY: continue
            b = _copy(board); b[r][c] = player
            scored.append((_eval_board(b, player, opponent, weights, SIZE), r, c))
    scored.sort(reverse=True)
    return [(r, c) for _, r, c in scored[:top_n]]

def _ordered_moves(board, player, weights, SIZE, top_n, depth):
    moves   = _get_moves(board, player, weights, SIZE, top_n)
    killers = [m for m in _killers.get(depth, []) if board[m[0]][m[1]] == EMPTY]
    seen    = set(killers)
    return (killers + [m for m in moves if m not in seen])[:top_n + len(killers)]


# ── search ────────────────────────────────────────────────────────────────────

def _pvs(board, player, opponent, depth, alpha, beta, maximizing, weights, SIZE, top_n, t_end) -> float:
    if time.time() > t_end:
        return 0.0

    key    = _board_key(board)
    cached = _tt_lookup(key, depth, alpha, beta)
    if cached is not None:
        score, exact, _ = cached
        if exact: return score

    active = player if maximizing else opponent
    moves  = _ordered_moves(board, active, weights, SIZE, top_n, depth)

    if depth == 0 or not moves:
        v = _eval_board(board, player, opponent, weights, SIZE, maximizing)
        _tt_store(key, 0, 0, v, None)
        return v

    orig_alpha = alpha
    best_score = -INF if maximizing else INF
    best_move  = None
    first      = True

    for i, (r, c) in enumerate(moves):
        b = _copy(board); b[r][c] = active
        lmr = 0
        if i >= 3 and depth >= 3 and (r, c) not in _killers.get(depth, []):
            lmr = 1 if i < 6 else 2

        if first:
            sc = _pvs(b, player, opponent, depth - 1, alpha, beta, not maximizing, weights, SIZE, top_n, t_end)
            first = False
        else:
            if maximizing:
                sc = _pvs(b, player, opponent, depth - 1 - lmr, alpha, alpha + 1, not maximizing, weights, SIZE, top_n, t_end)
                if alpha < sc < beta:
                    sc = _pvs(b, player, opponent, depth - 1, alpha, beta, not maximizing, weights, SIZE, top_n, t_end)
            else:
                sc = _pvs(b, player, opponent, depth - 1 - lmr, beta - 1, beta, not maximizing, weights, SIZE, top_n, t_end)
                if alpha < sc < beta:
                    sc = _pvs(b, player, opponent, depth - 1, alpha, beta, not maximizing, weights, SIZE, top_n, t_end)

        if maximizing:
            if sc > best_score: best_score = sc; best_move = (r, c)
            alpha = max(alpha, best_score)
        else:
            if sc < best_score: best_score = sc; best_move = (r, c)
            beta  = min(beta,   best_score)

        if alpha >= beta:
            _add_killer(depth, (r, c))
            break

    if   best_score <= orig_alpha: flag = 2
    elif best_score >= beta:       flag = 1
    else:                          flag = 0
    _tt_store(key, depth, flag, best_score, best_move)
    return best_score

def _iterative_deepen(board, player, max_depth, top_n, weights, SIZE, time_limit=1.8):
    opponent   = _opp(player)
    prev_score = _last_score[player]
    best_move  = None
    t0         = time.time()
    t_end      = t0 + time_limit

    for depth in range(1, max_depth + 1):
        if time.time() - t0 > time_limit:
            break
        lo = prev_score - ASP_WINDOW
        hi = prev_score + ASP_WINDOW
        attempts = 0
        while True:
            attempts += 1
            candidates = _ordered_moves(board, player, weights, SIZE, top_n + 4, depth)
            best = -INF; bm = []
            for r, c in candidates:
                b = _copy(board); b[r][c] = player
                sc = _pvs(b, player, opponent, depth - 1, lo, hi, False, weights, SIZE, top_n, t_end)
                if time.time() > t_end:
                    # Abort this iteration entirely
                    _last_score[player] = prev_score
                    return best_move if best_move else candidates[0]

                if sc > best:       best = sc; bm = [(r, c)]
                elif sc == best:    bm.append((r, c))
            if best <= lo:
                lo = max(-INF, lo - ASP_WINDOW * (2 ** attempts))
                if lo <= -INF / 2: lo = -INF; hi = INF
            elif best >= hi:
                hi = min(INF, hi + ASP_WINDOW * (2 ** attempts))
                if hi >= INF / 2: lo = -INF; hi = INF
            else:
                best_move  = random.choice(bm)
                prev_score = best
                break
            if lo <= -INF and hi >= INF:
                for r, c in candidates:
                    b = _copy(board); b[r][c] = player
                    sc = _pvs(b, player, opponent, depth - 1, -INF, INF, False, weights, SIZE, top_n, t_end)
                    if time.time() > t_end:
                        _last_score[player] = prev_score
                        return best_move if best_move else candidates[0]
                    if sc > best:    best = sc; bm = [(r, c)]
                    elif sc == best: bm.append((r, c))
                best_move  = random.choice(bm)
                prev_score = best
                break

    _last_score[player] = prev_score
    return best_move

def _endgame_exact(board, player, weights, SIZE):
    remaining = sum(cell == EMPTY for row in board for cell in row)
    move = _iterative_deepen(board, player, remaining, remaining, weights, SIZE, time_limit=1.8)
    return move if move else _get_moves(board, player, weights, SIZE, 1)[0]


# ── tactical helpers ──────────────────────────────────────────────────────────

def _analyse_opponent(board, opponent, SIZE) -> dict:
    player = _opp(opponent)
    lines  = []

    def scan(get_cell, direction):
        for i in range(SIZE):
            run = []; j = 0
            while j <= SIZE:
                if j < SIZE and get_cell(i, j) == opponent:
                    run.append(j); j += 1
                else:
                    if len(run) >= 2:
                        exts = []
                        if run[0] > 0 and get_cell(i, run[0] - 1) == EMPTY:
                            exts.append((i, run[0] - 1) if direction == 'row' else (run[0] - 1, i))
                        if run[-1] < SIZE - 1 and get_cell(i, run[-1] + 1) == EMPTY:
                            exts.append((i, run[-1] + 1) if direction == 'row' else (run[-1] + 1, i))
                        lines.append({
                            'len':       len(run),
                            'dir':       direction,
                            'exts':      exts,
                            'max_score': LINE_SCORE.get(min(7, len(run) + len(exts)), 0),
                        })
                    run = []; j += 1

    scan(lambda i, j: board[i][j], 'row')
    scan(lambda i, j: board[j][i], 'col')
    lines.sort(key=lambda x: (x['len'], x['max_score']), reverse=True)

    opp_cells = [(r, c) for r in range(SIZE) for c in range(SIZE) if board[r][c] == opponent]
    my_cells  = {(r, c) for r in range(SIZE) for c in range(SIZE) if board[r][c] == player}
    mirrored  = sum(1 for r, c in opp_cells if (SIZE - 1 - r, SIZE - 1 - c) in my_cells)
    is_mirror = len(opp_cells) > 2 and mirrored / max(len(opp_cells), 1) >= 0.55

    ext_map: dict = {}
    for ln in lines:
        for cell in ln['exts']:
            ext_map.setdefault(cell, []).append(ln)
    forks = sorted(
        [{'cell': cell, 'arms': lns, 'val': sum(l['max_score'] for l in lns)}
         for cell, lns in ext_map.items() if len(lns) >= 2],
        key=lambda x: x['val'], reverse=True,
    )

    return {'lines': lines, 'top': lines[0] if lines else None,
            'is_mirror': is_mirror, 'forks': forks}

def _threat_sequence_block(board, player, opponent, threat_data, SIZE):
    lines = [l for l in threat_data['lines'] if l['len'] >= 3 and l['exts']]
    if not lines:
        return None
    best_cell = None; best_val = -1
    for r in range(SIZE):
        for c in range(SIZE):
            if board[r][c] != EMPTY: continue
            neutralised = sum(l['max_score'] for l in lines if (r, c) in l['exts'])
            b = _copy(board); b[r][c] = player
            reduction = _longest_line(board, opponent, SIZE) - _longest_line(b, opponent, SIZE)
            neutralised += reduction * 10
            if neutralised > best_val:
                best_val = neutralised; best_cell = (r, c)
    return best_cell

def _sacrifice_calc(board, player, opponent, threat_cell, SIZE) -> dict:
    bA = _copy(board)
    bA[threat_cell[0]][threat_cell[1]] = player
    myA, oppA = _calc_scores(bA, player, opponent, SIZE)
    own_moves = _get_moves(board, player, W_DEF, SIZE, 3)
    if not own_moves:
        return {'block': True, 'move': threat_cell}
    bB  = _copy(board)
    bB[own_moves[0][0]][own_moves[0][1]] = player
    bB2 = _copy(bB)
    bB2[threat_cell[0]][threat_cell[1]] = opponent
    myB, oppB = _calc_scores(bB2, player, opponent, SIZE)
    gain_block = myA - oppA
    gain_sac   = myB - oppB
    if gain_sac > gain_block:
        return {'block': False, 'move': own_moves[0], 'block_gain': gain_block, 'sac_gain': gain_sac}
    return {'block': True, 'move': threat_cell, 'block_gain': gain_block, 'sac_gain': gain_sac}

def _find_fork(board, player, SIZE):
    opponent = _opp(player)
    best = None; best_val = -INF
    for r in range(SIZE):
        for c in range(SIZE):
            if board[r][c] != EMPTY: continue
            b = _copy(board); b[r][c] = player
            rr = cc = 1
            for d in range(1, SIZE):
                if c + d < SIZE and b[r][c + d] == player: rr += 1
                else: break
            for d in range(1, SIZE):
                if c - d >= 0 and b[r][c - d] == player: rr += 1
                else: break
            for d in range(1, SIZE):
                if r + d < SIZE and b[r + d][c] == player: cc += 1
                else: break
            for d in range(1, SIZE):
                if r - d >= 0 and b[r - d][c] == player: cc += 1
                else: break
            if rr >= 2 and cc >= 2:
                val = _eval_board(b, player, opponent, W_ATK, SIZE)
                if val > best_val: best_val = val; best = (r, c)
    return best

def _mirror_break(board, player, SIZE):
    for r in range(SIZE):
        for c in range(SIZE):
            if board[r][c] != EMPTY: continue
            if board[SIZE - 1 - r][SIZE - 1 - c] != EMPTY:
                return (r, c)
    return None

def _endgame_sequence(board, player, SIZE):
    opponent = _opp(player)
    moves    = _get_moves(board, player, W_ATK, SIZE, 10)
    if not moves: return None
    for r, c in moves:
        b = _copy(board); b[r][c] = player
        rr = cc = 1
        for d in range(1, SIZE):
            if c + d < SIZE and b[r][c + d] == player: rr += 1
            else: break
        for d in range(1, SIZE):
            if c - d >= 0 and b[r][c - d] == player: rr += 1
            else: break
        for d in range(1, SIZE):
            if r + d < SIZE and b[r + d][c] == player: cc += 1
            else: break
        for d in range(1, SIZE):
            if r - d >= 0 and b[r - d][c] == player: cc += 1
            else: break
        if rr >= 3 and cc >= 3:
            return (r, c)
    best = None; best_gain = -1
    for r, c in moves:
        b = _copy(board); b[r][c] = player
        after, _ = _calc_scores(b, player, opponent, SIZE)
        now, _   = _calc_scores(board, player, opponent, SIZE)
        if after - now > best_gain:
            best_gain = after - now; best = (r, c)
    return best


# ── strategy ──────────────────────────────────────────────────────────────────

def _apex_move(board, player, SIZE) -> tuple:
    opponent = _opp(player)
    phase    = _get_phase(board, SIZE)

    if phase == 'early':
        played_book = sum(1 for br, bc in OPENING_BOOK if board[br][bc] == player)
        for br, bc in OPENING_BOOK[played_book:]:
            if board[br][bc] == EMPTY:
                return (br, bc)

    empty_count = sum(cell == EMPTY for row in board for cell in row)
    if empty_count <= 8:
        return _endgame_exact(board, player, W_ATK, SIZE)

    threat = _analyse_opponent(board, opponent, SIZE)

    if threat['top'] and threat['top']['len'] >= 5 and threat['top']['exts']:
        opp_next = LINE_SCORE.get(min(7, threat['top']['len'] + 1), 0)
        my_best  = _get_moves(board, player, W_ATK, SIZE, 1)
        if my_best:
            mb = _copy(board)
            mb[my_best[0][0]][my_best[0][1]] = player
            my_gain = (_calc_scores(mb, player, opponent, SIZE)[0] -
                       _calc_scores(board, player, opponent, SIZE)[0])
            if opp_next > my_gain:
                return threat['top']['exts'][0]

    if phase == 'early' and threat['is_mirror']:
        mb = _mirror_break(board, player, SIZE)
        if mb: return mb

    if phase != 'late':
        fork = _find_fork(board, player, SIZE)
        if fork: return fork

    if phase == 'late':
        seq = _endgame_sequence(board, player, SIZE)
        if seq: return seq

    max_depth = 5 if phase == 'late' else (4 if phase == 'mid' else 3)
    top_n     = 6 if phase == 'late' else 9
    move = _iterative_deepen(board, player, max_depth, top_n, W_ATK, SIZE)
    return move if move else _get_moves(board, player, W_ATK, SIZE, 1)[0]

def _aegis_move(board, player, SIZE) -> tuple:
    opponent = _opp(player)
    phase    = _get_phase(board, SIZE)

    empty_count = sum(cell == EMPTY for row in board for cell in row)
    if empty_count <= 8:
        return _endgame_exact(board, player, W_DEF, SIZE)

    if phase == 'early':
        mid = SIZE // 2
        if board[mid][mid] == EMPTY:
            return (mid, mid)
        for r in range(SIZE):
            for c in range(SIZE):
                if board[r][c] == opponent:
                    mr, mc = SIZE - 1 - r, SIZE - 1 - c
                    if board[mr][mc] == EMPTY:
                        return (mr, mc)

    threat = _analyse_opponent(board, opponent, SIZE)

    if threat['forks']:
        r, c = threat['forks'][0]['cell']
        if board[r][c] == EMPTY:
            return (r, c)

    if threat['top'] and threat['top']['len'] >= 4:
        seq_block = _threat_sequence_block(board, player, opponent, threat, SIZE)
        if seq_block:
            sac = _sacrifice_calc(board, player, opponent, seq_block, SIZE)
            if not sac['block']:
                return sac['move']
            if threat['top']['len'] >= 5:
                return seq_block

    my_l  = _longest_line(board, player,   SIZE)
    opp_l = _longest_line(board, opponent, SIZE)
    if opp_l >= my_l + 2:
        best_block = None; best_red = SIZE + 1
        for r in range(SIZE):
            for c in range(SIZE):
                if board[r][c] != EMPTY: continue
                b = _copy(board); b[r][c] = player
                after = _longest_line(b, opponent, SIZE)
                if after < best_red:
                    best_red = after; best_block = (r, c)
        if best_block: return best_block

    if phase == 'late' and (not threat['top'] or threat['top']['len'] < 5):
        move = _iterative_deepen(board, player, 6, 6, W_DEF, SIZE)
        return move if move else _get_moves(board, player, W_DEF, SIZE, 1)[0]

    max_depth = 6 if phase == 'late' else (5 if phase == 'mid' else 3)
    top_n     = 6 if phase == 'late' else 9
    move = _iterative_deepen(board, player, max_depth, top_n, W_DEF, SIZE)
    return move if move else _get_moves(board, player, W_DEF, SIZE, 1)[0]

def _choose_move(board, player, SIZE) -> tuple:
    if _is_first_player(board, player, SIZE):
        return _apex_move(board, player, SIZE)
    else:
        return _aegis_move(board, player, SIZE)
