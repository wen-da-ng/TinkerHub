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
from core.tts_service import tts_service
from core.ocr_service import ocr_service
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
                message_id = data.get('message_id')
                logger.info(f"Received audio playback request for message {message_id}")
                success = await tts_service.play_audio(message_id)
                await websocket.send_json({
                    "type": "audio_complete",
                    "message_id": message_id,
                    "success": success
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
            
            # Create context from files
            files_context = ""
            if files:
                files_context = "You have been provided with the following files for analysis. Please read through all file contents carefully before responding:\n\n"
                for idx, file in enumerate(files, 1):
                    if file.get('isImage'):
                        # Process image with OCR and captioning
                        logger.info(f"Processing image file: {file['name']}")
                        result = await ocr_service.process_image(file['imageData'])
                        files_context += f"=== IMAGE {idx}: {file['name']} ===\n"
                        files_context += f"Type: {file['type']}\n"
                        files_context += f"Visual Content Description: {result['caption']}\n"
                        files_context += f"Extracted Text:\n{result['text']}\n\n"
                        
                        # Update file with caption for frontend display
                        file['caption'] = result['caption']
                    else:
                        # Handle text files
                        file_extension = os.path.splitext(file['name'])[1].lower()
                        language = SUPPORTED_FILE_TYPES['language_map'].get(file_extension, 'text')
                        
                        files_context += f"=== FILE {idx}: {file['name']} ===\n"
                        files_context += f"Type: {file['type']}\n"
                        files_context += f"Content ({language}):\n"
                        files_context += f"```{language}\n{file['content']}\n```\n\n"

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
            
            # Generate audio for response
            message_id = str(uuid.uuid4())
            audio_id = None
            
            try:
                audio_id = await tts_service.generate_speech(response_text, message_id)
                logger.info(f"Generated audio for message: {message_id}")
            except Exception as e:
                logger.error(f"TTS generation failed: {str(e)}")
                logger.exception("Full TTS error stack trace:")

            # Send complete response with search results if any
            await websocket.send_json({
                "type": "complete",
                "content": response_text,
                "search_results": search_results,
                "search_summary": context if data.get('showSummary', False) else "",
                "audio_id": audio_id
            })
            
    except WebSocketDisconnect:
        logger.info(f"Client {client_id} disconnected")
        await manager.disconnect(client_id, chat_id)
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        logger.exception("Full error stack trace:")
        await manager.disconnect(client_id, chat_id)