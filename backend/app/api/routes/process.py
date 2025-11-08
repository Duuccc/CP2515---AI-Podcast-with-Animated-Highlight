from fastapi import APIRouter, HTTPException, BackgroundTasks
from pathlib import Path
import json
from datetime import datetime

from app.models.schemas import ProcessRequest, ProcessingStatusResponse, ProcessingStatus
from app.core.config import settings
from app.services.transcription import get_transcription_service
from app.services.highlight_detector import get_highlight_detector

from app.services.video_generator import get_video_generator

router = APIRouter()

# In-memory storage for job status
job_statuses = {}

async def process_audio_task(job_id: str, audio_path: str):
    """Background task to process audio and generate videos"""
    try:
        job_dir = Path(settings.UPLOAD_DIR) / job_id
        output_dir = Path(settings.OUTPUT_DIR) / job_id
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Stage 1: Transcribing (0-50%)
        job_statuses[job_id] = {
            "status": ProcessingStatus.TRANSCRIBING,
            "progress": 10,
            "message": "Transcribing audio..."
        }
        
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
        
        # Stage 2: Analyzing (50-65%)
        job_statuses[job_id] = {
            "status": ProcessingStatus.ANALYZING,
            "progress": 55,
            "message": "Analyzing for highlights..."
        }
        
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
        
        # Stage 3: Generating Videos (65-95%)
        job_statuses[job_id] = {
            "status": ProcessingStatus.GENERATING,
            "progress": 65,
            "message": "Generating highlight videos..."
        }
        
        video_generator = get_video_generator()
        video_paths = []
        
        for i, highlight in enumerate(highlights):
            try:
                # Update progress for each video
                progress = 65 + (i * 10)  # 65%, 75%, 85%
                job_statuses[job_id] = {
                    "status": ProcessingStatus.GENERATING,
                    "progress": progress,
                    "message": f"Generating video {i+1} of {len(highlights)}..."
                }
                
                video_path = output_dir / f"highlight_{i+1}.mp4"
                
                video_generator.create_highlight_video(
                    audio_path=audio_path,
                    highlight=highlight,
                    output_path=str(video_path),
                    title=f"Podcast Highlight #{i+1}"
                )
                
                # Store relative path for frontend
                video_paths.append(f"/outputs/{job_id}/highlight_{i+1}.mp4")
                
                logger.info(f"Generated video {i+1}/{len(highlights)}")
                
            except Exception as e:
                logger.error(f"Failed to generate video {i+1}: {str(e)}")
                # Continue with other videos even if one fails
                continue
        
        # Stage 4: Complete (100%)
        job_statuses[job_id] = {
            "status": ProcessingStatus.COMPLETED,
            "progress": 100,
            "message": "Processing complete!",
            "highlights": highlights,
            "transcript": transcript["text"],
            "video_urls": video_paths  # List of generated videos
        }
        
        logger.info(f"Job {job_id} completed successfully with {len(video_paths)} videos")
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"ERROR in process_audio_task: {error_details}")
        
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