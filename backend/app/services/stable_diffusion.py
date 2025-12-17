import os
import torch
from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler
from PIL import Image
import gc
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class StableDiffusionService:
    """
    Stable Diffusion service optimized for GTX 1650 (4GB VRAM)
    Handles image generation from text prompts
    """
    
    def __init__(self, model_id: str = "runwayml/stable-diffusion-v1-5"):
        """
        Initialize Stable Diffusion service
        
        Args:
            model_id: HuggingFace model ID for Stable Diffusion
        """
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model_id = model_id
        self.pipe = None
        self._is_loaded = False
        
        logger.info(f"StableDiffusionService initialized on device: {self.device}")
        
        if self.device == "cuda":
            gpu_name = torch.cuda.get_device_name(0)
            vram_gb = torch.cuda.get_device_properties(0).total_memory / 1024**3
            logger.info(f"GPU: {gpu_name}, VRAM: {vram_gb:.2f} GB")
    
    def load_model(self):
        """Load Stable Diffusion model with memory optimizations"""
        if self._is_loaded:
            logger.info("Model already loaded")
            return
        
        logger.info(f"Loading Stable Diffusion model: {self.model_id}")
        
        try:
            # CRITICAL FIX: Use dtype instead of torch_dtype (deprecated warning in your log)
            # Also, for GTX 1650, float16 can cause black images. Try float32 first.
            self.pipe = StableDiffusionPipeline.from_pretrained(
                self.model_id,
                torch_dtype=torch.float32,  # Changed from torch_dtype
                safety_checker=None,
                requires_safety_checker=False,
            )
            
            # Move to device
            self.pipe = self.pipe.to(self.device)
            
            # Use DPM++ scheduler (faster, fewer steps needed)
            self.pipe.scheduler = DPMSolverMultistepScheduler.from_config(
                self.pipe.scheduler.config
            )
            
            # Memory optimizations for low VRAM GPUs
            self.pipe.enable_attention_slicing(1)
            self.pipe.enable_vae_slicing()
            
            # Try to enable xformers if available
            try:
                self.pipe.enable_xformers_memory_efficient_attention()
                logger.info("✓ xformers memory efficient attention enabled")
            except Exception:
                logger.info("✓ Using standard attention (xformers not available)")
            
            self._is_loaded = True
            logger.info("✓ Model loaded successfully with optimizations")
            
        except Exception as e:
            logger.error(f"✗ Failed to load model: {e}")
            raise
    
    def unload_model(self):
        """Unload model from memory to free VRAM"""
        if self.pipe is not None:
            del self.pipe
            self.pipe = None
            self._is_loaded = False
            
            gc.collect()
            if self.device == "cuda":
                torch.cuda.empty_cache()
            
            logger.info("Model unloaded from memory")
    
    def generate_image(
        self,
        prompt: str,
        negative_prompt: str = "blurry, bad quality, distorted, ugly, low resolution",
        width: int = 512,
        height: int = 512,
        num_inference_steps: int = 20,
        guidance_scale: float = 7.5,
        seed: Optional[int] = None
    ) -> Image.Image:
        """
        Generate image from text prompt
        
        Args:
            prompt: Text description of desired image
            negative_prompt: Things to avoid in generation
            width: Image width (divisible by 8, recommend 512 for GTX 1650)
            height: Image height (divisible by 8, recommend 512 for GTX 1650)
            num_inference_steps: Denoising steps (20-25 optimal for DPM++)
            guidance_scale: Prompt adherence (7-8 recommended)
            seed: Random seed for reproducibility
            
        Returns:
            PIL Image object
        """
        # Ensure model is loaded
        if not self._is_loaded:
            self.load_model()
        
        # Validate dimensions
        if width % 8 != 0 or height % 8 != 0:
            raise ValueError("Width and height must be divisible by 8")
        
        # Validate prompt is not empty
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty")
        
        # Set random seed
        generator = None
        if seed is not None:
            generator = torch.Generator(device=self.device).manual_seed(seed)
        
        # Clear CUDA cache before generation
        if self.device == "cuda":
            torch.cuda.empty_cache()
        
        logger.info(f"Generating image: '{prompt[:60]}...'")
        logger.info(f"Config: {width}x{height}, steps={num_inference_steps}, guidance={guidance_scale}, seed={seed}")
        
        try:
            # Generate image WITHOUT autocast - common cause of black images
            result = self.pipe(
                prompt=prompt,
                negative_prompt=negative_prompt,
                width=width,
                height=height,
                num_inference_steps=num_inference_steps,
                guidance_scale=guidance_scale,
                generator=generator
            )
            
            image = result.images[0]
            
            # Debug: Check if image is all black
            import numpy as np
            img_array = np.array(image)
            pixel_mean = img_array.mean()
            pixel_std = img_array.std()
            
            logger.info(f"✓ Image generated - Mean: {pixel_mean:.2f}, Std: {pixel_std:.2f}")
            
            if pixel_mean < 10 and pixel_std < 5:
                logger.warning("⚠ Generated image appears to be black/empty!")
                logger.warning(f"⚠ Prompt used: '{prompt}'")
                logger.warning(f"⚠ Try: 1) Better prompt 2) Different seed 3) More steps")
            
            return image
            
        except torch.cuda.OutOfMemoryError:
            logger.error("✗ CUDA out of memory. Try reducing resolution or unload other models")
            if self.device == "cuda":
                torch.cuda.empty_cache()
            raise
        except Exception as e:
            logger.error(f"✗ Error generating image: {e}")
            raise
    
    def save_image(self, image: Image.Image, output_path: str) -> str:
        """
        Save generated image to file
        
        Args:
            image: PIL Image to save
            output_path: Path where image will be saved
            
        Returns:
            Full path to saved image
        """
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Save image
            image.save(output_path, quality=95)
            logger.info(f"✓ Image saved: {output_path}")
            
            return output_path
            
        except Exception as e:
            logger.error(f"✗ Failed to save image: {e}")
            raise
    
    def is_available(self) -> bool:
        """Check if CUDA is available"""
        return torch.cuda.is_available()
    
    def get_device_info(self) -> dict:
        """Get device information"""
        info = {
            "device": self.device,
            "cuda_available": torch.cuda.is_available(),
            "model_loaded": self._is_loaded
        }
        
        if self.device == "cuda":
            info.update({
                "gpu_name": torch.cuda.get_device_name(0),
                "vram_total_gb": torch.cuda.get_device_properties(0).total_memory / 1024**3,
                "vram_allocated_gb": torch.cuda.memory_allocated(0) / 1024**3,
                "vram_reserved_gb": torch.cuda.memory_reserved(0) / 1024**3
            })
        
        return info
    
    def __del__(self):
        """Cleanup on deletion"""
        self.unload_model()