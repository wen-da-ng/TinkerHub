import logging
import os
import asyncio
import re
from pathlib import Path
from TTS.api import TTS
import torch
import hashlib
import unicodedata

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
                # Get device
                device = "cuda" if torch.cuda.is_available() else "cpu"
                # Initialize model and move to appropriate device
                self.tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)
                logger.info(f"TTS model loaded successfully on {device}")
            except Exception as e:
                logger.error(f"Failed to initialize TTS: {e}")
                raise

    def preprocess_markdown(self, text: str) -> str:
        """Remove or convert markdown formatting to make text suitable for TTS"""
        if not text:
            return ""
            
        # Handle array-like text
        if (text.startswith('[') and text.endswith(']')) or (text.startswith("['") and text.endswith("']")):
            try:
                # Extract quoted content and join with proper spacing
                items = re.findall(r'[\'"](.+?)[\'"]', text)
                if items:
                    # Join items into a proper paragraph
                    text = '. '.join(item.strip() for item in items if item.strip())
                    # Ensure proper sentence ending
                    if not text.endswith(('.', '!', '?')):
                        text += '.'
            except Exception as e:
                logger.warning(f"Error processing array-like text: {e}")
        
        # Common markdown formatting
        text = self._remove_markdown_formatting(text)
        
        # Clean up non-standard characters that TTS might struggle with
        text = self._normalize_text(text)
        
        return text.strip()

    def _remove_markdown_formatting(self, text: str) -> str:
        """Remove markdown formatting elements"""
        # Remove heading markers
        text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)
        
        # Remove emphasis markers
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)  # Bold **text**
        text = re.sub(r'\*(.+?)\*', r'\1', text)      # Italic *text*
        text = re.sub(r'__(.+?)__', r'\1', text)      # Bold __text__
        text = re.sub(r'_(.+?)_', r'\1', text)        # Italic _text_
        
        # Remove code formatting
        text = re.sub(r'`([^`]+?)`', r'\1', text)     # Inline code
        text = re.sub(r'```[\w-]*\n', '', text)       # Code block start
        text = re.sub(r'```', '', text)               # Code block end
        
        # Convert links [text](url) to just text
        text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)
        
        # Remove horizontal rules
        text = re.sub(r'^(---|\*\*\*|___)$', '', text, flags=re.MULTILINE)
        
        # Convert list items to natural language
        text = re.sub(r'^\s*[\-\*\+]\s+', '• ', text, flags=re.MULTILINE) 
        text = re.sub(r'^\s*\d+\.\s+', '. ', text, flags=re.MULTILINE)
        
        # Remove HTML tags
        text = re.sub(r'<(?!think)(?!\/think)[^>]+>', '', text)
        
        # Remove userStyle tags that might come from Claude
        text = re.sub(r'<userStyle>.*?</userStyle>', '', text)
        
        return text

    def _normalize_text(self, text: str) -> str:
        """Normalize text for better TTS processing"""
        # Fix punctuation sequences
        text = re.sub(r'\.{2,}', '...', text)  # Convert multiple periods to ellipsis
        text = re.sub(r'\.(\s*\.)+', '.', text)  # Remove redundant periods
        text = re.sub(r'\,(\s*\.)+', '.', text)  # Fix comma-period sequences
        
        # Remove solitary periods on their own line
        text = re.sub(r'^\s*\.\s*$', '', text, flags=re.MULTILINE)
        
        # Normalize whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)  # Normalize paragraph breaks
        text = re.sub(r'\s{2,}', ' ', text)     # Normalize spaces
        
        # Ensure proper sentence breaks
        text = re.sub(r'([.!?])\s+', r'\1 ', text)  # Ensure single space after sentence end
        
        # Fix common issues with sentence breaks
        text = re.sub(r'([.!?])\s*([A-Z])', r'\1 \2', text)  # Ensure space between sentences
        
        return text

    async def generate_and_play(self, text: str):
        try:
            # Log the original text for debugging (truncated)
            logger.debug(f"Original text for TTS (truncated): {text[:200]}...")
            
            # Preprocess markdown before TTS
            cleaned_text = self.preprocess_markdown(text)
            
            # Log the cleaned text (truncated)
            logger.debug(f"Cleaned text for TTS (truncated): {cleaned_text[:200]}...")
            
            # Initialize TTS if not already initialized
            if self.tts is None:
                self._init_tts()

            # Generate a unique filename based on text content
            text_hash = hashlib.md5(cleaned_text.encode()).hexdigest()
            output_path = self.output_dir / f"temp_{text_hash}.wav"
            
            logger.info(f"Generating speech for text: {cleaned_text[:100]}...")
            
            # Generate speech in a separate thread
            await asyncio.to_thread(
                self.tts.tts_to_file,
                text=cleaned_text,
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