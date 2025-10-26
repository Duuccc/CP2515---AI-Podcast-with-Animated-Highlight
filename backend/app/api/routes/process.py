from fastapi import APIRouter, HTTPException
from pathlib import Path

from app.models.schemas import ProcessRequest, ProcessingStatusResponse, ProcessingStatus
from app.core.config import settings

router = APIRouter()

# In-memory storage for job status (use Redis/DB in production)
job_statuses = {}

@router.post("/process", response_model=ProcessingStatusResponse)
async def process_audio(request: ProcessRequest):
    """
    Start processing the uploaded audio file
    """
    job_id = request.job_id
    
    # Check if job exists
    job_dir = Path(settings.UPLOAD_DIR) / job_id
    if not job_dir.exists():
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Initialize job status
    job_statuses[job_id] = {
        "status": ProcessingStatus.PENDING,
        "progress": 0,
        "message": "Processing started"
    }
    
    # TODO: Implement actual processing logic
    # For now, return pending status
    # In production, this would trigger a background task (Celery/Redis)
    
    return ProcessingStatusResponse(
        job_id=job_id,
        status=ProcessingStatus.PENDING,
        progress=0,
        message="Job queued for processing"
    )

@router.get("/process/{job_id}/start")
async def start_processing(job_id: str):
    """
    Trigger the actual processing (placeholder for background task)
    """
    if job_id not in job_statuses:
        job_statuses[job_id] = {
            "status": ProcessingStatus.PENDING,
            "progress": 0
        }
    
    # Update status to transcribing (mock processing)
    job_statuses[job_id] = {
        "status": ProcessingStatus.TRANSCRIBING,
        "progress": 25,
        "message": "Transcribing audio..."
    }
    
    return {"message": "Processing started", "job_id": job_id}