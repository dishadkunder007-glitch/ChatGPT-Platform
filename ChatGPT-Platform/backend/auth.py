import os
import uuid
import datetime
import jwt
import bcrypt
import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from database import get_db, User

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "chatgpt-platform-super-secret-key-change-in-production-2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not hashed_password:
        return False
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def create_access_token(data: dict, expires_delta: datetime.timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.datetime.utcnow() + expires_delta
    else:
        expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def generate_reset_token() -> str:
    return str(uuid.uuid4()).replace("-", "") + str(uuid.uuid4()).replace("-", "")


async def verify_google_token(credential: str) -> dict:
    """
    Verifies a Google ID token (from Google One-Tap / GSI) using Google's tokeninfo endpoint.
    Returns payload with email, name, picture, sub.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://oauth2.googleapis.com/tokeninfo",
                params={"id_token": credential},
                timeout=10.0
            )
        if response.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid Google token")

        payload = response.json()

        # Validate audience if GOOGLE_CLIENT_ID is set
        if GOOGLE_CLIENT_ID and payload.get("aud") != GOOGLE_CLIENT_ID:
            raise HTTPException(status_code=401, detail="Google token audience mismatch")

        return payload
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Google token verification failed: {str(e)}")


def get_or_create_guest_user(db: Session) -> User:
    guest = db.query(User).filter(User.email == "guest@chatgpt-platform.local").first()
    if not guest:
        guest = User(
            email="guest@chatgpt-platform.local",
            name="Guest User",
            is_guest=True,
            is_active=True
        )
        db.add(guest)
        db.commit()
        db.refresh(guest)
    return guest


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    if not token:
        return get_or_create_guest_user(db)

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            return get_or_create_guest_user(db)
    except Exception:
        return get_or_create_guest_user(db)

    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        return get_or_create_guest_user(db)
    return user


def require_authenticated_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """Strict version — raises 401 if not authenticated (for sensitive endpoints)."""
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user
