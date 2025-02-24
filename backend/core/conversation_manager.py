import aiosqlite
import asyncio
from typing import Dict, List, Optional
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class ConversationManager:
    def __init__(self, db_path: str = "conversations.db"):
        self.db_path = db_path
        self.conversations: Dict[str, List[Dict[str, str]]] = {}
        self._db_initialized = asyncio.Event()
        asyncio.create_task(self.init_db())

    async def init_db(self):
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("PRAGMA table_info(conversations)") as cursor:
                    columns = await cursor.fetchall()
                    has_metadata = any(col[1] == 'metadata' for col in columns)

                if not columns:
                    await db.execute("""
                        CREATE TABLE conversations (
                            chat_id TEXT,
                            role TEXT,
                            content TEXT,
                            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                            metadata TEXT
                        )
                    """)
                elif not has_metadata:
                    await db.execute("ALTER TABLE conversations ADD COLUMN metadata TEXT")

                await db.commit()
                logger.info("Database initialized successfully")
                self._db_initialized.set()
        except Exception as e:
            logger.error(f"Database initialization error: {e}")
            raise

    async def wait_for_db(self):
        await self._db_initialized.wait()

    async def add_message(self, chat_id: str, role: str, content: str, metadata: Optional[Dict] = None):
        await self.wait_for_db()
        
        if chat_id not in self.conversations:
            self.conversations[chat_id] = []
        
        message = {
            "role": role, 
            "content": content,
            "metadata": metadata or {}
        }
        
        self.conversations[chat_id].append(message)

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO conversations (chat_id, role, content, metadata) VALUES (?, ?, ?, ?)",
                (chat_id, role, content, json.dumps(metadata) if metadata else None)
            )
            await db.commit()

    async def get_history(self, chat_id: str) -> str:
        await self.wait_for_db()
        
        if chat_id not in self.conversations:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    "SELECT role, content, metadata FROM conversations WHERE chat_id = ? ORDER BY timestamp",
                    (chat_id,)
                ) as cursor:
                    rows = await cursor.fetchall()
                    self.conversations[chat_id] = [
                        {
                            "role": row[0],
                            "content": row[1],
                            "metadata": json.loads(row[2]) if row[2] else {}
                        } for row in rows
                    ]

        if not self.conversations.get(chat_id):
            return ""

        return "\n".join([f"{msg['role'].title()}: {msg['content']}" for msg in self.conversations[chat_id]])

    async def import_hub_file(self, chat_id: str, hub_data: Dict):
        try:
            await self.wait_for_db()
            
            if not hub_data.get('messages'):
                raise ValueError("No messages found in .hub file")

            # Clear existing conversations for this chat
            self.conversations[chat_id] = []
            
            async with aiosqlite.connect(self.db_path) as db:
                # Delete existing messages
                await db.execute("DELETE FROM conversations WHERE chat_id = ?", (chat_id,))
                
                # Import new messages
                for message in hub_data['messages']:
                    # Extract metadata from the message
                    metadata = {
                        'timestamp': message.get('timestamp'),
                        'model': message.get('model'),
                        'searchResults': message.get('searchResults', []),
                        'searchSummary': message.get('searchSummary', ''),
                        'thinkingContent': message.get('thinkingContent', ''),
                        'files': message.get('files', [])
                    }
                    
                    # Add to memory
                    message_dict = {
                        'role': message['role'],
                        'content': message['content'],
                        'metadata': metadata
                    }
                    self.conversations[chat_id].append(message_dict)
                    
                    # Add to database
                    await db.execute(
                        "INSERT INTO conversations (chat_id, role, content, metadata, timestamp) VALUES (?, ?, ?, ?, ?)",
                        (
                            chat_id,
                            message['role'],
                            message['content'],
                            json.dumps(metadata),
                            message.get('timestamp') or datetime.now().isoformat()
                        )
                    )
                
                await db.commit()
                
            logger.info(f"Successfully imported {len(hub_data['messages'])} messages for chat {chat_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error importing .hub file: {e}")
            logger.exception("Full error stack trace:")
            return False

    async def export_hub_file(self, chat_id: str) -> Dict:
        try:
            await self.wait_for_db()
            
            messages = []
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    "SELECT role, content, metadata, timestamp FROM conversations WHERE chat_id = ? ORDER BY timestamp",
                    (chat_id,)
                ) as cursor:
                    rows = await cursor.fetchall()
                    for row in rows:
                        metadata = json.loads(row[2]) if row[2] else {}
                        messages.append({
                            "role": row[0],
                            "content": row[1],
                            "timestamp": row[3],
                            "model": metadata.get('model'),
                            "searchResults": metadata.get('searchResults', []),
                            "searchSummary": metadata.get('searchSummary', ''),
                            "thinkingContent": metadata.get('thinkingContent', ''),
                            "files": metadata.get('files', [])
                        })

            return {
                "version": "1.0",
                "chatId": chat_id,
                "messages": messages,
                "metadata": {
                    "created": datetime.now().isoformat(),
                    "messageCount": len(messages),
                    "title": f"Chat Export {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                }
            }
            
        except Exception as e:
            logger.error(f"Error exporting .hub file: {e}")
            logger.exception("Full error stack trace:")
            return None

conversation_manager = ConversationManager()