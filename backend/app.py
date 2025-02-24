from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from core.connection_manager import manager
from core.ollama_client import ollama_client
from core.system_info import system_info
from routes.health import router as health_router
from routes.websocket import router as websocket_router, websocket_endpoint
from routes.tts import router as tts_router
from core.conversation_manager import conversation_manager

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all routers
app.include_router(health_router)
app.include_router(tts_router)
app.include_router(websocket_router)

# WebSocket endpoint
app.websocket("/ws/{client_id}/{chat_id}")(websocket_endpoint)

@app.get("/system_info")
async def get_system_info():
    return {"specs": system_info.get_system_specs()}

@app.on_event("startup")
async def startup():
    # Wait for database initialization
    await conversation_manager.wait_for_db()
    # Start processing requests
    asyncio.create_task(manager.process_request_queue())

@app.on_event("shutdown")
async def shutdown():
    await ollama_client.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)