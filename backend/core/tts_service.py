import logging
import os
import asyncio
from pathlib import Path
from TTS.api import TTS
import hashlib

logger = logging.getLogger(__name__)

class TTSService:
    _instance = None

    def __init__(self):
        logger.info("Initializing base TTS service structure...")
        self.tts = None
        self.output_dir = Path("audio_cache")
        self.output_dir.mkdir(exist_ok=True)
        logger.info(f"Audio cache directory created at {self.output_dir}")

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = TTSService()
        return cls._instance

    def _init_tts(self):
        """Initialize TTS only when needed"""
        if self.tts is None:
            try:
                logger.info("Initializing TTS model...")
                self.tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2", gpu=True)
                logger.info("TTS model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to initialize TTS: {e}")
                raise

    async def generate_and_play(self, text: str):
        try:
            # Initialize TTS if not already initialized
            if self.tts is None:
                self._init_tts()

            # Generate a unique filename based on text content
            text_hash = hashlib.md5(text.encode()).hexdigest()
            output_path = self.output_dir / f"temp_{text_hash}.wav"
            
            logger.info(f"Generating speech for text: {text[:100]}...")
            
            # Generate speech in a separate thread
            await asyncio.to_thread(
                self.tts.tts_to_file,
                text=text,
                file_path=str(output_path),
                speaker_wav="Jarvis.wav",
                language="en"
            )
            
            logger.info("Speech generation complete, starting playback...")

            # Play the audio file
            if os.name == 'nt':  # Windows
                os.system(f'powershell -c (New-Object Media.SoundPlayer "{output_path}").PlaySync()')
            else:  # Linux/Mac
                os.system(f'mpg123 "{output_path}"')

            logger.info("Audio playback complete")

            # Clean up the temporary file
            output_path.unlink(missing_ok=True)
            logger.info("Temporary audio file cleaned up")
            
        except Exception as e:
            logger.error(f"TTS error: {e}")
            logger.exception("Full error stack trace:")
            raise

    def cleanup(self):
        """Clean up TTS resources"""
        if self.tts is not None:
            try:
                del self.tts
                self.tts = None
                logger.info("Successfully cleaned up TTS model resources")
            except Exception as e:
                logger.error(f"Error cleaning up TTS model: {e}")

        # Clean up any remaining temporary files
        try:
            for file in self.output_dir.glob("temp_*.wav"):
                file.unlink(missing_ok=True)
            logger.info("Cleaned up temporary audio files")
        except Exception as e:
            logger.error(f"Error cleaning up temporary audio files: {e}")