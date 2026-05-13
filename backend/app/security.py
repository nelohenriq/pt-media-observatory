"""Security utilities for PT Media Observatory."""

import os
from datetime import datetime, timedelta
from typing import Optional

from passlib.context import CryptContext
from jose import JWTError, jwt
from pydantic import BaseSettings, EmailStr

# Password hashing context using Argon2
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# JWT settings
class Settings(BaseSettings):
    secret_key: str = os.getenv("JWT_SECRET", "super-secret-key-change-me")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    @property
    def access_token_expire(self) -> timedelta:
        return timedelta(minutes=self.access_token_expire_minutes)

    class Config:
        env_file = ".env"

settings = Settings()

# Password hashing utilities
def get_password_hash(password: str) -> str:
    """Hash a password using Argon2."""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)

# JWT token utilities
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or settings.access_token_expire)
    to_encode.update({"exp": expire})
    try:
        encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    except JWTError:
        raise RuntimeError("JWT encoding failed")
    return encoded_jwt

def decode_access_token(token: str) -> dict:
    """Decode a JWT token and return its payload."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload
    except JWTError as e:
        raise RuntimeError(f"JWT decoding error: {e}")

# FastAPI dependencies (placeholder for router usage)
def get_current_user(token: str = OAuth2PasswordRequestForm(...)) -> dict:
    """Dependency to get current user from token."""
    payload = decode_access_token(token)
    return payload  # In practice, fetch user from DB using payload["sub"]