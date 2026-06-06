import base64
import io
import hashlib
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import pyotp
import qrcode

from app.database import get_db
from app.models.user import User, LoginJournal, RefreshToken
from app.schemas.user import (
    UserCreate, UserResponse, LoginRequest, TokenResponse,
    RefreshRequest, TwoFactorSetupResponse, TwoFactorVerifyRequest,
    LoginJournalResponse,
)
from app.utils.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, verify_token,
)
from app.utils.dependencies import get_current_active_user
from app.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(data: UserCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.email == data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=data.email,
        full_name=data.full_name,
        password_hash=hash_password(data.password),
        role=data.role,
        department=data.department,
        phone=data.phone,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")

    if not user or not verify_password(data.password, user.password_hash):
        if user:
            db.add(LoginJournal(user_id=user.id, ip_address=ip, user_agent=ua, status="failed"))
            await db.commit()
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    if user.two_factor_enabled:
        if not data.totp_code:
            raise HTTPException(status_code=200, detail="2FA_REQUIRED", headers={"X-2FA-Required": "true"})
        totp = pyotp.TOTP(user.totp_secret)
        if not totp.verify(data.totp_code):
            raise HTTPException(status_code=401, detail="Invalid 2FA code")

    access_token = create_access_token({"sub": user.id})
    refresh_token_str = create_refresh_token({"sub": user.id})
    token_hash = hashlib.sha256(refresh_token_str.encode()).hexdigest()

    db.add(RefreshToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    ))
    db.add(LoginJournal(user_id=user.id, ip_address=ip, user_agent=ua, status="success"))
    await db.commit()

    return TokenResponse(access_token=access_token, refresh_token=refresh_token_str, user=user)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(data: RefreshRequest, db: AsyncSession = Depends(get_db)):
    payload = verify_token(data.refresh_token, token_type="refresh")
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    token_hash = hashlib.sha256(data.refresh_token.encode()).hexdigest()
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.is_revoked == False,
            RefreshToken.expires_at > datetime.utcnow(),
        )
    )
    stored_token = result.scalar_one_or_none()
    if not stored_token:
        raise HTTPException(status_code=401, detail="Refresh token not found or expired")

    user_result = await db.execute(select(User).where(User.id == stored_token.user_id))
    user = user_result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    stored_token.is_revoked = True
    new_access = create_access_token({"sub": user.id})
    new_refresh = create_refresh_token({"sub": user.id})
    new_hash = hashlib.sha256(new_refresh.encode()).hexdigest()

    db.add(RefreshToken(
        user_id=user.id,
        token_hash=new_hash,
        expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    ))
    await db.commit()

    return TokenResponse(access_token=new_access, refresh_token=new_refresh, user=user)


@router.post("/logout")
async def logout(data: RefreshRequest, db: AsyncSession = Depends(get_db)):
    token_hash = hashlib.sha256(data.refresh_token.encode()).hexdigest()
    result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    token = result.scalar_one_or_none()
    if token:
        token.is_revoked = True
        await db.commit()
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_active_user)):
    return current_user


@router.post("/2fa/setup", response_model=TwoFactorSetupResponse)
async def setup_2fa(current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db)):
    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret)
    provisioning_uri = totp.provisioning_uri(name=current_user.email, issuer_name="AiPlatforma")

    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(provisioning_uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    qr_base64 = base64.b64encode(buf.getvalue()).decode()

    current_user.totp_secret = secret
    await db.commit()

    return TwoFactorSetupResponse(secret=secret, qr_url=provisioning_uri, qr_image_base64=qr_base64)


@router.post("/2fa/verify")
async def verify_2fa(
    data: TwoFactorVerifyRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    if not current_user.totp_secret:
        raise HTTPException(status_code=400, detail="2FA not set up. Call /auth/2fa/setup first")
    totp = pyotp.TOTP(current_user.totp_secret)
    if not totp.verify(data.code):
        raise HTTPException(status_code=400, detail="Invalid TOTP code")
    current_user.two_factor_enabled = True
    await db.commit()
    return {"message": "2FA enabled successfully"}


@router.post("/2fa/disable")
async def disable_2fa(
    data: TwoFactorVerifyRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    if not current_user.two_factor_enabled:
        raise HTTPException(status_code=400, detail="2FA is not enabled")
    totp = pyotp.TOTP(current_user.totp_secret)
    if not totp.verify(data.code):
        raise HTTPException(status_code=400, detail="Invalid TOTP code")
    current_user.two_factor_enabled = False
    current_user.totp_secret = None
    await db.commit()
    return {"message": "2FA disabled successfully"}


@router.get("/login-journal", response_model=list[LoginJournalResponse])
async def get_login_journal(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(LoginJournal)
        .where(LoginJournal.user_id == current_user.id)
        .order_by(LoginJournal.created_at.desc())
        .limit(50)
    )
    return result.scalars().all()
