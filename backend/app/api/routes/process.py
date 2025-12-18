from fastapi import APIRouter, HTTPException, BackgroundTasks
from pathlib import Path
import json
from datetime import datetime
import logging

from app.models.schemas import ProcessRequest, ProcessingStatusResponse, ProcessingStatus
from app.core.config import settings
from app.services.transcription import get_transcription_service
from app.services.highlight_detector import get_highlight_detector
from app.services.video_generator import get_video_generator

router = APIRouter()

# In-memory storage for job status
job_statuses = {}

logger = logging.getLogger("app.api.routes.process")

async def process_audio_task(job_id: str, audio_path: str):
    """Background task to process audio and generate videos"""
    logger.info(f"[{job_id}] ===== PROCESSING TASK STARTED =====")
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
        logger.info(f"[{job_id}] Starting transcription...")
        transcript = transcription_service.transcribe_audio(audio_path)
        logger.info(f"[{job_id}] Transcription complete: {len(transcript.get('segments', []))} segments")
        
        # Save transcript
        transcript_file = job_dir / "transcript.json"
        logger.info(f"[{job_id}] Saving transcript to {transcript_file}")
        with open(transcript_file, "w", encoding="utf-8") as f:
            json.dump({
                "text": transcript["text"],
                "language": transcript["language"],
                "segments": transcript["segments"],
                "processed_at": datetime.now().isoformat()
            }, f, indent=2, ensure_ascii=False)
        
        # Stage 2: Analyzing (50-65%)
        logger.info(f"[{job_id}] Starting highlight detection...")
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
        logger.info(f"[{job_id}] Highlight detection complete: {len(highlights)} highlights found")
        
        # Save initial highlights (will be updated with AI hooks after video generation)
        highlights_file = job_dir / "highlights.json"
        logger.info(f"[{job_id}] Saving initial highlights to {highlights_file}")
        with open(highlights_file, "w", encoding="utf-8") as f:
            json.dump({
                "highlights": highlights,
                "processed_at": datetime.now().isoformat()
            }, f, indent=2, ensure_ascii=False)
        
        # Stage 3: Generating Videos (65-95%)
        logger.info(f"[{job_id}] Starting video generation for {len(highlights)} highlights...")
        job_statuses[job_id] = {
            "status": ProcessingStatus.GENERATING,
            "progress": 65,
            "message": "Generating highlight videos..."
        }
        
        video_generator = get_video_generator()
        video_paths = []
        images = []
        
        if not highlights:
            logger.warning(f"[{job_id}] No highlights found, skipping video generation")
        else:
            for i, highlight in enumerate(highlights):
                try:
                    # Update progress for each video
                    progress = 65 + (i * 10)  # 65%, 75%, 85%
                    logger.info(f"[{job_id}] Generating video {i+1}/{len(highlights)} (progress: {progress}%)")
                    job_statuses[job_id] = {
                        "status": ProcessingStatus.GENERATING,
                        "progress": progress,
                        "message": f"Generating video {i+1} of {len(highlights)}..."
                    }
                    
                    video_path = output_dir / f"highlight_{i+1}.mp4"
                    logger.info(f"[{job_id}] Video {i+1} - Highlight: {highlight.get('start_time', 0):.1f}s to {highlight.get('end_time', 0):.1f}s")
                    
                    # Generate video and capture AI hook if generated
                    images = []
                    for i in range(3):
                        image = video_generator.generate_background_image(
                            text=highlight.get('text', '')
                        )
                        images.append(image)

                    video_generator.create_video_from_images(
                        images=images,
                        audio_path=audio_path,
                        output_filename=video_path
                    )
                    
                    images.append(image)
                    
                    logger.info(f"[{job_id}] Successfully generated background image for highlight {i+1}")
                    
                except Exception as e:
                    import traceback
                    error_trace = traceback.format_exc()
                    logger.error(f"[{job_id}] Failed to generate video {i+1}: {str(e)}")
                    logger.error(f"[{job_id}] Error traceback: {error_trace}")
                    # Continue with other videos even if one fails
                    continue

            
        
        # Stage 4: Complete (100%)
        logger.info(f"[{job_id}] Processing complete! Generated {len(video_paths)} videos")
        
        # Save highlights with AI hooks (if any were generated)
        logger.info(f"[{job_id}] Saving highlights with AI metadata to {highlights_file}")
        with open(highlights_file, "w", encoding="utf-8") as f:
            json.dump({
                "highlights": highlights,
                "processed_at": datetime.now().isoformat(),
                "ai_features_used": {
                    "hooks": settings.USE_AI_HOOK,
                    "backgrounds": settings.USE_AI_BACKGROUND
                }
            }, f, indent=2, ensure_ascii=False)
        
        # Count how many AI hooks were generated
        ai_hooks_count = sum(1 for h in highlights if h.get('ai_hook'))
        if settings.USE_AI_HOOK:
            logger.info(f"[{job_id}] AI hooks generated: {ai_hooks_count}/{len(highlights)}")
        
        job_statuses[job_id] = {
            "status": ProcessingStatus.COMPLETED,
            "progress": 100,
            "message": "Processing complete!",
            "highlights": highlights,
            "transcript": transcript["text"],
            "video_urls": video_paths  # List of generated videos
        }
        
        logger.info(f"[{job_id}] Job completed successfully with {len(video_paths)} videos")
        
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
