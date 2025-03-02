import logging
from fastapi import WebSocket
from typing import Dict, Any

logger = logging.getLogger(__name__)

class BaseHandler:
    """Base handler for WebSocket message processing"""
    
    def __init__(self, websocket: WebSocket, chat_id: str):
        self.websocket = websocket
        self.chat_id = chat_id
        
    async def handle(self, data: Dict[str, Any]) -> bool:
        """
        Handle a WebSocket message
        
        Args:
            data: The parsed message data
            
        Returns:
            bool: True if the message was handled, False otherwise
        """
        raise NotImplementedError("Subclasses must implement handle()")
        
    async def send_json(self, data: Dict[str, Any]):
        """Send a JSON response to the WebSocket client"""
        await self.websocket.send_json(data)
        
    async def send_error(self, message: str):
        """Send an error message to the WebSocket client"""
        await self.send_json({
            "type": "error",
            "message": message
        })
        
    def log_error(self, message: str, exception: Exception = None):
        """Log an error message"""
        logger.error(message)
        if exception:
            logger.exception("Full error stack trace:")