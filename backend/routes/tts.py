from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from core.tts_service import TTSService

router = APIRouter()

class TTSRequest(BaseModel):
    text: str

@router.post("/tts/play")
async def play_tts(request: TTSRequest):
    try:
        # Get TTS service instance only when needed
        tts_service = TTSService.get_instance()
        await tts_service.generate_and_play(request.text)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.on_event("shutdown")
async def cleanup():
    """Clean up TTS resources on shutdown"""
    try:
        tts_service = TTSService.get_instance()
        tts_service.cleanup()
    except Exception as e:
        print(f"Error during TTS cleanup: {e}")