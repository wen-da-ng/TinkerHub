from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from core.connection_manager import manager
from core.ollama_client import ollama_client
from routes.health import router as health_router
from routes.websocket import websocket_endpoint
from routes.tts import router as tts_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(tts_router)
app.websocket("/ws/{client_id}/{chat_id}")(websocket_endpoint)

@app.on_event("startup")
async def startup():
    asyncio.create_task(manager.process_request_queue())

@app.on_event("shutdown")
async def shutdown():
    await ollama_client.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)