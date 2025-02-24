from fastapi import WebSocket, WebSocketDisconnect, HTTPException, APIRouter
import logging
import asyncio
import json
import uuid
import os
import aiosqlite
from datetime import datetime
from pathlib import Path
from core.connection_manager import manager
from core.ollama_client import ollama_client
from core.web_search import search_client
from core.conversation_manager import conversation_manager
from core.tts_service import TTSService
from core.ocr_service import OCRService
from core.image_caption_service import ImageCaptionService
from core.system_info import system_info
from config.file_types import SUPPORTED_FILE_TYPES

router = APIRouter()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

@router.get("/api/conversations/{chat_id}")
async def get_conversation(chat_id: str):
    try:
        await conversation_manager.wait_for_db()
        
        async with aiosqlite.connect("conversations.db") as db:
            async with db.execute(
                "SELECT role, content, metadata, timestamp FROM conversations WHERE chat_id = ? ORDER BY timestamp",
                (chat_id,)
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
                return {"messages": history}
    except Exception as e:
        logger.error(f"Error fetching conversation: {e}")
        logger.exception("Full error stack trace:")
        raise HTTPException(status_code=500, detail=str(e))

async def process_history_request(websocket: WebSocket, chat_id: str):
    try:
        await conversation_manager.wait_for_db()
        
        async with aiosqlite.connect("conversations.db") as db:
            async with db.execute(
                "SELECT role, content, metadata, timestamp FROM conversations WHERE chat_id = ? ORDER BY timestamp",
                (chat_id,)
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
                await websocket.send_json({
                    "type": "conversation_history",
                    "messages": history
                })
    except Exception as e:
        logger.error(f"Error sending conversation history: {e}")
        logger.exception("Full error stack trace:")
        await websocket.send_json({
            "type": "error",
            "message": f"Failed to fetch conversation history: {str(e)}"
        })

async def websocket_endpoint(websocket: WebSocket, client_id: str, chat_id: str):
    await manager.connect(websocket, client_id, chat_id)
    try:
        # Request initial conversation history
        await process_history_request(websocket, chat_id)
        
        while True:
            data = await websocket.receive_json()
            
            # Handle .hub file import/export
            if data.get('type') == 'hub_import':
                try:
                    success = await conversation_manager.import_hub_file(chat_id, data.get('hubFile', {}))
                    await websocket.send_json({
                        "type": "hub_import_response",
                        "success": success
                    })
                    if success:
                        await process_history_request(websocket, chat_id)
                    continue
                except Exception as e:
                    logger.error(f"Hub import error: {e}")
                    logger.exception("Full error stack trace:")
                    await websocket.send_json({
                        "type": "hub_import_response",
                        "success": False,
                        "error": str(e)
                    })
                    continue

            if data.get('type') == 'hub_export':
                try:
                    hub_data = await conversation_manager.export_hub_file(chat_id)
                    if hub_data:
                        await websocket.send_json({
                            "type": "hub_export_response",
                            "success": True,
                            "data": hub_data
                        })
                    else:
                        raise ValueError("Failed to export chat data")
                    continue
                except Exception as e:
                    logger.error(f"Hub export error: {e}")
                    logger.exception("Full error stack trace:")
                    await websocket.send_json({
                        "type": "hub_export_response",
                        "success": False,
                        "error": str(e)
                    })
                    continue

            # Handle get conversation history request
            if data.get('type') == 'get_conversation_history':
                await process_history_request(websocket, chat_id)
                continue

            # Handle system info request
            if data.get('type') == 'get_system_info':
                try:
                    specs = system_info.get_system_specs()
                    await websocket.send_json({
                        "type": "system_info",
                        "specs": specs
                    })
                except Exception as e:
                    logger.error(f"Error getting system info: {e}")
                    logger.exception("Full error stack trace:")
                    await websocket.send_json({
                        "type": "system_info",
                        "specs": {"error": str(e)}
                    })
                continue

            # Handle model list request
            if data.get('type') == 'get_models':
                try:
                    models_info = await ollama_client.get_model_details()
                    await websocket.send_json({
                        "type": "models",
                        "models": models_info
                    })
                except Exception as e:
                    logger.error(f"Error getting models: {e}")
                    logger.exception("Full error stack trace:")
                    await websocket.send_json({
                        "type": "models",
                        "models": []
                    })
                continue

            # Handle audio playback request
            if data.get('type') == 'play_audio':
                try:
                    text = data.get('text', '')
                    if text:
                        tts_service = TTSService.get_instance()
                        await tts_service.generate_and_play(text)
                        await websocket.send_json({
                            "type": "audio_complete",
                            "success": True
                        })
                except Exception as e:
                    logger.error(f"Audio playback error: {e}")
                    logger.exception("Full error stack trace:")
                    await websocket.send_json({
                        "type": "audio_complete",
                        "success": False,
                        "error": str(e)
                    })
                continue

            # Validate model selection
            model = data.get('model')
            if not model:
                await websocket.send_json({
                    "type": "error",
                    "message": "No model selected"
                })
                continue

            # Handle normal message with possible files
            message = data.get('message', '')
            files = data.get('files', [])
            metadata = {
                'model': model,
                'timestamp': datetime.now().isoformat(),
                'files': files
            }

            # Store message and files in conversation history
            user_message = message
            if files:
                file_names = ", ".join(f['name'] for f in files)
                user_message = f"{message}\n[Uploaded files: {file_names}]" if message else f"[Uploaded files: {file_names}]"
            
            await conversation_manager.add_message(chat_id, "user", user_message, metadata)
            history = await conversation_manager.get_history(chat_id)

            # Process files if present
            files_context = ""
            if files:
                files_context = "You have been provided with the following files for analysis. Please read through all file contents carefully before responding:\n\n"
                
                for idx, file in enumerate(files, 1):
                    if file.get('isImage'):
                        try:
                            if not hasattr(websocket_endpoint, 'ocr_service'):
                                websocket_endpoint.ocr_service = OCRService.get_instance()
                            
                            result = await websocket_endpoint.ocr_service.process_image(file['imageData'])
                            
                            files_context += f"=== IMAGE {idx}: {file['name']} ===\n"
                            files_context += f"Type: {file['type']}\n"
                            files_context += f"Visual Content Description: {result['caption']}\n"
                            files_context += f"Extracted Text:\n{result['text']}\n\n"
                            
                            file['caption'] = result['caption']
                        except Exception as e:
                            logger.error(f"Error processing image {file['name']}: {e}")
                            logger.exception("Full error stack trace:")
                            files_context += f"Error processing image {file['name']}: {str(e)}\n\n"
                    else:
                        file_extension = os.path.splitext(file['name'])[1].lower()
                        language = SUPPORTED_FILE_TYPES['language_map'].get(file_extension, 'text')
                        
                        files_context += f"=== FILE {idx}: {file['name']} ===\n"
                        files_context += f"Type: {file['type']}\n"
                        files_context += f"Content ({language}):\n"
                        files_context += f"```{language}\n{file['content']}\n```\n\n"

                files_context += "Please ensure you've read and understood all file contents before providing your response.\n\n"

            # Add search results if enabled
            context = files_context
            search_results = []
            
            if data.get('webSearchEnabled', True) and message.strip():
                query = await ollama_client.refine_search_query(message, history)
                search_results = await search_client.search(
                    query, 
                    data.get('searchType', 'text'),
                    data.get('resultsCount', 3)
                )
                
                if data.get('showSummary', False):
                    summary = await search_client.summarize_results(search_results)
                    context += f"\nSearch Summary: {summary}\n\nSearch Details:\n"
                
                context += "\n".join(
                    f"Title: {r['title']}\nURL: {r['link']}\n{r['snippet']}\n"
                    for r in search_results
                )

                metadata['search_results'] = search_results
                metadata['search_summary'] = context if data.get('showSummary', False) else ""

            # Generate response
            response_text = ""
            async for chunk in ollama_client.generate_response(
                model,
                message or "Please analyze the provided files.",
                context=context,
                history=history
            ):
                if isinstance(chunk, dict) and chunk.get('error'):
                    await websocket.send_json({
                        "type": "error",
                        "message": chunk['error']
                    })
                    break
                
                response_text += chunk
                await websocket.send_json({
                    "type": "stream",
                    "content": chunk
                })

            # Store assistant response
            await conversation_manager.add_message(
                chat_id, 
                "assistant", 
                response_text,
                {
                    'model': model,
                    'timestamp': datetime.now().isoformat(),
                    'search_results': search_results,
                    'search_summary': metadata.get('search_summary')
                }
            )

            # Send complete response
            await websocket.send_json({
                "type": "complete",
                "content": response_text,
                "search_results": search_results,
                "search_summary": metadata.get('search_summary', '')
            })

    except WebSocketDisconnect:
        logger.info(f"Client {client_id} disconnected from chat {chat_id}")
        await manager.disconnect(client_id, chat_id)
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        logger.exception("Full error stack trace:")
        await manager.disconnect(client_id, chat_id)