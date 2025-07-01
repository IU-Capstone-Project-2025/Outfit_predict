from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.user import UserCreate
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def get_user_by_email(db: AsyncSession, email: str):
    stmt = select(User).where(User.email == email)
    return await db.scalar(stmt)


async def create_user(db: AsyncSession, user_in: UserCreate):
    db_user = User(email=user_in.email, hashed_password=hash_password(user_in.password))
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user


async def authenticate_user(db: AsyncSession, email: str, password: str):
    user = await get_user_by_email(db, email)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user
