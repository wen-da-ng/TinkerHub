import pytesseract
from PIL import Image
import io
import base64
import logging
import re
import asyncio
from typing import Optional, Dict
from core.image_caption_service import ImageCaptionService

logger = logging.getLogger(__name__)

class OCRService:
    _instance = None

    def __init__(self):
        self.supported_formats = {'.png', '.jpg', '.jpeg', '.bmp', '.tiff'}
        self.tesseract_initialized = False

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = OCRService()
        return cls._instance

    def _init_tesseract(self):
        """Initialize tesseract only when needed"""
        if not self.tesseract_initialized:
            try:
                pytesseract.get_tesseract_version()
                self.tesseract_initialized = True
                logger.info("Tesseract OCR initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Tesseract OCR: {e}")
                raise

    def is_base64_image(self, data: str) -> bool:
        try:
            pattern = r'^data:image\/[a-zA-Z]+;base64,'
            if not re.match(pattern, data):
                return False
            base64_content = data.split(',')[1]
            base64.b64decode(base64_content)
            return True
        except Exception as e:
            logger.error(f"Base64 validation error: {e}")
            return False

    async def process_image(self, image_data: str) -> Dict[str, str]:
        """
        Process image data and extract both text and caption
        Args:
            image_data: Base64 encoded image data
        Returns:
            Dictionary containing extracted text and caption
        """
        try:
            if not self.is_base64_image(image_data):
                return {
                    "text": "Error: Invalid image format or corrupt image data",
                    "caption": None
                }

            # Initialize Tesseract if not already initialized
            if not self.tesseract_initialized:
                self._init_tesseract()

            # Run OCR and caption generation concurrently
            ocr_task = asyncio.create_task(self._extract_text(image_data))
            
            # Get the caption service instance and generate caption
            caption_service = ImageCaptionService.get_instance()
            caption_task = asyncio.create_task(caption_service.generate_caption(image_data))

            extracted_text, caption = await asyncio.gather(ocr_task, caption_task)
            
            # Clean up the extracted text
            cleaned_text = self._clean_extracted_text(extracted_text)
            
            if not cleaned_text:
                cleaned_text = "No text detected in the image"

            return {
                "text": cleaned_text,
                "caption": caption
            }
            
        except Exception as e:
            logger.error(f"Image processing error: {str(e)}")
            logger.exception("Full error stack trace:")
            return {
                "text": f"Error processing image: {str(e)}",
                "caption": None
            }

    async def _extract_text(self, image_data: str) -> str:
        """Extract text using OCR"""
        try:
            base64_content = image_data.split(',')[1]
            image_bytes = base64.b64decode(base64_content)
            image = Image.open(io.BytesIO(image_bytes))
            
            # Perform OCR in a thread pool to avoid blocking
            extracted_text = await asyncio.to_thread(
                pytesseract.image_to_string,
                image,
                config='--psm 3'  # Fully automatic page segmentation
            )
            
            return extracted_text
            
        except Exception as e:
            logger.error(f"OCR extraction error: {str(e)}")
            logger.exception("Full error stack trace:")
            return f"Error extracting text: {str(e)}"

    def _clean_extracted_text(self, text: str) -> str:
        """Clean up the extracted text by removing extra whitespace and invalid characters"""
        if not text:
            return ""
            
        # Remove extra whitespace and normalize line endings
        cleaned = re.sub(r'\s+', ' ', text)
        cleaned = re.sub(r'\n\s*\n', '\n', cleaned)
        
        # Remove any non-printable characters
        cleaned = ''.join(char for char in cleaned if char.isprintable() or char in '\n\t')
        
        return cleaned.strip()

    async def validate_image(self, image_data: str) -> tuple[bool, Optional[str]]:
        """
        Validate image data before processing
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not image_data:
            return False, "No image data provided"
            
        if not self.is_base64_image(image_data):
            return False, "Invalid image format"
            
        try:
            base64_content = image_data.split(',')[1]
            image_bytes = base64.b64decode(base64_content)
            Image.open(io.BytesIO(image_bytes))
            return True, None
        except Exception as e:
            return False, f"Invalid image data: {str(e)}"

    def cleanup(self):
        """Clean up any resources if needed"""
        self.tesseract_initialized = False
        logger.info("OCR service cleaned up")