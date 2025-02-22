from transformers import Blip2Processor, Blip2ForConditionalGeneration
import torch
from PIL import Image
import io
import base64
import logging
import re
import asyncio

logger = logging.getLogger(__name__)

class ImageCaptionService:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model_name = "Salesforce/blip2-opt-2.7b"
        self._init_model()

    def _init_model(self):
        """Initialize the BLIP-2 model"""
        try:
            logger.info("Initializing BLIP-2 model...")
            self.model = Blip2ForConditionalGeneration.from_pretrained(
                self.model_name, 
                torch_dtype=torch.float16, 
                device_map="auto"
            ).to(self.device)
            
            self.processor = Blip2Processor.from_pretrained(self.model_name)
            logger.info(f"BLIP-2 model initialized successfully on {self.device}")
        except Exception as e:
            logger.error(f"Failed to initialize BLIP-2 model: {e}")
            logger.exception("Full error stack trace:")
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

    async def generate_caption(self, image_data: str) -> str:
        """
        Generate a caption for the given image
        Args:
            image_data: Base64 encoded image data
        Returns:
            Generated caption or error message
        """
        try:
            if not self.is_base64_image(image_data):
                return "Error: Invalid image format"

            # Extract base64 content and convert to image
            base64_content = image_data.split(',')[1]
            image_bytes = base64.b64decode(base64_content)
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

            # Process image in a thread pool to avoid blocking
            def process_image():
                inputs = self.processor(images=image, return_tensors="pt").to(self.device, torch.float16)
                with torch.no_grad():
                    output = self.model.generate(**inputs, max_length=50)
                return self.processor.decode(output[0], skip_special_tokens=True)

            caption = await asyncio.to_thread(process_image)
            
            if not caption:
                return "No visual content could be described"
                
            return caption

        except Exception as e:
            logger.error(f"Caption generation error: {str(e)}")
            logger.exception("Full error stack trace:")
            return f"Error generating caption: {str(e)}"

    async def validate_image(self, image_data: str) -> tuple[bool, str | None]:
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

image_caption_service = ImageCaptionService()