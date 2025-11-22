from fastapi import APIRouter, HTTPException
from pathlib import Path
import json
import logging
from app.models.schemas import ProcessingStatusResponse, ProcessingStatus, Highlight
from app.core.config import settings

router = APIRouter()

# Import from process route (in production, use shared storage)
from app.api.routes.process import job_statuses

logger = logging.getLogger(__name__)

def _reconstruct_status_from_files(job_id: str) -> dict:
    """Try to reconstruct job status from saved files"""
    job_dir = Path(settings.UPLOAD_DIR) / job_id
    output_dir = Path(settings.OUTPUT_DIR) / job_id
    
    # Check if job directory exists
    if not job_dir.exists():
        return None
    
    # Check if processing is complete by looking for output files
    if output_dir.exists():
        video_files = list(output_dir.glob("highlight_*.mp4"))
        if video_files:
            # Try to load highlights and transcript
            highlights = []
            transcript = None
            video_urls = []
            
            # Load highlights
            highlights_file = job_dir / "highlights.json"
            if highlights_file.exists():
                try:
                    with open(highlights_file, "r", encoding="utf-8") as f:
                        highlights_data = json.load(f)
                        highlights_raw = highlights_data.get("highlights", [])
                        # Convert to Highlight models if needed
                        highlights = []
                        for h in highlights_raw:
                            # Ensure all required fields are present
                            if isinstance(h, dict):
                                highlight = Highlight(
                                    start_time=h.get("start_time", 0.0),
                                    end_time=h.get("end_time", 0.0),
                                    text=h.get("text", ""),
                                    confidence=h.get("confidence", 0.0),
                                    reason=h.get("reason", "Selected as highlight")
                                )
                                highlights.append(highlight)
                        logger.info(f"Loaded {len(highlights)} highlights from file")
                except Exception as e:
                    logger.warning(f"Could not load highlights: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
            
            # Load transcript
            transcript_file = job_dir / "transcript.json"
            if transcript_file.exists():
                try:
                    with open(transcript_file, "r", encoding="utf-8") as f:
                        transcript_data = json.load(f)
                        transcript = transcript_data.get("text", "")
                except Exception as e:
                    logger.warning(f"Could not load transcript: {e}")
            
            # Build video URLs
            for i in range(len(video_files)):
                video_urls.append(f"/outputs/{job_id}/highlight_{i+1}.mp4")
            
            return {
                "status": ProcessingStatus.COMPLETED,
                "progress": 100,
                "message": "Processing completed",
                "highlights": highlights,
                "transcript": transcript,
                "video_urls": video_urls
            }
    
    # Check if audio file exists but processing hasn't started
    audio_files = list(job_dir.glob("audio.*"))
    if audio_files:
        return {
            "status": ProcessingStatus.PENDING,
            "progress": 0,
            "message": "Job found but processing not started. Please trigger processing."
        }
    
    return None

@router.get("/status/{job_id}", response_model=ProcessingStatusResponse)
async def get_job_status(job_id: str):
    """
    Get the current status of a processing job
    """
    # First check in-memory status
    if job_id in job_statuses:
        status_data = job_statuses[job_id]
        
        # Return in-memory status
        response_data = {
            "job_id": job_id,
            "status": status_data.get("status", ProcessingStatus.PENDING),
            "progress": status_data.get("progress", 0),
            "message": status_data.get("message", "Processing...")
        }
        
        # Add additional data if available
        if "highlights" in status_data:
            # Convert highlights to Highlight models if they're dicts
            highlights_raw = status_data["highlights"]
            if highlights_raw:
                highlights = []
                for h in highlights_raw:
                    if isinstance(h, dict):
                        highlight = Highlight(
                            start_time=h.get("start_time", 0.0),
                            end_time=h.get("end_time", 0.0),
                            text=h.get("text", ""),
                            confidence=h.get("confidence", 0.0),
                            reason=h.get("reason", "Selected as highlight")
                        )
                        highlights.append(highlight)
                    else:
                        # Already a Highlight model
                        highlights.append(h)
                response_data["highlights"] = highlights
            else:
                response_data["highlights"] = []
        if "video_urls" in status_data:
            response_data["video_urls"] = status_data["video_urls"]
        if "transcript" in status_data:
            response_data["transcript"] = status_data["transcript"]
        if "error" in status_data:
            response_data["error"] = status_data["error"]
        
        return ProcessingStatusResponse(**response_data)
    
    # If not in memory, try to reconstruct from files
    reconstructed = _reconstruct_status_from_files(job_id)
    if reconstructed:
        return ProcessingStatusResponse(
            job_id=job_id,
            **reconstructed
        )
    
    # Job not found anywhere
    raise HTTPException(status_code=404, detail="Job not found")