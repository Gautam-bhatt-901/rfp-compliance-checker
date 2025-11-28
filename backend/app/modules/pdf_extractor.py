"""
PDF Text Extraction Module
Uses PyMuPDF for native text extraction with PaddleOCR fallback for scanned documents
NOW SUPPORTS: PDF (hybrid text/OCR with tables), Word (DOCX/DOC), Text, Markdown, RTF, ODT
"""

import io
import os
from typing import List, Dict, Union

import chardet
import fitz  # PyMuPDF
import numpy as np
from paddleocr import PaddleOCR
from PIL import Image

from app import config  # your existing config

# Optional / soft dependencies
try:
    from docx import Document as DocxDocument
except ImportError:
    DocxDocument = None

try:
    import markdown
except ImportError:
    markdown = None

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

try:
    import cv2
except ImportError:
    cv2 = None


class PDFExtractor:
    """Extracts text from multiple document formats (PDF, Word, Text, Markdown, etc.)."""

    def __init__(self):
        """Initialize document extractor with OCR engine and tunable PDF settings."""
        self.ocr = None  # Lazy loading for OCR

        # --- Hybrid PDF extraction thresholds / knobs ---
        # Minimum characters & words for a page's native text to be considered "good enough"
        # If below these, we treat the page as likely scanned / low-quality and run OCR.
        self.page_min_text_chars: int = getattr(config, "PDF_PAGE_MIN_TEXT_CHARS", 80)
        self.page_min_text_words: int = getattr(config, "PDF_PAGE_MIN_TEXT_WORDS", 10)

        # DPI used when rasterizing pages for OCR. Higher = better OCR but slower.
        self.ocr_dpi: int = getattr(config, "PDF_OCR_DPI", 300)

        # Preprocessing options for OCR – these can be overridden from config.PDF_OCR_PREPROCESS_CONFIG
        self.ocr_preprocess_config: Dict[str, Union[bool, float, int]] = getattr(
            config,
            "PDF_OCR_PREPROCESS_CONFIG",
            {
                "grayscale": True,
                "contrast_enhance": True,
                "contrast_factor": 1.5,
                "brightness_enhance": False,
                "brightness_factor": 1.1,
                "denoise": True,
                "sharpen": True,
            },
        )

        # Flags for optional libs
        self.has_pdfplumber: bool = pdfplumber is not None
        self.has_cv2: bool = cv2 is not None

    # -------------------------------------------------------------------------
    # OCR initialization & helpers
    # -------------------------------------------------------------------------

    def _initialize_ocr(self):
        """Initialize PaddleOCR (lazy loading to save memory)."""
        if self.ocr is None:
            self.ocr = PaddleOCR(
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_textline_orientation=False,
                lang="en",
            )

    # -------------------------------------------------------------------------
    # Generic helpers
    # -------------------------------------------------------------------------

    def _get_file_extension(self, file_path: str) -> str:
        """Get file extension in lowercase without dot."""
        return os.path.splitext(file_path)[1].lower().replace(".", "")

    def _detect_encoding(self, file_path: str) -> str:
        """Detect file encoding for text files."""
        try:
            with open(file_path, "rb") as f:
                raw_data = f.read()
                result = chardet.detect(raw_data)
                return result["encoding"] if result["encoding"] else "utf-8"
        except Exception:
            return "utf-8"

    # -------------------------------------------------------------------------
    # Text / Markdown / DOCX / RTF / ODT extraction
    # -------------------------------------------------------------------------

    def extract_text_from_txt(self, file_path: str) -> str:
        """
        Extract text from plain text files.

        Args:
            file_path: Path to text file

        Returns:
            Extracted text content as a single string
        """
        try:
            encoding = self._detect_encoding(file_path)
            with open(file_path, "r", encoding=encoding, errors="ignore") as f:
                text = f.read()
            return text
        except Exception as e:
            print(f"Text extraction error: {e}")
            return ""

    def extract_text_from_markdown(self, file_path: str) -> str:
        """
        Extract text from Markdown files, stripping most formatting.

        Args:
            file_path: Path to markdown file

        Returns:
            Extracted text content
        """
        try:
            encoding = self._detect_encoding(file_path)
            with open(file_path, "r", encoding=encoding, errors="ignore") as f:
                md_content = f.read()

            if markdown:
                # Remove markdown syntax for cleaner text
                import re

                text = re.sub(r"^#+\s+", "", md_content, flags=re.MULTILINE)  # headers
                text = re.sub(
                    r"[*_]{1,2}([^*_]+)[*_]{1,2}", r"\1", text
                )  # bold / italic
                text = re.sub(
                    r"\[([^\]]+)\]\([^)]+\)", r"\1", text
                )  # links: [text](url) -> text
                text = re.sub(
                    r"```[^`]*```", "", text, flags=re.DOTALL
                )  # code blocks
                text = re.sub(r"`([^`]+)`", r"\1", text)  # inline code
                return text
            else:
                # If markdown module isn't available, just return raw text
                return md_content
        except Exception as e:
            print(f"Markdown extraction error: {e}")
            return ""

    def extract_text_from_docx(self, file_path: str) -> str:
        """
        Extract text from Word DOCX files.

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
            text_content: List[str] = []

            # Extract from paragraphs
            for paragraph in doc.paragraphs:
                if paragraph.text:
                    text_content.append(paragraph.text)

            # Extract from tables
            for table in doc.tables:
                for row in table.rows:
                    row_cells = [cell.text for cell in row.cells if cell.text]
                    if row_cells:
                        text_content.append("\t".join(row_cells))

            return "\n".join(text_content)
        except Exception as e:
            print(f"DOCX extraction error: {e}")
            return ""

    def extract_text_from_rtf(self, file_path: str) -> str:
        """
        Extract text from RTF files (basic extraction).

        NOTE: Previous implementation in this file was broken (returned 'pages'
        and referenced undefined variables). This version returns a single
        text string while still being intentionally simple.

        Args:
            file_path: Path to RTF file

        Returns:
            Extracted text content
        """
        try:
            import re

            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                rtf_content = f.read()

            # Very basic RTF to text:
            # 1. Remove RTF groups like {\...}
            text = re.sub(r"\{\\[^}]*\}", "", rtf_content)
            # 2. Remove backslash commands like \b0, \par, etc.
            text = re.sub(r"\\[a-zA-Z]+\d*\s?", "", text)
            # 3. Remove leftover braces
            text = text.replace("{", "").replace("}", "")
            return text
        except Exception as e:
            print(f"RTF extraction error: {e}")
            return ""

    # -------------------------------------------------------------------------
    # PDF: hybrid per-page text / OCR + table extraction using pdfplumber
    # -------------------------------------------------------------------------

    def _should_use_native_page_text(self, text: str) -> bool:
        """
        Decide whether a page's native (selectable) text is "good enough" to use,
        or if we should treat the page as scanned and do OCR.

        Heuristics (easy to tune):
        - If stripped length < self.page_min_text_chars -> use OCR
        - If word count   < self.page_min_text_words -> use OCR
        """
        if not text:
            return False

        # Normalize whitespace to avoid over-counting
        normalized = " ".join(text.split())
        num_chars = len(normalized)
        num_words = len(normalized.split()) if normalized else 0

        if num_chars < self.page_min_text_chars:
            return False
        if num_words < self.page_min_text_words:
            return False

        return True

    def _render_page_to_image(self, page: fitz.Page) -> Image.Image:
        """
        Render a PyMuPDF page to a PIL Image for OCR.

        Uses DPI defined in self.ocr_dpi; higher gives better OCR but is slower.
        """
        zoom = self.ocr_dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        mode = "RGB" if pix.n < 4 else "RGBA"
        img = Image.frombytes(mode, [pix.width, pix.height], pix.samples)
        return img

    def _preprocess_image_for_ocr(self, image: Image.Image) -> Image.Image:
        """
        Preprocess an image before sending to OCR.

        Steps (all configurable via self.ocr_preprocess_config):
        - Convert to grayscale (often improves OCR stability)
        - Enhance contrast / brightness
        - Optional de-noising (Gaussian + adaptive threshold if OpenCV is available)
        - Optional sharpening

        All steps are modular and can be toggled or tuned later.
        """
        from PIL import ImageEnhance, ImageFilter

        cfg = self.ocr_preprocess_config.copy()
        img = image

        # 1. Grayscale
        if cfg.get("grayscale", True):
            img = img.convert("L")

        # 2. Contrast enhancement
        if cfg.get("contrast_enhance", True):
            factor = float(cfg.get("contrast_factor", 1.5))
            img = ImageEnhance.Contrast(img).enhance(factor)

        # 3. Brightness adjustment (optional)
        if cfg.get("brightness_enhance", False):
            factor = float(cfg.get("brightness_factor", 1.1))
            img = ImageEnhance.Brightness(img).enhance(factor)

        # 4. De-noising / binarization
        if cfg.get("denoise", True):
            if self.has_cv2:
                # Use OpenCV for a stronger denoise + adaptive threshold
                img_np = np.array(img)
                if img_np.ndim == 3:
                    gray = cv2.cvtColor(img_np, cv2.COLOR_BGR2GRAY)
                else:
                    gray = img_np

                blur = cv2.GaussianBlur(gray, (5, 5), 0)
                # Adaptive threshold to improve text clarity
                th = cv2.adaptiveThreshold(
                    blur,
                    255,
                    cv2.ADAPTIVE_THRESH_MEAN_C,
                    cv2.THRESH_BINARY,
                    31,
                    10,
                )
                img = Image.fromarray(th)
            else:
                # Simple Pillow-based denoise
                img = img.filter(ImageFilter.MedianFilter(size=3))

        # 5. Sharpen
        if cfg.get("sharpen", True):
            img = img.filter(ImageFilter.SHARPEN)

        return img

    def _run_ocr_on_image(self, image: Image.Image) -> str:
        """Run PaddleOCR on a PIL image and return plain text."""
        self._initialize_ocr()
        preprocessed = self._preprocess_image_for_ocr(image)
        img_np = np.array(preprocessed)

        result = self.ocr.ocr(img_np)
        lines: List[str] = []

        # result is typically [[ [bbox, (text, conf)], ... ]]
        for page_result in result:
            for line in page_result:
                try:
                    text = line[1][0]
                except Exception:
                    text = ""
                if text:
                    lines.append(text)

        return "\n".join(lines)

    def _table_to_markdown(self, table: List[List[Union[str, None]]]) -> str:
        """
        Convert a pdfplumber-extracted table (list of rows) to a Markdown-style table.

        First row is treated as header. This is a heuristic; you can adjust if
        many RFPs have no explicit header row.
        """
        if not table:
            return ""

        # Sanitize cells
        sanitized_rows: List[List[str]] = []
        for row in table:
            sanitized_rows.append(
                [str(cell).strip() if cell is not None else "" for cell in row]
            )

        header = sanitized_rows[0]
        body = sanitized_rows[1:]

        col_count = len(header)
        header_line = "| " + " | ".join(header) + " |"
        separator_line = "| " + " | ".join(["---"] * col_count) + " |"
        body_lines = ["| " + " | ".join(r) + " |" for r in body]

        return "\n".join([header_line, separator_line] + body_lines)

    def extract_text_from_pdf(self, file_path: str) -> str:
        """
        Hybrid PDF extraction (page-level text vs. OCR + inline table blocks).

        Behavior (per page):
        1. Attempt native text extraction with PyMuPDF.
        2. If the page has "enough" text (based on character & word thresholds),
           use the native text.
        3. If the page has little or no selectable text, treat it as scanned and:
           - Render the page to an image.
           - Preprocess the image (grayscale, denoise, sharpen, etc.).
           - Run OCR on that page only.
        4. If pdfplumber is available:
           - Detect tables and convert each to a Markdown-style table.
           - Insert table blocks at the end of the page text with explicit markers:
             [[TABLE_START page=<n> index=<m>]]
             <markdown table>
             [[TABLE_END]]
        5. Concatenate all page texts (in order) into a single output string.
        """
        all_pages_text: List[str] = []

        # Open PDFs with PyMuPDF
        doc = fitz.open(file_path)

        plumber_pdf = None
        if self.has_pdfplumber:
            try:
                plumber_pdf = pdfplumber.open(file_path)
            except Exception as e:
                print(f"pdfplumber failed to open {file_path}: {e}")
                plumber_pdf = None

        try:
            for page_index in range(len(doc)):
                page = doc.load_page(page_index)
                page_number = page_index + 1

                # 1. Native text
                native_text = page.get_text("text") or ""
                use_native = self._should_use_native_page_text(native_text)
                if use_native:
                    page_text = native_text.strip()
                    used_ocr = False
                else:
                    # 2. OCR for low-text / scanned pages
                    page_image = self._render_page_to_image(page)
                    ocr_text = self._run_ocr_on_image(page_image)
                    page_text = ocr_text.strip()
                    used_ocr = True

                # 3. Table extraction with pdfplumber (if available)
                if plumber_pdf is not None:
                    try:
                        plumber_page = plumber_pdf.pages[page_index]
                        tables = plumber_page.extract_tables()
                        if tables:
                            table_blocks: List[str] = []
                            for t_index, table in enumerate(tables, start=1):
                                if not table:
                                    continue
                                markdown_table = self._table_to_markdown(table)
                                if not markdown_table.strip():
                                    continue

                                # Mark table region clearly so downstream parser can detect
                                table_block = (
                                    f"\n\n[[TABLE_START page={page_number} index={t_index}]]\n"
                                    f"{markdown_table}\n"
                                    f"[[TABLE_END]]\n"
                                )
                                table_blocks.append(table_block)

                            if table_blocks:
                                # For simplicity, append tables after page text.
                                # If you need precise vertical ordering later, you can
                                # switch to pdfplumber's .find_tables() with bbox and
                                # interleave text and tables by y-coordinate.
                                page_text = page_text.rstrip() + "".join(table_blocks)
                    except Exception as e:
                        print(
                            f"pdfplumber table extraction error on page {page_number}: {e}"
                        )

                # Optional: you could add page markers here if ever needed,
                # but we keep output backward-compatible (just text + table markers).
                all_pages_text.append(page_text)

        finally:
            doc.close()
            if plumber_pdf is not None:
                plumber_pdf.close()

        return "\n\n".join([p for p in all_pages_text if p])

    # -------------------------------------------------------------------------
    # Main public API
    # -------------------------------------------------------------------------

    def extract_text(self, file_path: str) -> str:
        """
        Main extraction method with automatic format detection and fallback.

        Args:
            file_path: Path to document file

        Returns:
            Extracted text content as a single string.
        """
        file_ext = self._get_file_extension(file_path)
        filename = os.path.basename(file_path)

        # Route to appropriate extractor based on file type
        if file_ext == "pdf":
            print(f"✓ Hybrid PDF extraction (text + OCR + tables): {filename}")
            return self.extract_text_from_pdf(file_path)

        elif file_ext in ["docx", "doc"]:
            print(f"✓ Extracting from Word document: {filename}")
            return self.extract_text_from_docx(file_path)

        elif file_ext == "txt":
            print(f"✓ Extracting from text file: {filename}")
            return self.extract_text_from_txt(file_path)

        elif file_ext in ["md", "markdown"]:
            print(f"✓ Extracting from Markdown file: {filename}")
            return self.extract_text_from_markdown(file_path)

        elif file_ext == "rtf":
            print(f"✓ Extracting from RTF file: {filename}")
            return self.extract_text_from_rtf(file_path)

        elif file_ext == "odt":
            print(f"⚠ ODT format detected. Attempting text extraction: {filename}")
            # Try to read as zip file (ODT is XML-based)
            try:
                import zipfile
                import xml.etree.ElementTree as ET

                with zipfile.ZipFile(file_path) as zf:
                    content_xml = zf.read("content.xml")
                    root = ET.fromstring(content_xml)
                    # Extract all text nodes
                    text_nodes: List[str] = []
                    for elem in root.iter():
                        if elem.text:
                            text_nodes.append(elem.text)
                    return "\n".join(text_nodes)
            except Exception as e:
                print(f"ODT extraction error: {e}")
                return ""

        else:
            print(f"⚠ Unsupported file format: {file_ext}. Treating as plain text.")
            # Try to read as plain text as fallback
            return self.extract_text_from_txt(file_path)

    def extract_multiple(self, file_paths: List[str]) -> Dict[str, str]:
        """
        Extract text from multiple document files.

        Args:
            file_paths: List of document file paths

        Returns:
            Dictionary mapping filename to extracted text
        """
        results: Dict[str, str] = {}
        for file_path in file_paths:
            filename = os.path.basename(file_path)
            text = self.extract_text(file_path)
            results[filename] = text
        return results
