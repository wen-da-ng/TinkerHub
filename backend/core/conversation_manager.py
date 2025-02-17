import aiosqlite
import asyncio
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

class ConversationManager:
    def __init__(self, db_path: str = "conversations.db"):
        self.db_path = db_path
        self.conversations: Dict[str, List[Dict[str, str]]] = {}
        asyncio.create_task(self.init_db())

    async def init_db(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    chat_id TEXT,
                    role TEXT,
                    content TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.commit()

    async def add_message(self, chat_id: str, role: str, content: str):
        if chat_id not in self.conversations:
            self.conversations[chat_id] = []
        
        self.conversations[chat_id].append({"role": role, "content": content})

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO conversations (chat_id, role, content) VALUES (?, ?, ?)",
                (chat_id, role, content)
            )
            await db.commit()

    async def get_history(self, chat_id: str) -> str:
        if chat_id not in self.conversations:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    "SELECT role, content FROM conversations WHERE chat_id = ? ORDER BY timestamp",
                    (chat_id,)
                ) as cursor:
                    rows = await cursor.fetchall()
                    self.conversations[chat_id] = [
                        {"role": row[0], "content": row[1]} for row in rows
                    ]

        if not self.conversations.get(chat_id):
            return ""

        return "\n".join([f"{msg['role'].title()}: {msg['content']}" for msg in self.conversations[chat_id]])

conversation_manager = ConversationManager()