import logging
import json
import os
import aiosqlite
from datetime import datetime
from fastapi import WebSocket
from typing import Dict, Any, List
from core.connection_manager import manager
from core.ollama_client import ollama_client
from core.web_search import search_client
from core.conversation_manager import conversation_manager
from core.ocr_service import OCRService
from config.file_types import SUPPORTED_FILE_TYPES
from .base_handler import BaseHandler

logger = logging.getLogger(__name__)

class ChatHandler(BaseHandler):
    """Handler for chat message processing"""
    
    async def handle(self, data: Dict[str, Any]) -> bool:
        """Handle chat-related messages"""
        
        if data.get('message') is not None or (data.get('files') and not data.get('type')):
            await self._process_chat_message(data)
            return True
            
        if data.get('type') == 'get_conversation_history':
            await self._process_history_request()
            return True
            
        return False
            
    async def _process_chat_message(self, data: Dict[str, Any]):
        """Process a chat message and generate a response"""
        try:
            model = data.get('model')
            if not model:
                await self.send_error("No model selected")
                return
                
            message = data.get('message', '')
            files = data.get('files', [])
            
            metadata = {
                'model': model,
                'timestamp': datetime.now().isoformat(),
                'files': files
            }

            user_message = message
            if files:
                file_names = ", ".join(f['name'] for f in files)
                user_message = f"{message}\n[Files included: {file_names}]" if message else f"[Files included: {file_names}]"
            
            await conversation_manager.add_message(self.chat_id, "user", user_message, metadata)
            history = await conversation_manager.get_history(self.chat_id)

            files_context = ""
            if files:
                files_context = await self._process_files(files)

            context = files_context
            search_results = []
            
            if data.get('webSearchEnabled', True) and message.strip():
                context, search_results = await self._perform_search(message, history, data)
                metadata['search_results'] = search_results
                metadata['search_summary'] = context if data.get('showSummary', False) else ""

            response_text = ""
            async for chunk in ollama_client.generate_response(
                model,
                message or "Please analyze the provided files.",
                context=context,
                history=history
            ):
                if isinstance(chunk, dict) and chunk.get('error'):
                    await self.send_json({
                        "type": "error",
                        "message": chunk['error']
                    })
                    break
                
                response_text += chunk
                await self.send_json({
                    "type": "stream",
                    "content": chunk
                })

            await conversation_manager.add_message(
                self.chat_id, 
                "assistant", 
                response_text,
                {
                    'model': model,
                    'timestamp': datetime.now().isoformat(),
                    'search_results': search_results,
                    'search_summary': metadata.get('search_summary')
                }
            )

            await self.send_json({
                "type": "complete",
                "content": response_text,
                "search_results": search_results,
                "search_summary": metadata.get('search_summary', '')
            })
            
        except Exception as e:
            self.log_error(f"Error processing chat message: {e}", e)
            await self.send_error(f"Error processing message: {str(e)}")
    
    async def _process_files(self, files: List[Dict]) -> str:
        """Process uploaded files and create context for LLM"""
        files_context = "You have been provided with the following files for analysis. Please read through all file contents carefully before responding:\n\n"
        
        for idx, file in enumerate(files, 1):
            if file.get('isImage'):
                try:
                    ocr_service = OCRService.get_instance()
                    result = await ocr_service.process_image(file['imageData'])
                    
                    files_context += f"=== IMAGE {idx}: {file['name']} ===\n"
                    files_context += f"Type: {file['type']}\n"
                    files_context += f"Visual Content Description: {result['caption']}\n"
                    files_context += f"Extracted Text:\n{result['text']}\n\n"
                    
                except Exception as e:
                    self.log_error(f"Error processing image {file['name']}: {e}", e)
                    files_context += f"Error processing image {file['name']}: {str(e)}\n\n"
            else:
                file_extension = os.path.splitext(file['name'])[1].lower()
                language = SUPPORTED_FILE_TYPES['language_map'].get(file_extension, 'text')
                path_info = f" (Path: {file['path']})" if 'path' in file else ""
                
                files_context += f"=== FILE {idx}: {file['name']}{path_info} ===\n"
                files_context += f"Type: {file['type']}\n"
                files_context += f"Content ({language}):\n"
                files_context += f"```{language}\n{file['content']}\n```\n\n"

        files_context += "Please ensure you've read and understood all file contents before providing your response.\n\n"
        return files_context
            
    async def _perform_search(self, message: str, history: str, data: Dict[str, Any]) -> tuple[str, List]:
        """Perform web search and create context"""
        query = await ollama_client.refine_search_query(message, history)
        search_results = await search_client.search(
            query, 
            data.get('searchType', 'text'),
            data.get('resultsCount', 3)
        )
        
        context = ""
        if data.get('showSummary', False):
            summary = await search_client.summarize_results(search_results)
            context += f"\nSearch Summary: {summary}\n\nSearch Details:\n"
        
        context += "\n".join(
            f"Title: {r['title']}\nURL: {r['link']}\n{r['snippet']}\n"
            for r in search_results
        )
        
        return context, search_results
            
    async def _process_history_request(self):
        """Process a conversation history request"""
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
                            "timestamp": row[3]
                        } for row in rows
                    ]
                    await self.send_json({
                        "type": "conversation_history",
                        "messages": history
                    })
        except Exception as e:
            self.log_error(f"Error sending conversation history: {e}", e)
            await self.send_error(f"Failed to fetch conversation history: {str(e)}")