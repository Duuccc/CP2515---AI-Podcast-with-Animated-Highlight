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
    
    def create_highlight_video(
        self,
        audio_path: str,
        highlight: Dict,
        output_path: str,
        title: str = "Podcast Highlight"
    ) -> str:
        """Create an animated video with effects"""
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
            
            # 2. Create animated background
            logger.info("🌈 Creating animated background...")
            background = self._create_animated_gradient(duration)
            background = background.set_fps(self.fps)
            
            # 3. Create animated waveform
            logger.info("📊 Creating waveform...")
            waveform = self._create_animated_waveform(audio_clip, duration)
            if waveform:
                waveform = waveform.set_fps(self.fps)
            
            # 4. Create title card with animation
            logger.info("📝 Creating title card...")
            title_clip = self._create_animated_title(title, duration)
            if title_clip:
                title_clip = title_clip.set_fps(self.fps)
            
            # 5. Create animated subtitles
            logger.info("💬 Creating animated subtitles...")
            subtitle_clips = self._create_animated_subtitles(
                highlight['text'],
                duration
            )
            for clip in subtitle_clips:
                clip.set_fps(self.fps)
            
            # 6. Add decorative elements
            logger.info("✨ Adding decorative elements...")
            decorations = self._create_decorations(duration)
            if decorations:
                decorations = decorations.set_fps(self.fps)
            
            # 7. Composite all elements
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
            
            # 8. Add audio
            if audio_clip:
                final_video = final_video.set_audio(audio_clip)
            
            # 9. Add fade in/out
            logger.info("🎭 Adding transitions...")
            fade_duration = min(0.5, duration / 4)  # Don't fade more than 25% of video
            final_video = final_video.fadein(fade_duration).fadeout(fade_duration)
            
            # 10. Export
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
            
            return output_path
            
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