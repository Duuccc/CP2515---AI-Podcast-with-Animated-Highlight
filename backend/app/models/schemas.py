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
    style: Optional[str] = "waveform"  # waveform, captions, animated

class Highlight(BaseModel):
    start_time: float
    end_time: float
    text: str
    confidence: float
    reason: str  # Why this was selected as highlight

class ProcessingStatusResponse(BaseModel):
    job_id: str
    status: ProcessingStatus
    progress: int  # 0-100
    message: str
    highlights: Optional[List[Highlight]] = None
    video_url: Optional[str] = None
    error: Optional[str] = None

class JobStatus(BaseModel):
    job_id: str
    status: ProcessingStatus
    created_at: str
    updated_at: str
    progress: int
    result: Optional[dict] = None