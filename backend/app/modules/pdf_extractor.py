"""
PDF Text Extraction Module
Uses PyMuPDF for native text extraction with PaddleOCR fallback for scanned documents
NOW SUPPORTS: PDF, Word (DOCX/DOC), Text, Markdown, RTF, ODT
"""

import fitz  # PyMuPDF
from paddleocr import PaddleOCR
from PIL import Image
import io
import numpy as np
from typing import Tuple, List, Dict, Union
import os
import chardet
from app import config

# Import document format handlers
try:
    from docx import Document as DocxDocument
except ImportError:
    DocxDocument = None

try:
    import markdown
except ImportError:
    markdown = None

class PDFExtractor:
    """Extracts text from multiple document formats (PDF, Word, Text, Markdown, etc.)"""
    
    def __init__(self):
        """Initialize document extractor with OCR engine"""
        self.ocr = None  # Lazy loading for OCR
        
    def _initialize_ocr(self):
        """Initialize PaddleOCR (lazy loading to save memory)"""
        if self.ocr is None:
            self.ocr = PaddleOCR(
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_textline_orientation=False,
                lang='en'
            )
    
    def _get_file_extension(self, file_path: str) -> str:
        """Get file extension in lowercase"""
        return os.path.splitext(file_path)[1].lower().replace('.', '')
    
    def _detect_encoding(self, file_path: str) -> str:
        """Detect file encoding for text files"""
        try:
            with open(file_path, 'rb') as f:
                raw_data = f.read()
                result = chardet.detect(raw_data)
                return result['encoding'] if result['encoding'] else 'utf-8'
        except:
            return 'utf-8'
    
    def extract_text_from_txt(self, file_path: str) -> str:
        """
        Extract text from plain text files
        
        Args:
            file_path: Path to text file
            
        Returns:
            Extracted text content
        """
        try:
            encoding = self._detect_encoding(file_path)
            with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
                text = f.read()
            return text
        except Exception as e:
            print(f"Text extraction error: {e}")
            return ""
    
    def extract_text_from_markdown(self, file_path: str) -> str:
        """
        Extract text from Markdown files
        
        Args:
            file_path: Path to markdown file
            
        Returns:
            Extracted text content
        """
        try:
            encoding = self._detect_encoding(file_path)
            with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
                md_content = f.read()
            
            # Convert markdown to plain text (remove formatting)
            if markdown:
                # Remove markdown syntax for cleaner text
                import re
                # Remove headers
                text = re.sub(r'^#+\\s+', '', md_content, flags=re.MULTILINE)
                # Remove bold/italic
                text = re.sub(r'[*_]{1,2}([^*_]+)[*_]{1,2}', r'\\1', text)
                # Remove links
                text = re.sub(r'\\[([^\\]]+)\\]\\([^)]+\\)', r'\\1', text)
                # Remove code blocks
                text = re.sub(r'```[^`]*```', '', text, flags=re.DOTALL)
                text = re.sub(r'`([^`]+)`', r'\\1', text)
                return text
            else:
                return md_content
        except Exception as e:
            print(f"Markdown extraction error: {e}")
            return ""
    
    def extract_text_from_docx(self, file_path: str) -> str:
        """
        Extract text from Word DOCX files
        
        Args:
            file_path: Path to DOCX file
            
        Returns:
            Extracted text content
        """
        if DocxDocument is None:
            print("python-docx not installed. Cannot extract from DOCX.")
            return ""
        
        try:
            doc = DocxDocument(file_path)
            text_content = []
            
            # Extract from paragraphs
            for paragraph in doc.paragraphs:
                text_content.append(paragraph.text)
            
            # Extract from tables
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        text_content.append(cell.text)
            
            return '\\n'.join(text_content)
        except Exception as e:
            print(f"DOCX extraction error: {e}")
            return ""
    
    def extract_text_from_rtf(self, file_path: str) -> str:
        """
        Extract text from RTF files (basic extraction)
        
        Args:
            file_path: Path to RTF file
            
        Returns:
            Extracted text content
        """
        try:
            import re
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                rtf_content = f.read()
            
            # Basic RTF to text conversion (remove RTF control words)
            text = re.sub(r'\\{[^}]*\\}', '', rtf_content)
            text = re.sub(r'\\\\[a-z]+\\d*\\s?', '', text)
            text = re.sub(r'[{}]', '', text)
            return text.strip()
        except Exception as e:
            print(f"RTF extraction error: {e}")
            return ""
    
    def extract_text_native(self, pdf_path: str) -> Tuple[str, bool]:
        """
        Extract text using PyMuPDF native extraction (PDF only)
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Tuple of (extracted_text, is_successful)
        """
        try:
            doc = fitz.open(pdf_path)
            text_content = []
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text("text")
                text_content.append(text)
            
            doc.close()
            full_text = "\\n".join(text_content)
            
            # Check if extraction was successful (enough text)
            is_successful = len(full_text.strip()) > config.PDF_TEXT_THRESHOLD
            
            return full_text, is_successful
            
        except Exception as e:
            print(f"Native extraction error: {e}")
            return "", False
    
    def extract_text_ocr(self, pdf_path: str) -> str:
        """
        Extract text using PaddleOCR for scanned documents (PDF only)
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Extracted text from OCR
        """
        self._initialize_ocr()
        
        try:
            doc = fitz.open(pdf_path)
            text_content = []
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # Convert page to image
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for better OCR
                img_data = pix.tobytes("png")
                image = Image.open(io.BytesIO(img_data))
                
                # Convert to numpy array
                img_array = np.array(image)
                
                # Perform OCR
                result = self.ocr.ocr(img_array, cls=True)
                
                # Extract text from OCR results
                if result and result[0]:
                    page_text = []
                    for line in result[0]:
                        if line[1][1] > config.OCR_CONFIDENCE_THRESHOLD:  # Confidence check
                            page_text.append(line[1][0])
                    text_content.append(" ".join(page_text))
            
            doc.close()
            return "\\n".join(text_content)
            
        except Exception as e:
            print(f"OCR extraction error: {e}")
            return ""
    
    def extract_pages(self, file_path: str) -> Dict[int, str]:
        """
        Extract text content split by pages.
        For non-paginated formats (txt, md), returns chunks.
        
        Args:
            file_path: Path to document
            
        Returns:
            Dictionary {page_number: text_content}
        """
        file_ext = self._get_file_extension(file_path)
        
        if file_ext == 'pdf':
            return self._extract_pdf_pages(file_path)
        elif file_ext in ['docx', 'doc']:
            # Word docs don't have strict pages, but we can simulate paragraphs
            text = self.extract_text_from_docx(file_path)
            return self._chunk_text(text)
        else:
            # Fallback for text files
            text = self.extract_text(file_path)
            return self._chunk_text(text)
    
    def _extract_pdf_pages(self, pdf_path: str) -> Dict[int, str]:
        """Extract PDF text page by page"""
        pages = {}
        try:
            doc = fitz.open(pdf_path)
            for page_num, page in enumerate(doc):
                text = page.get_text("text")
                
                # Fallback to OCR if page is empty (scanned)
                if len(text.strip()) < config.PDF_TEXT_THRESHOLD:
                    # Note: We use a simplified OCR call here to avoid massive overhead
                    # In production, you might want to flag this page for heavy OCR
                    text = "[SCANNED_PAGE_DETECTED]" 
                
                pages[page_num + 1] = text
            doc.close()
        except Exception as e:
            print(f"Error extracting PDF pages: {e}")
            return {1: ""}
        return pages
    
    def _chunk_text(self, text: str, chunk_size: int = 3000) -> Dict[int, str]:
        """Helper to split raw text into pseudo-pages"""
        pages = {}
        if not text:
            return pages
            
        chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
        for i, chunk in enumerate(chunks):
            pages[i + 1] = chunk
        return pages

    def extract_text(self, file_path: str) -> str:
        """
        Main extraction method with automatic format detection and fallback
        
        Args:
            file_path: Path to document file
            
        Returns:
            Extracted text content
        """
        file_ext = self._get_file_extension(file_path)
        filename = os.path.basename(file_path)
        
        # Route to appropriate extractor based on file type
        if file_ext == 'pdf':
            # Try native extraction first
            text, is_successful = self.extract_text_native(file_path)
            
            if is_successful:
                print(f"✓ Native extraction successful for {filename}")
                return text
            else:
                # Fallback to OCR
                print(f"↻ Using OCR for {filename} (low text content detected)")
                return self.extract_text_ocr(file_path)
        
        elif file_ext in ['docx', 'doc']:
            print(f"✓ Extracting from Word document: {filename}")
            return self.extract_text_from_docx(file_path)
        
        elif file_ext == 'txt':
            print(f"✓ Extracting from text file: {filename}")
            return self.extract_text_from_txt(file_path)
        
        elif file_ext in ['md', 'markdown']:
            print(f"✓ Extracting from Markdown file: {filename}")
            return self.extract_text_from_markdown(file_path)
        
        elif file_ext == 'rtf':
            print(f"✓ Extracting from RTF file: {filename}")
            return self.extract_text_from_rtf(file_path)
        
        elif file_ext == 'odt':
            print(f"⚠ ODT format detected. Attempting text extraction: {filename}")
            # Try to read as zip file (ODT is XML-based)
            try:
                import zipfile
                import xml.etree.ElementTree as ET
                with zipfile.ZipFile(file_path) as zf:
                    content_xml = zf.read('content.xml')
                    root = ET.fromstring(content_xml)
                    # Extract all text nodes
                    text_nodes = []
                    for elem in root.iter():
                        if elem.text:
                            text_nodes.append(elem.text)
                    return '\\n'.join(text_nodes)
            except Exception as e:
                print(f"ODT extraction error: {e}")
                return ""
        
        else:
            print(f"⚠ Unsupported file format: {file_ext}")
            # Try to read as plain text as fallback
            return self.extract_text_from_txt(file_path)
    
    def extract_multiple(self, file_paths: List[str]) -> dict:
        """
        Extract text from multiple document files
        
        Args:
            file_paths: List of document file paths
            
        Returns:
            Dictionary mapping filename to extracted text
        """
        results = {}
        for file_path in file_paths:
            filename = os.path.basename(file_path)
            text = self.extract_text(file_path)
            results[filename] = text
        return results