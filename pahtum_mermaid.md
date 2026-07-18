# Pah-Tum Tournament Dashboard — Mermaid Diagrams

---

## 1. 🏗️ Overall System Architecture

```mermaid
graph TB
    subgraph Browser["🌐 Browser (localhost:5173)"]
        UI["React App\n(Vite + TailwindCSS)"]
    end

    subgraph Frontend["📦 Frontend Pages"]
        D["Dashboard"]
        T["Tournaments"]
        B["Bots"]
        PG["Play Game"]
        LB["Leaderboard"]
        PL["Players"]
        MH["Match History"]
    end

    subgraph Backend["⚙️ FastAPI Backend (localhost:8000)"]
        API["FastAPI App\n(main.py)"]
        TR["routes/tournaments.py"]
        MR["routes/matches.py"]
        BR["routes/bots.py"]
        GR["routes/game.py"]
        LR["routes/leaderboard.py"]
        GE["game_engine.py"]
        DB["database.py\n(in-memory dict)"]
    end

    subgraph Storage["💾 Persistence"]
        JSON["db.json"]
    end

    subgraph Bots["🤖 Team Bots"]
        TB["team_bots/\nteam1_xxx.py\nteam7_xxx.py\n...team13_xxx.py"]
        CORE["pahtum_core.py\n(shared helper lib)"]
    end

    UI --> |"/api/* via Vite proxy"| API
    API --> TR & MR & BR & GR & LR
    TR & MR & BR & GR & LR --> DB
    DB --> |"save on every write"| JSON
    JSON --> |"load on startup"| DB
    GR --> GE
    BR --> |"importlib.import_module()"| TB
    TB --> |"imports"| CORE
```

---

## 2. 🔄 End-to-End Request Flow (Bot vs Bot Match)

```mermaid
sequenceDiagram
    participant Browser
    participant Vite as Vite Proxy
    participant FastAPI
    participant GameEngine as game_engine.py
    participant Importlib as importlib
    participant BotA as Team A bot_move()
    participant BotB as Team B bot_move()
    participant DB as database.py / db.json

    Browser->>Vite: POST /api/game/bot-vs-bot
    Vite->>FastAPI: forwards request
    FastAPI->>DB: fetch match + bot details
    FastAPI->>GameEngine: create PahTumGame(board_size)

    loop Until board is full
        GameEngine->>Importlib: import_module("team_bots.team7_xxx")
        Importlib->>BotA: bot_move(game_state)
        Note over BotA: asyncio.wait_for(timeout=5s)
        BotA-->>GameEngine: {row: 3, col: 4}
        GameEngine->>GameEngine: apply_move() + score_board()

        GameEngine->>Importlib: import_module("team_bots.team3_xxx")
        Importlib->>BotB: bot_move(game_state)
        BotB-->>GameEngine: {row: 1, col: 2}
        GameEngine->>GameEngine: apply_move() + score_board()
    end

    GameEngine-->>FastAPI: final scores + winner
    FastAPI->>DB: update match result + bot stats
    DB->>DB: save to db.json
    FastAPI-->>Browser: {winner, white_score, black_score, moves[], final_board}
    Browser->>Browser: Animate moves on GameBoard.jsx
```

---

## 3. 🤖 Bot Upload & Registration Lifecycle

```mermaid
flowchart TD
    A["Admin uploads team7.py\nvia Bots page UI"] --> B["POST /api/bots/upload-local\nmultipart form data"]
    B --> C{"Is it a .py file?"}
    C -- No --> ERR1["❌ 400 Error: Only .py allowed"]
    C -- Yes --> D["Generate safe slug:\nteam7_21fbab24.py"]
    D --> E["Save file to\nbackend/team_bots/"]
    E --> F["importlib.import_module\n('team_bots.team7_21fbab24')"]
    F --> G{"Can import\n+ find bot_move()?"}
    G -- No --> ERR2["❌ 400 Error: Import failed"]
    G -- Yes --> H["Insert bot record in DB\n{name, module, entry_function,\nwins:0, losses:0, status:'registered'}"]
    H --> I["✅ Bot registered!"]
    I --> J["Admin clicks 'Test Bot'"]
    J --> K["POST /api/bots/{id}/test"]
    K --> L["Call bot_move(SAMPLE_STATE)\nwith 5s asyncio timeout"]
    L --> M{"Response has\nrow + col?"}
    M -- Yes --> N["✅ status: 'online'"]
    M -- Timeout --> O["⏰ status: 'timeout'"]
    M -- Error --> P["💥 status: 'error'"]
    M -- Bad format --> Q["⚠️ status: 'invalid_response'"]
```

---

## 4. ⚔️ Knockout Tournament Format

