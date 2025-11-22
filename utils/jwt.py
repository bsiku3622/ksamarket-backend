from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
import os

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session as SQLSession

from db.connection import get_db
from db.models import User, UserStatus  # 실제 User 모델 임포트

# JWT 설정
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "secret")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7


def create_access_token(user_id: int):
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)

    payload = {
        "sub": str(user_id),
        "iat": int(now.timestamp()),  # 발급 시간
        "exp": int(expire.timestamp()),  # 만료 시간
    }

    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


def get_current_user(request: Request, db: SQLSession = Depends(get_db)):
    auth_header = request.cookies.get("token")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")

    token = auth_header.split(" ")[1]

    payload = decode_access_token(token)
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid token")

    try:
        user_id = int(user_id)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = (
        db.query(User)
        .filter(User.id == user_id, User.status != UserStatus.DELETED)
        .first()
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.status == UserStatus.SUSPENDED:  # type: ignore
        raise HTTPException(status_code=403, detail="User is suspended")
    if user.status == UserStatus.SUSPENDED:  # type: ignore
        raise HTTPException(status_code=403, detail="Email not verified")

    return user
