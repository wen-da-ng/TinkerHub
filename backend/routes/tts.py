from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from core.tts_service import tts_service

router = APIRouter()

class TTSRequest(BaseModel):
    text: str

@router.post("/tts/play")
async def play_tts(request: TTSRequest):
    try:
        await tts_service.generate_and_play(request.text)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))