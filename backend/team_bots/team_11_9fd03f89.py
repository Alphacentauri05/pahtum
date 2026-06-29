import time

def bot_move(game_state: dict) -> dict:
    """
    Negamax with Alpha-Beta Pruning + Custom Evaluation
    Depth: 3 (safe within 2 second time limit)
    """

    board = game_state["board"]
    SIZE = game_state["board_size"]
    player = game_state.get("your_stone") or game_state.get("current_player") or "W"
    CENTER = SIZE // 2

    SEQUENCE_POINTS = [0, 0, 0, 3, 10, 25, 56, 119]
    SEARCH_DEPTH = 3

    # ── Board utilities ──────────────────────────────────────────────────────

    def _copy_board(b):
        return [row[:] for row in b]

    def _get_valid_moves(b):
        return [
            (r, c)
            for r in range(SIZE)
            for c in range(SIZE)
            if b[r][c] == "."
        ]

    def _center_distance(r, c):
        return abs(r - CENTER) + abs(c - CENTER)

    def _opponent(p):
        if p in ("W", "B"):
            return "B" if p == "W" else "W"
        return "O" if p == "X" else "X"

    def _is_board_full(b):
        return all(b[r][c] != "." for r in range(SIZE) for c in range(SIZE))

    # ── Sequence scoring ─────────────────────────────────────────────────────

    def _count_sequences(b, p):
        total = 0
        for r in range(SIZE):                        # horizontal
            count = 0
            for c in range(SIZE):
                if b[r][c] == p:
                    count += 1
                else:
                    if count >= 3:
                        total += SEQUENCE_POINTS[min(count, len(SEQUENCE_POINTS) - 1)]
                    count = 0
            if count >= 3:
                total += SEQUENCE_POINTS[min(count, len(SEQUENCE_POINTS) - 1)]
        for c in range(SIZE):                        # vertical
            count = 0
            for r in range(SIZE):
                if b[r][c] == p:
                    count += 1
                else:
                    if count >= 3:
                        total += SEQUENCE_POINTS[min(count, len(SEQUENCE_POINTS) - 1)]
                    count = 0
            if count >= 3:
                total += SEQUENCE_POINTS[min(count, len(SEQUENCE_POINTS) - 1)]
        return total

    def _count_run_lengths(b, p):
        runs = {}
        for r in range(SIZE):                        # horizontal
            count = 0
            for c in range(SIZE):
                if b[r][c] == p:
                    count += 1
                else:
                    if count > 0:
                        runs[count] = runs.get(count, 0) + 1
                    count = 0
            if count > 0:
                runs[count] = runs.get(count, 0) + 1
        for c in range(SIZE):                        # vertical
            count = 0
            for r in range(SIZE):
                if b[r][c] == p:
                    count += 1
                else:
                    if count > 0:
                        runs[count] = runs.get(count, 0) + 1
                    count = 0
            if count > 0:
                runs[count] = runs.get(count, 0) + 1
        return runs

    # ── Evaluation ───────────────────────────────────────────────────────────

    def _evaluate(b, p):
        opp = _opponent(p)
        score_diff = _count_sequences(b, p) - _count_sequences(b, opp)

        my_runs  = _count_run_lengths(b, p)
        opp_runs = _count_run_lengths(b, opp)
        potential = my_runs.get(2, 0) * 2  + my_runs.get(1, 0)  * 0.5
        threat    = opp_runs.get(2, 0) * 2 + opp_runs.get(1, 0) * 0.5

        center_bonus = 0.0
        for r in range(SIZE):
            for c in range(SIZE):
                if b[r][c] == p:
                    center_bonus += (6 - _center_distance(r, c)) * 0.1
                elif b[r][c] == opp:
                    center_bonus -= (6 - _center_distance(r, c)) * 0.1

        return score_diff + potential - threat + center_bonus

    # ── Move ordering ────────────────────────────────────────────────────────

    def _order_moves(b, moves, p):
        opp = _opponent(p)
        scored = []
        for (r, c) in moves:
            tmp = _copy_board(b)
            tmp[r][c] = p
            diff = _count_sequences(tmp, p) - _count_sequences(tmp, opp)
            scored.append((diff - _center_distance(r, c) * 0.01, r, c))
        scored.sort(reverse=True)
        return [(r, c) for (_, r, c) in scored]

    # ── Negamax + Alpha-Beta ─────────────────────────────────────────────────

    def _negamax(b, depth, alpha, beta, p, start_time, time_limit=1.8):
        if time.time() - start_time > time_limit:
            return _evaluate(b, p)
        if _is_board_full(b) or depth == 0:
            return _evaluate(b, p)

        moves = _get_valid_moves(b)
        if not moves:
            return _evaluate(b, p)

        moves = _order_moves(b, moves, p)
        opp   = _opponent(p)
        best  = float("-inf")

        for (r, c) in moves:
            tmp = _copy_board(b)
            tmp[r][c] = p
            score = -_negamax(tmp, depth - 1, -beta, -alpha, opp, start_time, time_limit)
            if score > best:
                best = score
            if best > alpha:
                alpha = best
            if alpha >= beta:
                break

        return best

    # ── Root search ──────────────────────────────────────────────────────────

    start_time = time.time()

    moves = _get_valid_moves(board)
    if not moves:
        return {"row": 0, "col": 0}

    # First move: take center
    empty_count = sum(b == "." for row in board for b in row)
    if empty_count == SIZE * SIZE:
        return {"row": CENTER, "col": CENTER}

    ordered  = _order_moves(board, moves, player)
    opp      = _opponent(player)
    best_score = float("-inf")
    best_move  = ordered[0]

    for (r, c) in ordered:
        if time.time() - start_time > 1.7:
            break
        tmp = _copy_board(board)
        tmp[r][c] = player
        score = -_negamax(
            tmp, SEARCH_DEPTH - 1,
            float("-inf"), float("inf"),
            opp, start_time, time_limit=1.8
        )
        if score > best_score:
            best_score = score
            best_move  = (r, c)

    return {"row": best_move[0], "col": best_move[1]}