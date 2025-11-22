from datetime import datetime, timedelta, timezone
from fastapi import (
    APIRouter,
    Depends,
    Request,
    Response,
    HTTPException,
    BackgroundTasks,
)
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from sqlalchemy import or_
from db.connection import get_db
from db.models import (
    TokenCreate,
    UserStatus,
    User,
    VerificationEmailCreate,
)
from sqlalchemy.orm import Session as SQLSession

from responses.auth_responses import (
    EMAIL_ALREADY_VERIFIED,
    INVALID_PASSWORD,
    USER_IS_PENDING,
    USER_IS_SUSPENDED,
    USER_NOT_FOUND,
)

from os import getenv
import smtplib
from email.message import EmailMessage
import secrets
import string

from utils.jwt import get_current_user

router = APIRouter()

ph = PasswordHasher()

email_verification_tokens = {}


def random_string(length=16):
    return "".join(
        secrets.choice(string.ascii_letters + string.digits) for _ in range(length)
    )


def send_verification_email(id: int, token: str, email):
    html_content = f"""
        <html>
        <body>
            <h1>크사장터에 오신것을 환영합니다</h1>
            <p>이메일을 확인하려면 아래 링크를 클릭해주세요!</p>
            <a href="http://localhost:8080/auth/email-verifications?id={id}&token={token}">이메일 인증하기</a>
            <p>만약 당신의 이메일로 인증 요청을 보낸적이 없다면, 이 이메일을 무시하십시오.</p>
            <p>이 링크는 1시간 이후 만료됩니다.</p>
        </body>
        </html>
    """

    msg = EmailMessage()
    msg["Subject"] = "서비스 이메일 인증"
    msg["From"] = "크사장터 <no-reply@zevoers.dev>"
    msg["To"] = email
    msg.add_alternative(html_content, subtype="html")

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(getenv("EMAIL_ID", ""), getenv("EMAIL_PW", ""))
        server.send_message(msg)


@router.post("/email-verifications")
def create_email_verifications(
    data: VerificationEmailCreate,
    db: SQLSession = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    try:
        user = (
            db.query(User)
            .filter(
                User.email == data.email,
                User.status != UserStatus.DELETED,
            )
            .first()
        )
        if not user:
            raise USER_NOT_FOUND
        if user.status == UserStatus.SUSPENDED:  # type: ignore
            raise USER_IS_SUSPENDED
        if user.status == UserStatus.ACTIVE:  # type: ignore
            raise EMAIL_ALREADY_VERIFIED

        token = random_string(48) + str(int(datetime.now().timestamp()) * 1000000)

        email_verification_tokens[data.id] = {
            "token": token,
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        background_tasks.add_task(send_verification_email, data.id, token, data.email)
        return {"message": "Verification email sent successfully"}
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/email-verifications")
def check_email_vefications(id: int, token: str, db: SQLSession = Depends(get_db)):
    try:
        data = email_verification_tokens.get(id)
        if not data:
            raise HTTPException(
                status_code=400, detail="Unvalid email verification token"
            )
        if data["token"] != token:
            raise HTTPException(
                status_code=400, detail="Unvalid email verification token"
            )
        if data["expires_at"] < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=400, detail="Email verification token expired"
            )

        user = (
            db.query(User)
            .filter(User.id == id, User.status != UserStatus.DELETED)
            .first()
        )
        if not user:  # type: ignore
            raise USER_NOT_FOUND
        if user.status == UserStatus.SUSPENDED:  # type: ignore
            raise USER_IS_SUSPENDED
        if user.status == UserStatus.ACTIVE:  # type: ignore
            raise EMAIL_ALREADY_VERIFIED

        user.status = UserStatus.ACTIVE  # type: ignore
        db.commit()

        del email_verification_tokens[id]

        return {"message": "Email verified successfully"}
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/token", description="Login and create JWT token")
def create_token(data: TokenCreate, db: SQLSession = Depends(get_db)):
    try:
        user = (
            db.query(User)
            .filter(
                User.email == data.email,
                User.status != UserStatus.DELETED,
            )
            .first()
        )
        if not user:
            raise USER_NOT_FOUND
        if user.status == UserStatus.SUSPENDED:  # type: ignore
            raise USER_IS_SUSPENDED
        if user.status == UserStatus.PENDING:  # type: ignore
            raise USER_IS_PENDING

        try:
            ph.verify(user.password, data.password)  # type: ignore
        except VerifyMismatchError:
            raise INVALID_PASSWORD

        from utils.jwt import create_access_token

        access_token = create_access_token(user.id)  # type: ignore

        # return {"access_token": access_token, "token_type": "bearer"}
        response = Response(status_code=200)
        response.set_cookie(key="token", value=f"Bearer {access_token}", httponly=True)
        return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
