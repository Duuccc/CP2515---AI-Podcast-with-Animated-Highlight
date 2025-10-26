from fastapi import APIRouter, UploadFile, File, HTTPException
from pathlib import Path
import uuid
import os
from datetime import datetime

from app.core.config import settings
from app.models.schemas import UploadResponse

router = APIRouter()

@router.post("/upload", response_model=UploadResponse)
async def upload_audio(file: UploadFile = File(...)):
    """
    Upload an audio file for processing
    """
    # Validate file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(settings.ALLOWED_EXTENSIONS)}"
        )
    
    # Generate unique job ID
    job_id = str(uuid.uuid4())
    
    # Create job directory
    job_dir = Path(settings.UPLOAD_DIR) / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    
    # Save uploaded file
    file_path = job_dir / f"audio{file_ext}"
    
    try:
        contents = await file.read()
        file_size = len(contents)
        
        # Check file size
        if file_size > settings.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size: {settings.MAX_FILE_SIZE / 1024 / 1024}MB"
            )
        
        with open(file_path, "wb") as f:
            f.write(contents)
        
        # Save metadata
        metadata = {
            "job_id": job_id,
            "original_filename": file.filename,
            "file_size": file_size,
            "uploaded_at": datetime.now().isoformat(),
            "status": "uploaded"
        }
        
        return UploadResponse(
            job_id=job_id,
            filename=file.filename,
            file_size=file_size,
            message="File uploaded successfully"
        )
    
    except Exception as e:
        # Clean up on error
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")