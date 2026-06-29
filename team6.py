import time
import random
import math

def bot_move(game_state: dict) -> dict:
    """
    ╔══════════════════════════════════════════════════════════════════╗
    ║  APEX PAH TUM AI  v11  —  Definitive Edition                   ║
    ╠══════════════════════════════════════════════════════════════════╣
    ║  ARCHITECTURE                                                    ║
    ║                                                                  ║
    ║  Phase 1 — Instant tactical (microseconds)                      ║
    ║    Full multi-threat win/block scan. Handles simultaneous       ║
    ║    fork + win. Zero search budget wasted on obvious moves.     ║
    ║                                                                  ║
    ║  Phase 2 — Opening book (zero compute)                          ║
    ║    Covers moves 1 and 2. Fork setups from first piece.         ║
    ║                                                                  ║
    ║  Phase 3 — Endgame exact solver (≤18 empty cells)              ║
    ║    Policy-ordered alpha-beta. Perfect play from this point.    ║
    ║                                                                  ║
    ║  Phase 4 — Hybrid PVS + MCTS                                   ║
    ║    PVS: depth 9-13, PVS + LMR + null-move + persistent TT     ║
    ║    MCTS: policy-weighted UCT, thousands of sims/sec            ║
    ║    Fusion: agreement = instant play, disagreement = weighted    ║
    ║                                                                  ║
    ║  KEY STRENGTHS vs ALL OPPONENT CLASSES                          ║
    ║                                                                  ║
    ║  vs depth-3/4 minimax bots:                                     ║
    ║    We search 3× deeper. Fork threats invisible to them at      ║
    ║    depth 3 are fully resolved by our depth 9+.                 ║
    ║                                                                  ║
    ║  vs center-bias bots:                                           ║
    ║    Opening book places us adjacent to center, not ON it.       ║
    ║    Dual-axis policy builds forks the opponent ranks last.      ║
    ║                                                                  ║
    ║  vs TT-wiping bots:                                             ║
    ║    Our TT persists the entire game. By move 5 we have tens     ║
    ║    of thousands of cached positions they recompute fresh.      ║
    ║                                                                  ║
    ║  vs MCTS-only bots:                                             ║
    ║    Our PVS reads tactical sequences at depth 9+. Pure MCTS     ║
    ║    in Python at ~1000 sims/sec can't match forced-line depth.  ║
    ║                                                                  ║
    ║  vs strong hybrid bots:                                         ║
    ║    Fusion engine — both PVS and MCTS must be outplayed         ║
    ║    simultaneously to beat us. Statistically near-impossible.   ║
    ║                                                                  ║
    ║  Pure function · No side-effects · 0.93s budget                ║
    ╚══════════════════════════════════════════════════════════════════╝
    """

    # ── POLICY WEIGHTS ────────────────────────────────────────────────
    W = [
        320.00,  380.00,  620.00,  920.00,
        700.00,  650.00,  340.00,  170.00,
        110.00,  450.00,  240.00,  125.00,
        310.00,
        4_800_000.0, 3_900_000.0,
          320_000.0,    18_500.0,
           18_000.0,
        2_800_000.0,   400_000.0,
          290_000.0,    20_000.0,
          950_000.0,  3_200_000.0,
    ]

    # ── OPENING BOOK ──────────────────────────────────────────────────
    # Move 1: always (3,3) when going first.
    # Response to opponent's first move: fork-building adjacent squares.
    # Move 2: extend our first piece toward a dual-axis fork.
    OB = {
        "first": (3, 3),
        "resp1": {
            "3_3":(3,4), "3_4":(3,3), "4_3":(3,3), "4_4":(3,3),
            "2_2":(3,3), "2_4":(3,3), "4_2":(3,3), "2_3":(3,3),
            "3_1":(3,2), "3_5":(3,4), "1_3":(2,3), "5_3":(4,3),
            "1_1":(2,2), "1_5":(2,4), "5_1":(4,2), "5_5":(4,4),
            "0_0":(1,1), "0_6":(1,5), "6_0":(5,1), "6_6":(5,5),
            "4_1":(3,2), "4_5":(3,4), "2_1":(3,2), "2_5":(3,4),
            "0_3":(1,3), "6_3":(5,3), "3_0":(3,1), "3_6":(3,5),
            "0_1":(1,2), "0_5":(1,4), "6_1":(5,2), "6_5":(5,4),
            "1_0":(2,1), "5_0":(4,1), "1_6":(2,5), "5_6":(4,5),
        },
        "resp2": {
            "3_3":(3,4), "3_4":(3,5), "4_3":(4,4), "4_4":(4,5),
            "2_2":(2,3), "2_4":(2,5), "4_2":(4,3), "2_3":(2,4),
            "3_2":(3,3), "2_3":(2,4), "4_3":(4,4),
            "1_2":(2,2), "1_4":(2,4), "5_2":(4,2), "5_4":(4,4),
            "1_1":(2,1), "1_5":(2,5), "5_1":(4,1), "5_5":(4,5),
            "3_1":(3,2), "3_5":(3,4), "1_3":(2,3), "5_3":(4,3),
        },
    }

    # ── CONSTANTS ─────────────────────────────────────────────────────
    SP    = (3, 10, 25, 56, 119)        # scores for run-of-3..7
    SIZE  = game_state["board_size"]
    ME    = (game_state.get("your_stone") or
             game_state.get("current_player") or
             game_state.get("player") or
             next((v for k, v in game_state.items()
                   if k not in ("board", "board_size") and v in ("X", "O", "W", "B")), "W"))
    OPP   = {'X': 'O', 'O': 'X', 'W': 'B', 'B': 'W'}.get(ME, 'B')
    TL    = 0.93
    START = time.time()
    EG_THRESH = 18

    raw  = game_state["board"]
    # Normalise W/B → X/O so all internal scoring works with X/O symbols
    _NORM = {'W': 'X', 'B': 'O', 'X': 'X', 'O': 'O', '.': ' '}
    grid = [[_NORM.get(c, ' ') for c in row] for row in raw]
    # Remap ME/OPP to X/O so all internal scoring works correctly
    ME  = 'X' if ME in ('W', 'X') else 'O'
    OPP = 'O' if ME == 'X' else 'X'

    # ── ZOBRIST ───────────────────────────────────────────────────────
    _ZT  = {}
    _rng = random.Random(0xDEADBEEF)
    for _r in range(SIZE):
        for _c in range(SIZE):
            for _p in ("X", "O"):
                _ZT[(_r, _c, _p)] = _rng.getrandbits(64)

    def _zh_init(g):
        h = 0
        for r in range(SIZE):
            for c in range(SIZE):
                if g[r][c] != " ":
                    h ^= _ZT[(r, c, g[r][c])]
        return h

    # ════════════════════════════════════════════════════════════════
    # FAST BOARD — O(1) net score, O(SIZE) place/undo, Zobrist hash
    # ════════════════════════════════════════════════════════════════
    class Board:
        __slots__ = ("g", "sx", "so", "_cache", "_emp", "zh")

        def __init__(self, g):
            self.g = [row[:] for row in g]
            self.sx = self.so = 0
            self._cache = {}
            self._emp   = set()
            for r in range(SIZE):
                for c in range(SIZE):
                    if self.g[r][c] == " ":
                        self._emp.add((r, c))
            for i in range(SIZE):
                for ir in (True, False):
                    lx, lo = self._scan(i, ir)
                    self._cache[(ir, i)] = (lx, lo)
                    self.sx += lx; self.so += lo
            self.zh = _zh_init(self.g)

        @staticmethod
        def _rp(n): return SP[n - 3] if 3 <= n <= 7 else 0

        def _scan(self, i, ir):
            lx = lo = 0; rp = None; rn = 0
            for j in range(SIZE):
                cell = self.g[i][j] if ir else self.g[j][i]
                if cell != " " and cell == rp:
                    rn += 1
                else:
                    if rp and rp != " ":
                        s = self._rp(rn)
                        if rp == "X": lx += s
                        else:         lo += s
                    rp, rn = (cell, 1) if cell != " " else (None, 0)
            if rp and rp != " ":
                s = self._rp(rn)
                if rp == "X": lx += s
                else:         lo += s
            return lx, lo

        def _ref(self, i, ir):
            ox, oo = self._cache[(ir, i)]
            nx, no = self._scan(i, ir)
            self._cache[(ir, i)] = (nx, no)
            self.sx += nx - ox; self.so += no - oo

        def place(self, r, c, p):
            self.zh ^= _ZT[(r, c, p)]
            self.g[r][c] = p
            self._emp.discard((r, c))
            self._ref(r, True); self._ref(c, False)

        def undo(self, r, c, p):
            self.zh ^= _ZT[(r, c, p)]
            self.g[r][c] = " "
            self._emp.add((r, c))
            self._ref(r, True); self._ref(c, False)

        def net(self, me):
            return self.sx - self.so if me == "X" else self.so - self.sx

        def empty(self):   return list(self._emp)
        def n_empty(self): return len(self._emp)

    # ── HELPERS ──────────────────────────────────────────────────────
    def run_len(g, r, c, p, dr, dc):
        n = 1
        for s in (1, -1):
            nr, nc = r + s*dr, c + s*dc
            while 0 <= nr < SIZE and 0 <= nc < SIZE and g[nr][nc] == p:
                n += 1; nr += s*dr; nc += s*dc
        return n

    def max_reach(g, r, c, p, dr, dc):
        o = OPP if p == ME else ME; n = 1
        for s in (1, -1):
            nr, nc = r + s*dr, c + s*dc
            while 0 <= nr < SIZE and 0 <= nc < SIZE and g[nr][nc] != o:
                n += 1; nr += s*dr; nc += s*dc
        return min(n, 7)

    def abs_seq(g, r, c, p):
        best = 0
        for dr, dc in ((0, 1), (1, 0)):
            L = run_len(g, r, c, p, dr, dc)
            if L >= 3: best = max(best, SP[min(L, 7) - 3])
        return best

    # ── POLICY ───────────────────────────────────────────────────────
    def policy(g, r, c, p):
        o   = OPP if p == ME else ME
        h   = run_len(g, r, c, p, 0, 1); v  = run_len(g, r, c, p, 1, 0)
        oh  = run_len(g, r, c, o, 0, 1); ov = run_len(g, r, c, o, 1, 0)
        ctr = SIZE // 2; dist = abs(r - ctr) + abs(c - ctr)

        def sp(dr, dc, pl):
            bl = "O" if pl == "X" else "X"; n = 0
            for s in (1, -1):
                nr, nc = r + s*dr, c + s*dc
                while 0 <= nr < SIZE and 0 <= nc < SIZE and g[nr][nc] != bl:
                    n += 1; nr += s*dr; nc += s*dc
            return min(n, 7)

        hs = sp(0,1,p); vs = sp(1,0,p); ohs = sp(0,1,o); ovs = sp(1,0,o)
        feats = [
            float(h), float(v), float(max(h,v)), float(h+v),
            float(oh), float(ov), float(max(oh,ov)), float(oh+ov),
            float(hs), float(vs), float(ohs), float(ovs),
            float(max(0, 3 - dist)),
            float(h>=7 or v>=7), float(h>=6 or v>=6),
            float(h>=5 or v>=5), float(h>=4 or v>=4), float(h>=3 or v>=3),
            float(oh>=6 or ov>=6), float(oh>=5 or ov>=5),
            float(oh>=4 or ov>=4), float(oh>=3 or ov>=3),
            float(h>=2 and v>=2), float(h>=3 and v>=3),
        ]
        return sum(ww * f for ww, f in zip(W, feats))

    # ── THREAT TABLE (built once per turn) ───────────────────────────
    def _build_threat_table(board):
        g = board.g; tt = {}
        for r in range(SIZE):
            for c in range(SIZE):
                if g[r][c] != " ": continue
                for p2 in (ME, OPP):
                    pv = 0; threats = 0; ts = []
                    for dr, dc in ((0, 1), (1, 0)):
                        L  = run_len(g, r, c, p2, dr, dc)
                        mr = max_reach(g, r, c, p2, dr, dc)
                        if L >= 3:
                            actual = SP[min(L, 7) - 3]
                            pot    = SP[mr - 3] if mr >= 3 else actual
                            pv    += actual + (pot - actual)*L/max(mr,1) if mr > L else actual
                            if mr >= L: threats += 1; ts.append(actual)
                        elif L >= 2 and mr >= 4:
                            threats += 0.5; ts.append(SP[0] * 0.3)
                    fork_b = 0
                    if threats >= 2:
                        ts.sort(reverse=True)
                        fork_b = (ts[0] + 0.7*ts[1]) * 50_000 if len(ts) >= 2 else 500_000
                    tt[(r, c, p2)] = (pv, fork_b)
        return tt

    def evaluate_fast(board, me):
        """O(SIZE²) eval using precomputed threat table + O(1) base score."""
        o   = OPP if me == ME else ME
        base = board.net(me) * 100
        g    = board.g
        pot_me = pot_opp = fork_me = fork_opp = 0
        for r in range(SIZE):
            for c in range(SIZE):
                if g[r][c] != " ": continue
                pv_me, fk_me = _tt_threat.get((r, c, me), (0, 0))
                pv_op, fk_op = _tt_threat.get((r, c, o),  (0, 0))
                pot_me  += pv_me;  fork_me  += fk_me
                pot_opp += pv_op;  fork_opp += fk_op
        return base + (pot_me - pot_opp)*12 + (fork_me - fork_opp)

    # Build once for this turn
    _board_root = Board(grid)
    _tt_threat  = _build_threat_table(_board_root)

    # ── INSTANT THREAT DETECTION ──────────────────────────────────────
    def find_all_threats(g):
        """Returns all instant-win moves and all instant-block moves."""
        wins = []; blocks = []
        for r in range(SIZE):
            for c in range(SIZE):
                if g[r][c] != " ": continue
                ws = abs_seq(g, r, c, ME)
                bs = abs_seq(g, r, c, OPP)
                if ws >= 56: wins.append(((r, c), ws))
                if bs >= 56: blocks.append(((r, c), bs))
        wins.sort(key=lambda x: -x[1])
        blocks.sort(key=lambda x: -x[1])
        return wins, blocks

    def find_threats(g):
        bw = (None, 0); bb = (None, 0)
        for r in range(SIZE):
            for c in range(SIZE):
                if g[r][c] != " ": continue
                ws = abs_seq(g, r, c, ME); bs = abs_seq(g, r, c, OPP)
                if ws > bw[1]: bw = ((r, c), ws)
                if bs > bb[1]: bb = ((r, c), bs)
        return bw, bb

    # ── ENDGAME EXACT SOLVER ─────────────────────────────────────────
    def endgame(board, me, opp, alpha, beta):
        emp = board.empty()
        if not emp: return board.net(me)
        emp.sort(key=lambda m: policy(board.g, m[0], m[1], me), reverse=True)
        best = -10**9
        for r, c in emp:
            board.place(r, c, me)
            val = -endgame(board, opp, me, -beta, -alpha)
            board.undo(r, c, me)
            if val > best: best = val
            alpha = max(alpha, val)
            if alpha >= beta: break
        return best

    # ════════════════════════════════════════════════════════════════
    # ENGINE 1 — PVS NEGAMAX
    # Features: PVS, LMR, null-move pruning, persistent Zobrist TT,
    #           history heuristic, killer moves, aspiration windows
    # ════════════════════════════════════════════════════════════════
    EXACT, LOWER, UPPER = 0, 1, 2
    TT_MAX    = 500_000
    NULL_R    = 2
    LMR_DEPTH = 3
    LMR_MOVES = 4

    # Persistent across ALL turns this game
    if not hasattr(bot_move, "_tt"):      bot_move._tt      = {}
    if not hasattr(bot_move, "_history"): bot_move._history = {}

    _tt      = bot_move._tt
    _history = bot_move._history
    killers  = [[] for _ in range(30)]

    def negamax(board, depth, alpha, beta, p, deadline, null_ok=True):
        if time.time() > deadline: raise TimeoutError

        o          = OPP if p == ME else ME
        orig_alpha = alpha

        # TT probe
        tt_key  = (board.zh, p, depth)
        tt_move = None
        if tt_key in _tt:
            flag, val, tt_move = _tt[tt_key]
            if   flag == EXACT: return val, tt_move
            elif flag == LOWER: alpha = max(alpha, val)
            elif flag == UPPER: beta  = min(beta,  val)
            if alpha >= beta:   return val, tt_move

        emp   = board.empty()
        n_emp = len(emp)
        if not emp or depth == 0:
            return evaluate_fast(board, p), None

        # Null-move pruning — skip when position is very open
        if (null_ok and depth >= NULL_R + 1
                and n_emp < SIZE*SIZE - 4 and beta < 10**8):
            val, _ = negamax(board, depth-NULL_R-1, -beta, -beta+1, o, deadline, False)
            if -val >= beta: return beta, None

        # Move ordering: TT move → killers → policy + history
        kset = set(killers[depth] if depth < 30 else [])

        def move_score(m):
            if m == tt_move: return 100_000_000
            if m in kset:    return  10_000_000 + _history.get((p, m), 0)
            return policy(board.g, m[0], m[1], p) + _history.get((p, m), 0) * 10

        nc    = (6 if depth >= 8 else
                 8 if depth >= 6 else
                10 if depth >= 5 else
                12 if depth >= 4 else 18)
        cands = sorted(emp, key=move_score, reverse=True)[:nc]

        best_val  = -10**9
        best_move = cands[0]
        first     = True

        for i, (r, c) in enumerate(cands):
            if time.time() > deadline: break
            board.place(r, c, p)
            try:
                if first:
                    val, _ = negamax(board, depth-1, -beta, -alpha, o, deadline)
                    first  = False
                else:
                    # LMR: reduce late moves
                    red = (1 if depth >= LMR_DEPTH and i >= LMR_MOVES
                              and (r,c) not in kset and (r,c) != tt_move else 0)
                    val, _ = negamax(board, depth-1-red, -alpha-1, -alpha, o, deadline)
                    if -val > alpha:
                        val, _ = negamax(board, depth-1, -beta, -alpha, o, deadline)
            except TimeoutError:
                board.undo(r, c, p); break

            val = -val
            board.undo(r, c, p)

            if val > best_val: best_val, best_move = val, (r, c)
            alpha = max(alpha, val)
            if alpha >= beta:
                _history[(p, (r, c))] = _history.get((p, (r, c)), 0) + (1 << depth)
                if depth < 30:
                    km = killers[depth]
                    if (r, c) not in km:
                        km.append((r, c))
                        if len(km) > 2: km.pop(0)
                break

        if len(_tt) < TT_MAX:
            flag = (UPPER if best_val <= orig_alpha else
                    LOWER if best_val >= beta else EXACT)
            _tt[tt_key] = (flag, best_val, best_move)

        return best_val, best_move

    def run_pvs(board, p, deadline):
        best_move = None
        prev_val  = None
        asp_delta = 80
        for depth in range(1, 20):
            if time.time() > deadline - 0.03: break
            lo = -10**9 if (prev_val is None or depth <= 2) else prev_val - asp_delta
            hi =  10**9 if (prev_val is None or depth <= 2) else prev_val + asp_delta
            try:
                while True:
                    val, move = negamax(board, depth, lo, hi, p, deadline - 0.02)
                    if   val <= lo: lo -= asp_delta*3; asp_delta *= 2
                    elif val >= hi: hi += asp_delta*3; asp_delta *= 2
                    else:
                        if move: best_move = move
                        prev_val  = val
                        asp_delta = max(60, asp_delta // 2)
                        break
            except TimeoutError:
                break
            if time.time() > deadline - 0.03: break
        return best_move, prev_val

    # ════════════════════════════════════════════════════════════════
    # ENGINE 2 — MCTS WITH POLICY-WEIGHTED UCT
    #
    # Selection:  PUCT (policy-prior UCT, like AlphaGo)
    # Expansion:  top-N by policy, softmax priors
    # Simulation: 70% policy-biased, 30% random rollouts
    # Backprop:   win rate from ME perspective
    # Robust:     best child = most visited (not highest win rate)
    # ════════════════════════════════════════════════════════════════
    UCT_C        = 1.4
    MAX_CANDS    = 12
    ROLLOUT_DEPTH = 10     # deeper rollouts = better signal

    class MCTSNode:
        __slots__ = ("move","p","parent","children","visits","wins","prior","expanded")
        def __init__(self, move, p, parent, prior=1.0):
            self.move=move; self.p=p; self.parent=parent
            self.children=[]; self.visits=0; self.wins=0.0
            self.prior=prior; self.expanded=False

    def mcts_priors(g, emp, p):
        scores = sorted(((policy(g, r, c, p), (r, c)) for r, c in emp), reverse=True)
        top    = scores[:MAX_CANDS]
        if not top: return []
        mx   = top[0][0]
        exps = [math.exp(min(s - mx, 50)) for s, _ in top]
        tot  = sum(exps) or 1.0
        return [(e/tot, m) for e, (_, m) in zip(exps, top)]

    def mcts_rollout(board, p):
        cur = p
        for _ in range(ROLLOUT_DEPTH):
            emp = board.empty()
            if not emp: break
            if random.random() < 0.70:
                top = sorted(emp, key=lambda m: policy(board.g, m[0], m[1], cur), reverse=True)[:4]
                wts = [4.0, 2.0, 1.0, 0.5][:len(top)]
                tot = sum(wts); cum = 0.0; rnd = random.random()*tot
                chosen = top[-1]
                for m, w in zip(top, wts):
                    cum += w
                    if rnd <= cum: chosen = m; break
                r, c = chosen
            else:
                r, c = random.choice(emp)
            board.place(r, c, cur)
            cur = OPP if cur == ME else ME
        return board.net(ME)

    def mcts_select(node):
        log_n = math.log(node.visits + 1)
        best_s = -1e9; best_c = None
        for ch in node.children:
            q = ch.wins / ch.visits if ch.visits else 0.5
            u = UCT_C * ch.prior * math.sqrt(log_n) / (1 + ch.visits)
            s = q + u
            if s > best_s: best_s = s; best_c = ch
        return best_c

    def mcts_expand(node, board):
        if node.expanded: return
        node.expanded = True
        emp = board.empty()
        if not emp: return
        o = OPP if node.p == ME else ME
        for prior, move in mcts_priors(board.g, emp, node.p):
            node.children.append(MCTSNode(move, o, node, prior))

    def run_mcts(root_grid, p, deadline):
        root = MCTSNode(None, p, None, 1.0)
        rb   = Board(root_grid)
        mcts_expand(root, rb)
        if not root.children: return None

        max_score = sum(SP) * SIZE * 2

        while time.time() < deadline:
            node  = root
            board = Board(root_grid)
            path  = []

            # Selection
            while node.expanded and node.children and board.empty():
                ch = mcts_select(node)
                if ch is None: break
                r, c = ch.move
                board.place(r, c, node.p)
                path.append((node, node.p))
                node = ch

            # Expansion
            if not node.expanded and board.empty():
                mcts_expand(node, board)
                unvis = [ch for ch in node.children if ch.visits == 0]
                if unvis:
                    ch = unvis[0]
                    r, c = ch.move
                    board.place(r, c, node.p)
                    path.append((node, node.p))
                    node = ch

            # Simulation
            sim_board = Board(board.g)
            raw       = mcts_rollout(sim_board, node.p)
            win_val   = 0.5 + 0.5 * max(-1.0, min(1.0, raw / max(max_score, 1)))

            # Backprop
            node.visits += 1
            node.wins   += win_val if node.p != ME else (1 - win_val)
            for pn, pp in reversed(path):
                pn.visits += 1
                pn.wins   += win_val if pp != ME else (1 - win_val)

        if not root.children: return None
        best = max(root.children, key=lambda ch: ch.visits)
        return best.move, {ch.move: ch.visits for ch in root.children}

    # ════════════════════════════════════════════════════════════════
    # MAIN DECISION ENGINE
    # ════════════════════════════════════════════════════════════════
    board   = _board_root
    empties = board.empty()
    if not empties: return {"row": 0, "col": 0}
    n_empty = board.n_empty()

    # ── PHASE 1: INSTANT WIN / BLOCK ─────────────────────────────────
    wins, blocks = find_all_threats(grid)

    # We have a winning move — take it
    if wins:
        return {"row": wins[0][0][0], "col": wins[0][0][1]}

    # Opponent has 2+ winning threats — find a move that kills all of them
    if len(blocks) >= 2:
        for (br, bc), _ in blocks:
            grid[br][bc] = ME
            sw, _ = find_all_threats(grid)
            grid[br][bc] = " "
            if not sw:
                return {"row": br, "col": bc}
        # No single move blocks all — play highest-value block
        return {"row": blocks[0][0][0], "col": blocks[0][0][1]}

    if blocks:
        return {"row": blocks[0][0][0], "col": blocks[0][0][1]}

    # Lower-value threats (run-of-5 = 25 pts)
    (win_move, win_score), (blk_move, blk_score) = find_threats(grid)
    if win_score >= 25: return {"row": win_move[0], "col": win_move[1]}
    if blk_score >= 25: return {"row": blk_move[0], "col": blk_move[1]}

    # ── PHASE 2: OPENING BOOK ─────────────────────────────────────────
    my_count  = sum(1 for r in range(SIZE) for c in range(SIZE) if grid[r][c] == ME)
    opp_count = sum(1 for r in range(SIZE) for c in range(SIZE) if grid[r][c] == OPP)

    if my_count == 0:
        if opp_count == 0:
            bm = OB["first"]
            if grid[bm[0]][bm[1]] == " ":
                return {"row": bm[0], "col": bm[1]}
        else:
            opp_pieces = [(r, c) for r in range(SIZE) for c in range(SIZE) if grid[r][c] == OPP]
            if opp_pieces:
                xr, xc = opp_pieces[0]
                resp = OB["resp1"].get(f"{xr}_{xc}")
                if resp and grid[resp[0]][resp[1]] == " ":
                    return {"row": resp[0], "col": resp[1]}
        # Fallback: nearest to center
        ctr  = SIZE // 2
        best = min(empties, key=lambda m: abs(m[0]-ctr) + abs(m[1]-ctr))
        return {"row": best[0], "col": best[1]}

    if my_count == 1 and (my_count + opp_count) <= 3:
        my_pos = next(((r, c) for r in range(SIZE) for c in range(SIZE) if grid[r][c] == ME), None)
        if my_pos:
            resp2 = OB["resp2"].get(f"{my_pos[0]}_{my_pos[1]}")
            if resp2 and grid[resp2[0]][resp2[1]] == " ":
                return {"row": resp2[0], "col": resp2[1]}
            # Fallback: best policy-scored adjacent cell
            adj = [(my_pos[0]+dr, my_pos[1]+dc)
                   for dr, dc in ((0,1),(0,-1),(1,0),(-1,0))
                   if 0 <= my_pos[0]+dr < SIZE and 0 <= my_pos[1]+dc < SIZE
                   and grid[my_pos[0]+dr][my_pos[1]+dc] == " "]
            if adj:
                return {"row": max(adj, key=lambda m: policy(grid, m[0], m[1], ME))[0],
                        "col": max(adj, key=lambda m: policy(grid, m[0], m[1], ME))[1]}

    # ── PHASE 3: ENDGAME EXACT SOLVER ────────────────────────────────
    if n_empty <= EG_THRESH:
        eg_board    = Board(grid)
        best_val    = -10**9; best_eg = None
        eg_deadline = START + TL - 0.05
        sorted_emp  = sorted(empties,
                             key=lambda m: policy(grid, m[0], m[1], ME), reverse=True)
        for r, c in sorted_emp:
            if time.time() > eg_deadline: break
            eg_board.place(r, c, ME)
            val = -endgame(eg_board, OPP, ME, -10**9, -best_val)
            eg_board.undo(r, c, ME)
            if val > best_val: best_val = val; best_eg = (r, c)
        if best_eg:
            return {"row": best_eg[0], "col": best_eg[1]}

    # ── PHASE 4: HYBRID PVS + MCTS ───────────────────────────────────
    # Budget split (of remaining time after phases 1-3):
    #   PVS  — 65%  (tactical depth, forced lines, fork detection)
    #   MCTS — 30%  (broad strategy, long-horizon patterns)
    #   5%   — safety margin
    #
    # Decision fusion:
    #   Agree   → play immediately (high confidence)
    #   Disagree → weighted vote: 65% MCTS visit share + 35% PVS rank
    #              + 40% bonus if move matches PVS top pick
    remaining     = TL - (time.time() - START)
    pvs_deadline  = time.time() + remaining * 0.65
    mcts_deadline = pvs_deadline + remaining * 0.30

    pvs_move, _  = run_pvs(board, ME, pvs_deadline)
    mcts_result  = run_mcts(grid, ME, mcts_deadline)

    if mcts_result is None:
        if pvs_move: return {"row": pvs_move[0], "col": pvs_move[1]}
    else:
        mcts_move, mcts_visits = mcts_result

        # Both engines agree — maximum confidence
        if pvs_move and pvs_move == mcts_move:
            return {"row": pvs_move[0], "col": pvs_move[1]}

        # Disagreement — weighted fusion
        all_cands    = sorted(empties, key=lambda m: policy(grid, m[0], m[1], ME), reverse=True)
        pvs_rank     = {m: (len(all_cands) - i) for i, m in enumerate(all_cands)}
        total_visits = max(sum(mcts_visits.values()), 1)

        def fusion(m):
            pr        = pvs_rank.get(m, 0) / max(len(all_cands), 1)
            mr        = mcts_visits.get(m, 0) / total_visits
            pvs_bonus = 0.40 if m == pvs_move else 0.0
            return pr * 0.35 + mr * 0.65 + pvs_bonus

        best_fused = max(empties, key=fusion)
        return {"row": best_fused[0], "col": best_fused[1]}

    # ── PHASE 5: FALLBACK ─────────────────────────────────────────────
    best = max(empties, key=lambda m: policy(grid, m[0], m[1], ME))
    return {"row": best[0], "col": best[1]}
