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
                    has_folder_context = any(col[1] == 'folder_context' for col in columns)

                if not columns:
                    await db.execute("""
                        CREATE TABLE conversations (
                            chat_id TEXT,
                            role TEXT,
                            content TEXT,
                            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                            metadata TEXT,
                            folder_context TEXT
                        )
                    """)
                elif not has_metadata:
                    await db.execute("ALTER TABLE conversations ADD COLUMN metadata TEXT")
                elif not has_folder_context:
                    await db.execute("ALTER TABLE conversations ADD COLUMN folder_context TEXT")

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

    async def add_folder_context(self, chat_id: str, folder_path: str, files: List[Dict]):
        await self.wait_for_db()
        
        folder_context = {
            'folder_path': folder_path,
            'timestamp': datetime.now().isoformat(),
            'files': files
        }
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO conversations (chat_id, role, content, metadata, folder_context) VALUES (?, ?, ?, ?, ?)",
                (
                    chat_id,
                    "system",
                    f"Using folder as context: {folder_path}",
                    json.dumps({'timestamp': datetime.now().isoformat()}),
                    json.dumps(folder_context)
                )
            )
            await db.commit()

    async def get_history(self, chat_id: str) -> str:
        await self.wait_for_db()
        
        if chat_id not in self.conversations:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    "SELECT role, content, metadata, folder_context FROM conversations WHERE chat_id = ? ORDER BY timestamp",
                    (chat_id,)
                ) as cursor:
                    rows = await cursor.fetchall()
                    self.conversations[chat_id] = [
                        {
                            "role": row[0],
                            "content": row[1],
                            "metadata": json.loads(row[2]) if row[2] else {},
                            "folder_context": json.loads(row[3]) if row[3] else None
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

            self.conversations[chat_id] = []
            
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("DELETE FROM conversations WHERE chat_id = ?", (chat_id,))
                
                # Import folder context if present
                if hub_data.get('folderContext'):
                    folder_context = hub_data['folderContext']
                    
                    # Handle path field variations
                    folder_path = None
                    if isinstance(folder_context, dict):
                        if 'path' in folder_context:
                            folder_path = folder_context['path']
                        elif 'folder_path' in folder_context:
                            folder_path = folder_context['folder_path']
                            # For consistency on export
                            folder_context['path'] = folder_path
                    
                    if folder_path:
                        await db.execute(
                            "INSERT INTO conversations (chat_id, role, content, metadata, folder_context) VALUES (?, ?, ?, ?, ?)",
                            (
                                chat_id,
                                "system",
                                f"Using folder as context: {folder_path}",
                                json.dumps({'timestamp': datetime.now().isoformat()}),
                                json.dumps(folder_context)
                            )
                        )
                
                # Import messages
                for message in hub_data['messages']:
                    if 'role' not in message or 'content' not in message:
                        logger.warning(f"Skipping invalid message in hub file: {message}")
                        continue
                    
                    timestamp = message.get('timestamp') or datetime.now().isoformat()
                    
                    metadata = {
                        'timestamp': timestamp,
                        'model': message.get('model'),
                        'searchResults': message.get('searchResults', []),
                        'searchSummary': message.get('searchSummary', ''),
                        'thinkingContent': message.get('thinkingContent', ''),
                        'files': message.get('files', [])
                    }
                    
                    message_dict = {
                        'role': message['role'],
                        'content': message['content'],
                        'metadata': metadata
                    }
                    self.conversations[chat_id].append(message_dict)
                    
                    await db.execute(
                        "INSERT INTO conversations (chat_id, role, content, metadata, timestamp) VALUES (?, ?, ?, ?, ?)",
                        (
                            chat_id,
                            message['role'],
                            message['content'],
                            json.dumps(metadata),
                            timestamp
                        )
                    )
                
                await db.commit()
                
            logger.info(f"Successfully imported {len(hub_data['messages'])} messages for chat {chat_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error importing .hub file: {e}")
            logger.exception("Full error stack trace:")
            return False

    async def export_hub_file(self, chat_id: str, title: str = None) -> Dict:
        try:
            await self.wait_for_db()
            
            messages = []
            folder_context = None
            
            # Make sure we're using the correct chat_id parameter in the SQL queries
            async with aiosqlite.connect(self.db_path) as db:
                # Get folder context if exists
                async with db.execute(
                    "SELECT folder_context FROM conversations WHERE chat_id = ? AND folder_context IS NOT NULL ORDER BY timestamp DESC LIMIT 1",
                    (chat_id,)  # Make sure chat_id is passed correctly here
                ) as cursor:
                    row = await cursor.fetchone()
                    if row and row[0]:
                        folder_context = json.loads(row[0])
                
                # Get messages
                async with db.execute(
                    "SELECT role, content, metadata, timestamp FROM conversations WHERE chat_id = ? AND role != 'system' ORDER BY timestamp",
                    (chat_id,)  # And here
                ) as cursor:
                    rows = await cursor.fetchall()
                    
                    # Add debug logging
                    logger.debug(f"Retrieved {len(rows)} messages for chat_id {chat_id}")
                    
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

            hub_data = {
                "version": "1.0",
                "chatId": chat_id,
                "messages": messages,
                "folderContext": folder_context,
                "metadata": {
                    "created": datetime.now().isoformat(),
                    "messageCount": len(messages),
                    "title": title or f"Chat Export {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                }
            }
            
            # Debug log the hub data
            logger.debug(f"Export hub data: messages={len(messages)}, has_folder_context={folder_context is not None}")
            
            return hub_data
            
        except Exception as e:
            logger.error(f"Error exporting .hub file: {e}")
            logger.exception("Full error stack trace:")
            return None
        
    async def _db_connection(self):
        """Get a database connection"""
        await self.wait_for_db()
        return await aiosqlite.connect(self.db_path)

conversation_manager = ConversationManager()