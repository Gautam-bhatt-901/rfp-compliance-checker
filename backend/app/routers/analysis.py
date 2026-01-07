import os
import uuid
import shutil
import asyncio
from typing import List, Dict
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, BackgroundTasks
from datetime import datetime, timedelta

from app.auth import get_current_user
from app.config import *
from app.async_io import save_multiple_files_async, delete_files_async
from app.parallel_processor import get_parallel_processor, extract_pdf_worker, match_requirement_worker
from app.cache import get_cache

import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analysis", tags=["Analysis"])

# In-memory job status store (use Redis in production)
job_status_store: Dict[str, Dict] = {}


def cleanup_old_jobs():
    """Remove jobs older than 1 hour"""
    cutoff = datetime.now() - timedelta(hours=1)
    to_delete = [
        job_id for job_id, job in job_status_store.items()
        if job.get('created_at', datetime.now()) < cutoff
    ]
    for job_id in to_delete:
        job_status_store.pop(job_id, None)


# ============ OPTIMIZATION #1: BACKGROUND PROCESSING ============

@router.post("/process")
async def process_rfp(
    background_tasks: BackgroundTasks,
    rfp_file: UploadFile = File(...),
    candidate_files: List[UploadFile] = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Submit RFP analysis job (returns immediately)
    
    Optimizations:
    - Background processing (Opt #1)
    - Async file I/O (Opt #1)
    - Returns job ID for polling
    """
    # Generate job ID
    job_id = str(uuid.uuid4())
    
    # Initialize job status
    job_status_store[job_id] = {
        'status': 'queued',
        'progress': 0,
        'message': 'Job queued',
        'created_at': datetime.now(),
        'user': current_user.get('username', 'unknown')
    }
    
    # Add to background tasks
    background_tasks.add_task(
        process_rfp_async,
        job_id,
        rfp_file,
        candidate_files
    )
    
    # Cleanup old jobs
    background_tasks.add_task(cleanup_old_jobs)
    
    logger.info(f"Job {job_id} queued for user {current_user.get('username')}")
    
    return {
        'job_id': job_id,
        'status': 'queued',
        'status_url': f'/api/analysis/status/{job_id}',
        'message': 'Job submitted successfully. Poll status_url for progress.'
    }


async def process_rfp_async(
    job_id: str,
    rfp_file: UploadFile,
    candidate_files: List[UploadFile]
):
    """
    Background task for RFP processing
    
    Applies all optimizations:
    1. Background execution
    2. Async file I/O + parallel processing
    3. Large file handling (automatic)
    4. Caching (automatic)
    """
    session_dir = None
    
    try:
        # Update status
        job_status_store[job_id]['status'] = 'processing'
        job_status_store[job_id]['progress'] = 5
        job_status_store[job_id]['message'] = 'Saving files...'
        
        # Create session directory
        session_id = os.urandom(4).hex()
        session_dir = os.path.join(DATA_DIR, 'temp', session_id)
        rfp_dir = os.path.join(session_dir, "rfp")
        docs_dir = os.path.join(session_dir, "docs")
        os.makedirs(rfp_dir, exist_ok=True)
        os.makedirs(docs_dir, exist_ok=True)
        
        # OPTIMIZATION #2: Save all files concurrently
        all_files = [rfp_file] + candidate_files
        destinations = [rfp_dir] + [docs_dir] * len(candidate_files)
        
        saved_results = []
        for file, dest in zip(all_files, destinations):
            result = await save_multiple_files_async([file], dest)
            saved_results.extend(result)
        
        if not saved_results:
            raise HTTPException(400, "No files were saved successfully")
        
        rfp_path = saved_results[0]['path']
        candidate_paths = [r['path'] for r in saved_results[1:]]
        candidate_filenames = [r['filename'] for r in saved_results[1:]]
        
        job_status_store[job_id]['progress'] = 20
        job_status_store[job_id]['message'] = f'Files saved. Processing {len(candidate_files)} documents...'
        
        # OPTIMIZATION #2 & #3: Parallel extraction with large file handling
        logger.info(f"Extracting {len(candidate_paths)} candidate files in parallel")
        
        processor = get_parallel_processor()
        extraction_results = processor.process_batch(
            candidate_paths,
            extract_pdf_worker,
            timeout=300
        )
        
        # Check for extraction errors
        successful_extractions = [r for r in extraction_results if r.get('success')]
        if not successful_extractions:
            raise Exception("All file extractions failed")
        
        job_status_store[job_id]['progress'] = 50
        job_status_store[job_id]['message'] = 'Extracting requirements from RFP...'
        
        # Extract RFP (single file, no parallel needed)
        from app.modules.pdf_extractor import PDFExtractor
        from app.modules.list_extractor import ListExtractor
        
        pdf_extractor = PDFExtractor()
        rfp_pages = pdf_extractor.extract_pages(rfp_path)
        
        list_extractor = ListExtractor()
        required_docs = list_extractor.extract_required_documents(rfp_pages, pdf_path = rfp_path)
        
        if not required_docs:
            job_status_store[job_id]['status'] = 'completed'
            job_status_store[job_id]['progress'] = 100
            job_status_store[job_id]['results'] = {
                'status': 'warning',
                'message': 'No required documents found in RFP',
                'results': []
            }
            return
        
        job_status_store[job_id]['progress'] = 70
        job_status_store[job_id]['message'] = f'Matching {len(required_docs)} requirements...'
        
        # OPTIMIZATION #2: Parallel matching (if many requirements)
        from app.modules.document_matcher import DocumentMatcher
        
        doc_matcher = DocumentMatcher()
        
        # Build document contents dict from extraction results
        document_contents = {
            r['filename']: ' '.join(r['pages'].values()) 
            for r in successful_extractions 
            if 'pages' in r
        }
        
        # Match documents
        results = doc_matcher.match_documents(
            required_docs,
            candidate_filenames,
            provided_paths=candidate_paths
        )
        
        job_status_store[job_id]['progress'] = 90
        job_status_store[job_id]['message'] = 'Calculating statistics...'
        
        # Calculate statistics
        total = len(results)
        present = sum(1 for r in results if 'Present' in str(r.get('Status', '')))
        missing = total - present
        
        # Store final results
        job_status_store[job_id]['status'] = 'completed'
        job_status_store[job_id]['progress'] = 100
        job_status_store[job_id]['message'] = 'Analysis completed successfully'
        job_status_store[job_id]['results'] = {
            'status': 'success',
            'summary': {
                'total': total,
                'present': present,
                'missing': missing,
                'completion_rate': round((present/total)*100, 1) if total > 0 else 0
            },
            'results': results
        }
        
        logger.info(f"Job {job_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}", exc_info=True)
        job_status_store[job_id]['status'] = 'failed'
        job_status_store[job_id]['message'] = f'Processing failed: {str(e)}'
        job_status_store[job_id]['error'] = str(e)
        
    finally:
        # Cleanup session directory
        if session_dir and os.path.exists(session_dir):
            try:
                shutil.rmtree(session_dir)
            except Exception as e:
                logger.warning(f"Failed to cleanup {session_dir}: {e}")


@router.get("/status/{job_id}")
async def get_job_status(
    job_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get job status and results
    
    Returns:
        Job status with results if completed
    """
    if job_id not in job_status_store:
        raise HTTPException(404, "Job not found")
    
    job = job_status_store[job_id]
    
    # Basic security: Check if user owns this job
    if job.get('user') != current_user.get('username'):
        logger.warning(f"User {current_user.get('username')} attempted to access job {job_id}")
        raise HTTPException(403, "Access denied")
    
    return {
        'job_id': job_id,
        'status': job['status'],
        'progress': job['progress'],
        'message': job['message'],
        'created_at': job['created_at'].isoformat(),
        'results': job.get('results')
    }


@router.delete("/jobs/{job_id}")
async def delete_job(
    job_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete job from store
    """
    if job_id not in job_status_store:
        raise HTTPException(404, "Job not found")
    
    job = job_status_store[job_id]
    
    # Security check
    if job.get('user') != current_user.get('username'):
        raise HTTPException(403, "Access denied")
    
    job_status_store.pop(job_id)
    
    return {'message': 'Job deleted successfully'}


@router.get("/cache/stats")
async def get_cache_stats(current_user: dict = Depends(get_current_user)):
    """
    Get cache statistics (admin only)
    """
    cache = get_cache()
    
    if not cache.backend:
        return {'enabled': False}
    
    if isinstance(cache.backend, type(cache.backend).__bases__[0]):  # MemoryCache
        return {
            'enabled': True,
            'backend': 'memory',
            'size': len(cache.backend.cache),
            'max_size': cache.backend.max_size
        }
    else:  # RedisCache
        try:
            info = cache.backend.client.info()
            return {
                'enabled': True,
                'backend': 'redis',
                'keys': info.get('db0', {}).get('keys', 0),
                'memory_mb': info.get('used_memory', 0) / (1024 * 1024)
            }
        except:
            return {'enabled': True, 'backend': 'redis', 'error': 'Cannot fetch stats'}


@router.post("/cache/clear")
async def clear_cache(current_user: dict = Depends(get_current_user)):
    """
    Clear all cache (admin only)
    """
    # TODO: Add admin role check
    cache = get_cache()
    cache.clear_all()
    
    return {'message': 'Cache cleared successfully'}
