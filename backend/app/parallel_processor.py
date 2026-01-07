"""
Parallel Processing Module - Optimization #2
Windows-compatible parallel document processing
"""

import os
import sys
import multiprocessing
from concurrent.futures import ProcessPoolExecutor, as_completed, TimeoutError
from typing import List, Callable, Any, Dict
import psutil
import logging
from functools import partial

from app.config import *

logger = logging.getLogger(__name__)

# Windows compatibility: Set spawn method
if os.name == 'nt':
    try:
        multiprocessing.set_start_method('spawn', force=True)
    except RuntimeError:
        pass  # Already set


class ParallelProcessor:
    """
    Manages parallel processing of documents with automatic worker scaling
    """
    
    def __init__(self, max_workers: int = None):
        """
        Initialize parallel processor
        
        Args:
            max_workers: Maximum worker processes (None = auto-detect)
        """
        self.max_workers = max_workers or self._get_optimal_workers()
        self.executor = None
        logger.info(f"ParallelProcessor initialized with {self.max_workers} workers")
    
    def _get_optimal_workers(self) -> int:
        """
        Calculate optimal number of worker processes
        
        Returns:
            Optimal worker count
        """
        if MAX_WORKER_PROCESSES > 0:
            return MAX_WORKER_PROCESSES
        
        # Get CPU count
        cpu_count = os.cpu_count() or 4
        
        # Get available memory
        try:
            available_memory_mb = psutil.virtual_memory().available / (1024 * 1024)
            
            # Estimate: Each worker needs ~500MB for PDF processing
            memory_limited_workers = int(available_memory_mb / MEMORY_LIMIT_MB)
            
            # Use minimum of CPU count and memory-limited count, capped at 8
            optimal = min(cpu_count, memory_limited_workers, 8)
            
            # Ensure at least 2 workers
            return max(2, optimal)
        except:
            # Fallback if psutil fails
            return min(cpu_count, 4)
    
    def _ensure_executor(self):
        """Lazy initialization of executor"""
        if self.executor is None:
            self.executor = ProcessPoolExecutor(max_workers=self.max_workers)
    
    def process_batch(
        self, 
        items: List[Any], 
        process_func: Callable,
        timeout: int = 300
    ) -> List[Dict]:
        """
        Process items in parallel with timeout and error handling
        
        Args:
            items: List of items to process
            process_func: Function to apply to each item (must be picklable)
            timeout: Timeout per item in seconds
        
        Returns:
            List of results (same length as items)
        """
        if not items:
            return []
        
        # Skip parallel processing for small batches
        if len(items) < MIN_FILES_FOR_PARALLEL or not ENABLE_PARALLEL_PROCESSING:
            logger.info(f"Processing {len(items)} items sequentially")
            return [self._safe_process_single(process_func, item) for item in items]
        
        logger.info(f"Processing {len(items)} items in parallel with {self.max_workers} workers")
        
        self._ensure_executor()
        results = [None] * len(items)
        
        # Submit all tasks
        future_to_idx = {
            self.executor.submit(process_func, item): idx
            for idx, item in enumerate(items)
        }
        
        # Collect results as they complete
        for future in as_completed(future_to_idx, timeout=timeout * len(items)):
            idx = future_to_idx[future]
            try:
                result = future.result(timeout=timeout)
                results[idx] = result
            except TimeoutError:
                logger.error(f"Item {idx} timed out after {timeout}s")
                results[idx] = {'error': 'timeout', 'index': idx}
            except Exception as e:
                logger.error(f"Item {idx} failed: {e}")
                results[idx] = {'error': str(e), 'index': idx}
        
        return results
    
    def _safe_process_single(self, func: Callable, item: Any) -> Dict:
        """
        Process single item with error handling
        
        Args:
            func: Processing function
            item: Item to process
        
        Returns:
            Result dict or error dict
        """
        try:
            return func(item)
        except Exception as e:
            logger.error(f"Processing failed: {e}")
            return {'error': str(e), 'item': str(item)}
    
    def shutdown(self, wait: bool = True):
        """Shutdown executor"""
        if self.executor:
            self.executor.shutdown(wait=wait)
            self.executor = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()


# ============ WORKER FUNCTIONS (Module-level for pickl ability) ============

def extract_pdf_worker(file_path: str) -> Dict:
    """
    Worker function for PDF extraction (must be at module level for Windows)
    
    Args:
        file_path: Path to PDF file
    
    Returns:
        Dict with extraction results
    """
    try:
        from app.modules.pdf_extractor import PDFExtractor
        
        extractor = PDFExtractor()
        pages = extractor.extract_pages(file_path)
        
        return {
            'success': True,
            'file_path': file_path,
            'filename': os.path.basename(file_path),
            'pages': pages,
            'page_count': len(pages)
        }
    except Exception as e:
        logger.error(f"PDF extraction failed for {file_path}: {e}")
        return {
            'success': False,
            'file_path': file_path,
            'filename': os.path.basename(file_path),
            'error': str(e)
        }


def match_requirement_worker(args: tuple) -> Dict:
    """
    Worker function for requirement matching
    
    Args:
        args: Tuple of (requirement_dict, provided_files, document_contents)
    
    Returns:
        Match result dict
    """
    try:
        requirement, provided_files, document_contents = args
        
        from app.modules.document_matcher import DocumentMatcher
        
        matcher = DocumentMatcher()
        
        # Perform matching for single requirement
        result = matcher.match_documents(
            [requirement],
            provided_files,
            provided_paths=list(document_contents.keys()) if document_contents else None
        )
        
        return result[0] if result else {'error': 'No match result'}
        
    except Exception as e:
        logger.error(f"Matching failed: {e}")
        return {
            'Required Document': requirement.get('document_name', 'Unknown'),
            'Status': '[FAIL] Missing',
            'error': str(e)
        }


# ============ GLOBAL PROCESSOR INSTANCE ============

# Create a global instance to be reused across requests
_global_processor = None

def get_parallel_processor() -> ParallelProcessor:
    """Get or create global parallel processor instance"""
    global _global_processor
    if _global_processor is None:
        _global_processor = ParallelProcessor()
    return _global_processor
