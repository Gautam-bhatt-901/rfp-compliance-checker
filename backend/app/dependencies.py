"""
Shared dependencies for FastAPI routes
"""
from functools import lru_cache
from app.modules.pdf_extractor import PDFExtractor
from app.modules.docling_extractor import DoclingExtractor
from app.modules.document_matcher import DocumentMatcher
from app.modules.rag_matcher import RAGMatcher
from app import config


@lru_cache()
def get_pdf_extractor():
    """Singleton PDF extractor"""
    return PDFExtractor()


@lru_cache()
def get_list_extractor():
    """Singleton list extractor"""
    return DoclingExtractor()


@lru_cache()
def get_document_matcher():
    """Singleton document matcher (legacy/fallback)"""
    return DocumentMatcher()


@lru_cache()
def get_rag_matcher():
    """
    Singleton RAG matcher
    Uses the shared PDF extractor instance
    """
    pdf_extractor = get_pdf_extractor()
    return RAGMatcher(pdf_extractor=pdf_extractor)
