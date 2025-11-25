"""
Shared dependencies and utility functions
"""
from functools import lru_cache
from app.modules.pdf_extractor import PDFExtractor
from app.modules.list_extractor import ListExtractor
from app.modules.document_matcher import DocumentMatcher

# Singleton instances (cached for performance)
@lru_cache()
def get_pdf_extractor():
    """Get cached PDF extractor instance"""
    return PDFExtractor()

@lru_cache()
def get_list_extractor():
    """Get cached list extractor instance"""
    return ListExtractor()

@lru_cache()
def get_document_matcher():
    """Get cached document matcher instance"""
    return DocumentMatcher()
