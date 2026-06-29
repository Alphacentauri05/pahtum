import time
import random

TIME_LIMIT = 1.7
SIMULATION_LIMIT = 2000


def _copy(board):
    return [row[:] for row in board]


def opponent_of(p):
    """Switch between the two stones used by the server ('W' and 'B')."""
    if p in ("W", "B"):
        return "B" if p == "W" else "W"
    return "O" if p == "X" else "X"


def is_valid_move(board, r, c):
    """Cell is valid if it is on the board and currently empty ('.')."""
    n = len(board)
    return 0 <= r < n and 0 <= c < n and board[r][c] == "."


def get_moves(board):
    moves = []
    n = len(board)
    for r in range(n):
        for c in range(n):
            if is_valid_move(board, r, c):
                moves.append((r, c))
    return moves


def _generate_scoring_table(n: int) -> dict[int, int]:
    scores = {1: 0, 2: 0, 3: 3}
    for L in range(4, n + 1):
        scores[L] = 2 * scores[L - 1] + L
    return scores


def _scores_for_board(board):
    return _generate_scoring_table(len(board))


def _score_for_player(board, stone):
    """Score all horizontal and vertical runs for the given stone."""
    total = 0
    n = len(board)
    scores_for_n = _scores_for_board(board)
    # Horizontal
    for r in range(n):
        run = 0
        for c in range(n):
            if board[r][c] == stone:
                run += 1
            else:
                if run > 0:
                    total += scores_for_n.get(run, 0)
                run = 0
        if run > 0:
            total += scores_for_n.get(run, 0)
    # Vertical
    for c in range(n):
        run = 0
        for r in range(n):
            if board[r][c] == stone:
                run += 1
            else:
                if run > 0:
                    total += scores_for_n.get(run, 0)
                run = 0
        if run > 0:
            total += scores_for_n.get(run, 0)
    return total


def evaluate(board, player):
    """Heuristic value = score(player) - score(opponent) using Pah-Tum scoring."""
    opponent = opponent_of(player)
    s1 = _score_for_player(board, player)
    s2 = _score_for_player(board, opponent)
    return s1 - s2


class Node:
    def __init__(self, board, player, move=None, parent=None):
        self.board = board
        self.player = player
        self.move = move
        self.parent = parent
        self.children = []
        self.visits = 0
        self.wins = 0
        self.untried = get_moves(board)


def ucb(child, total_visits):
    if child.visits == 0:
        return 999999
    return (
        child.wins / child.visits
        + 1.4 * ((total_visits ** 0.5) / (1 + child.visits))
    )


def select(node):
    while not node.untried and node.children:
        total = node.visits
        node = max(node.children, key=lambda c: ucb(c, total))
    return node


def expand(node):
    move = node.untried.pop()
    b = _copy(node.board)
    b[move[0]][move[1]] = node.player

    child = Node(
        b,
        opponent_of(node.player),
        move,
        node,
    )

    node.children.append(child)
    return child


def simulate(board, player, root_player):
    b = _copy(board)
    p = player

    for _ in range(20):
        moves = get_moves(b)
        if not moves:
            break

        r, c = random.choice(moves)
        b[r][c] = p
        p = opponent_of(p)

    score = evaluate(b, root_player)

    if score > 0:
        return 1
    if score < 0:
        return -1
    return 0


def backprop(node, result):
    while node is not None:
        node.visits += 1
        node.wins += result
        node = node.parent


def play_move_2(board, player):
    start = time.time()
    root = Node(_copy(board), player)

    simulations = 0

    while time.time() - start < TIME_LIMIT:
        node = root
        node = select(node)

        if node.untried:
            node = expand(node)

        result = simulate(node.board, node.player, player)
        backprop(node, result)

        simulations += 1
        if simulations > SIMULATION_LIMIT:
            break

    if not root.children:
        moves = get_moves(board)
        return random.choice(moves)

    best = max(root.children, key=lambda c: c.visits)
    return best.move


# =======================
# 🔥 THIS IS THE API ENTRY
# =======================

def bot_move(game_state: dict) -> dict:
    """
    This function receives the JSON input exactly as provided
    and returns JSON with row and col.
    """

    board = game_state["board"]
    player = game_state["your_stone"]

    row, col = play_move_2(board, player)

    return {
        "row": row,
        "col": col
    }