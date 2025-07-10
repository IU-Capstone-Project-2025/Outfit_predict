# app/api/v1/deps.py

from app.core.config import Settings, get_settings
from app.core.security import decode_access_token
from app.db.database import get_session
from app.models.user import User
from app.schemas.user import TokenData
from app.storage.minio_client import MinioService
from app.storage.qdrant_client import QdrantService
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


def get_settings_dep() -> Settings:
    return get_settings()


def get_minio() -> MinioService:
    return MinioService()


def get_qdrant() -> QdrantService:
    return QdrantService()


get_db = get_session  # type: ignore[assignment]


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_session)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        token_data = TokenData(user_id=user_id)
    except JWTError:
        raise credentials_exception

    user = await db.scalar(select(User).where(User.id == token_data.user_id))
    if user is None:
        raise credentials_exception
    return user
