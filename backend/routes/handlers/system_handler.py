import logging
from fastapi import WebSocket
from typing import Dict, Any
from core.system_info import system_info
from core.ollama_client import ollama_client
from .base_handler import BaseHandler

logger = logging.getLogger(__name__)

class SystemHandler(BaseHandler):
    """Handler for system information and model-related operations"""
    
    async def handle(self, data: Dict[str, Any]) -> bool:
        """Handle system-related messages"""
        
        if data.get('type') == 'get_system_info':
            await self._process_system_info()
            return True
            
        if data.get('type') == 'get_models':
            await self._process_get_models()
            return True
            
        return False
    
    async def _process_system_info(self):
        """Process a system info request"""
        try:
            specs = system_info.get_system_specs()
            await self.send_json({
                "type": "system_info",
                "specs": specs
            })
        except Exception as e:
            self.log_error(f"Error getting system info: {e}", e)
            await self.send_json({
                "type": "system_info",
                "specs": {"error": str(e)}
            })
    
    async def _process_get_models(self):
        """Process a get models request"""
        try:
            models_info = await ollama_client.get_model_details()
            await self.send_json({
                "type": "models",
                "models": models_info
            })
        except Exception as e:
            self.log_error(f"Error getting models: {e}", e)
            await self.send_json({
                "type": "models",
                "models": []
            })