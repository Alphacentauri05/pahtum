# PahTum AI Competition Platform
## System Architecture v2

---

# Vision

PahTum is no longer only a tournament dashboard.

The goal is to evolve it into a complete AI Competition Platform where multiple users can upload AI bots, test them, register them for tournaments and compete securely.

The architecture must be modular so that future games besides PahTum can be supported.

---

# Overall Architecture

```mermaid
flowchart TB

A[Browser]

subgraph Frontend
B[React + Vite + Tailwind]
C[Authentication]
D[Dashboard]
E[Bot Management]
F[Tournament Pages]
G[Bot Testing Arena]
H[Leaderboard]
I[Profile]
end

subgraph Backend
J[FastAPI]
K[Authentication Service]
L[Bot Service]
M[Tournament Service]
N[Game Service]
O[Admin Service]
P[Notification Service]
end

subgraph Core Engine
Q[Bot Loader]
R[Game Engine]
S[Tournament Engine]
T[Scoring Engine]
U[Scheduler Future]
end

subgraph Database
V[(CouchDB)]
end

A --> B

B --> J

J --> K
J --> L
J --> M
J --> N
J --> O
J --> P

L --> Q
N --> R
M --> S
R --> T

K --> V
L --> V
M --> V
N --> V
O --> V
P --> V

Q --> V
S --> V
```

---

# Backend Folder Structure

```text
backend/

config/

auth/

routes/

services/

engines/

database/

storage/

uploads/

utils/

models/

main.py
```

---

# Frontend Folder Structure

```text
frontend/src

pages/

components/

layouts/

api/

hooks/

context/

assets/

styles/
```

---

# CouchDB Collections

```mermaid
erDiagram

USER ||--o{ BOT : owns

USER ||--o{ TOURNAMENT_REGISTRATION : registers

BOT ||--o{ BOT_VERSION : contains

BOT ||--o{ BOT_TEST : tested

TOURNAMENT ||--o{ MATCH : contains

MATCH ||--|| BOT : white

MATCH ||--|| BOT : black

USER {
string id
string username
string email
string password_hash
string role
datetime created_at
}

BOT {
string id
string owner_id
string name
string description
boolean active
}

BOT_VERSION {
string id
string bot_id
string file_path
datetime uploaded_at
}

BOT_TEST {
string id
string bot_id
string opponent
string result
}

TOURNAMENT {
string id
string name
string format
string status
}

MATCH {
string id
string white_bot
string black_bot
string winner
}
```

---

# Authentication Flow

```mermaid
sequenceDiagram

User->>Frontend: Login

Frontend->>Backend: POST /login

Backend->>CouchDB: Verify User

CouchDB-->>Backend: User

Backend-->>Frontend: JWT

Frontend->>Frontend: Store JWT

Frontend->>Backend: Future Requests

Backend->>Backend: Verify JWT
```

---

# Bot Upload Flow

```mermaid
flowchart TD

A[Choose Python File]

B[Validate]

C[Store Metadata]

D[Save File]

E[Create Bot Version]

F[Test Import]

G[Test bot_move]

H[Save Bot]

I[Ready]

A-->B

B-->C

C-->D

D-->E

E-->F

F-->G

G-->H

H-->I
```

---

# Bot Testing Flow

```mermaid
flowchart TD

A[Choose Bot]

B[Choose Opponent]

C[Run Game Engine]

D[Execute Both Bots]

E[Store Result]

F[Statistics]

G[Register]

A-->B

B-->C

C-->D

D-->E

E-->F

F-->G
```

---

# Tournament Flow

```mermaid
flowchart TD

Create Tournament

↓

Open Registration

↓

Users Register One Bot

↓

Registration Closed

↓

Bracket Generated

↓

Matches Scheduled

↓

Bot Execution

↓

Results Stored

↓

Leaderboard Updated

↓

Tournament Ends
```

---

# Admin Flow

```mermaid
flowchart TD

Admin Login

↓

Dashboard

↓

Create Tournament

↓

Manage Users

↓

Manage Bots

↓

Monitor Matches

↓

View Logs

↓

Platform Settings
```

---

# User Dashboard

The dashboard should contain

• Profile

• Statistics

• Notifications

• Active Tournament

• My Bots

• Recent Matches

• Bot Performance

• Registered Tournament

• Quick Actions

---

# Bot Management

Each user can own multiple bots.

Example

User

├── Minimax

├── AlphaBeta

├── MCTS

├── Experimental

└── Final

Only ONE bot may be registered per tournament.

Users may freely test all bots before registration.

---

# Security Rules

Users

✔ Upload bots

✔ Test bots

✔ Register tournaments

✔ View their own bots

Users cannot

✘ View another user's source code

✘ Download another user's bots

✘ Edit another user's bots

Admins

✔ Manage platform

✔ Manage tournaments

✔ Manage users

✔ Monitor logs

---

# Core Engine

These components remain backend-only.

Game Engine

Tournament Engine

Scoring Engine

Bot Loader

Scheduler

They must never be directly accessible from frontend.

---

# Database Rules

Use CouchDB.

Do NOT use db.json.

Read connection information from environment variables.

COUCHDB_URL

COUCHDB_USERNAME

COUCHDB_PASSWORD

COUCHDB_DATABASE

---

# Phase 1

Authentication

Role Based Access

CouchDB

Modern Dashboard

Multiple Bots

Bot Testing Arena

Tournament Registration

Admin Dashboard

Secure Bot Storage

---

# Phase 2

Automatic Match Scheduling

Automatic Tournament Progression

Realtime Updates

WebSockets

Rating System

Analytics

Multiple Games

Spectator Mode

Cloud Deployment

---

# Development Rules

Never rewrite working code unnecessarily.

Reuse existing Game Engine.

Reuse existing Tournament Engine.

Reuse existing Bot Loader.

Only refactor where needed.

Always maintain a runnable application.

Think like a production software architect.
