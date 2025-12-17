# Stable Diffusion Setup Guide

## Overview
Stable Diffusion has been integrated as a **free, local alternative** to DALL-E for generating video backgrounds. It runs on your GPU (GTX 1650) without API costs.

## Hardware Requirements
- ✅ **Your Setup**: GTX 1650 (4GB VRAM) + 8GB RAM
- ✅ **Optimized**: The code is configured for 4GB VRAM

## Installation

1. **Install dependencies**:
```bash
cd backend
pip install diffusers accelerate transformers safetensors
```

2. **Verify CUDA**:
```python
python -c "import torch; print('CUDA available:', torch.cuda.is_available())"
```

## Configuration

In `backend/app/core/config.py`:

```python
USE_STABLE_DIFFUSION: bool = True  # Enable/disable
SD_IMAGE_WIDTH: int = 512         # 512 for 4GB VRAM (safe)
SD_IMAGE_HEIGHT: int = 896        # Vertical format (9:16)
SD_INFERENCE_STEPS: int = 20      # 20 = fast, 30-50 = quality
```

## Performance Tips for GTX 1650

### If you get "Out of Memory" errors:

1. **Reduce image size**:
   ```python
   SD_IMAGE_WIDTH: int = 384
   SD_IMAGE_HEIGHT: int = 672
   ```

2. **Reduce inference steps**:
   ```python
   SD_INFERENCE_STEPS: int = 15  # Faster, slightly lower quality
   ```

3. **Close other GPU applications** (games, other ML models)

4. **Enable CPU offload** (uncomment in `stable_diffusion.py`):
   ```python
   self.pipe.enable_model_cpu_offload()
   ```

## How It Works

1. **First generation**: Downloads model (~4GB) - one time only
2. **Subsequent generations**: Uses cached model (fast)
3. **Generation time**: ~10-30 seconds per image on GTX 1650
4. **Memory usage**: ~3-4GB VRAM with optimizations

## Priority Order

The system tries backgrounds in this order:
1. **Stable Diffusion** (if `USE_STABLE_DIFFUSION = True`) - FREE, LOCAL
2. **DALL-E** (if `USE_AI_BACKGROUND = True`) - PAID, API
3. **Animated Gradient** (fallback) - FREE, NO GPU

## Troubleshooting

### "CUDA out of memory"
- Reduce `SD_IMAGE_WIDTH` and `SD_IMAGE_HEIGHT`
- Reduce `SD_INFERENCE_STEPS`
- Close other applications using GPU

### "Model download failed"
- Check internet connection
- Model is ~4GB, ensure enough disk space
- Try again, download resumes automatically

### "Generation too slow"
- Normal for GTX 1650: 10-30 seconds per image
- Reduce `SD_INFERENCE_STEPS` for speed
- Consider using gradient backgrounds for faster processing

## Model Information

- **Model**: `runwayml/stable-diffusion-v1-5`
- **Size**: ~4GB (downloads once, cached locally)
- **Location**: `~/.cache/huggingface/hub/` (automatic)

## Cost Comparison

| Method | Cost | Speed | Quality |
|--------|------|-------|---------|
| Stable Diffusion | FREE | 10-30s | Good |
| DALL-E 3 | $0.04/image | 5-10s | Excellent |
| Gradient | FREE | Instant | Basic |

