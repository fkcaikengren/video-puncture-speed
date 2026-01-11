import asyncio
import sys
import os
from sqlalchemy import select

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import async_session
from app.api.users.models import User
from app.api.videos.models import Category
from app.core.security import get_password_hash

async def seed_data():
    async with async_session() as session:
        try:
            print("Starting database seed...")
            
            # 1. Create Users
            print("Checking/Creating Users...")
            result = await session.execute(select(User).where(User.username == "admin"))
            if not result.scalar_one_or_none():
                admin = User(
                    username="admin",
                    password_hash=get_password_hash("admin123"),
                    role="admin"
                )
                session.add(admin)
                print("  - Created admin user")
            else:
                print("  - Admin user already exists")

            result = await session.execute(select(User).where(User.username == "user"))
            if not result.scalar_one_or_none():
                user = User(
                    username="user",
                    password_hash=get_password_hash("user123"),
                    role="user"
                )
                session.add(user)
                print("  - Created normal user")
            else:
                print("  - Normal user already exists")
            
            # 2. Create Categories
            print("Checking/Creating Categories...")
            categories = ["Default"]
            for name in categories:
                result = await session.execute(select(Category).where(Category.name == name))
                if not result.scalar_one_or_none():
                    cat = Category(name=name)
                    session.add(cat)
                    print(f"  - Created category: {name}")
                else:
                    print(f"  - Category {name} already exists")

            await session.commit()
            print("Seeding completed successfully!")
            
        except Exception as e:
            print(f"An error occurred during seeding: {e}")
            await session.rollback()
            raise

if __name__ == "__main__":
    asyncio.run(seed_data())
