# # chat_logger.py
# import asyncpg
# import os
# from datetime import datetime

# DATABASE_URL = os.getenv("DATABASE_URL")

# class ChatLogger:
#     def __init__(self):
#         self.pool = None

#     async def connect(self):
#         self.pool = await asyncpg.create_pool(DATABASE_URL)

#     async def ensure_user(self, phone: str) -> int:
#         async with self.pool.acquire() as conn:
#             row = await conn.fetchrow("SELECT id FROM users WHERE phone = $1", phone)
#             if row:
#                 return row['id']
#             else:
#                 row = await conn.fetchrow("INSERT INTO users (phone) VALUES ($1) RETURNING id", phone)
#                 return row['id']

#     async def log_message(self, phone: str, content: str, is_user: bool, msg_type: str = "text"):
#         user_id = await self.ensure_user(phone)
#         async with self.pool.acquire() as conn:
#             await conn.execute("""
#                 INSERT INTO messages (user_id, message_type, content, is_from_user)
#                 VALUES ($1, $2, $3, $4)
#             """, user_id, msg_type, content, is_user)

#     async def get_recent_messages(self, phone: str, limit: int = 10):
#         user_id = await self.ensure_user(phone)
#         async with self.pool.acquire() as conn:
#             rows = await conn.fetch("""
#                 SELECT message_type, content, is_from_user, timestamp
#                 FROM messages
#                 WHERE user_id = $1
#                 ORDER BY timestamp DESC
#                 LIMIT $2
#             """, user_id, limit)
#             return list(reversed(rows))



# chat_logger.py
import asyncpg
import os
from datetime import datetime

class ChatLogger:
    def __init__(self):
        self.db_url = os.getenv("OWNER_PORTAL_URL_LOCAL")
        self.pool = None

    async def connect(self):
        clean_url = self.db_url.replace("postgresql+asyncpg", "postgresql")
        self.pool = await asyncpg.create_pool(clean_url)

    async def log_message(self, phone: str, message: str, is_user: bool):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO chat_logs (phone, message, is_customer, timestamp)
                VALUES ($1, $2, $3, $4)
            """, phone, message, is_user, datetime.utcnow())
    async def get_recent_messages(self, phone: str, limit: int = 20):
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT message, is_customer, timestamp
                FROM chat_logs
                WHERE phone = $1
                ORDER BY timestamp DESC
                LIMIT $2
            """, phone, limit)
            return list(reversed(rows))
    async def log_summary(self, phone: str, summary: str):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO chat_summaries (phone, summary)
                VALUES ($1, $2)
            """, phone, summary, datetime.utcnow())
    async def get_latest_summary(self, phone: str):
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT summary
                FROM chat_summaries
                WHERE phone = $1
                ORDER BY timestamp DESC
                LIMIT 1
            """, phone)
            return row['summary'] if row else None
    async def update_summary(self, phone: str, summary: str):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE chat_summaries
                SET summary = $2, timestamp = $3
                WHERE phone = $1
            """, phone, summary, datetime.utcnow())

logger = ChatLogger()