from fastapi import APIRouter, HTTPException
from app.models.schemas import ProcessingStatusResponse, ProcessingStatus, Highlight

router = APIRouter()

# Import from process route (in production, use shared storage)
from app.api.routes.process import job_statuses

@router.get("/status/{job_id}", response_model=ProcessingStatusResponse)
async def get_job_status(job_id: str):
    """
    Get the current status of a processing job
    """
    if job_id not in job_statuses:
        raise HTTPException(status_code=404, detail="Job not found")
    
    status_data = job_statuses[job_id]
    
    # Mock completed status with highlights for demo
    if status_data.get("progress", 0) >= 100:
        return ProcessingStatusResponse(
            job_id=job_id,
            status=ProcessingStatus.COMPLETED,
            progress=100,
            message="Processing completed",
            highlights=[
                Highlight(
                    start_time=12.5,
                    end_time=45.2,
                    text="This is an amazing discovery in AI technology...",
                    confidence=0.92,
                    reason="High engagement score, emotional peak detected"
                ),
                Highlight(
                    start_time=67.8,
                    end_time=98.1,
                    text="The future of podcasting will be transformed...",
                    confidence=0.88,
                    reason="Key topic mention, high energy speech pattern"
                )
            ],
            video_url=f"/outputs/{job_id}/highlight.mp4"
        )
    
    return ProcessingStatusResponse(
        job_id=job_id,
        status=status_data.get("status", ProcessingStatus.PENDING),
        progress=status_data.get("progress", 0),
        message=status_data.get("message", "Processing...")
    )