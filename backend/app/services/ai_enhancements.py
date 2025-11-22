from openai import OpenAI
import os
import logging
import requests
from PIL import Image
from io import BytesIO
from typing import Optional, Dict
import time

logger = logging.getLogger(__name__)

class AIEnhancementService:
    """
    AI-powered enhancements for video generation
    Uses GPT-4 for hooks and DALL-E 3 for backgrounds
    """
    
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OPENAI_API_KEY not found. AI features will be disabled.")
            self.client = None
        else:
            self.client = OpenAI(api_key=api_key)
            logger.info("✅ AI Enhancement Service initialized")
    
    def generate_viral_hook(self, highlight_text: str, max_retries: int = 3) -> str:
        """
        Generate attention-grabbing hook using GPT-4
        
        Args:
            highlight_text: The highlight transcript
            max_retries: Number of retry attempts
            
        Returns:
            Short, punchy hook text (3-7 words)
        """
        if not self.client:
            logger.warning("OpenAI client not available, using default hook")
            return "Podcast Highlight"
        
        try:
            logger.info("🎯 Generating viral hook with GPT-4...")
            
            prompt = f"""Create a SHORT, attention-grabbing hook (3-7 words max) for this podcast clip.
            
Rules:
- Must be 3-7 words only
- Should create curiosity or surprise
- Use power words (shocking, secret, truth, never, always, etc.)
- Make it viral-worthy for TikTok/Instagram
- No quotes, just the text

Podcast content: {highlight_text[:300]}

Return ONLY the hook text, nothing else."""

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",  # Cheaper, faster alternative to gpt-4
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at creating viral TikTok and Instagram Reels hooks. You specialize in short, punchy, attention-grabbing phrases that make people stop scrolling."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=50,
                temperature=0.8,  # More creative
                presence_penalty=0.3
            )
            
            hook = response.choices[0].message.content.strip()
            
            # Remove quotes if GPT added them
            hook = hook.strip('"').strip("'")
            
            # Ensure it's not too long
            words = hook.split()
            if len(words) > 10:
                hook = ' '.join(words[:7])
            
            logger.info(f"✅ Generated hook: '{hook}'")
            logger.info(f"💰 Tokens used: {response.usage.total_tokens}")
            
            return hook
            
        except Exception as e:
            logger.error(f"❌ Failed to generate hook: {str(e)}")
            return "Podcast Highlight"
    
    def generate_background_image(
        self, 
        highlight_text: str,
        size: str = "1024x1792",  # Vertical format
        quality: str = "standard",
        max_retries: int = 3
    ) -> Optional[Image.Image]:
        """
        Generate themed background image using DALL-E 3
        
        Args:
            highlight_text: The highlight transcript
            size: Image size (1024x1792 for vertical)
            quality: "standard" or "hd"
            
        Returns:
            PIL Image object or None if failed
        """
        if not self.client:
            logger.warning("OpenAI client not available, skipping background generation")
            return None
        
        try:
            logger.info("🎨 Generating background with DALL-E 3...")
            
            # Analyze content to create better prompt
            content_keywords = self._extract_keywords(highlight_text)
            
            # Create DALL-E prompt
            prompt = self._create_dalle_prompt(highlight_text, content_keywords)
            
            logger.info(f"📝 DALL-E prompt: {prompt}")
            
            response = self.client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size=size,
                quality=quality,
                n=1,
            )
            
            image_url = response.data[0].url
            logger.info(f"✅ Image generated: {image_url}")
            logger.info(f"💰 Cost: ~$0.04 (standard) or ~$0.08 (HD)")
            
            # Download image
            logger.info("⬇️ Downloading image...")
            img_response = requests.get(image_url, timeout=30)
            img_response.raise_for_status()
            
            image = Image.open(BytesIO(img_response.content))
            logger.info(f"✅ Image downloaded: {image.size}")
            
            return image
            
        except Exception as e:
            logger.error(f"❌ Failed to generate background: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def _extract_keywords(self, text: str) -> str:
        """Extract key topics from text using GPT-4"""
        if not self.client:
            return ""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{
                    "role": "user",
                    "content": f"Extract 3-5 key visual themes from this text (one word each, comma separated): {text[:200]}"
                }],
                max_tokens=30,
                temperature=0.5
            )
            
            keywords = response.choices[0].message.content.strip()
            logger.info(f"📋 Keywords: {keywords}")
            return keywords
            
        except:
            return ""
    
    def _create_dalle_prompt(self, text: str, keywords: str) -> str:
        """Create optimized DALL-E prompt"""
        
        # Base style
        base_style = "Modern abstract background, vibrant gradient colors, professional podcast aesthetic, vertical composition"
        
        # Add keywords if available
        if keywords:
            theme = f", inspired by themes of {keywords}"
        else:
            theme = ""
        
        # Content-aware details
        content_snippet = text[:100].lower()
        
        # Determine mood/style based on content
        if any(word in content_snippet for word in ['exciting', 'amazing', 'breakthrough', 'incredible']):
            mood = ", energetic and dynamic"
        elif any(word in content_snippet for word in ['serious', 'important', 'critical', 'problem']):
            mood = ", serious and focused"
        elif any(word in content_snippet for word in ['future', 'technology', 'ai', 'innovation']):
            mood = ", futuristic and tech-inspired"
        else:
            mood = ", engaging and contemporary"
        
        prompt = f"{base_style}{theme}{mood}. Suitable for social media content, no text or faces, abstract design, 9:16 aspect ratio."
        
        # Ensure prompt isn't too long
        if len(prompt) > 1000:
            prompt = prompt[:997] + "..."
        
        return prompt
    
    def enhance_highlight_metadata(self, highlight: Dict) -> Dict:
        """
        Add AI-generated metadata to highlight
        
        Args:
            highlight: Highlight dictionary with text
            
        Returns:
            Enhanced highlight with hook and image
        """
        enhanced = highlight.copy()
        
        # Generate hook
        hook = self.generate_viral_hook(highlight['text'])
        enhanced['ai_hook'] = hook
        
        # Generate background (optional - can be slow)
        # background = self.generate_background_image(highlight['text'])
        # enhanced['ai_background'] = background
        
        return enhanced


# Singleton
_ai_service = None

def get_ai_enhancement_service() -> AIEnhancementService:
    """Get or create AI enhancement service instance"""
    global _ai_service
    if _ai_service is None:
        _ai_service = AIEnhancementService()
    return _ai_service