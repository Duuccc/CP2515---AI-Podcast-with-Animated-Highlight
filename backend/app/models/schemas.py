from pydantic import BaseModel
from typing import Optional, List
from enum import Enum

class ProcessingStatus(str, Enum):
    PENDING = "pending"
    UPLOADING = "uploading"
    TRANSCRIBING = "transcribing"
    ANALYZING = "analyzing"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"

class UploadResponse(BaseModel):
    job_id: str
    filename: str
    file_size: int
    message: str

class ProcessRequest(BaseModel):
    job_id: str
    highlight_duration: Optional[int] = 60
    style: Optional[str] = "waveform"

class Highlight(BaseModel):
    start_time: float
    end_time: float
    text: str
    confidence: float
    reason: str

class ProcessingStatusResponse(BaseModel):
    job_id: str
    status: ProcessingStatus
    progress: int
    message: str
    highlights: Optional[List[Highlight]] = None
    video_url: Optional[str] = None        # Single video (backward compatibility)
    video_urls: Optional[List[str]] = None # NEW: Multiple videos
    transcript: Optional[str] = None       # NEW: Full transcript
    error: Optional[str] = None

class JobStatus(BaseModel):
    job_id: str
    status: ProcessingStatus
    created_at: str
    updated_at: str
    progress: int
    result: Optional[dict] = None