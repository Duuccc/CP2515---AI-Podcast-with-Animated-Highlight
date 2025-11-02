from fastapi import APIRouter, HTTPException, BackgroundTasks
from pathlib import Path
import json
from datetime import datetime

from app.models.schemas import ProcessRequest, ProcessingStatusResponse, ProcessingStatus
from app.core.config import settings
from app.services.transcription import get_transcription_service
from app.services.highlight_detector import get_highlight_detector

router = APIRouter()

# In-memory storage for job status
job_statuses = {}

async def process_audio_task(job_id: str, audio_path: str):
    """Background task to process audio"""
    try:
        job_dir = Path(settings.UPLOAD_DIR) / job_id
        
        # Update: Transcribing
        job_statuses[job_id] = {
            "status": ProcessingStatus.TRANSCRIBING,
            "progress": 10,
            "message": "Transcribing audio..."
        }
        
        # Transcribe
        transcription_service = get_transcription_service()
        transcript = transcription_service.transcribe_audio(audio_path)
        
        # Save transcript
        transcript_file = job_dir / "transcript.json"
        with open(transcript_file, "w", encoding="utf-8") as f:
            json.dump({
                "text": transcript["text"],
                "language": transcript["language"],
                "segments": transcript["segments"],
                "processed_at": datetime.now().isoformat()
            }, f, indent=2, ensure_ascii=False)
        
        # Update: Analyzing
        job_statuses[job_id] = {
            "status": ProcessingStatus.ANALYZING,
            "progress": 60,
            "message": "Analyzing for highlights..."
        }
        
        # Detect highlights
        highlight_detector = get_highlight_detector()
        highlights = highlight_detector.detect_highlights(
            transcript["segments"],
            num_highlights=3
        )
        
        # Save highlights
        highlights_file = job_dir / "highlights.json"
        with open(highlights_file, "w", encoding="utf-8") as f:
            json.dump({
                "highlights": highlights,
                "processed_at": datetime.now().isoformat()
            }, f, indent=2, ensure_ascii=False)
        
        # Update: Complete
        job_statuses[job_id] = {
            "status": ProcessingStatus.COMPLETED,
            "progress": 100,
            "message": "Processing complete!",
            "highlights": highlights,
            "transcript": transcript["text"]
        }
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"ERROR in process_audio_task: {error_details}")
        
        job_statuses[job_id] = {
            "status": ProcessingStatus.FAILED,
            "progress": 0,
            "message": f"Processing failed: {str(e)}",
            "error": str(e)
        }

@router.post("/process", response_model=ProcessingStatusResponse)
async def process_audio(request: ProcessRequest, background_tasks: BackgroundTasks):
    """Start processing the uploaded audio file"""
    job_id = request.job_id
    
    # Check if job exists
    job_dir = Path(settings.UPLOAD_DIR) / job_id
    if not job_dir.exists():
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Find audio file
    audio_files = list(job_dir.glob("audio.*"))
    if not audio_files:
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    audio_path = str(audio_files[0])
    
    # Initialize job status
    job_statuses[job_id] = {
        "status": ProcessingStatus.PENDING,
        "progress": 0,
        "message": "Starting processing..."
    }
    
    # Add background task
    background_tasks.add_task(process_audio_task, job_id, audio_path)
    
    return ProcessingStatusResponse(
        job_id=job_id,
        status=ProcessingStatus.PENDING,
        progress=0,
        message="Job queued for processing"
    )

@router.get("/process/{job_id}/start")
async def start_processing(job_id: str, background_tasks: BackgroundTasks):
    """Trigger processing"""
    # Check if already processing
    if job_id in job_statuses:
        current_status = job_statuses[job_id]
        return {
            "message": "Already processing or completed",
            "job_id": job_id,
            "status": current_status.get("status")
        }
    
    # Find audio file
    job_dir = Path(settings.UPLOAD_DIR) / job_id
    if not job_dir.exists():
        raise HTTPException(status_code=404, detail="Job not found")
    
    audio_files = list(job_dir.glob("audio.*"))
    if not audio_files:
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    audio_path = str(audio_files[0])
    
    # Initialize and start
    job_statuses[job_id] = {
        "status": ProcessingStatus.PENDING,
        "progress": 5,
        "message": "Initializing..."
    }
    
    # Add background task
    background_tasks.add_task(process_audio_task, job_id, audio_path)
    
    return {"message": "Processing started", "job_id": job_id}