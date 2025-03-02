from fastapi import WebSocket, WebSocketDisconnect, HTTPException, APIRouter
import logging
import asyncio
import json
import uuid
import aiosqlite
from datetime import datetime
import aiosqlite
from core.connection_manager import manager
from core.conversation_manager import conversation_manager
from core.tts_service import TTSService
from routes.handlers import ChatHandler, FileHandler, HubHandler, SystemHandler

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

async def websocket_endpoint(websocket: WebSocket, client_id: str, chat_id: str):
    await manager.connect(websocket, client_id, chat_id)
    
    # Initialize handlers
    chat_handler = ChatHandler(websocket, chat_id)
    file_handler = FileHandler(websocket, chat_id)
    hub_handler = HubHandler(websocket, chat_id)
    system_handler = SystemHandler(websocket, chat_id)
    
    try:
        await chat_handler.handle({"type": "get_conversation_history"})
        
        while True:
            data = await websocket.receive_json()
            handled = False
            if not handled:
                handled = await system_handler.handle(data)
            if not handled:
                handled = await file_handler.handle(data)
            if not handled:
                handled = await hub_handler.handle(data)
            
            if not handled and data.get('type') == 'play_audio':
                try:
                    text = data.get('text', '')
                    if text:
                        tts_service = TTSService.get_instance()
                        await tts_service.generate_and_play(text)
                        await websocket.send_json({
                            "type": "audio_complete",
                            "success": True
                        })
                    handled = True
                except Exception as e:
                    logger.error(f"Audio playback error: {e}")
                    logger.exception("Full error stack trace:")
                    await websocket.send_json({
                        "type": "audio_complete",
                        "success": False,
                        "error": str(e)
                    })
                    handled = True

            if not handled:
                data['chatId'] = chat_id
                handled = await chat_handler.handle(data)
            
            if not handled:
                await websocket.send_json({
                    "type": "error",
                    "message": f"Unrecognized message type: {data.get('type')}"
                })

    except WebSocketDisconnect:
        logger.info(f"Client {client_id} disconnected from chat {chat_id}")
        await manager.disconnect(client_id, chat_id)
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        logger.exception("Full error stack trace:")
        await manager.disconnect(client_id, chat_id)