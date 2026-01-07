"""
Async I/O Module - Optimization #1 & #2
Provides async file operations and parallel processing
"""

import os
import asyncio
import aiofiles
from pathlib import Path
from typing import List, Dict
from fastapi import UploadFile, HTTPException
from app.config import *
import logging

logger = logging.getLogger(__name__)

# ============ OPTIMIZATION #1: ASYNC FILE I/O ============

async def save_upload_file_async(
    upload_file: UploadFile, 
    destination: str,
    chunk_size: int = 8192
) -> str:
    """
    Save uploaded file asynchronously with streaming
    
    Args:
        upload_file: FastAPI UploadFile object
        destination: Destination directory
        chunk_size: Chunk size for streaming (8KB default)
    
    Returns:
        Full path to saved file
    
    Security:
        - Sanitizes filename to prevent path traversal
        - Validates file size
        - Streams data to prevent memory overflow
    """
    try:
        # Security: Sanitize filename
        safe_filename = Path(upload_file.filename).name  # Removes any path components
        if not safe_filename or safe_filename.startswith('.'):
            raise HTTPException(400, "Invalid filename")
        
        # Security: Validate file extension
        file_ext = Path(safe_filename).suffix.lower()
        if file_ext not in ['.pdf', '.docx', '.doc', '.txt', '.md']:
            raise HTTPException(400, f"Unsupported file type: {file_ext}")
        
        file_path = os.path.join(destination, safe_filename)
        
        # Create destination directory if needed
        os.makedirs(destination, exist_ok=True)
        
        # Stream file to disk asynchronously
        total_bytes = 0
        max_bytes = MAX_PDF_SIZE_MB * 1024 * 1024
        
        async with aiofiles.open(file_path, 'wb') as f:
            while True:
                chunk = await upload_file.read(chunk_size)
                if not chunk:
                    break
                
                total_bytes += len(chunk)
                
                # Security: Check file size limit
                if total_bytes > max_bytes:
                    # Clean up partial file
                    await f.close()
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    raise HTTPException(413, f"File too large. Maximum size: {MAX_PDF_SIZE_MB}MB")
                
                await f.write(chunk)
        
        logger.info(f"Saved file: {safe_filename} ({total_bytes / 1024:.2f} KB)")
        return file_path
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving file {upload_file.filename}: {e}")
        raise HTTPException(500, f"File save failed: {str(e)}")
    finally:
        await upload_file.close()


async def save_multiple_files_async(
    files: List[UploadFile], 
    destination: str
) -> List[Dict[str, str]]:
    """
    Save multiple files concurrently (Optimization #2: Parallel I/O)
    
    Args:
        files: List of UploadFile objects
        destination: Destination directory
    
    Returns:
        List of dicts with 'filename' and 'path' keys
    """
    tasks = [
        save_upload_file_async(file, destination) 
        for file in files
    ]
    
    try:
        # Execute all saves concurrently
        paths = await asyncio.gather(*tasks, return_exceptions=True)
        
        results = []
        for idx, result in enumerate(paths):
            if isinstance(result, Exception):
                logger.error(f"Failed to save {files[idx].filename}: {result}")
                # Re-raise if it's an HTTP exception
                if isinstance(result, HTTPException):
                    raise result
                # Otherwise, skip this file
                continue
            
            results.append({
                'filename': Path(result).name,
                'path': result
            })
        
        return results
        
    except Exception as e:
        logger.error(f"Batch file save failed: {e}")
        raise


async def read_file_async(file_path: str, encoding: str = 'utf-8') -> str:
    """
    Read file asynchronously
    
    Args:
        file_path: Path to file
        encoding: Text encoding
    
    Returns:
        File contents as string
    """
    try:
        async with aiofiles.open(file_path, 'r', encoding=encoding, errors='ignore') as f:
            content = await f.read()
        return content
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")
        return ""


async def delete_files_async(file_paths: List[str]):
    """
    Delete multiple files asynchronously
    
    Args:
        file_paths: List of file paths to delete
    """
    async def delete_single(path: str):
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception as e:
            logger.warning(f"Failed to delete {path}: {e}")
    
    await asyncio.gather(*[delete_single(p) for p in file_paths], return_exceptions=True)


# ============ FILE VALIDATION ============

def validate_file_security(upload_file: UploadFile) -> bool:
    """
    Validate file for security issues
    
    Args:
        upload_file: UploadFile object
    
    Returns:
        True if valid, raises HTTPException otherwise
    """
    # Check filename
    if not upload_file.filename:
        raise HTTPException(400, "Missing filename")
    
    # Check for path traversal attempts
    if '..' in upload_file.filename or '/' in upload_file.filename or '\\' in upload_file.filename:
        raise HTTPException(400, "Invalid filename: path traversal detected")
    
    # Validate content type (if provided)
    if upload_file.content_type and upload_file.content_type not in ALLOWED_MIME_TYPES:
        logger.warning(f"Suspicious content type: {upload_file.content_type}")
    
    return True
