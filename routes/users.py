from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import or_
from db.models import *
from db.connection import get_db
from sqlalchemy.orm import Session as SQLSession
from argon2 import PasswordHasher

from responses.auth_responses import USER_NOT_FOUND
from utils.jwt import get_current_user


router = APIRouter()

ph = PasswordHasher()


@router.post("/", response_model=UserResponse)
async def create_user(data: UserCreate, db: SQLSession = Depends(get_db)):
    try:
        if len(data.password) < 8:
            raise HTTPException(
                status_code=400, detail="Password mus be at least 8 characters long"
            )
        if data.email.split("@")[-1] != "ksa.hs.kr":
            raise HTTPException(
                status_code=400, detail="Email must be a ksa.hs.kr address"
            )
        existing_user = (
            db.query(User)
            .filter(
                or_(
                    User.email == data.email,
                )
            )
            .first()
        )
        if existing_user:
            raise HTTPException(status_code=400, detail="User already exists")

        new_user = User(
            email=data.email,
            password=ph.hash(data.password),
            username=data.username,
        )
        db.add(new_user)
        db.commit()
        return Response(status_code=201)
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/me", response_model=UserResponse)
async def get_my_userdata(request: Request, db: SQLSession = Depends(get_db)):
    return get_current_user(request, db)


@router.patch("/me")
async def patch_me(data: UserPatch, request: Request, db: SQLSession = Depends(get_db)):
    try:
        user = get_current_user(request, db)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(user, field, value)
        db.commit()
        db.refresh(user)
        return user
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/me")
async def delete_me(request: Request, db: SQLSession = Depends(get_db)):
    try:
        user = get_current_user(request, db)
        user.status = UserStatus.DELETED  # type: ignore
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{id}", response_model=UserResponse)
async def get_user_by_id(id: int, db: SQLSession = Depends(get_db)):
    user = (
        db.query(User)
        .filter(
            User.id == id,
            User.status != UserStatus.DELETED,
        )
        .first()
    )
    if not user:
        raise USER_NOT_FOUND
    return user


@router.get("/by-email/{email}", response_model=UserResponse)
async def get_user_by_email(email: str, db: SQLSession = Depends(get_db)):
    user = (
        db.query(User)
        .filter(
            User.email == email,
            User.status != UserStatus.DELETED,
        )
        .first()
    )
    if not user:
        raise USER_NOT_FOUND
    return user
