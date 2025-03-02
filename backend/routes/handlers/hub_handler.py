import logging
import json
import aiosqlite
from datetime import datetime
from fastapi import WebSocket
from typing import Dict, Any
from core.conversation_manager import conversation_manager
from .base_handler import BaseHandler

logger = logging.getLogger(__name__)

class HubHandler(BaseHandler):
    """Handler for .hub file import/export operations"""
    
    async def handle(self, data: Dict[str, Any]) -> bool:
        """Handle hub-related messages"""
        
        if data.get('type') == 'hub_import':
            await self._process_hub_import(data)
            return True
            
        if data.get('type') == 'hub_export':
            await self._process_hub_export(data)
            return True
            
        return False
    
    async def _process_hub_import(self, data: Dict[str, Any]):
        """Process a hub file import request"""
        try:
            hub_file = data.get('hubFile', {})
            
            if not hub_file:
                raise ValueError("No hub file data provided")
                
            success = await conversation_manager.import_hub_file(self.chat_id, hub_file)
            
            await self.send_json({
                "type": "hub_import_response",
                "success": success
            })
            
            if success:
                # Trigger a history refresh
                await self._send_conversation_history()
        except Exception as e:
            self.log_error(f"Hub import error: {e}", e)
            await self.send_json({
                "type": "hub_import_response",
                "success": False,
                "error": str(e)
            })
    
    async def _process_hub_export(self, data: Dict[str, Any]):
        """Process a hub file export request"""
        try:
            logger.info(f"Exporting hub file for chat_id: {self.chat_id}")
            
            # Extract title from the request data
            title = data.get('title', f"Chat Export {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                
            hub_data = await conversation_manager.export_hub_file(self.chat_id, title)
            
            if not hub_data:
                raise ValueError("Failed to export chat data")
                
            logger.info(f"Hub export successful, message count: {len(hub_data.get('messages', []))}")
                
            await self.send_json({
                "type": "hub_export_response",
                "success": True,
                "data": hub_data
            })
        except Exception as e:
            self.log_error(f"Hub export error: {e}", e)
            await self.send_json({
                "type": "hub_export_response",
                "success": False,
                "error": str(e)
            })
            
    async def _send_conversation_history(self):
        """Send conversation history after a successful import"""
        try:
            await conversation_manager.wait_for_db()
            
            async with aiosqlite.connect("conversations.db") as db:
                async with db.execute(
                    "SELECT role, content, metadata, timestamp FROM conversations WHERE chat_id = ? ORDER BY timestamp",
                    (self.chat_id,)
                ) as cursor:
                    rows = await cursor.fetchall()
                    history = [
                        {
                            "role": row[0],
                            "content": row[1],
                            "metadata": json.loads(row[2]) if row[2] else {},
                            "timestamp": row[3],
                            # Extract these fields directly to make them more accessible
                            "thinkingContent": json.loads(row[2]).get('thinkingContent', '') if row[2] else '',
                            "searchResults": json.loads(row[2]).get('searchResults', []) if row[2] else [],
                            "searchSummary": json.loads(row[2]).get('searchSummary', '') if row[2] else '',
                            "files": json.loads(row[2]).get('files', []) if row[2] else [],
                            "model": json.loads(row[2]).get('model', '') if row[2] else ''
                        } for row in rows
                    ]
                    await self.send_json({
                        "type": "conversation_history",
                        "messages": history
                    })
        except Exception as e:
            self.log_error(f"Error sending conversation history: {e}", e)