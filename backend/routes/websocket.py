# backend/routes/websocket.py

from fastapi import WebSocket, WebSocketDisconnect
import logging
import asyncio
import json
import uuid
import os
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

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

async def get_models_handler(websocket: WebSocket):
    try:
        models_info = await ollama_client.get_model_details()
        await websocket.send_json({
            "type": "models",
            "models": models_info
        })
    except Exception as e:
        logger.error(f"Error sending models: {e}")
        await websocket.send_json({
            "type": "models",
            "models": []  # Return empty list to indicate error
        })

async def get_system_info_handler(websocket: WebSocket):
    try:
        specs = system_info.get_system_specs()
        await websocket.send_json({
            "type": "system_info",
            "specs": specs
        })
    except Exception as e:
        logger.error(f"Error sending system info: {e}")
        await websocket.send_json({
            "type": "system_info",
            "specs": {
                'error': str(e)
            }
        })

async def process_image_files(files):
    """Process image files with lazy loading of services"""
    files_context = ""
    ocr_service = None
    
    for idx, file in enumerate(files, 1):
        if file.get('isImage'):
            try:
                # Initialize OCR service only when needed
                if ocr_service is None:
                    ocr_service = OCRService.get_instance()
                
                logger.info(f"Processing image file: {file['name']}")
                result = await ocr_service.process_image(file['imageData'])
                
                files_context += f"=== IMAGE {idx}: {file['name']} ===\n"
                files_context += f"Type: {file['type']}\n"
                files_context += f"Visual Content Description: {result['caption']}\n"
                files_context += f"Extracted Text:\n{result['text']}\n\n"
                
                # Update file with caption for frontend display
                file['caption'] = result['caption']
            except Exception as e:
                logger.error(f"Error processing image {file['name']}: {e}")
                files_context += f"Error processing image {file['name']}: {str(e)}\n\n"
        else:
            # Handle text files
            file_extension = os.path.splitext(file['name'])[1].lower()
            language = SUPPORTED_FILE_TYPES['language_map'].get(file_extension, 'text')
            
            files_context += f"=== FILE {idx}: {file['name']} ===\n"
            files_context += f"Type: {file['type']}\n"
            files_context += f"Content ({language}):\n"
            files_context += f"```{language}\n{file['content']}\n```\n\n"

    return files_context

async def websocket_endpoint(websocket: WebSocket, client_id: str, chat_id: str):
    await manager.connect(websocket, client_id, chat_id)
    try:
        while True:
            data = await websocket.receive_json()
            
            # Handle system info request
            if data.get('type') == 'get_system_info':
                await get_system_info_handler(websocket)
                continue
            
            # Handle model list request
            if data.get('type') == 'get_models':
                await get_models_handler(websocket)
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

            # Validate model availability
            available_models = await ollama_client.get_model_details()
            if not any(m['name'] == model for m in available_models):
                await websocket.send_json({
                    "type": "error",
                    "message": f"Selected model {model} is not available"
                })
                continue
            
            # Handle normal message with possible files
            logger.info(f"Message from {client_id}:{chat_id}")
            
            message = data.get('message', '')
            files = data.get('files', [])
            
            # Process files if present
            files_context = ""
            if files:
                files_context = "You have been provided with the following files for analysis. Please read through all file contents carefully before responding:\n\n"
                files_context += await process_image_files(files)
                files_context += "Please ensure you've read and understood all file contents before providing your response.\n\n"

            # Store message and files in conversation history
            user_message = message
            if files:
                file_names = ", ".join(f['name'] for f in files)
                user_message = f"{message}\n[Uploaded files: {file_names}]" if message else f"[Uploaded files: {file_names}]"
            
            await conversation_manager.add_message(chat_id, "user", user_message)
            history = await conversation_manager.get_history(chat_id)
            
            # Combine file context with search context if enabled
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

            # Set prompt based on message content
            if message.strip():
                prompt = message
            else:
                if any(file.get('isImage') for file in files):
                    prompt = "Please analyze the provided images, including any text extracted through OCR, and provide a detailed explanation of their contents and meaning."
                else:
                    prompt = "Please analyze the provided files and provide a detailed explanation of their contents."

            # Generate response using combined context
            response_text = ""
            error_occurred = False
            
            async for chunk in ollama_client.generate_response(
                model,
                prompt,
                context=context,
                history=history,
                system_prompt="You are a helpful assistant with expertise in analyzing files, code, and images. When presented with files or images, carefully read through all content before responding. For images, analyze both the visual content and any extracted text. Consider the entire context of each file or image."
            ):
                if chunk.startswith("Error:"):
                    error_occurred = True
                    await websocket.send_json({
                        "type": "error",
                        "message": chunk
                    })
                    break
                    
                response_text += chunk
                await websocket.send_json({"type": "stream", "content": chunk})

            if error_occurred:
                continue

            await conversation_manager.add_message(chat_id, "assistant", response_text)

            # Send complete response with search results if any
            await websocket.send_json({
                "type": "complete",
                "content": response_text,
                "search_results": search_results,
                "search_summary": context if data.get('showSummary', False) else ""
            })
            
    except WebSocketDisconnect:
        logger.info(f"Client {client_id} disconnected")
        await manager.disconnect(client_id, chat_id)
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        logger.exception("Full error stack trace:")
        await manager.disconnect(client_id, chat_id)