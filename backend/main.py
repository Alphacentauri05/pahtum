"""
Pah-Tum Tournament Dashboard — FastAPI Backend
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import connect_db, close_db
from routes import tournaments, players, matches, game, leaderboard, bots, player_api, auth


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    yield
    await close_db()


app = FastAPI(
    title="Pah-Tum Tournament API",
    description="Backend for the Pah-Tum board game tournament dashboard",
    version="1.0.0",
    lifespan=lifespan,
)

import os

# CORS — specific origins via environment variables
frontend_url_env = os.getenv("FRONTEND_URL", "http://localhost:5173")
origins = [origin.strip() for origin in frontend_url_env.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount route modules
app.include_router(tournaments.router)
app.include_router(players.router)
app.include_router(matches.router)
app.include_router(game.router)
app.include_router(leaderboard.router)
app.include_router(bots.router)
app.include_router(player_api.router)
app.include_router(auth.router)


@app.get("/")
async def root():
    return {"message": "Pah-Tum Tournament API is running 🎮"}
