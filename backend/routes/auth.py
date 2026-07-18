from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
import auth
from models import UserCreate, UserResponse, Token, Role
from database import find_one, insert_one
from config import settings

router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.post("/signup", response_model=UserResponse)
async def signup(user: UserCreate):
    existing_user = await find_one("users", {"username": user.username})
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")
        
    existing_email = await find_one("users", {"email": user.email})
    if existing_email:
        raise HTTPException(status_code=400, detail="Email already registered")
        
    user_dict = {
        "username": user.username,
        "name": user.username, # Fallback name to username
        "avatar_color": "#8b5cf6", # Default purple avatar
        "email": user.email,
        "password_hash": auth.get_password_hash(user.password),
        "role": Role.USER
    }
    
    new_user = await insert_one("users", user_dict)
    return new_user

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await find_one("users", {"$or": [{"username": form_data.username}, {"email": form_data.username}]})
    if not user or not auth.verify_password(form_data.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user["username"], "role": user["role"]}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: dict = Depends(auth.get_current_user)):
    return current_user
