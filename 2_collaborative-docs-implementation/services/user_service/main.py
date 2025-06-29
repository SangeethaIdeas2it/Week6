# main.py
import os
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from passlib.context import CryptContext
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr, constr
from typing import Optional
import aioredis
import logging
import uvicorn
from datetime import datetime, timedelta
from security import (
    is_password_complex,
    SecurityHeadersMiddleware,
    log_security_event,
    AccountLockoutManager
)

# --- Configuration ---
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:password@localhost:5432/collabdocs")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# --- Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# --- Database Setup ---
Base = declarative_base()
engine = create_async_engine(DATABASE_URL, echo=False, future=True)
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

# --- Redis Setup ---
redis = None

# --- Password Hashing ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# --- JWT Token Utilities ---
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict):
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = data.copy()
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def store_refresh_token(user_id: int, token: str):
    await redis.set(f"refresh_token:{user_id}", token, ex=REFRESH_TOKEN_EXPIRE_DAYS*24*3600)

async def get_stored_refresh_token(user_id: int):
    return await redis.get(f"refresh_token:{user_id}")

async def delete_refresh_token(user_id: int):
    await redis.delete(f"refresh_token:{user_id}")

# --- Models ---
from sqlalchemy import Column, Integer, String, DateTime

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

# --- Pydantic Schemas ---
class UserCreate(BaseModel):
    email: EmailStr
    password: constr(min_length=8)
    full_name: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserProfile(BaseModel):
    id: int
    email: EmailStr
    full_name: Optional[str] = None
    created_at: datetime

class UserUpdate(BaseModel):
    full_name: Optional[str] = None

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenRefresh(BaseModel):
    refresh_token: str

# --- FastAPI App Setup ---
app = FastAPI(title="User Service", version="1.0.0")

app.add_middleware(SecurityHeadersMiddleware)

# CORS: In production, set allow_origins to trusted domains only
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-frontend-domain.com"],  # Update for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Dependency ---
async def get_db():
    async with async_session() as session:
        yield session

# --- Auth Dependency ---
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = await db.get(User, user_id)
    if user is None:
        raise credentials_exception
    return user

# --- Error Handling ---
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": {"code": "INTERNAL_SERVER_ERROR", "message": str(exc)}}
    )

# --- Endpoints ---
lockout_manager = None

@app.on_event("startup")
async def startup():
    global redis, lockout_manager
    redis = await aioredis.from_url(REDIS_URL, decode_responses=True)
    lockout_manager = AccountLockoutManager(redis)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("User Service started.")

@app.on_event("shutdown")
async def shutdown():
    await redis.close()
    logger.info("User Service shutdown.")

@app.post("/auth/register", response_model=UserProfile)
async def register(user: UserCreate, db: AsyncSession = Depends(get_db), request: Request = None):
    if not is_password_complex(user.password):
        log_security_event("weak_password_register", user=user.email, ip=request.client.host if request else None)
        raise HTTPException(status_code=400, detail="Password does not meet complexity requirements.")
    existing = await db.execute(
        User.__table__.select().where(User.email == user.email)
    )
    if existing.scalar():
        log_security_event("register_email_exists", user=user.email, ip=request.client.host if request else None)
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed = get_password_hash(user.password)
    new_user = User(email=user.email, hashed_password=hashed, full_name=user.full_name)
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    log_security_event("register_success", user=user.email, ip=request.client.host if request else None)
    return UserProfile.from_orm(new_user)

@app.post("/auth/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db), request: Request = None):
    email = form_data.username
    if await lockout_manager.is_locked(email):
        log_security_event("login_locked_out", user=email, ip=request.client.host if request else None)
        raise HTTPException(status_code=403, detail="Account locked due to too many failed attempts. Try again later.")
    result = await db.execute(User.__table__.select().where(User.email == email))
    user = result.scalar()
    if not user or not verify_password(form_data.password, user.hashed_password):
        attempts = await lockout_manager.record_failed_attempt(email)
        log_security_event("login_failed", user=email, ip=request.client.host if request else None)
        if attempts >= lockout_manager.max_attempts:
            log_security_event("login_account_locked", user=email, ip=request.client.host if request else None)
            raise HTTPException(status_code=403, detail="Account locked due to too many failed attempts. Try again later.")
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    await lockout_manager.reset_attempts(email)
    access_token = create_access_token({"sub": user.id})
    refresh_token = create_refresh_token({"sub": user.id})
    await store_refresh_token(user.id, refresh_token)
    log_security_event("login_success", user=email, ip=request.client.host if request else None)
    return Token(access_token=access_token, refresh_token=refresh_token)

@app.get("/auth/me", response_model=UserProfile)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserProfile.from_orm(current_user)

@app.put("/auth/profile", response_model=UserProfile)
async def update_profile(update: UserUpdate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    if update.full_name:
        current_user.full_name = update.full_name
    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)
    return UserProfile.from_orm(current_user)

@app.post("/auth/refresh", response_model=Token)
async def refresh_token(data: TokenRefresh, db: AsyncSession = Depends(get_db)):
    try:
        payload = jwt.decode(data.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        stored = await get_stored_refresh_token(user_id)
        if stored.decode() != data.refresh_token:
            raise HTTPException(status_code=401, detail="Refresh token mismatch")
        user = await db.get(User, user_id)
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        access_token = create_access_token({"sub": user.id})
        refresh_token = create_refresh_token({"sub": user.id})
        await store_refresh_token(user.id, refresh_token)
        return Token(access_token=access_token, refresh_token=refresh_token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

@app.post("/auth/logout")
async def logout(current_user: User = Depends(get_current_user)):
    await delete_refresh_token(current_user.id)
    return {"success": True, "message": "Logged out"}

@app.get("/health")
async def health():
    return {"status": "ok"}

# --- Security: Rate Limiting Middleware (Simple Example) ---
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response as StarletteResponse

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_requests: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    async def dispatch(self, request: StarletteRequest, call_next):
        client_ip = request.client.host
        key = f"rl:{client_ip}"
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, self.window_seconds)
        if count > self.max_requests:
            return StarletteResponse(
                content="Rate limit exceeded",
                status_code=429
            )
        return await call_next(request)

app.add_middleware(RateLimitMiddleware)

# --- Input Sanitization Example ---
def sanitize_input(value: str) -> str:
    # Simple sanitization, extend as needed
    return value.replace("<", "&lt;").replace(">", "&gt;")

# --- Run the app ---
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8003, reload=True)

