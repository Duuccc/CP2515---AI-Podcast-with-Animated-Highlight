import whisper
import torch
import os
from pathlib import Path
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class TranscriptionService:
    def __init__(self, model_name: str = "base"):
        """
        Initialize Whisper model
        """
        # TEMPORARY: Force CPU to avoid CUDA NaN errors
        self.device = "cpu"
        logger.info(f"Using device: {self.device}")
        
        logger.info(f"Loading Whisper model: {model_name}")
        self.model = whisper.load_model(model_name, device=self.device)
        logger.info("Whisper model loaded successfully")
    
    def transcribe_audio(
        self, 
        audio_path: str, 
        language: Optional[str] = None
    ) -> Dict:
        """Transcribe audio file using Whisper"""
        try:
            logger.info(f"Transcribing audio: {audio_path} on {self.device}")
            
            # Transcribe WITHOUT fp16 (causes NaN on some GPUs)
            result = self.model.transcribe(
                audio_path,
                language=language,
                task="transcribe",
                word_timestamps=True,
                verbose=False,
                fp16=False  # IMPORTANT: Disable FP16
            )
            
            # Format output
            formatted_result = {
                "text": result["text"],
                "language": result["language"],
                "segments": []
            }
            
            for segment in result["segments"]:
                formatted_result["segments"].append({
                    "start": segment["start"],
                    "end": segment["end"],
                    "text": segment["text"].strip(),
                    "confidence": segment.get("avg_logprob", 0.0)
                })
            
            logger.info(f"Transcription complete: {len(formatted_result['segments'])} segments")
            return formatted_result
            
        except Exception as e:
            logger.error(f"Transcription failed: {str(e)}")
            raise Exception(f"Transcription error: {str(e)}")

# Singleton instance
_transcription_service = None

def get_transcription_service(model_name: str = "base") -> TranscriptionService:
    """Get or create transcription service instance"""
    global _transcription_service
    if _transcription_service is None:
        _transcription_service = TranscriptionService(model_name)
    return _transcription_service