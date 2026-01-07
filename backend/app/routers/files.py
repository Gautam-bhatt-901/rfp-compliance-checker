"""
File management routes
Handle file uploads, deletions, and listing
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from typing import List
import os
from pathlib import Path

from app.auth import get_current_user
from app.models import User
from app.modules.utils import validate_file_extension
from app import config

router = APIRouter(prefix="/api/files", tags=["Files"])

@router.post("/upload/rfp")
async def upload_rfp(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """Upload RFP file temporarily"""
    if not validate_file_extension(file.filename, config.ALLOWED_EXTENSIONS):
        raise HTTPException(
            status_code=400,
            detail=f"File format not supported. Allowed: {', '.join(config.ALLOWED_EXTENSIONS)}"
        )
    
    # Validate file size
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()  # Get position (file size)
    file.file.seek(0)  # Reset to beginning
    
    max_size = config.MAX_FILE_SIZE_MB * 1024 * 1024
    if file_size > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"File size exceeds {config.MAX_FILE_SIZE_MB}MB limit"
        )
    
    return {
        "filename": file.filename,
        "size": file_size,
        "status": "ready"
    }

@router.get("/supported-formats")
async def get_supported_formats():
    """Get list of supported file formats"""
    return {
        "formats": config.SUPPORTED_FORMATS,
        "max_file_size_mb": config.MAX_FILE_SIZE_MB
    }

@router.delete("/clear/{user_id}")
async def clear_user_files(
    current_user: User = Depends(get_current_user)
):
    """Clear all uploaded files for current user"""
    user_rfp_dir = config.UPLOAD_RFP_DIR / str(current_user.id)
    user_docs_dir = config.UPLOAD_DOCS_DIR / str(current_user.id)
    
    from app.modules.utils import clear_directory
    
    if user_rfp_dir.exists():
        clear_directory(str(user_rfp_dir))
    if user_docs_dir.exists():
        clear_directory(str(user_docs_dir))
    
    return {"message": "Files cleared successfully"}
