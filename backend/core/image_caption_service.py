from transformers import Blip2Processor, Blip2ForConditionalGeneration
import torch
from PIL import Image
import io
import base64
import logging
import re
import asyncio
import gc

logger = logging.getLogger(__name__)

class ImageCaptionService:
    _instance = None
    
    def __init__(self):
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA GPU is required but not available")
            
        self.device = "cuda"
        self.model_name = "Salesforce/blip2-opt-2.7b"
        self.model = None
        self.processor = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = ImageCaptionService()
        return cls._instance

    def _init_model(self):
        """Initialize the BLIP-2 model using GPU only"""
        if self.model is not None:
            return

        try:
            logger.info("Initializing BLIP-2 model on GPU")
            
            # Clear GPU memory before loading model
            torch.cuda.empty_cache()
            gc.collect()
            
            # Load processor and model
            self.processor = Blip2Processor.from_pretrained(self.model_name)
            self.model = Blip2ForConditionalGeneration.from_pretrained(
                self.model_name,
                torch_dtype=torch.float16,
                device_map="auto"
            ).to(self.device)
            
            # Enable CUDA optimizations
            torch.backends.cudnn.benchmark = True
            
            logger.info("BLIP-2 model initialized successfully on GPU")
            
            # Perform a test inference
            self._test_model()
            
        except Exception as e:
            logger.error(f"Failed to initialize BLIP-2 model: {e}")
            logger.exception("Full error stack trace:")
            raise

    def _test_model(self):
        """Perform a test inference to verify model setup"""
        try:
            test_image = Image.new('RGB', (224, 224), color='white')
            inputs = self.processor(images=test_image, return_tensors="pt").to(self.device)
            with torch.no_grad():
                _ = self.model.generate(
                    **inputs,
                    max_new_tokens=50,
                    num_beams=5,
                    early_stopping=True
                )
            logger.info("Model test inference successful")
        except Exception as e:
            logger.error(f"Model test inference failed: {e}")
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
        """Generate a caption for the given image using GPU"""
        try:
            if not self.is_base64_image(image_data):
                return "Error: Invalid image format"

            # Initialize model if not already initialized
            if self.model is None:
                self._init_model()

            # Extract base64 content and convert to image
            base64_content = image_data.split(',')[1]
            image_bytes = base64.b64decode(base64_content)
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

            # Process image in a thread pool to avoid blocking
            def process_image():
                try:
                    # Clear GPU memory before processing
                    torch.cuda.empty_cache()
                    gc.collect()

                    inputs = self.processor(images=image, return_tensors="pt").to(self.device)
                    
                    with torch.no_grad():
                        output = self.model.generate(
                            **inputs,
                            max_new_tokens=50,
                            num_beams=5,
                            early_stopping=True
                        )
                    
                    # Clear GPU memory after processing
                    torch.cuda.empty_cache()
                    gc.collect()
                    
                    return self.processor.decode(output[0], skip_special_tokens=True)
                except Exception as e:
                    logger.error(f"Error in image processing: {e}")
                    raise

            caption = await asyncio.to_thread(process_image)
            
            if not caption:
                return "No visual content could be described"
                
            return caption

        except Exception as e:
            logger.error(f"Caption generation error: {str(e)}")
            logger.exception("Full error stack trace:")
            return f"Error generating caption: {str(e)}"

    async def validate_image(self, image_data: str) -> tuple[bool, str | None]:
        """Validate image data before processing"""
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
        """Clean up GPU resources"""
        if self.model is not None:
            try:
                del self.model
                del self.processor
                self.model = None
                self.processor = None
                torch.cuda.empty_cache()
                gc.collect()
                logger.info("Successfully cleaned up image caption model resources")
            except Exception as e:
                logger.error(f"Error cleaning up image caption model: {e}")