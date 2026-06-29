import random

EMPTY = "."

def bot_move(game_state: dict) -> dict:
    board = [row[:] for row in game_state["board"]]
    n = game_state["board_size"]

    me = (game_state.get("your_stone")
          or game_state.get("current_player")
          or game_state.get("player")
          or "W")
    opp = {'X': 'O', 'O': 'X', 'W': 'B', 'B': 'W'}.get(me, 'B')

    total_moves = sum(cell != EMPTY for row in board for cell in row)
    directions = [(0,1),(1,0),(1,1),(1,-1)]
    center = n // 2

    # Dynamic weights
    if total_moves <= 4:
        W_WIN = 100000
        W_BLOCK_WIN = 90000
        W_MAKE4 = 17000
        W_BLOCK4 = 12000
        W_MAKE3 = 5500
        W_BLOCK3 = 700
        W_INTERSECTION = 8000
        W_CENTER = 90
    elif total_moves <= 14:
        W_WIN = 100000
        W_BLOCK_WIN = 90000
        W_MAKE4 = 17000
        W_BLOCK4 = 12000
        W_MAKE3 = 4500
        W_BLOCK3 = 2000
        W_INTERSECTION = 7000
        W_CENTER = 50
    else:
        W_WIN = 100000
        W_BLOCK_WIN = 95000
        W_MAKE4 = 20000
        W_BLOCK4 = 16000
        W_MAKE3 = 3000
        W_BLOCK3 = 3500
        W_INTERSECTION = 4000
        W_CENTER = 15

    def analyze_move(b, r, c, p):
        max_len = 0
        lines = 0

        for dr, dc in directions:
            count = 1

            i = 1
            while True:
                nr = r + dr*i
                nc = c + dc*i
                if 0 <= nr < n and 0 <= nc < n and b[nr][nc] == p:
                    count += 1
                    i += 1
                else:
                    break

            i = 1
            while True:
                nr = r - dr*i
                nc = c - dc*i
                if 0 <= nr < n and 0 <= nc < n and b[nr][nc] == p:
                    count += 1
                    i += 1
                else:
                    break

            if count > max_len:
                max_len = count

            if count >= 2:
                lines += 1

        return max_len, lines

    def opponent_threat_after_move(r, c):
        board[r][c] = me
        worst = 0

        for rr in range(n):
            for cc in range(n):
                if board[rr][cc] != EMPTY:
                    continue

                board[rr][cc] = opp
                opp_len, opp_lines = analyze_move(board, rr, cc, opp)
                board[rr][cc] = EMPTY

                if opp_len >= 4:
                    worst = max(worst, 8000)

                if opp_lines >= 2:
                    worst = max(worst, 5000)

        board[r][c] = EMPTY
        return worst

    best_score = float("-inf")
    best_moves = []

    for r in range(n):
        for c in range(n):
            if board[r][c] != EMPTY:
                continue

            score = 0

            # Offensive
            board[r][c] = me
            my_len, my_lines = analyze_move(board, r, c, me)
            board[r][c] = EMPTY

            if my_len >= 5:
                return {"row": r, "col": c}

            if my_len == 4:
                score += W_MAKE4
            elif my_len == 3:
                score += W_MAKE3

            if my_lines >= 2:
                score += W_INTERSECTION * my_lines

            # Defensive
            board[r][c] = opp
            opp_len, opp_lines = analyze_move(board, r, c, opp)
            board[r][c] = EMPTY

            if opp_len >= 5:
                return {"row": r, "col": c}

            if opp_len == 4:
                score += W_BLOCK4
            elif opp_len == 3:
                score += W_BLOCK3

            # Center bonus
            dist = abs(r - center) + abs(c - center)
            score += max(0, W_CENTER - dist * 5)

            # Cluster bonus
            friendly_neighbors = 0
            for dr in [-1,0,1]:
                for dc in [-1,0,1]:
                    if dr == 0 and dc == 0:
                        continue
                    nr = r + dr
                    nc = c + dc
                    if 0 <= nr < n and 0 <= nc < n and board[nr][nc] == me:
                        friendly_neighbors += 1

            score += friendly_neighbors * 220

            # Trap prevention
            score -= opponent_threat_after_move(r, c)

            if score > best_score:
                best_score = score
                best_moves = [(r,c)]
            elif score == best_score:
                best_moves.append((r,c))

    if best_moves:
        r, c = random.choice(best_moves)
        return {"row": r, "col": c}

    for r in range(n):
        for c in range(n):
            if board[r][c] == EMPTY:
                return {"row": r, "col": c}

    return {"row": 0, "col": 0}