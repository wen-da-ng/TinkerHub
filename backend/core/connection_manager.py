import asyncio
import logging
from typing import Dict
from fastapi import WebSocket
from core.cache import SearchCache

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Dict[str, WebSocket]] = {}
        self.request_queue = asyncio.Queue()
        self.search_cache = SearchCache()

    async def connect(self, websocket: WebSocket, client_id: str, chat_id: str):
        await websocket.accept()
        if client_id not in self.active_connections:
            self.active_connections[client_id] = {}
        self.active_connections[client_id][chat_id] = websocket
        logger.info(f"Client {client_id} connected to chat {chat_id}")

    async def disconnect(self, client_id: str, chat_id: str):
        if client_id in self.active_connections:
            if chat_id in self.active_connections[client_id]:
                del self.active_connections[client_id][chat_id]
                logger.info(f"Client {client_id} disconnected from chat {chat_id}")

    async def process_request_queue(self):
        while True:
            try:
                request = await self.request_queue.get()
                await self._process_request(request)
                self.request_queue.task_done()
                await asyncio.sleep(2)
            except Exception as e:
                logger.error(f"Error processing request: {e}")

    async def _process_request(self, request):
        try:
            await asyncio.sleep(0)
        except Exception as e:
            logger.error(f"Error in _process_request: {e}")

manager = ConnectionManager()