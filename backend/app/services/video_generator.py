from moviepy.editor import (
    AudioFileClip,
    CompositeVideoClip
)
from moviepy.video.VideoClip import VideoClip
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import logging
from typing import Dict, List, Optional, Tuple
import os
import tempfile
import textwrap
from app.services.stable_diffusion import StableDiffusionService
import requests
from io import BytesIO
from app.core.config import settings
from datetime import datetime

logger = logging.getLogger(__name__)

class VideoGenerator:
    """
    Generate animated social media-ready highlight videos with MoviePy
    """
    
    def __init__(self):
        self.width = 1080
        self.height = 1920
        self.fps = 30
        
        # Color scheme
        self.bg_color_start = (59, 130, 246)   # Blue
        self.bg_color_end = (147, 51, 234)     # Purple
        self.text_color = (255, 255, 255)      # White
        self.accent_color = (34, 211, 238)     # Cyan
        
        # Try to find a suitable font
        self.font_path = self._find_font()

        self.sd_service = StableDiffusionService()  
        
        current_file_dir = os.path.dirname(os.path.abspath(__file__))
        # Go up to backend directory (from app/services/ -> app -> backend)
        backend_dir = os.path.dirname(os.path.dirname(current_file_dir))
        
        # Create directories in backend root
        self.images_dir = os.path.join(backend_dir, "images")
        self.videos_dir = backend_dir
        os.makedirs(self.images_dir, exist_ok=True)
        os.makedirs(self.videos_dir, exist_ok=True)

        logger.info(f"VideoGenerator initialized: {self.width}x{self.height} @ {self.fps}fps")
        logger.info(f"Using font: {self.font_path if self.font_path else 'default'}")
    
    def _find_font(self) -> Optional[str]:
        """Try to find a suitable font path for PIL"""
        # Common font paths on different systems
        font_paths = [
            # Windows
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/calibri.ttf",
            "C:/Windows/Fonts/calibrib.ttf",
            # Linux
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            # macOS
            "/System/Library/Fonts/Helvetica.ttc",
            "/Library/Fonts/Arial.ttf",
        ]
        
        for path in font_paths:
            if os.path.exists(path):
                try:
                    # Test if font can be loaded
                    ImageFont.truetype(path, size=80)
                    return path
                except:
                    continue
        
        return None
    
    def _create_text_image(
        self,
        text: str,
        width: int,
        font_size: int = 65,
        color: Tuple[int, int, int] = (255, 255, 255),
        stroke_color: Tuple[int, int, int] = (0, 0, 0),
        stroke_width: int = 3
    ) -> Image.Image:
        """Create a PIL image with text rendered on transparent background"""
        # Load font
        font = None
        if self.font_path:
            try:
                font = ImageFont.truetype(self.font_path, size=font_size)
            except:
                pass
        
        if font is None:
            try:
                # Try to load default font with size
                font = ImageFont.load_default()
            except:
                font = None
        
        # Wrap text to fit width
        max_chars_per_line = width // (font_size // 2) if font else width // 20
        wrapped_lines = textwrap.wrap(text, width=max_chars_per_line)
        
        # Calculate text dimensions
        line_height = font_size
        if font:
            # Get text dimensions
            bbox = None
            for line in wrapped_lines:
                try:
                    bbox = font.getbbox(line)
                    if bbox:
                        line_height = bbox[3] - bbox[1] if len(bbox) == 4 else font_size
                        break
                except:
                    # Fallback if getbbox not available
                    try:
                        bbox = font.getsize(line)
                        line_height = bbox[1] if len(bbox) >= 2 else font_size
                        break
                    except:
                        pass
            
        text_height = len(wrapped_lines) * (line_height + 10) + 20
        text_width = width
        
        # Create image with transparent background
        img = Image.new('RGBA', (text_width, text_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Draw text with stroke
        y_offset = 10
        for line in wrapped_lines:
            # Calculate text width for centering
            if font:
                try:
                    if hasattr(font, 'getbbox'):
                        bbox = font.getbbox(line)
                        line_width = bbox[2] - bbox[0]
                    else:
                        line_width = font.getsize(line)[0]
                except:
                    line_width = len(line) * font_size // 2
            else:
                line_width = len(line) * font_size // 2
            
            x_offset = (text_width - line_width) // 2
            
            if font:
                # Draw stroke (outline)
                if stroke_width > 0:
                    for dx in [-stroke_width, 0, stroke_width]:
                        for dy in [-stroke_width, 0, stroke_width]:
                            if dx != 0 or dy != 0:
                                try:
                                    draw.text(
                                        (x_offset + dx, y_offset + dy),
                                        line,
                                        font=font,
                                        fill=stroke_color
                                    )
                                except:
                                    pass
                
                # Draw main text
                try:
                    draw.text((x_offset, y_offset), line, font=font, fill=color)
                except:
                    draw.text((x_offset, y_offset), line, fill=color)

            else:
                # Fallback without font
                if stroke_width > 0:
                    for dx in [-stroke_width, 0, stroke_width]:
                        for dy in [-stroke_width, 0, stroke_width]:
                            if dx != 0 or dy != 0:
                                draw.text((x_offset + dx, y_offset + dy), line, fill=stroke_color)
                draw.text((x_offset, y_offset), line, fill=color)
            
            y_offset += line_height + 10
        
        return img
    
    def _create_background_from_image(self, pil_image: Image.Image, duration: float) -> VideoClip:
        """Convert PIL image to animated video clip background"""
        try:
            # Resize image to match video dimensions
            pil_image = pil_image.resize((self.width, self.height), Image.Resampling.LANCZOS)
            
            # Convert to numpy array
            img_array = np.array(pil_image.convert('RGB'))
            
            # Ensure correct shape (height, width, 3)
            if len(img_array.shape) == 2:
                # Grayscale, convert to RGB
                img_array = np.stack([img_array, img_array, img_array], axis=2)
            
            def make_frame(t):
                # Optionally add subtle animation (zoom, pan, or fade)
                # For now, return static frame
                return img_array
            
            clip = VideoClip(make_frame, duration=duration)
            clip = clip.set_fps(self.fps)
            return clip
        except Exception as e:
            logger.warning(f"Failed to create background from image: {e}")
            return None
    
    def _create_prompt(self, text: str, style: str) -> str:
        """
        Create optimized Stable Diffusion prompt from highlight text
        
        Args:
            text: Highlight text
            style: Visual style context
            
        Returns:
            Optimized prompt string
        """
        text_lower = text.lower()
        
        # Determine mood/style based on content
        if any(word in text_lower for word in ['exciting', 'amazing', 'breakthrough', 'incredible', 'wow']):
            mood = "energetic, dynamic, vibrant"
        elif any(word in text_lower for word in ['serious', 'important', 'critical', 'problem', 'challenge']):
            mood = "serious, focused, professional"
        elif any(word in text_lower for word in ['calm', 'peaceful', 'serene', 'gentle']):
            mood = "calm, peaceful, serene"
        else:
            mood = "balanced, contemporary"
        
        # Build prompt based on style
        if style == "podcast studio":
            prompt = f"Cute chibi anime character doing a podcast, energetic and dynamic atmosphere."
        elif style == "abstract":
            prompt = f"Chibi anime character hosting a podcast with a serious and focused mood. Clean studio setup, high-quality microphone, calm lighting, neutral colors, organized desk. serious, focused, professional"
        elif style == "nature":
            prompt = f"Soft chibi anime character doing a peaceful and serene podcast session. Pastel colors, gentle lighting, cozy room, soft shadows, relaxed expression, cute studio microphone. calm, peaceful, serene"
        elif style == "tech":
            prompt = f"Chibi anime character recording a podcast, balanced and contemporary aesthetic. Modern studio desk, charming expression, clean lineart, soft but clear lighting. balanced, contemporary, modern"
        else:
            prompt = f"{style} background, {mood}, professional, high quality, detailed"
        
        return prompt
    
    def generate_background_image(
        self,
        text: str,
        style: str = "podcast studio",
        seed: Optional[int] = None
    ) -> Image.Image:
        """
        Generate background image based on highlight text
        
        Args:
            text: Highlight text to generate image from
            style: Visual style/context (e.g., "podcast studio", "abstract", "nature")
            seed: Random seed for reproducibility
            
        Returns:
            PIL Image
        """
        try:
            # Create optimized prompt from highlight text
            prompt = self._create_prompt(text, style)
            prompt = "anime style illustration, high quality, detailed anime character, young anime girl hosting a podcast, sitting at a desk, professional podcast setup, headphones on, modern podcast studio, soft studio lighting, cozy atmosphere, clean background, sharp lineart, vibrant colors, cel shading, depth of field, 4k, masterpiece, best quality"
            
            logger.info(f"Generating background for: '{text[:50]}...'")
            
            # Generate image using SD service
            image = self.sd_service.generate_image(
                prompt=prompt,
                negative_prompt="low quality, worst quality, blurry, jpeg artifacts, bad anatomy, extra fingers, missing fingers, deformed face, cross-eye, poorly drawn hands, watermark, logo, text, cropped, out of frame, nsfw",
                width=512,
                height=512,
                num_inference_steps=20,
                guidance_scale=7.5,
                seed=seed
            )
            
            image_path = os.path.join("images", f"image__{datetime.now().strftime("%Y%m%d_%H%M%S")}.png")
            self.sd_service.save_image(image, image_path)

            return image
            
        except Exception as e:
            logger.error(f"Failed to generate image: {e}")
            raise
    
    def generate_images_for_highlights(
        self,
        highlights: List[str],
        style: str = "podcast studio",
        seed: Optional[int] = None
    ) -> List[Image.Image]:
        """
        Generate multiple background images for podcast highlights
        
        Args:
            highlights: List of highlight text snippets
            style: Visual style for all images
            seed: Base seed (will be incremented for each image)
            
        Returns:
            List of PIL Images
        """
        images = []
        
        for i, highlight in enumerate(highlights):
            logger.info(f"Processing highlight {i+1}/{len(highlights)}")
            
            # Use seed + i for variation while maintaining consistency
            current_seed = seed + i if seed is not None else None
            
            try:
                image = self.generate_background_image(
                    text=highlight,
                    style=style,
                    seed=current_seed
                )
                images.append(image)
                
                # Save individual image
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                image_path = os.path.join(self.images_dir, f"highlight_{i}_{timestamp}.png")
                self.sd_service.save_image(image, image_path)
                
            except Exception as e:
                logger.error(f"Failed to generate image for highlight {i}: {e}")
                # Continue with other highlights
                continue
        
        logger.info(f"Generated {len(images)} images")
        return images

    def create_video_from_images(
        self,
        images: List[Image.Image],
        audio_path: Optional[str] = None,
        output_filename: str = "podcast_video.mp4",
        fps: int = 24,
        duration_per_image: float = 3.0,
        transition_duration: float = 0.5,
        add_ken_burns: bool = True
    ) -> str:
        """
        Create video from generated images with optional audio
        
        Args:
            images: List of PIL Images
            audio_path: Path to audio file (optional)
            output_filename: Output video filename
            fps: Frames per second
            duration_per_image: Duration each image is shown (seconds)
            transition_duration: Crossfade transition duration (seconds)
            add_ken_burns: Add zoom/pan animation to static images
            
        Returns:
            Path to generated video
        """
        try:
            from moviepy.editor import ImageSequenceClip, AudioFileClip, concatenate_videoclips
            import numpy as np
            
            # Try importing transitions (compatibility for different moviepy versions)
            try:
                from moviepy.video.fx.all import crossfadein, crossfadeout
            except ImportError:
                # MoviePy 2.x uses different import path
                try:
                    from moviepy.video.fx.crossfadein import crossfadein
                    from moviepy.video.fx.crossfadeout import crossfadeout
                except ImportError:
                    crossfadein = None
                    crossfadeout = None
                    logger.warning("Crossfade effects not available, videos will have no transitions")
            
            if not images:
                raise ValueError("No images provided for video creation")
            
            logger.info(f"Creating video from {len(images)} images")
            
            # Convert PIL images to numpy arrays
            image_arrays = [np.array(img) for img in images]
            
            # Create clips for each image with transitions
            clips = []
            for i, img_array in enumerate(image_arrays):
                # Create clip from single image
                clip = ImageSequenceClip([img_array], fps=fps)
                clip = clip.set_duration(duration_per_image)
                
                # Add Ken Burns effect (zoom and pan animation)
                if add_ken_burns:
                    clip = self._add_ken_burns_effect(clip, i)
                
                # Add crossfade transitions if available
                if crossfadein and crossfadeout:
                    if i > 0:
                        clip = crossfadein(clip, transition_duration)
                    if i < len(image_arrays) - 1:
                        clip = crossfadeout(clip, transition_duration)
                
                clips.append(clip)
            
            # Concatenate all clips
            final_clip = concatenate_videoclips(clips, method="compose")
            
            # Add audio if provided
            if audio_path and os.path.exists(audio_path):
                logger.info(f"Adding audio: {audio_path}")
                audio = AudioFileClip(audio_path)
                
                # Trim or loop video to match audio length
                if final_clip.duration < audio.duration:
                    # Loop video to match audio
                    n_loops = int(audio.duration / final_clip.duration) + 1
                    final_clip = concatenate_videoclips([final_clip] * n_loops)
                
                final_clip = final_clip.set_duration(audio.duration)
                final_clip = final_clip.set_audio(audio)
            
            # Save video  
            output_path = os.path.join(self.videos_dir, output_filename)
            
            logger.info(f"Saving video to: {os.path.abspath(output_path)}")
            
            final_clip.write_videofile(
                output_path,
                fps=fps,
                codec='libx264',
                audio_codec='aac',
                temp_audiofile='temp-audio.m4a',
                remove_temp=True,
                logger=None  # Suppress moviepy's verbose logging
            )
            
            logger.info(f"✓ Video saved: {output_path}")
            return output_path
            
        except ImportError:
            logger.error("moviepy not installed. Install with: pip install moviepy")
            raise
        except Exception as e:
            logger.error(f"Failed to create video: {e}")
            raise
    
    def _add_ken_burns_effect(self, clip, index):
        """
        Add Ken Burns effect (zoom and pan) to make static images more dynamic
        
        Args:
            clip: MoviePy clip
            index: Image index (used to vary the effect)
            
        Returns:
            Animated clip
        """
        try:
            # Alternate between zoom in and zoom out
            zoom_in = index % 2 == 0
            duration = clip.duration
            
            def zoom_effect(get_frame, t):
                frame = get_frame(t)
                h, w = frame.shape[:2]
                
                # Calculate zoom factor over time (1.0 to 1.15)
                progress = t / duration
                if zoom_in:
                    zoom = 1.0 + (0.15 * progress)
                else:
                    zoom = 1.15 - (0.15 * progress)
                
                # Calculate crop box for zoom effect
                new_h, new_w = int(h / zoom), int(w / zoom)
                
                # Center crop
                top = (h - new_h) // 2
                left = (w - new_w) // 2
                
                # Crop and resize back to original size
                from PIL import Image
                import numpy as np
                img = Image.fromarray(frame)
                img = img.crop((left, top, left + new_w, top + new_h))
                img = img.resize((w, h), Image.Resampling.LANCZOS)
                
                return np.array(img)
            
            return clip.fl(zoom_effect)
            
        except Exception as e:
            logger.warning(f"Could not apply Ken Burns effect: {e}")
            return clip
    

    def generate_podcast_video(
        self,
        highlights: List[str],
        audio_path: str,
        style: str = "podcast studio",
        seed: Optional[int] = None,
        output_filename: Optional[str] = None
    ) -> str:
        """
        Complete pipeline: Generate images from highlights and create video with audio
        
        Args:
            highlights: List of podcast highlight texts
            audio_path: Path to podcast audio file
            style: Visual style for images
            seed: Random seed for reproducibility
            output_filename: Custom output filename (auto-generated if None)
            
        Returns:
            Path to generated video
        """
        logger.info("Starting podcast video generation pipeline")
        
        # Generate images
        images = self.generate_background_image(
            text=highlights,
            style=style,
            seed=seed
        )
        
        if not images:
            raise ValueError("No images were generated")
        
        # Generate output filename
        if output_filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"podcast_{timestamp}.mp4"
        
        # Create video
        video_path = self.create_video_from_images(
            images=images,
            audio_path=audio_path,
            output_filename=output_filename,
            duration_per_image=len(highlights) / len(images) if audio_path else 3.0
        )
        
        logger.info("✓ Podcast video generation complete")
        return video_path
        
    def create_highlight_video(
        self,
        audio_path: str,
        highlight: Dict,
        output_path: str,
        title: str = "Podcast Highlight",
        use_ai_hook: bool = True,
        use_ai_background: bool = False
    ) -> Tuple[str, Optional[str]]:
        """
        Create an animated video with effects
        
        Args:
            audio_path: Path to audio file
            highlight: Highlight dictionary with text, start_time, end_time
            output_path: Output video path
            title: Default title (will be replaced by AI hook if use_ai_hook=True)
            use_ai_hook: Whether to generate AI hook using GPT-4
            use_ai_background: Whether to generate background using DALL-E (slower, costs money)
        """
        audio_clip = None
        final_video = None
        
        try:
            logger.info(f"🎬 Creating animated video: {highlight['start_time']:.1f}s - {highlight['end_time']:.1f}s")
            
            # Ensure output directory exists
            output_dir = os.path.dirname(output_path)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
            
            # 1. Extract audio segment
            logger.info("🎵 Extracting audio...")
            audio_clip = self._extract_audio_segment(
                audio_path,
                highlight['start_time'],
                highlight['end_time']
            )
            duration = audio_clip.duration
            logger.info(f"✅ Audio extracted: {duration:.2f}s")
            
            # Ensure minimum duration
            if duration < 1.0:
                raise ValueError(f"Audio segment too short: {duration:.2f}s")
            
            # 2. Generate AI hook (if enabled)
            video_title = title
            generated_hook = None
            if use_ai_hook:
                try:
                    ai_service = get_ai_enhancement_service()
                    hook = ai_service.generate_viral_hook(highlight.get('text', ''))
                    if hook and hook != "Podcast Highlight":
                        video_title = hook
                        generated_hook = hook
                        logger.info(f"✨ Using AI-generated hook: '{video_title}'")
                except Exception as e:
                    logger.warning(f"Failed to generate AI hook, using default: {e}")
                    video_title = title
            
            # 3. Create background (Stable Diffusion, DALL-E, or gradient)
            background = None
            
            # Try Stable Diffusion first (local, free)
            if settings.USE_STABLE_DIFFUSION:
                try:
                    logger.info("🎨 Generating background with Stable Diffusion (local)...")
                    sd_service = get_stable_diffusion_service()
                    bg_image = sd_service.generate_background_image(
                        highlight.get('text', ''),
                        width=settings.SD_IMAGE_WIDTH,
                        height=settings.SD_IMAGE_HEIGHT,
                        num_inference_steps=settings.SD_INFERENCE_STEPS
                    )
                    if bg_image:
                        background = self._create_background_from_image(bg_image, duration)
                        logger.info("✅ Using Stable Diffusion background")
                except Exception as e:
                    logger.warning(f"Failed to generate Stable Diffusion background: {e}")
            
            # Try DALL-E if Stable Diffusion failed and enabled
            if background is None and use_ai_background:
                try:
                    logger.info("🎨 Generating AI background with DALL-E...")
                    ai_service = get_ai_enhancement_service()
                    # DALL-E 3 only supports: 1024x1024, 1024x1792, or 1792x1024
                    # Use 1024x1792 for vertical format (closest to our 1080x1920)
                    dalle_size = "1024x1792"
                    bg_image = ai_service.generate_background_image(
                        highlight.get('text', ''),
                        size=dalle_size,
                        quality="standard"
                    )
                    if bg_image:
                        background = self._create_background_from_image(bg_image, duration)
                        logger.info("✅ Using DALL-E background")
                except Exception as e:
                    logger.warning(f"Failed to generate DALL-E background: {e}")
            
            # Fallback to animated gradient if both AI methods failed or disabled
            if background is None:
                logger.info("🌈 Creating animated gradient background...")
                background = self._create_animated_gradient(duration)
            
            background = background.set_fps(self.fps)
            
            # 4. Create animated waveform
            logger.info("📊 Creating waveform...")
            waveform = self._create_animated_waveform(audio_clip, duration)
            if waveform:
                waveform = waveform.set_fps(self.fps)
            
            # 5. Create title card with animation (using AI hook if generated)
            logger.info("📝 Creating title card...")
            title_clip = self._create_animated_title(video_title, duration)
            if title_clip:
                title_clip = title_clip.set_fps(self.fps)
            
            # 6. Create animated subtitles
            logger.info("💬 Creating animated subtitles...")
            subtitle_clips = self._create_animated_subtitles(
                highlight['text'],
                duration
            )
            for clip in subtitle_clips:
                clip.set_fps(self.fps)
            
            # 7. Add decorative elements
            logger.info("✨ Adding decorative elements...")
            decorations = self._create_decorations(duration)
            if decorations:
                decorations = decorations.set_fps(self.fps)
            
            # 8. Composite all elements
            logger.info("🎨 Compositing video...")
            all_clips = [background]
            
            # Add optional clips if they exist
            if decorations:
                all_clips.append(decorations)
            if waveform:
                all_clips.append(waveform)
            if title_clip:
                all_clips.append(title_clip)
            all_clips.extend(subtitle_clips)
            
            # Create composite with proper sizing
            final_video = CompositeVideoClip(
                all_clips, 
                size=(self.width, self.height),
                bg_color=(0, 0, 0)  # Black background as fallback
            )
            final_video = final_video.set_duration(duration)
            final_video = final_video.set_fps(self.fps)
            
            # 9. Add audio
            if audio_clip:
                final_video = final_video.set_audio(audio_clip)
            
            # 10. Add fade in/out
            logger.info("🎭 Adding transitions...")
            fade_duration = min(0.5, duration / 4)  # Don't fade more than 25% of video
            final_video = final_video.fadein(fade_duration).fadeout(fade_duration)
            
            # 11. Export
            logger.info(f"💾 Exporting to: {output_path}")
            temp_audio_path = os.path.join(tempfile.gettempdir(), f'temp-audio-{os.getpid()}.m4a')
            
            final_video.write_videofile(
                output_path,
                fps=self.fps,
                codec='libx264',
                audio_codec='aac',
                temp_audiofile=temp_audio_path,
                remove_temp=True,
                logger=None,
                preset='medium',
                bitrate='2500k',
                threads=4,
                verbose=False
            )
            
            file_size = os.path.getsize(output_path)
            logger.info(f"✅ Video created: {file_size:,} bytes ({file_size / 1024 / 1024:.2f} MB)")
            
            return output_path, generated_hook
            
        except Exception as e:
            logger.error(f"❌ Video generation failed: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            raise Exception(f"Video generation error: {str(e)}")
        
        finally:
            # Cleanup
            if audio_clip:
                try:
                    audio_clip.close()
                except:
                    pass
            if final_video:
                try:
                    final_video.close()
                except:
                    pass
    
    def _extract_audio_segment(
        self,
        audio_path: str,
        start_time: float,
        end_time: float
    ) -> AudioFileClip:
        """Extract audio segment with error handling"""
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        audio = None
        try:
            audio = AudioFileClip(audio_path)
            audio_duration = audio.duration
            
            # Clamp times to valid range
            start_time = max(0, min(start_time, audio_duration))
            end_time = max(start_time + 0.1, min(end_time, audio_duration))
            
            if end_time <= start_time:
                raise ValueError(f"Invalid time range: {start_time} to {end_time}")
            
            segment = audio.subclip(start_time, end_time)
            return segment
        except Exception as e:
            if audio:
                try:
                    audio.close()
                except:
                    pass
            raise Exception(f"Failed to extract audio segment: {str(e)}")
    
    def _create_animated_gradient(self, duration: float) -> VideoClip:
        """Create animated gradient background using numpy for efficiency"""
        def make_frame(t):
            try:
                # Animate gradient position
                offset = (t / duration * 200) % 200
                
                # Create gradient using numpy (much faster)
                y_coords = np.arange(self.height, dtype=np.float32)
                # Create progress array from 0 to 1, cycling with offset
                progress = ((y_coords + offset) % (self.height * 2)) / (self.height * 2)
                progress = np.clip(progress, 0.0, 1.0)
                
                # Interpolate colors for each row
                r = (self.bg_color_start[0] + (self.bg_color_end[0] - self.bg_color_start[0]) * progress).astype(np.uint8)
                g = (self.bg_color_start[1] + (self.bg_color_end[1] - self.bg_color_start[1]) * progress).astype(np.uint8)
                b = (self.bg_color_start[2] + (self.bg_color_end[2] - self.bg_color_start[2]) * progress).astype(np.uint8)
                
                # Reshape to column vectors
                r = r.reshape(-1, 1)
                g = g.reshape(-1, 1)
                b = b.reshape(-1, 1)
                
                # Repeat across width and stack into RGB
                r = np.tile(r, (1, self.width))
                g = np.tile(g, (1, self.width))
                b = np.tile(b, (1, self.width))
                
                # Stack into RGB image (height, width, 3)
                frame = np.stack([r, g, b], axis=2)
                
                return frame
            except Exception as e:
                logger.warning(f"Error creating gradient frame at t={t}: {e}")
                import traceback
                logger.error(traceback.format_exc())
                # Return solid color as fallback
                return np.full((self.height, self.width, 3), self.bg_color_start, dtype=np.uint8)
        
        clip = VideoClip(make_frame, duration=duration)
        clip = clip.set_fps(self.fps)
        return clip
    
    def _create_animated_waveform(self, audio_clip, duration: float) -> Optional[VideoClip]:
        """Create animated audio waveform visualization"""
        try:
            def make_frame(t):
                try:
                    # Create waveform image with RGB (no alpha for compositing)
                    img = Image.new('RGB', (self.width, 200), (0, 0, 0))
                    draw = ImageDraw.Draw(img)
                    
                    # Create animated bars
                    num_bars = 40
                    bar_width = max(1, (self.width - 200) // num_bars)
                    center_y = 100
                    
                    for i in range(num_bars):
                        # Animate bar height based on time and position
                        phase = t * 3 + i * 0.5
                        height_variation = np.sin(phase) * 0.3 + 0.7
                        bar_height = int(80 * height_variation)
                        
                        x = 100 + i * bar_width
                        y_top = center_y - bar_height // 2
                        y_bottom = center_y + bar_height // 2
                        
                        # Use accent color with varying intensity
                        intensity = int(255 * height_variation)
                        r = int(self.accent_color[0] * intensity / 255)
                        g = int(self.accent_color[1] * intensity / 255)
                        b = int(self.accent_color[2] * intensity / 255)
                        
                        draw.rectangle(
                            [x, y_top, x + bar_width - 2, y_bottom],
                            fill=(r, g, b)
                        )
                    
                    return np.array(img)
                except Exception as e:
                    logger.warning(f"Error creating waveform frame at t={t}: {e}")
                    return np.zeros((200, self.width, 3), dtype=np.uint8)
            
            waveform_clip = VideoClip(make_frame, duration=duration)
            waveform_clip = waveform_clip.set_fps(self.fps)
            waveform_clip = waveform_clip.set_position(('center', int(self.height * 0.4)))
            return waveform_clip
        except Exception as e:
            logger.warning(f"Failed to create waveform: {e}")
            return None
    
    def _create_animated_title(self, title: str, duration: float) -> Optional[VideoClip]:
        """Create animated title with effects using PIL"""
        try:
            title_duration = min(3.0, duration * 0.3)
            if title_duration < 0.5:
                return None
            
            # Create text image using PIL
            text_img = self._create_text_image(
                title,
                width=self.width - 100,
                font_size=80,
                color=(255, 255, 255),
                stroke_color=(0, 0, 0),
                stroke_width=3
            )
            
            # Convert PIL image to numpy array
            # Note: PIL size is (width, height), but numpy array is (height, width, channels)
            text_w, text_h = text_img.size  # PIL format: (width, height)
            
            # Create video clip from text image
            def make_text_frame(t):
                try:
                    # Apply fade effect
                    if t < 0.5:
                        alpha = t / 0.5
                    elif t > title_duration - 0.5:
                        alpha = (title_duration - t) / 0.5
                    else:
                        alpha = 1.0
                    
                    # Convert RGBA to RGB with alpha blending
                    # Use transparent background so text shows on gradient
                    if text_img.mode == 'RGBA':
                        # Get RGBA array (numpy format: height, width, channels)
                        rgba_array = np.array(text_img)
                        # numpy array shape is (height, width, channels)
                        rgb = rgba_array[:, :, :3].astype(np.float32)
                        alpha_channel = rgba_array[:, :, 3:4].astype(np.float32) / 255.0
                        # Create transparent background (numpy format: height, width, channels)
                        frame = np.zeros((rgba_array.shape[0], rgba_array.shape[1], 3), dtype=np.uint8)
                        # Blend text on transparent background
                        frame = (frame * (1 - alpha_channel) + rgb * alpha_channel).astype(np.uint8)
                        # Apply overall fade
                        frame = (frame * alpha).astype(np.uint8)
                    else:
                        # Already RGB
                        frame = np.array(text_img.convert('RGB'))
                        frame = (frame * alpha).astype(np.uint8)
                    
                    return frame
                except Exception as e:
                    logger.warning(f"Error creating title frame at t={t}: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                    # Return correct shape based on image
                    if text_img.mode == 'RGBA':
                        rgba_array = np.array(text_img)
                        return np.zeros((rgba_array.shape[0], rgba_array.shape[1], 3), dtype=np.uint8)
                    else:
                        rgb_array = np.array(text_img.convert('RGB'))
                        return np.zeros_like(rgb_array)
            
            txt_clip = VideoClip(make_text_frame, duration=title_duration)
            txt_clip = txt_clip.set_fps(self.fps)
            txt_clip = txt_clip.set_position(('center', 100))
            
            return txt_clip
            
        except Exception as e:
            logger.warning(f"Could not create animated title: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def _create_animated_subtitles(
        self,
        text: str,
        duration: float
    ) -> List[VideoClip]:
        """Create animated subtitles with smooth transitions using PIL"""
        if not text or not text.strip():
            return []
        
        words = text.split()
        if not words:
            return []
        
        words_per_chunk = 6
        clips = []
        num_chunks = max(1, (len(words) + words_per_chunk - 1) // words_per_chunk)
        chunk_duration = max(0.5, duration / num_chunks)
        
        for i in range(num_chunks):
            start_idx = i * words_per_chunk
            end_idx = min(start_idx + words_per_chunk, len(words))
            chunk_text = ' '.join(words[start_idx:end_idx])
            
            if not chunk_text.strip():
                continue
            
            try:
                # Create text image using PIL
                text_img = self._create_text_image(
                    chunk_text,
                    width=self.width - 120,
                    font_size=65,
                    color=(255, 255, 255),
                    stroke_color=(0, 0, 0),
                    stroke_width=3
                )
                
                # Note: PIL size is (width, height), but numpy array is (height, width, channels)
                text_w, text_h = text_img.size  # PIL format: (width, height)
                
                # Create semi-transparent background box
                bg_width = min(text_w + 40, self.width - 40)
                bg_height = text_h + 30
                
                def make_text_bg(t):
                    try:
                        # Create RGB image with semi-transparent dark background
                        # Use dark gray to simulate transparency
                        img = Image.new('RGB', (bg_width, bg_height), (0, 0, 0))
                        return np.array(img)
                    except:
                        return np.zeros((bg_height, bg_width, 3), dtype=np.uint8)
                
                def make_text_frame(t):
                    try:
                        # t is relative to clip start (0 to chunk_duration)
                        # Calculate fade
                        fade_duration = min(0.3, chunk_duration / 3)
                        
                        if i > 0 and t < fade_duration:
                            # Fade in for non-first chunks
                            alpha = t / fade_duration
                        elif i < num_chunks - 1 and t > chunk_duration - fade_duration:
                            # Fade out for non-last chunks
                            alpha = (chunk_duration - t) / fade_duration
                        else:
                            # Full opacity
                            alpha = 1.0
                        
                        # Convert RGBA to RGB with proper alpha handling
                        if text_img.mode == 'RGBA':
                            # Get RGBA array (numpy format: height, width, channels)
                            rgba_array = np.array(text_img)
                            # numpy array shape is (height, width, channels)
                            rgb = rgba_array[:, :, :3].astype(np.float32)
                            alpha_channel = rgba_array[:, :, 3:4].astype(np.float32) / 255.0
                            # Create transparent background (numpy format: height, width, channels)
                            frame = np.zeros((rgba_array.shape[0], rgba_array.shape[1], 3), dtype=np.uint8)
                            # Blend text on transparent (black) background
                            frame = (frame * (1 - alpha_channel) + rgb * alpha_channel).astype(np.uint8)
                            # Apply fade
                            frame = (frame * alpha).astype(np.uint8)
                        else:
                            # Already RGB
                            text_array = np.array(text_img.convert('RGB'))
                            frame = (text_array * alpha).astype(np.uint8)

                        return frame
                    except Exception as e:
                        logger.warning(f"Error creating text frame: {e}")
                        import traceback
                        logger.error(traceback.format_exc())
                        # Return correct shape based on image
                        if text_img.mode == 'RGBA':
                            rgba_array = np.array(text_img)
                            return np.zeros((rgba_array.shape[0], rgba_array.shape[1], 3), dtype=np.uint8)
                        else:
                            rgb_array = np.array(text_img.convert('RGB'))
                            return np.zeros_like(rgb_array)
                
                text_bg = VideoClip(make_text_bg, duration=chunk_duration)
                text_bg = text_bg.set_fps(self.fps)
                text_bg = text_bg.set_position(('center', int(self.height * 0.72)))
                
                # Create text clip
                txt_clip = VideoClip(make_text_frame, duration=chunk_duration)
                txt_clip = txt_clip.set_fps(self.fps)
                txt_clip = txt_clip.set_position(('center', int(self.height * 0.73)))
                
                # Timing
                start_time = i * chunk_duration
                txt_clip = txt_clip.set_start(start_time).set_duration(chunk_duration)
                text_bg = text_bg.set_start(start_time).set_duration(chunk_duration)
                
                clips.extend([text_bg, txt_clip])
                
            except Exception as e:
                logger.warning(f"Could not create subtitle chunk {i}: {e}")
                import traceback
                logger.error(traceback.format_exc())
                continue
        
        return clips
    
    def _create_decorations(self, duration: float) -> Optional[VideoClip]:
        """Create animated decorative elements"""
        try:
            def make_frame(t):
                try:
                    # Create RGB image (no alpha for compositing)
                    img = Image.new('RGB', (self.width, self.height), (0, 0, 0))
                    draw = ImageDraw.Draw(img)
                    
                    # Animated circles
                    for i in range(3):
                        # Moving circles
                        angle = (t * 0.5 + i * 2.1) % (2 * np.pi)
                        x = int(self.width / 2 + 400 * np.cos(angle))
                        y = int(300 + 200 * np.sin(angle * 1.5))
                        
                        radius = 20 + int(10 * np.sin(t * 2 + i))
                        radius = max(5, min(50, radius))  # Clamp radius
                        
                        # Vary intensity instead of opacity
                        intensity = int(100 + 50 * np.sin(t * 3 + i))
                        intensity = max(50, min(150, intensity))
                        
                        # Scale color by intensity
                        r = int(self.accent_color[0] * intensity / 255)
                        g = int(self.accent_color[1] * intensity / 255)
                        b = int(self.accent_color[2] * intensity / 255)
                        
                        # Draw circle
                        draw.ellipse(
                            [x - radius, y - radius, x + radius, y + radius],
                            fill=(r, g, b)
                        )
                    
                    return np.array(img)
                except Exception as e:
                    logger.warning(f"Error creating decoration frame at t={t}: {e}")
                    return np.zeros((self.height, self.width, 3), dtype=np.uint8)
            
            decoration_clip = VideoClip(make_frame, duration=duration)
            decoration_clip = decoration_clip.set_fps(self.fps)
            return decoration_clip
        except Exception as e:
            logger.warning(f"Failed to create decorations: {e}")
            return None
    
# Singleton
_video_generator = None

def get_video_generator():
    global _video_generator
    if _video_generator is None:
        _video_generator = VideoGenerator()
    return _video_generator