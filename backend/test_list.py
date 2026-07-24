import asyncio
import uuid
from database import async_session, init_db
from models.user import User
from routes.documents import list_documents

async def main():
    await init_db()
    async with async_session() as db:
        user = User(id=uuid.UUID('4748bf75-33b4-4239-a6ee-d43da3121247'), email="test@test.com", username="testuser", hashed_password="pwd")
        try:
            res = await list_documents(page=1, page_size=20, db=db, current_user=user)
            print(res)
        except Exception as e:
            import traceback
            traceback.print_exc()

asyncio.run(main())
