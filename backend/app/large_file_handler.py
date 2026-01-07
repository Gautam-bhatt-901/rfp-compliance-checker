"""
Large File Handler - Optimization #3
Chunked processing for large PDFs with memory optimization
"""

import fitz  # PyMuPDF
import os
import logging
from typing import Dict, Generator, Optional
from app.config import *

logger = logging.getLogger(__name__)


class LargePDFHandler:
    """
    Handles large PDF files with chunked processing and memory optimization
    """
    
    def __init__(self, chunk_size: int = None, selective_ocr: bool = True):
        """
        Initialize handler
        
        Args:
            chunk_size: Pages per chunk (default from config)
            selective_ocr: Only OCR low-text pages
        """
        self.chunk_size = chunk_size or PDF_CHUNK_SIZE_PAGES
        self.selective_ocr = selective_ocr and OCR_SELECTIVE_MODE
        self.ocr = None  # Lazy load
    
    def _initialize_ocr(self):
        """Lazy load OCR engine"""
        if self.ocr is None:
            from paddleocr import PaddleOCR
            self.ocr = PaddleOCR(
                use_angle_cls=False,
                lang=PADDLEOCR_LANG,
                use_gpu=PADDLEOCR_USE_GPU,
                show_log=PADDLEOCR_SHOW_LOG
            )
            logger.info("OCR engine initialized")
    
    def is_large_file(self, file_path: str) -> bool:
        """
        Check if file should use chunked processing
        
        Args:
            file_path: Path to PDF
        
        Returns:
            True if file is large
        """
        try:
            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
            
            # Check file size
            if file_size_mb > 30:  # >30MB
                return True
            
            # Check page count
            doc = fitz.open(file_path)
            page_count = len(doc)
            doc.close()
            
            return page_count > 50  # >50 pages
            
        except Exception as e:
            logger.warning(f"Could not determine file size: {e}")
            return False
    
    def extract_pages_chunked(self, pdf_path: str) -> Generator[Dict[int, str], None, None]:
        """
        Extract PDF in chunks (generator to save memory)
        
        Args:
            pdf_path: Path to PDF
        
        Yields:
            Chunk dict {page_num: text}
        """
        if not ENABLE_CHUNKED_PROCESSING:
            # Fall back to normal extraction
            yield self._extract_all_at_once(pdf_path)
            return
        
        doc = None
        try:
            doc = fitz.open(pdf_path)
            total_pages = len(doc)
            
            logger.info(f"Processing {total_pages} pages in chunks of {self.chunk_size}")
            
            for start_page in range(0, total_pages, self.chunk_size):
                end_page = min(start_page + self.chunk_size, total_pages)
                
                chunk_dict = {}
                
                for page_num in range(start_page, end_page):
                    page = doc[page_num]
                    
                    # Extract text
                    text = page.get_text()
                    
                    # Selective OCR: Only if page has minimal text
                    if self.selective_ocr and len(text.strip()) < PDF_TEXT_THRESHOLD:
                        logger.debug(f"Page {page_num + 1} needs OCR")
                        text = self._ocr_page(page)
                    
                    chunk_dict[page_num + 1] = text
                    
                    # Free memory
                    page = None
                
                yield chunk_dict
                
                logger.debug(f"Processed pages {start_page + 1}-{end_page}")
            
        except Exception as e:
            logger.error(f"Chunked extraction failed: {e}")
            raise
        finally:
            if doc:
                doc.close()
    
    def _ocr_page(self, page) -> str:
        """
        Perform OCR on a single page
        
        Args:
            page: PyMuPDF page object
        
        Returns:
            Extracted text
        """
        try:
            if self.ocr is None:
                self._initialize_ocr()
            
            # Convert to image with reduced DPI for speed
            from PIL import Image
            import io
            import numpy as np
            
            pix = page.get_pixmap(dpi=OCR_DPI)  # Lower DPI = faster
            img_data = pix.tobytes("png")
            image = Image.open(io.BytesIO(img_data))
            img_array = np.array(image)
            
            # Perform OCR
            result = self.ocr.ocr(img_array)
            
            # Extract text
            if result and result[0]:
                lines = []
                for line in result[0]:
                    if len(line) >= 2:
                        text, confidence = line[1]
                        if confidence > OCR_CONFIDENCE_THRESHOLD:
                            lines.append(text)
                return ' '.join(lines)
            
            return ""
            
        except Exception as e:
            logger.error(f"OCR failed: {e}")
            return ""
    
    def _extract_all_at_once(self, pdf_path: str) -> Dict[int, str]:
        """
        Fallback: Extract entire PDF at once
        
        Args:
            pdf_path: Path to PDF
        
        Returns:
            Dict of {page_num: text}
        """
        doc = fitz.open(pdf_path)
        pages = {}
        
        for page_num, page in enumerate(doc):
            text = page.get_text()
            
            # OCR if needed
            if self.selective_ocr and len(text.strip()) < PDF_TEXT_THRESHOLD:
                text = self._ocr_page(page)
            
            pages[page_num + 1] = text
        
        doc.close()
        return pages
    
    def extract_with_memory_limit(self, pdf_path: str) -> Dict[int, str]:
        """
        Extract PDF while monitoring memory usage
        
        Args:
            pdf_path: Path to PDF
        
        Returns:
            Complete dict of {page_num: text}
        """
        import psutil
        
        all_pages = {}
        
        for chunk in self.extract_pages_chunked(pdf_path):
            all_pages.update(chunk)
            
            # Check memory usage
            memory_mb = psutil.Process().memory_info().rss / (1024 * 1024)
            if memory_mb > MEMORY_LIMIT_MB:
                logger.warning(f"Memory usage: {memory_mb:.2f}MB (limit: {MEMORY_LIMIT_MB}MB)")
                # Force garbage collection
                import gc
                gc.collect()
        
        return all_pages


def should_use_large_file_handler(file_path: str) -> bool:
    """
    Determine if file requires large file handling
    
    Args:
        file_path: Path to file
    
    Returns:
        True if should use chunked processing
    """
    handler = LargePDFHandler()
    return handler.is_large_file(file_path)
