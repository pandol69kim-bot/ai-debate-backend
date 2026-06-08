"""DB에 is_admin 컬럼 추가 스크립트 — 최초 1회만 실행"""
import asyncio
from sqlalchemy import text
from app.db.session import engine


async def main():
    async with engine.begin() as conn:
        await conn.execute(text(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE"
        ))
    print("OK: users table - is_admin column added")
    await engine.dispose()


asyncio.run(main())
