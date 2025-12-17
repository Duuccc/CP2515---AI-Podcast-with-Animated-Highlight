"""
Debug script to troubleshoot black image generation in Stable Diffusion
Run this to diagnose and fix the issue
"""

import torch
from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler
from PIL import Image
import numpy as np
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_environment():
    """Check CUDA and environment setup"""
    print("\n" + "="*60)
    print("ENVIRONMENT CHECK")
    print("="*60)
    
    print(f"PyTorch version: {torch.__version__}")
    print(f"CUDA available: {torch.cuda.is_available()}")
    
    if torch.cuda.is_available():
        print(f"CUDA version: {torch.version.cuda}")
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f} GB")
        print(f"Current VRAM allocated: {torch.cuda.memory_allocated(0) / 1024**3:.2f} GB")
    else:
        print("⚠ CUDA not available - using CPU (very slow)")


def test_basic_generation():
    """Test basic image generation with different configurations"""
    print("\n" + "="*60)
    print("TEST 1: Basic Generation (FP32)")
    print("="*60)
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    
    try:
        # Load with FP32 (more stable, but uses more VRAM)
        print("Loading model in FP32...")
        pipe = StableDiffusionPipeline.from_pretrained(
            "runwayml/stable-diffusion-v1-5",
            torch_dtype=torch.float32,  # Use FP32 first to test
            safety_checker=None,
            requires_safety_checker=False
        )
        pipe = pipe.to(device)
        
        # Simple prompt
        prompt = "tiny chibi character sitting in a professional podcast studio, big headphones, condenser microphone, monitors, warm orange-blue lighting, cinematic atmosphere but cute, anime chibi style, crisp outlines, HD detail"

        print(f"Generating with prompt: '{prompt}'")
        result = pipe(
            prompt=prompt,
            num_inference_steps=25,
            guidance_scale=7.5,
            generator=torch.Generator(device=device).manual_seed(42)
        )
        
        image = result.images[0]
        
        # Analyze image
        img_array = np.array(image)
        print(f"\nImage statistics:")
        print(f"  Shape: {img_array.shape}")
        print(f"  Mean: {img_array.mean():.2f}")
        print(f"  Std: {img_array.std():.2f}")
        print(f"  Min: {img_array.min()}")
        print(f"  Max: {img_array.max()}")
        
        if img_array.mean() < 10:
            print("❌ BLACK IMAGE DETECTED!")
            return False
        else:
            print("✅ Image generated successfully!")
            image.save("test_fp1.png")
            print("Saved as: test_fp32.png")
            return True
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
    finally:
        if 'pipe' in locals():
            del pipe
        torch.cuda.empty_cache()


def test_fp16_generation():
    """Test with FP16 (memory efficient but can cause issues)"""
    print("\n" + "="*60)
    print("TEST 2: FP16 Generation")
    print("="*60)
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    
    try:
        print("Loading model in FP16...")
        pipe = StableDiffusionPipeline.from_pretrained(
            "runwayml/stable-diffusion-v1-5",
            torch_dtype=torch.float16,
            safety_checker=None,
            requires_safety_checker=False
        )
        pipe = pipe.to(device)
        
        prompt = "a beautiful sunset over the ocean, vibrant colors, high quality"
        
        print(f"Generating with prompt: '{prompt}'")
        
        # Generate WITHOUT autocast
        result = pipe(
            prompt=prompt,
            num_inference_steps=25,
            guidance_scale=7.5,
            generator=torch.Generator(device=device).manual_seed(42)
        )
        
        image = result.images[0]
        img_array = np.array(image)
        
        print(f"\nImage statistics:")
        print(f"  Mean: {img_array.mean():.2f}")
        print(f"  Std: {img_array.std():.2f}")
        
        if img_array.mean() < 10:
            print("❌ BLACK IMAGE with FP16!")
            print("💡 Solution: Use FP32 or try different model")
            return False
        else:
            print("✅ FP16 works!")
            image.save("test_fp16.png")
            return True
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
    finally:
        if 'pipe' in locals():
            del pipe
        torch.cuda.empty_cache()


def test_with_optimizations():
    """Test with all optimizations (what you're using)"""
    print("\n" + "="*60)
    print("TEST 3: With Optimizations (Your Current Setup)")
    print("="*60)
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    
    try:
        print("Loading model with all optimizations...")
        pipe = StableDiffusionPipeline.from_pretrained(
            "runwayml/stable-diffusion-v1-5",
            torch_dtype=torch.float16,
            safety_checker=None,
            requires_safety_checker=False
        )
        pipe = pipe.to(device)
        
        # Add optimizations
        pipe.scheduler = DPMSolverMultistepScheduler.from_config(
            pipe.scheduler.config
        )
        pipe.enable_attention_slicing(1)
        pipe.enable_vae_slicing()
        
        try:
            pipe.enable_xformers_memory_efficient_attention()
            print("✓ xformers enabled")
        except:
            print("✓ xformers not available")
        
        prompt = "professional podcast studio, modern interior, warm lighting, detailed"
        
        print(f"Generating with prompt: '{prompt}'")
        result = pipe(
            prompt=prompt,
            negative_prompt="blurry, bad quality, distorted",
            num_inference_steps=20,
            guidance_scale=7.5,
            generator=torch.Generator(device=device).manual_seed(42)
        )
        
        image = result.images[0]
        img_array = np.array(image)
        
        print(f"\nImage statistics:")
        print(f"  Mean: {img_array.mean():.2f}")
        print(f"  Std: {img_array.std():.2f}")
        
        if img_array.mean() < 10:
            print("❌ BLACK IMAGE with optimizations!")
            return False
        else:
            print("✅ Works with optimizations!")
            image.save("test_optimized.png")
            return True
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
    finally:
        if 'pipe' in locals():
            del pipe
        torch.cuda.empty_cache()


def main():
    """Run all diagnostic tests"""
    print("\n" + "🔍 " + "="*58)
    print("STABLE DIFFUSION BLACK IMAGE DIAGNOSTIC")
    print("="*60 + "\n")
    
    check_environment()
    
    # Run tests
    test1 = test_basic_generation()
    test2 = test_fp16_generation()
    test3 = test_with_optimizations()
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY & RECOMMENDATIONS")
    print("="*60)
    
    if test1 and test2 and test3:
        print("✅ All tests passed! Your setup is working correctly.")
        print("💡 The black image issue might be due to:")
        print("   1. Empty or invalid prompts")
        print("   2. Wrong prompt formatting")
        print("   3. Need better/more descriptive prompts")
        
    elif test1 and not test2:
        print("⚠ FP16 causing black images on your GPU")
        print("💡 SOLUTION: Switch to FP32")
        print("\nIn stable_diffusion.py, change:")
        print("   torch_dtype=torch.float16  →  torch_dtype=torch.float32")
        print("\nNote: Uses more VRAM but generates proper images")
        
    elif not test1:
        print("❌ Basic generation failed")
        print("💡 Possible issues:")
        print("   1. Model not downloaded correctly")
        print("   2. CUDA/PyTorch installation issue")
        print("   3. Insufficient VRAM")
        print("\nTry:")
        print("   pip install --upgrade torch torchvision")
        print("   pip install --upgrade diffusers transformers")
    
    print("\n" + "="*60)
    print("Next steps:")
    print("1. Check the generated test images")
    print("2. If FP32 works but FP16 doesn't, update your code to use FP32")
    print("3. Make sure prompts are descriptive and not empty")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()