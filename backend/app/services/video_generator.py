from moviepy.editor import (
    AudioFileClip, 
    TextClip, 
    CompositeVideoClip,
    ColorClip,
    concatenate_videoclips
)
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from pathlib import Path
import logging
from typing import Dict, List, Tuple
import os

logger = logging.getLogger(__name__)

class VideoGenerator:
    """
    Generate social media-ready highlight videos
    Optimized for TikTok/Instagram Reels (9:16 aspect ratio)
    """
    
    def __init__(self):
        # Video dimensions (9:16 aspect ratio for vertical video)
        self.width = 1080
        self.height = 1920
        self.fps = 30
        
        # Colors
        self.bg_color_start = (59, 130, 246)  # Blue
        self.bg_color_end = (147, 51, 234)    # Purple
        self.text_color = (255, 255, 255)     # White
        self.accent_color = (34, 211, 238)    # Cyan
        
        logger.info(f"VideoGenerator initialized: {self.width}x{self.height} @ {self.fps}fps")
    
    def create_highlight_video(
        self,
        audio_path: str,
        highlight: Dict,
        output_path: str,
        title: str = "Podcast Highlight"
    ) -> str:
        """
        Create a video for a single highlight
        
        Args:
            audio_path: Path to original audio file
            highlight: Dict with start_time, end_time, text
            output_path: Where to save the video
            title: Optional title for the video
            
        Returns:
            Path to generated video file
        """
        try:
            logger.info(f"Creating video: {highlight['start_time']:.1f}s - {highlight['end_time']:.1f}s")
            
            # 1. Extract audio segment
            logger.info("Extracting audio segment...")
            audio_clip = self._extract_audio_segment(
                audio_path,
                highlight['start_time'],
                highlight['end_time']
            )
            duration = audio_clip.duration
            
            # 2. Create background
            logger.info("Creating background...")
            background = self._create_gradient_background(duration)
            
            # 3. Create title card (first 2 seconds)
            logger.info("Creating title card...")
            title_clip = self._create_title_card(title, min(2.0, duration * 0.2))
            
            # 4. Create animated subtitles
            logger.info("Creating subtitles...")
            subtitle_clips = self._create_animated_subtitles(
                highlight['text'],
                duration
            )
            
            # 5. Create waveform visualization
            logger.info("Creating waveform...")
            waveform_clip = self._create_waveform_placeholder(duration)
            
            # 6. Combine all visual elements
            logger.info("Compositing video...")
            video_clips = [background, waveform_clip, title_clip] + subtitle_clips
            final_video = CompositeVideoClip(video_clips, size=(self.width, self.height))
            final_video = final_video.set_duration(duration)
            
            # 7. Add audio
            final_video = final_video.set_audio(audio_clip)
            
            # 8. Export video
            logger.info(f"Exporting to: {output_path}")
            final_video.write_videofile(
                output_path,
                fps=self.fps,
                codec='libx264',
                audio_codec='aac',
                temp_audiofile=f'temp-audio-{os.getpid()}.m4a',
                remove_temp=True,
                logger=None,  # Suppress moviepy verbose output
                preset='medium',  # Balance between speed and quality
                bitrate='2000k'   # Good quality for social media
            )
            
            # 9. Cleanup
            audio_clip.close()
            final_video.close()
            
            logger.info(f"Video created successfully: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Video generation failed: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            raise Exception(f"Video generation error: {str(e)}")
    
    def _extract_audio_segment(
        self,
        audio_path: str,
        start_time: float,
        end_time: float
    ) -> AudioFileClip:
        """Extract a segment from the audio file"""
        audio = AudioFileClip(audio_path)
        segment = audio.subclip(start_time, end_time)
        audio.close()
        return segment
    
    def _create_gradient_background(self, duration: float) -> ColorClip:
        """Create an animated gradient background"""
        def make_frame(t):
            # Create gradient image
            img = Image.new('RGB', (self.width, self.height))
            draw = ImageDraw.Draw(img)
            
            # Animate gradient position
            offset = int((t / duration) * 100) % 100
            
            for y in range(self.height):
                # Calculate color at this y position
                progress = (y + offset) / self.height
                
                r = int(self.bg_color_start[0] + (self.bg_color_end[0] - self.bg_color_start[0]) * progress)
                g = int(self.bg_color_start[1] + (self.bg_color_end[1] - self.bg_color_start[1]) * progress)
                b = int(self.bg_color_start[2] + (self.bg_color_end[2] - self.bg_color_start[2]) * progress)
                
                draw.line([(0, y), (self.width, y)], fill=(r, g, b))
            
            return np.array(img)
        
        from moviepy.video.VideoClip import VideoClip
        return VideoClip(make_frame, duration=duration)
    
    def _create_title_card(self, title: str, duration: float) -> TextClip:
        """Create title text overlay"""
        try:
            txt_clip = TextClip(
                title,
                fontsize=70,
                color='white',
                font='Arial-Bold',
                stroke_color='black',
                stroke_width=3,
                method='caption',
                size=(self.width - 100, None),
                align='center'
            )
            
            # Position at top, fade in and out
            txt_clip = txt_clip.set_position(('center', 100))
            txt_clip = txt_clip.set_duration(duration)
            txt_clip = txt_clip.crossfadein(0.3).crossfadeout(0.3)
            
            return txt_clip
        except Exception as e:
            logger.warning(f"Could not create title card: {e}")
            # Return empty clip if title creation fails
            return ColorClip(size=(1, 1), color=(0,0,0), duration=duration).set_opacity(0)
    
    def _create_animated_subtitles(
        self,
        text: str,
        duration: float
    ) -> List[TextClip]:
        """Create animated subtitle text"""
        # Split text into chunks (words)
        words = text.split()
        words_per_chunk = 6  # Show 6 words at a time
        
        clips = []
        num_chunks = (len(words) + words_per_chunk - 1) // words_per_chunk
        chunk_duration = duration / num_chunks if num_chunks > 0 else duration
        
        for i in range(num_chunks):
            start_idx = i * words_per_chunk
            end_idx = min(start_idx + words_per_chunk, len(words))
            chunk_text = ' '.join(words[start_idx:end_idx])
            
            try:
                # Create text clip for this chunk
                txt_clip = TextClip(
                    chunk_text,
                    fontsize=60,
                    color='white',
                    font='Arial-Bold',
                    stroke_color='black',
                    stroke_width=2,
                    method='caption',
                    size=(self.width - 100, None),
                    align='center'
                )
                
                # Position at bottom third
                txt_clip = txt_clip.set_position(('center', self.height * 0.7))
                
                # Set timing
                start_time = i * chunk_duration
                txt_clip = txt_clip.set_start(start_time)
                txt_clip = txt_clip.set_duration(chunk_duration)
                
                # Add fade transitions
                if i > 0:  # Not first chunk
                    txt_clip = txt_clip.crossfadein(0.2)
                if i < num_chunks - 1:  # Not last chunk
                    txt_clip = txt_clip.crossfadeout(0.2)
                
                clips.append(txt_clip)
                
            except Exception as e:
                logger.warning(f"Could not create subtitle chunk {i}: {e}")
                continue
        
        return clips
    
    def _create_waveform_placeholder(self, duration: float) -> ColorClip:
        """Create a placeholder for waveform (simplified version)"""
        # For now, just create a semi-transparent bar
        # Full waveform visualization is complex and can be added later
        waveform = ColorClip(
            size=(self.width - 200, 150),
            color=self.accent_color,
            duration=duration
        )
        waveform = waveform.set_opacity(0.3)
        waveform = waveform.set_position(('center', self.height * 0.45))
        
        return waveform
    
    def create_multiple_highlights(
        self,
        audio_path: str,
        highlights: List[Dict],
        output_dir: str,
        title_prefix: str = "Highlight"
    ) -> List[str]:
        """
        Create videos for multiple highlights
        
        Returns:
            List of paths to generated videos
        """
        output_paths = []
        
        for i, highlight in enumerate(highlights):
            try:
                output_path = os.path.join(output_dir, f"highlight_{i+1}.mp4")
                title = f"{title_prefix} #{i+1}"
                
                video_path = self.create_highlight_video(
                    audio_path=audio_path,
                    highlight=highlight,
                    output_path=output_path,
                    title=title
                )
                
                output_paths.append(video_path)
                logger.info(f"Generated highlight {i+1}/{len(highlights)}")
                
            except Exception as e:
                logger.error(f"Failed to generate highlight {i+1}: {str(e)}")
                continue
        
        return output_paths

# Singleton instance
_video_generator = None

def get_video_generator() -> VideoGenerator:
    """Get or create video generator instance"""
    global _video_generator
    if _video_generator is None:
        _video_generator = VideoGenerator()
    return _video_generator