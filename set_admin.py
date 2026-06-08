"""
관리자 계정 설정 스크립트
사용법: python set_admin.py <email>
"""
import asyncio
import sys
from sqlalchemy import select, update
from app.db.session import AsyncSessionLocal
from app.models.db_models import User


async def set_admin(email: str):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user:
            print(f"ERROR: '{email}' 이메일 유저를 찾을 수 없습니다.")
            return
        await db.execute(
            update(User).where(User.email == email).values(is_admin=True)
        )
        await db.commit()
        print(f"OK: '{email}' 계정에 관리자 권한을 부여했습니다.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python set_admin.py <email>")
        sys.exit(1)
    asyncio.run(set_admin(sys.argv[1]))