```mermaid
flowchart TD
    A["Create Tournament\nformat: knockout"] --> B["Register Players & Bots"]
    B --> C["POST /generate-bracket"]
    C --> D["Shuffle participants\nPad with BYEs to power of 2"]
    D --> E["Round 1 Matches Created\nin DB with status: scheduled"]
    E --> F{"BYE match?"}
    F -- Yes --> G["Auto-complete:\nwinner = white"]
    F -- No --> H["Admin plays match\n(bot vs bot simulation)"]
    G & H --> I["PUT /matches/{id}/result"]
    I --> J["Update match: completed\nUpdate bot/player stats"]
    J --> K{"All matches in\nthis round done?"}
    K -- No --> H
    K -- Yes --> L["_advance_bracket()\ncollect round winners"]
    L --> M{"Is this the\nfinal round?"}
    M -- No --> N["Create next round matches\n(winners paired up)"]
    N --> H
    M -- Yes --> O["✅ Tournament status: completed"]
```

---

## 5. 🏆 Group Stage Tournament Format

```mermaid
flowchart TD
    A["Create Tournament\nformat: group_stage"] --> B["Register Teams"]
    B --> C["POST /generate-groups\nPhase 1 begins"]
    C --> D["Random split:\nGroup A | Group B"]
    D --> E["Round-robin matches\nwithin each group"]
    E --> F["Play all Phase 1 matches\n(bot simulations)"]
    F --> G["Standings calculated:\npoints = 3W + 1D + 0L\ntiebreak: score diff"]
    G --> H["POST /advance-to-phase2\nTop N from each group qualify"]
    H --> I["🪟 BOT SWAP WINDOW OPENS\nTeams can upload improved bot\nPOST /swap-bot"]
    I --> J["POST /start-phase2\nSwap window closes"]
    J --> K["Phase 2: Round-robin\namong all qualifiers\n(cross-group finals)"]
    K --> L["Play all Phase 2 matches"]
    L --> M["Final Standings\nPhase 2 leaderboard"]
    M --> N["✅ Tournament completed"]
```

---

## 6. 🎮 Game Engine Scoring Logic

```mermaid
flowchart LR
    A["score_board(board, player)"] --> B["Scan all rows\nhorizontally"]
    A --> C["Scan all columns\nvertically"]
    B --> D["Count contiguous\nrun of player stones"]
    C --> D
    D --> E["score_line(run_length)"]
    E --> F{"run length?"}
    F -- "1 or 2" --> G["0 points"]
    F -- "3" --> H["3 points"]
    F -- "4+" --> I["2 × score(L-1) + L\nrecursive formula"]
    G & H & I --> J["Sum all runs\n= total score"]
```

---

## 7. 🗄️ Database Schema (db.json collections)

```mermaid
erDiagram
    PLAYERS {
        string id
        string name
        string email
        int wins
        int losses
        int draws
        int matches_played
        int total_score
    }

    BOTS {
        string id
        string name
        string owner
        string type
        string module
        string entry_function
        string api_url
        string status
        int wins
        int losses
        int draws
    }

    TOURNAMENTS {
        string id
        string name
        string format
        string status
        int board_size
        int max_players
        list registered_players
        list rounds
        int phase
        string phase2_status
        list phase2_participants
        object groups
    }

    MATCHES {
        string id
        string tournament_id
        string player_white_id
        string player_black_id
        int board_size
        int round_num
        int match_index
        string group
        int phase
        string status
        int white_score
        int black_score
        string winner
        list moves
        list final_board
    }

    TOURNAMENTS ||--o{ MATCHES : "has"
    PLAYERS ||--o{ MATCHES : "plays in"
    BOTS ||--o{ MATCHES : "plays in"
    TOURNAMENTS ||--o{ PLAYERS : "registers"
    TOURNAMENTS ||--o{ BOTS : "registers"
```

---

## 8. 🔁 Frontend Page Flow (React Router)

```mermaid
graph LR
    SB["Sidebar\nNavigation"] --> DA["/ Dashboard\nStats overview"]
    SB --> TO["/ Tournaments\nList + Create"]
    TO --> TD["/tournaments/:id\nDetail + Bracket\n+ Play Matches"]
    SB --> BO["/bots\nUpload + Test + Manage"]
    SB --> PL["/players\nRegister + Stats"]
    SB --> PG["/play\nInteractive Game\nPvP / PvBot / BvB"]
    SB --> LB["/leaderboard\nGlobal Rankings"]
    SB --> MH["/matches\nMatch History"]

    PG --> GB["GameBoard.jsx\n(renders N×N grid)"]
    PG --> WP["WinPredictor.jsx\n(score probability bar)"]
    TD --> GB
```
