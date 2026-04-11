"""
GeM Bid Document Extractor — Zone-Based Pipeline

Handles the NEW GeM bid format where document names are a flat
comma-separated list in Zone A, and details are scattered across
Zones B / C / D.

PIPELINE
  Stage 1   → PyMuPDF full-doc text extraction (fast, free)
  Stage 2   → Segment document into Zones A / B / C / D
  Stage 3   → Zone A: Extract doc list + bid metadata
              (Docling table parse → regex fallback)
  Stage 4   → External ATC: auto-detect URL → silent download → inject into Zone C
  Stage 5A  → Zone B: standard eligibility docs (regex anchors, zero LLM cost)
  Stage 5B  → Zone C: ATC-tagged docs (single LLM call, ATC text only)
  Stage 5C  → Zone D: BoQ / Technical Specs table
  Stage 5.5 → LLM batch enrichment: generates rich 50-150 word descriptions
              + verbatim quotes for ALL documents (one call)
  Stage 6   → Assemble final list in EXACT same schema as old DoclingExtractor

FALLBACK
  If Zone A yields no doc list → old Docling table extraction
  (preserves compatibility with non-GeM RFPs)

PUBLIC API — UNCHANGED
  DoclingExtractor.extract_required_documents(rfp_path) → List[Dict]
  DoclingExtractor.extraction_cost      (float)
  DoclingExtractor.bid_metadata         (dict)   
  DoclingExtractor.has_external_atc     (bool)   
  DoclingExtractor.external_atc_message (str)    
  DoclingExtractor.atc_document_url     (str)   
"""

import gc
import hashlib
import json
import re
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import difflib
import fitz  # PyMuPDF
from openai import OpenAI
from pydantic import BaseModel

from app import config

# ── Zone-detection config (all overridable in config.py) ──────────────────────

_ATC_SECTION_HEADERS: List[str] = getattr(
    config, "GEM_ATC_SECTION_HEADERS",
    [
        "Buyer Added Bid Specific Terms and Conditions",
        "Buyer Added text based ATC clauses",
        "Buyer Added ATC",
        "ATC clauses",
    ],
)

_BOQ_SECTION_HEADER: str = getattr(
    config, "GEM_BOQ_SECTION_HEADER", "Technical Specifications"
)

# Configurable anchor patterns for Zone B routing.
# Key   = canonical document name (substring match)
# Value = regex pattern to locate its clause in Zone B text
_ZONE_B_ANCHORS: Dict[str, str] = getattr(
    config, "GEM_ZONE_B_ANCHORS",
    {
        "Experience Criteria":     r"Experience Criteria\s*:|Years of Past Experience",
        "Past Performance":        r"Past Performance\s*:",
        "Bidder Turnover":         r"minimum average annual financial turnover of the bidder",
        "OEM Annual Turnover":     r"OEM Turn Over Criteria\s*:",
        "Past Project Experience": r"Past Experience of Similar Services:|Past Project Experience",
    },
)

# Substrings that route a document name to Zone C (ATC)
_ATC_DOC_PATTERNS: List[str] = getattr(
    config, "GEM_ATC_DOC_PATTERNS",
    ["Requested in ATC", "Additional Doc", "OEM Authorization Certificate"],
)

_EXTERNAL_ATC_PHRASE = "Buyer uploaded ATC document"


# ── Pydantic models ────────────────────────────────────────────────────────────

class ExtractedDocument(BaseModel):
    document_name: str
    detailed_requirement: str           # Raw zone-extracted text (input to Stage 5.5)
    source_zone: str
    source_anchor: Optional[str] = None
    source_clause_number: Optional[str] = None
    is_external_atc_required: bool = False
    # ── Populated by _enrich_descriptions_with_llm (Stage 5.5) ───────────────
    rich_description: str = ""          # LLM-written 50-150 word description
    verbatim_quote: str = ""            # Exact phrase from source text
    validation_type_hint: str = "document_existence"
    threshold_hint: Optional[float] = None
    unit_hint: Optional[str] = None
    years_hint: Optional[int] = None
    evidence_docs_hint: List[str] = []


# ── Main extractor ─────────────────────────────────────────────────────────────

class DoclingExtractor:
    """
    GeM Bid Document Extractor.
    Public API is identical to the old DoclingExtractor.
    """

    # Scout keywords used only in the fallback path for non-GeM PDFs
    _HOT_KEYWORDS = [
        "checklist", "annexure", "appendix", "submission", "mandatory", "criteria",
        "eligibility", "qualification", "enclosure", "documents required",
        "technical bid", "required documents", "documentary evidence",
        "undertaking", "certificate", "proof", "supporting documents", "evaluation",
        "document required from seller",
    ]
    _HEADER_BOOSTS = [
        ("eligibility criteria", 10), ("qualification criteria", 10),
        ("documents to be submitted", 8), ("list of documents", 8),
        ("mandatory documents", 8), ("pre-qualification", 6),
        ("buyer added bid specific terms", 8), ("technical specifications", 6),
    ]

    def __init__(self):
        if not config.OPENAI_API_KEY:
            raise ValueError("[FAIL] OPENAI_API_KEY is not set")
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)
        self.extraction_cost: float = 0.0
        self._cache: Dict[str, List[Dict]] = {}
        self._converter = None
        self._external_atc_text: str = ""   # Manual injection fallback

        # Extra state — populated after each extract_required_documents() call
        self.bid_metadata: Dict = {}
        self.has_external_atc: bool = False
        self.external_atc_message: Optional[str] = None
        self.atc_document_url: Optional[str] = None

        print("[OK] DoclingExtractor (GeM Zone-Based Pipeline) initialized")

    def set_external_atc_content(self, atc_text: str) -> None:
        """
        Manually inject ATC content (fallback used by re-analyze-atc endpoint
        when auto-download fails due to authentication or network issues).
        Must be called BEFORE extract_required_documents().
        """
        self._external_atc_text = atc_text
        print(f"  [OK] External ATC injected manually: {len(atc_text)} chars")

    # =========================================================================
    # PUBLIC ENTRY POINT
    # =========================================================================

    def extract_required_documents(self, rfp_path: str) -> List[Dict]:
        """
        Extract all compliance requirements from a GeM bid PDF.

        Returns:
            List of requirement dicts. Each dict has these keys (same as old
            DoclingExtractor — downstream modules need zero changes):
              criterion_id, document_name, description, validation_type,
              threshold, unit, years_required, calculation, conditions,
              logic, context, criticality, evidence_documents, verbatim_quote,
              source_zone, is_external_atc_required

        Side effects after call:
            self.bid_metadata, self.has_external_atc,
            self.external_atc_message, self.atc_document_url,
            self.extraction_cost
        """
        print("\n" + "=" * 60)
        print("  GEM ZONE-BASED EXTRACTOR — STARTING")
        print("=" * 60)

        # Reset per-call state
        self.extraction_cost = 0.0
        self.bid_metadata = {}
        self.has_external_atc = False
        self.external_atc_message = None
        self.atc_document_url = None

        # ── Cache check ──────────────────────────────────────────────────────
        cache_key = self._hash_file(rfp_path)
        if config.EXTRACTION_CACHE_ENABLED and cache_key in self._cache:
            cached = self._cache[cache_key]
            print(f"[OK] Cache hit → {len(cached)} requirements")
            print("=" * 60 + "\n")
            return cached

        # ── Stage 1: Full-document text via PyMuPDF ──────────────────────────
        pages = self._extract_full_text(rfp_path)
        if not pages:
            print("[FAIL] No text extracted")
            return []
        print(f"  Extracted {len(pages)} pages")

        # ── Stage 2: Segment into zones ──────────────────────────────────────
        zones = self._segment_zones(pages)

        # ── Stage 3: Zone A — doc list + bid metadata ─────────────────────────
        doc_list, bid_metadata = self._extract_zone_a(zones["zone_a"], rfp_path)
        self.bid_metadata = bid_metadata
        print(f"  Zone A: {len(doc_list)} docs | metadata: {list(bid_metadata.keys())}")

        if not doc_list:
            print("[WARNING] Zone A empty — using fallback extraction for non-GeM PDF")
            result = self._fallback_old_extraction(rfp_path)
            if config.EXTRACTION_CACHE_ENABLED:
                self._cache[cache_key] = result
            return result

        # ── Stage 4: External ATC auto-download ──────────────────────────────
        full_text = "\n".join(pages.values())
        zones = self._handle_external_atc(rfp_path, full_text, zones)

        # ── Stage 5: Route each document ─────────────────────────────────────
        standard_docs, atc_docs, boq_docs = [], [], []
        for name in doc_list:
            if self._is_boq_doc(name):
                boq_docs.append(name)
            elif self._is_atc_doc(name):
                atc_docs.append(name)
            else:
                standard_docs.append(name)

        print(f"   Routing: Standard={len(standard_docs)} | "
            f"ATC={len(atc_docs)} | BoQ={len(boq_docs)}")

        documents = []

        # Zone B — standard eligibility (regex anchors, no LLM cost)
        for name in standard_docs:
            documents.append(self._extract_zone_b_detail(name, zones["zone_b"]))

        # Zone C — resolve pre-tagged ATC documents (chunked LLM call)
        if atc_docs:
            documents.extend(
                self._resolve_atc_with_llm(atc_docs, doc_list, zones["zone_c"])
            )

        # ── Zone C DISCOVERY PASS ─────────────────────────────────────
        # Scan entire Zone C text for documents NOT pre-tagged in Zone A.
        # Captures: EMD, ISO 9001, OEM Warranty, Malicious Code Cert,
        # GST Invoice, Service Centre Details, Local Content Undertaking, etc.
        already_found_names = [d.document_name for d in documents]
        if zones["zone_c"].strip():
            newly_discovered = self._discover_untagged_atc_docs(
                known_doc_names=already_found_names,
                zone_c_text=zones["zone_c"],
            )
            if newly_discovered:
                print(f"   [FIX 2] Discovery pass: {len(newly_discovered)} new doc(s)")
                documents.extend(newly_discovered)

        # Zone D — BoQ compliance
        for name in boq_docs:
            documents.append(
                self._extract_zone_d_boq(name, zones["zone_d"], rfp_path)
            )

        # ── Deduplicate before enrichment ─────────────────────────────
        # After discovery pass, same doc can appear twice (Zone A tag + discovery).
        documents = self._deduplicate_documents(documents)
        print(f"   Total unique documents after dedup: {len(documents)}")

        # ── Stage 5.5: LLM batch enrichment — rich descriptions ──────────────
        # This is what makes the Description column match Image 2 (old quality).
        documents = self._enrich_descriptions_with_llm(documents, bid_metadata)

        # ── Stage 6: Convert to downstream schema ─────────────────────────────
        requirements = self._convert_to_requirement_format(documents, bid_metadata)

        if config.EXTRACTION_CACHE_ENABLED:
            self._cache[cache_key] = requirements

        print(f"[OK] Done: {len(requirements)} requirements | Cost: ${self.extraction_cost:.4f}")
        print("=" * 60 + "\n")
        return requirements

    # =========================================================================
    # STAGE 1 — FULL TEXT EXTRACTION
    # =========================================================================

    def _extract_full_text(self, rfp_path: str) -> Dict[int, str]:
        pages: Dict[int, str] = {}
        try:
            doc = fitz.open(rfp_path)
            for i, page in enumerate(doc):
                text = page.get_text("text").strip()
                if text:
                    pages[i + 1] = text
            doc.close()
        except Exception as e:
            print(f"  [WARNING] Text extraction failed: {e}")
        return pages

    # =========================================================================
    # STAGE 2 — ZONE SEGMENTATION
    # =========================================================================

    def _segment_zones(self, pages: Dict[int, str]) -> Dict[str, str]:
        zones: Dict[str, str] = {
            "zone_a": "", "zone_b": "", "zone_c": "", "zone_d": ""
        }

        # Zone A: first 2 pages (Bid Details Table)
        zones["zone_a"] = "\n".join(pages[p] for p in sorted(pages) if p <= 2)

        # find ATC start page dynamically, use as Zone B upper bound
        atc_start_page = self._find_atc_start_page(pages)
        zones["zone_b"] = "\n".join(
            pages[p] for p in sorted(pages) if 2 <= p < atc_start_page
        )
        print(f"   Zone B: pages 2-{atc_start_page - 1} "
            f"({atc_start_page - 2} eligibility pages captured)")

        # Zone C: from ATC section header to end of document
        for page_num in sorted(pages):
            for header in _ATC_SECTION_HEADERS:
                idx = pages[page_num].lower().find(header.lower())
                if idx != -1:
                    parts = [
                        pages[page_num][idx:] if p == page_num else pages[p]
                        for p in sorted(pages) if p >= page_num
                    ]
                    zones["zone_c"] = "\n".join(parts)
                    print(f"  ATC section: page {page_num}")
                    break
            if zones["zone_c"]:
                break

        if not zones["zone_c"]:
            print("  [INFO] ATC section not found in bid body (may be external or absent)")

        # Zone D: Technical Specifications table
        for page_num in sorted(pages):
            if _BOQ_SECTION_HEADER.lower() in pages[page_num].lower():
                idx = pages[page_num].lower().find(_BOQ_SECTION_HEADER.lower())
                parts = [pages[page_num][idx:]] + [
                    pages[p] for p in sorted(pages) if p > page_num
                ]
                zones["zone_d"] = "\n".join(parts)
                print(f"  Technical Specs: page {page_num}")
                break

        return zones

    def _find_atc_start_page(self, pages: dict) -> int:
        """
        FIX 1 HELPER: Dynamically find the page where the ATC section begins.
        Returns last_page+1 as sentinel if no ATC header found (external ATC).
        """
        for page_num in sorted(pages):
            for header in _ATC_SECTION_HEADERS:
                if header.lower() in pages[page_num].lower():
                    return page_num
        # Sentinel: Zone B covers everything up to end of document
        return max(pages.keys(), default=2) + 1

    def _discover_untagged_atc_docs(
        self,
        known_doc_names: list,
        zone_c_text: str,
    ) -> list:
        """
        FIX 2: One LLM call to scan the ENTIRE Zone C text and find required
        documents NOT pre-tagged in Zone A. This is the single biggest source
        of missed documents in the current pipeline.
        """
        if not zone_c_text.strip():
            return []

        import json as _json
        import difflib as _difflib

        atc_snippet = zone_c_text[:20000]
        known_str = "\n".join(f"- {n}" for n in known_doc_names)

        prompt = f"""You are an expert Indian Government procurement analyst.

    ALREADY IDENTIFIED DOCUMENTS (do NOT include these in your answer):
    {known_str}

    ATC (Additional Terms and Conditions) SECTION TEXT:
    {atc_snippet}

    TASK:
    Find EVERY document, certificate, proof, undertaking, payment receipt,
    or submission a BIDDER MUST PROVIDE that is NOT in the already-identified list.

    Common items to look for:
    - EMD / Earnest Money Deposit (DD, banker's cheque, NEFT/RTGS receipt)
    - ISO 9001 Certificate
    - OEM Warranty Certificate
    - Malicious Code Certificate / Self-Declaration
    - Local Content Certificate / Make in India Undertaking
    - Service Centre Details
    - Police Verification Certificate
    - GST Invoice + GST Portal Screenshot
    - Bid Security Declaration Form (for MSE / DPIIT Startups)
    - Any Annexure labelled as a mandatory submission

    For each new document:
    - "document_name": concise name, under 10 words, Title Case
    - "requirement_detail": EXACT verbatim text from ATC (up to 300 chars)
    - "source_clause": clause number if visible, else null

    If NO new documents found, return: {{"new_documents": []}}

    Return ONLY this JSON:
    {{
    "new_documents": [
        {{"document_name": "...", "requirement_detail": "...", "source_clause": null}}
    ]
    }}"""

        try:
            response = self.client.chat.completions.create(
                model=config.OPENAI_MODEL,
                messages=[
                    {"role": "system",
                    "content": "You are a precise procurement analyst. Return valid JSON only."},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.0,
                seed=42,
                max_tokens=2000,
                timeout=config.OPENAI_TIMEOUT,
            )
            self._track_cost(response.usage)

            parsed = _json.loads(response.choices[0].message.content.strip())
            new_docs_raw = parsed.get("new_documents", [])

            discovered = []
            for item in new_docs_raw:
                name = item.get("document_name", "").strip()
                detail = item.get("requirement_detail", "").strip()
                clause = str(item.get("source_clause") or "")

                if not name or len(name) < 4:
                    continue

                # Guard: skip if near-duplicate of an already-found document
                close = _difflib.get_close_matches(
                    name.lower(),
                    [n.lower() for n in known_doc_names],
                    n=1, cutoff=0.75,
                )
                if close:
                    continue

                discovered.append(
                    ExtractedDocument(
                        document_name=name,
                        detailed_requirement=detail or f"Required per ATC clause {clause}.",
                        source_zone="Zone C (ATC — Discovery Pass)",
                        source_clause_number=clause or None,
                        is_external_atc_required=False,
                    )
                )

            print(f"   [OK] Discovery pass: {len(discovered)} new doc(s) found")
            return discovered

        except Exception as e:
            print(f"   [WARNING] Zone C discovery pass failed: {e}")
            return []

    def _deduplicate_documents(self, documents: list) -> list:
        """
        FIX 3: Remove near-duplicate documents after all zones are merged.
        Uses fuzzy name matching (cutoff=0.80). Keeps the entry with more detail.

        Example pairs caught:
        "OEM Authorization Certificate" vs "OEM Auth Certificate"
        "Bidder Annual Turnover"         vs "Bidder Turnover"
        "EMD Payment Document"           vs "EMD (Earnest Money Deposit)"
        """
        import difflib as _difflib

        seen_names: list = []
        seen_docs: list = []
        deduped: list = []

        for doc in documents:
            name_lower = doc.document_name.lower().strip()
            close = _difflib.get_close_matches(
                name_lower, seen_names, n=1, cutoff=0.80
            )
            if close:
                idx = seen_names.index(close[0])
                # Keep whichever version has more detail
                if len(doc.detailed_requirement) > len(seen_docs[idx].detailed_requirement):
                    deduped[idx] = doc
                    seen_docs[idx] = doc
            else:
                seen_names.append(name_lower)
                seen_docs.append(doc)
                deduped.append(doc)

        removed = len(documents) - len(deduped)
        if removed:
            print(f"   [DEDUP] Removed {removed} near-duplicate(s)")
        return deduped

    # =========================================================================
    # STAGE 3 — ZONE A: Doc list + Bid Metadata
    # =========================================================================

    def _extract_zone_a(self, zone_a_text: str, rfp_path: str) -> Tuple[List[str], Dict]:
        doc_list: List[str] = []
        metadata: Dict = {}

        # Try Docling table extraction on pages 1–2 first
        try:
            table_md = self._docling_extract_pages(rfp_path, [1, 2])
            if table_md:
                doc_list, metadata = self._parse_zone_a_from_table_md(table_md)
        except Exception as e:
            print(f"  [WARNING] Docling Zone A: {e}")

        # Regex fallback on plain text
        if not doc_list:
            doc_list, metadata = self._parse_zone_a_from_text(zone_a_text)

        return doc_list, metadata

    def _docling_extract_pages(self, rfp_path: str, page_nums: List[int]) -> Optional[str]:
        """Run Docling on specific pages, return table markdown."""
        converter = self._get_converter()
        tables: List[str] = []
        for page_num in page_nums:
            try:
                result = converter.convert(rfp_path, page_range=(page_num, page_num))
                for table in result.document.tables:
                    try:
                        md = table.export_to_markdown()
                        if md and len(md.strip()) > 10:
                            tables.append(f"[Page {page_num}]\n{md}")
                    except Exception:
                        pass
                del result
                gc.collect()
            except Exception as e:
                print(f"  [WARNING] Docling page {page_num}: {e}")
        return "\n\n".join(tables) if tables else None

    def _parse_zone_a_from_table_md(self, table_md: str) -> Tuple[List[str], Dict]:
        """
        Parse doc list from Docling table markdown.
        Supports:
        - Same-row comma-separated cell (original)
        - Multi-row: each subsequent row is one doc name
        - Cell that contains a newline-separated list instead of commas
        """
        doc_list: List[str] = []
        lines = table_md.split("\n")

        for i, line in enumerate(lines):
            if "document required from seller" not in line.lower():
                continue

            # ── Strategy 1: comma-separated value in same row ──────────────────
            cells = [c.strip() for c in line.split("|") if c.strip()]
            for cell in reversed(cells):
                if "," in cell and len(cell) > 20:
                    candidates = [
                        d.strip() for d in cell.split(",")
                        if d.strip() and self._is_valid_document_name(d.strip())
                    ]
                    if candidates:
                        doc_list = candidates
                        break

            if doc_list:
                break

            # ── Strategy 2: value in next few rows (one doc per cell) ──────────
            collected: List[str] = []
            for j in range(i + 1, min(i + 20, len(lines))):
                next_line = lines[j]
                if re.match(r"^\s*\|[-\s:|]+\|\s*$", next_line):
                    continue
                if not next_line.strip() and collected:
                    break
                cells = [
                    c.strip() for c in next_line.split("|")
                    if c.strip() and c.strip() != "---"
                ]
                if not cells:
                    if collected:
                        break
                    continue
                for cell in cells:
                    if any(kw in cell.lower() for kw in [
                        "document required", "seller", "sno", "s.no", "sl.no"
                    ]):
                        continue
                    # Comma-separated inside a cell
                    if "," in cell and len(cell) > 20:
                        parts = [
                            d.strip() for d in cell.split(",")
                            if d.strip() and self._is_valid_document_name(d.strip())
                        ]
                        if len(parts) >= 2:
                            collected.extend(parts)
                    elif self._is_valid_document_name(cell):
                        collected.append(cell)

                if any("," in c for c in cells):
                    break

            if collected:
                doc_list = collected
                break

            # ── Strategy 3: newline-separated value in a single large cell ─────
            if not doc_list:
                for j in range(i, min(i + 5, len(lines))):
                    cells = [
                        c.strip() for c in lines[j].split("|")
                        if c.strip() and c.strip() != "---"
                    ]
                    for cell in cells:
                        if "\n" in cell and len(cell) > 30:
                            parts = [
                                d.strip() for d in cell.split("\n")
                                if d.strip() and self._is_valid_document_name(d.strip())
                            ]
                            if len(parts) >= 2:
                                doc_list = parts
                                break
                    if doc_list:
                        break

        if doc_list:
            print(f"  Zone A table: {len(doc_list)} docs parsed")

        return doc_list, self._extract_metadata_patterns(table_md)

    def _parse_zone_a_from_text(self, text: str) -> Tuple[List[str], Dict]:
        """
        Extract doc list from plain text Zone A.
        Handles comma-separated on one line, multi-line numbered list,
        and various label spellings used across different GeM bid versions.
        """
        doc_list: List[str] = []

        # ── Pattern group 1: comma-separated on same line ──────────────────────
        same_line_patterns = [
            r"Document\s+required\s+from\s+seller\s*[:\|]\s*([^\n\|]{20,})",
            r"Documents?\s+[Rr]equired\s+from\s+[Ss]eller\s*[:\|]\s*([^\n\|]{20,})",
            r"Documents?\s+to\s+be\s+[Ss]ubmitted\s*[:\|]\s*([^\n\|]{20,})",
            r"Required\s+Documents?\s+from\s+[Ss]eller\s*[:\|]\s*([^\n\|]{20,})",
            r"Mandatory\s+Documents?\s*[:\|]\s*([^\n\|]{20,})",
            r"Supporting\s+Documents?\s+[Rr]equired\s*[:\|]\s*([^\n\|]{20,})",
        ]
        for pattern in same_line_patterns:
            m = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if m:
                raw = re.sub(r"\s+", " ", m.group(1).strip())
                candidates = [d.strip() for d in raw.split(",") if d.strip() and self._is_valid_document_name(d.strip())]
                if candidates:
                    doc_list = candidates
                    print(f"  Regex (same-line) doc list: {len(doc_list)} items")
                    break

        if doc_list:
            return doc_list, self._extract_metadata_patterns(text)

        # ── Pattern group 2: label followed by numbered/bulleted multi-line list ─
        header_patterns = [
            r"Document\s+required\s+from\s+seller",
            r"Documents?\s+[Rr]equired\s+from\s+[Ss]eller",
            r"Documents?\s+to\s+be\s+[Ss]ubmitted",
            r"Mandatory\s+Documents?",
            r"Required\s+Documents?",
            r"List\s+of\s+Documents?",
        ]
        for header_pat in header_patterns:
            hm = re.search(header_pat, text, re.IGNORECASE)
            if not hm:
                continue
            section = text[hm.end():]
            # Extract each list item that starts with a number, bullet, letter
            items = re.findall(
                r"(?:^\s*(?:\d+[\.\)]\s+|[a-z][\.\)]\s+|[-•*]\s+))(.+?)(?=\n|$)",
                section,
                re.MULTILINE | re.IGNORECASE,
            )
            items = [i.strip().rstrip(",;") for i in items if len(i.strip()) > 4]
            if len(items) >= 2:
                doc_list = items
                print(f"  Regex (multi-line) doc list: {len(doc_list)} items")
                break

        return doc_list, self._extract_metadata_patterns(text)

    def _extract_metadata_patterns(self, text: str) -> Dict:
        """Extract standard GeM bid metadata fields with regex."""
        patterns = {
            "bid_number":                  r"Bid\s+Number\s*[:\|]\s*([^\n\|]+)",
            "ministry":                    r"Ministry\s*/?\s*State\s+Name\s*[:\|]\s*([^\n\|]+)",
            "organization":                r"Organization\s+Name\s*[:\|]\s*([^\n\|]+)",
            "min_avg_annual_turnover":     (
                r"(?:Minimum\s+Average\s+Annual\s+(?:Financial\s+)?Turnover"
                r"|minimum.*?turnover)[^\n\|]*[:\|]\s*([^\n\|]+)"
            ),
            "oem_avg_turnover":            r"OEM\s+(?:Average\s+)?(?:Annual\s+)?Turn\s*[Oo]ver\s*[:\|]\s*([^\n\|]+)",
            "years_past_experience":       r"Years?\s+of\s+Past\s+Experience\s+[Rr]equired\s*[:\|]\s*([^\n\|]+)",
            "past_performance_percentage": r"Past\s+Performance\s*[:\|]\s*([^\n\|]*\d+\s*%[^\n\|]*)",
            "mse_relaxation":              r"MSE\s+(?:Exemption|Relaxation)\s*[:\|]\s*([^\n\|]+)",
            "startup_relaxation":          r"Startup\s+(?:Exemption|Relaxation)\s*[:\|]\s*([^\n\|]+)",
        }
        return {
            k: m.group(1).strip()
            for k, p in patterns.items()
            if (m := re.search(p, text, re.IGNORECASE))
        }

    def _is_valid_document_name(self, text: str) -> bool:
        """
        Returns True only if the text looks like a real document name.
        Rejects full sentences, instructions, and clause text that
        the multi-row Zone A parser can accidentally pick up.
        """
        t = text.strip()

        # Too short or too long to be a document name
        if len(t) < 4 or len(t) > 120:
            return False

        # Reject if it starts with sentence starters (clause text, not doc names)
        sentence_starters = (
            "the ", "a ", "an ", "this ", "that ", "all ", "any ",
            "bidder ", "vendor ", "supplier ", "firm ", "agency ",
            "please ", "note ", "as per ", "in case ", "if ", "where ",
            "documents must", "documents shall", "documents to prove",
        )
        lower = t.lower()
        if any(lower.startswith(s) for s in sentence_starters):
            return False

        # Reject if it contains verb phrases typical of clause text
        clause_phrases = [
            "must be uploaded", "shall be", "will be", "must be submitted",
            "to prove his", "to prove their", "for evaluation by",
            "eligibility for", "click here", "view the file",
            "as applicable", "if any", "where applicable",
        ]
        if any(ph in lower for ph in clause_phrases):
            return False

        # Reject if word count is too high (sentences have many words)
        word_count = len(t.split())
        if word_count > 12:
            return False

        return True

    # =========================================================================
    # STAGE 4 — EXTERNAL ATC AUTO-DOWNLOAD
    # =========================================================================

    def _handle_external_atc(
        self, rfp_path: str, full_text: str, zones: Dict[str, str]
    ) -> Dict[str, str]:
        """
        Detects external ATC reference in the bid, extracts the URL from PDF
        annotations, downloads the ATC PDF silently, and injects its text into
        Zone C before any document routing happens.

        Falls back to manually injected ATC text (set_external_atc_content) if
        auto-download fails.
        """
        if _EXTERNAL_ATC_PHRASE.lower() not in full_text.lower():
            return zones  # Nothing to do

        self.has_external_atc = True
        print("  External ATC reference detected — auto-resolving...")

        try:
            from app.modules.atc_downloader import (
                extract_atc_url_from_pdf,
                try_auto_download_atc,
                build_atc_status_message,
            )

            atc_url = extract_atc_url_from_pdf(rfp_path)
            self.atc_document_url = atc_url

            if atc_url:
                save_dir = str(Path(rfp_path).parent)
                downloaded_path, dl_status = try_auto_download_atc(atc_url, save_dir)

                if dl_status == "auto_success" and downloaded_path:
                    atc_pages = self._extract_full_text(downloaded_path)
                    if atc_pages:
                        atc_text = "\n".join(atc_pages.values())
                        # Prepend to any ATC clauses already found in the bid body
                        zones["zone_c"] = atc_text + "\n\n" + zones.get("zone_c", "")
                        self.has_external_atc = False   # Fully resolved
                        self.external_atc_message = build_atc_status_message(
                            dl_status, atc_url
                        )
                        print(f"  [OK] ATC auto-resolved: {len(atc_text)} chars in Zone C")
                        return zones

                # Download failed — set the user-facing message
                self.external_atc_message = build_atc_status_message(dl_status, atc_url)
                print(f"  [INFO] ATC auto-download status: {dl_status}")
            else:
                self.external_atc_message = build_atc_status_message("no_link", None)

        except ImportError:
            print("  [WARNING] atc_downloader not available — skipping auto-download")
            self.external_atc_message = "External ATC detected. Upload it manually."
        except Exception as e:
            print(f"  [WARNING] ATC auto-download exception: {e}")
            self.external_atc_message = f"ATC auto-download error: {str(e)[:80]}"

        # Fallback: use manually injected ATC content (from re-analyze-atc endpoint)
        if self._external_atc_text.strip():
            print("  Using manually injected ATC content (fallback)")
            zones["zone_c"] = self._external_atc_text + "\n\n" + zones.get("zone_c", "")
            self.has_external_atc = False
            self.external_atc_message = "ATC content resolved via manual upload."

        return zones

    # =========================================================================
    # STAGE 5 — ROUTING HELPERS
    # =========================================================================

    def _is_atc_doc(self, doc_name: str) -> bool:
        return any(p.lower() in doc_name.lower() for p in _ATC_DOC_PATTERNS)

    def _is_boq_doc(self, doc_name: str) -> bool:
        n = doc_name.lower()
        return "compliance of boq" in n or "boq specification" in n

    # =========================================================================
    # STAGE 5A — ZONE B: Standard eligibility (regex anchors, no LLM cost)
    # =========================================================================

    def _extract_zone_b_detail(self, doc_name: str, zone_b_text: str) -> ExtractedDocument:
        """
        Locate anchor keyword for this document in Zone B and extract clause text.
        If no regex anchor matches, falls back to an LLM call with the full Zone B
        text to avoid producing empty stub descriptions.
        """
        best_match = best_anchor = None

        # ── Direct name match (most reliable) ─────────────────────────────────
        for anchor_name, pattern in _ZONE_B_ANCHORS.items():
            if anchor_name.lower() in doc_name.lower() or doc_name.lower() in anchor_name.lower():
                m = re.search(pattern, zone_b_text, re.IGNORECASE)
                if m:
                    best_match, best_anchor = m, pattern
                    break

        # ── Word-overlap fallback ──────────────────────────────────────────────
        if not best_match:
            doc_words = set(re.findall(r"\w+", doc_name.lower())) - {"of", "the", "a", "and", "or"}
            for anchor_name, pattern in _ZONE_B_ANCHORS.items():
                anchor_words = set(re.findall(r"\w+", anchor_name.lower()))
                if anchor_words & doc_words:
                    m = re.search(pattern, zone_b_text, re.IGNORECASE)
                    if m:
                        best_match, best_anchor = m, pattern
                        break

        # ── Regex matched: extract clause text ────────────────────────────────
        if best_match:
            text_after = zone_b_text[best_match.start():]
            end = re.search(r"\n\s*\d+\s*\.\s+[A-Z]", text_after[50:])
            detail = (
                text_after[:end.start() + 50].strip() if end else text_after[:1200].strip()
            )
            return ExtractedDocument(
                document_name=doc_name,
                detailed_requirement=detail,
                source_zone="Zone B (Standard Clauses)",
                source_anchor=best_anchor,
            )

        # ── LLM fallback: ask LLM to find the clause ──────────────────────────
        # Only runs when no regex matched. Sends Zone B text to GPT to extract
        # the specific clause for this document, avoiding empty stub descriptions.
        print(f"  [INFO] No regex match for '{doc_name}' — using LLM Zone B fallback")
        extracted_detail = self._llm_extract_zone_b_clause(doc_name, zone_b_text)

        return ExtractedDocument(
            document_name=doc_name,
            detailed_requirement=extracted_detail,
            source_zone="Zone B (Standard Clauses — LLM assisted)",
        )

    def _llm_extract_zone_b_clause(self, doc_name: str, zone_b_text: str) -> str:
        """
        LLM fallback for Zone B: when regex anchors don't match, send the Zone B
        text to GPT and ask it to extract the relevant clause for this document.
        Uses a lightweight targeted prompt (not the full enrichment call).
        """
        if not zone_b_text.strip():
            return f"Standard eligibility document — {doc_name}. Manual review required."

        # Limit Zone B text to save tokens
        zone_b_snippet = zone_b_text[:6000]

        prompt = f"""You are an expert in Indian GeM bid documents.

    DOCUMENT NEEDED: "{doc_name}"

    ZONE B TEXT (eligibility clauses from bid):
    {zone_b_snippet}

    TASK: Find and extract the EXACT clause or paragraph that defines the requirement
    for "{doc_name}". Copy the exact text word-for-word from Zone B.

    If "{doc_name}" is not mentioned at all in the Zone B text, reply with:
    "Not explicitly stated in eligibility clauses. Standard GeM compliance applies for {doc_name}."

    Return ONLY the extracted clause text, no JSON, no explanation."""

        try:
            response = self.client.chat.completions.create(
                model=config.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are a precise text extraction assistant."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.0,
                max_tokens=600,
                timeout=config.OPENAI_TIMEOUT,
            )
            self._track_cost(response.usage)
            result = response.choices[0].message.content.strip()
            print(f"  [OK] LLM Zone B fallback extracted {len(result)} chars for '{doc_name}'")
            return result if result else f"Standard eligibility document — {doc_name}."
        except Exception as e:
            print(f"  [WARNING] LLM Zone B fallback failed for '{doc_name}': {e}")
            return f"Standard eligibility document — {doc_name}. Manual review required."

    # =========================================================================
    # STAGE 5B — ZONE C: ATC documents (single LLM call)
    # =========================================================================

    def _resolve_atc_with_llm(
        self,
        atc_docs: List[str],
        full_doc_list: List[str],
        zone_c_text: str,
    ) -> List[ExtractedDocument]:
        """
        Send ONLY the ATC section text to LLM (not the full PDF).
        All ATC-tagged docs resolved in ONE call per chunk to minimise cost.

        If the ATC is longer than GEM_ATC_MAX_CHARS_PER_CALL, it is split
        into overlapping chunks and each chunk is resolved independently,
        then results are merged. This ensures no clause is silently dropped.
        """
        if not zone_c_text.strip():
            print("  [WARNING] Zone C empty — ATC docs unresolved")
            msg = self.external_atc_message or "Manual review required."
            return [
                ExtractedDocument(
                    document_name=n,
                    detailed_requirement=f"ATC section not found. {msg}",
                    source_zone="Zone C (ATC)",
                    is_external_atc_required=self.has_external_atc,
                )
                for n in atc_docs
            ]

        max_chars = getattr(config, "GEM_ATC_MAX_CHARS_PER_CALL", 25000)

        # Split long ATC text into overlapping chunks so no clause is missed
        chunks: List[str] = []
        if len(zone_c_text) <= max_chars:
            chunks = [zone_c_text]
        else:
            print(f"  ATC text is {len(zone_c_text)} chars — splitting into chunks of {max_chars}")
            overlap = 500  # character overlap to avoid cutting a clause in half
            start = 0
            while start < len(zone_c_text):
                end = min(start + max_chars, len(zone_c_text))
                chunks.append(zone_c_text[start:end])
                if end == len(zone_c_text):
                    break
                start = end - overlap  # back up by overlap to avoid mid-clause cuts

        print(f"  LLM resolving {len(atc_docs)} ATC docs across {len(chunks)} chunk(s)...")

        # Accumulate results across all chunks; first non-stub answer wins
        accumulated: Dict[str, ExtractedDocument] = {}

        for chunk_idx, atc_chunk in enumerate(chunks, 1):
            # Only send docs that haven't been resolved yet
            unresolved = [
                n for n in atc_docs
                if n not in accumulated
                or "not specified" in accumulated[n].detailed_requirement.lower()
                or "standard gem format" in accumulated[n].detailed_requirement.lower()
            ]
            if not unresolved:
                print(f"  All ATC docs resolved after chunk {chunk_idx - 1}")
                break

            try:
                response = self.client.chat.completions.create(
                    model=config.OPENAI_MODEL,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are an expert Government procurement compliance analyst "
                                "specializing in Indian GeM bid documents. Return valid JSON only."
                            ),
                        },
                        {
                            "role": "user",
                            "content": self._build_atc_prompt(unresolved, full_doc_list, atc_chunk),
                        },
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.0,
                    seed=42,
                    max_tokens=config.OPENAI_MAX_TOKENS,
                    timeout=config.OPENAI_TIMEOUT,
                )
                self._track_cost(response.usage)

                items = json.loads(response.choices[0].message.content).get("atc_documents", [])

                for item in items:
                    name = item.get("document_name", "").strip()
                    if not name:
                        continue
                    detail = item.get("detailed_requirement", "").strip()
                    is_stub = (
                        not detail
                        or "not specified in atc" in detail.lower()
                        or "standard gem format" in detail.lower()
                    )
                    # Only write if this chunk gave a real answer
                    if not is_stub or name not in accumulated:
                        accumulated[name] = ExtractedDocument(
                            document_name=name,
                            detailed_requirement=detail or "Not specified in ATC - Standard GeM format applies.",
                            source_zone="Zone C (ATC)",
                            source_clause_number=str(item.get("source_clause_number") or ""),
                            is_external_atc_required=item.get("is_external_atc_required", False),
                        )

            except Exception as e:
                print(f"  [FAIL] ATC LLM call chunk {chunk_idx} failed: {e}")

        # Build final list — guarantee every requested doc has an entry
        results: List[ExtractedDocument] = []
        for name in atc_docs:
            if name in accumulated:
                results.append(accumulated[name])
            else:
                results.append(
                    ExtractedDocument(
                        document_name=name,
                        detailed_requirement="Not specified in ATC - Standard GeM format applies.",
                        source_zone="Zone C (ATC)",
                        is_external_atc_required=self.has_external_atc,
                    )
                )

        print(f"  [OK] ATC resolved: {len(results)} docs")
        return results

    def _discover_untagged_atc_docs(self, known_doc_names: List[str], zone_c_text: str) -> List[ExtractedDocument]:
        """Scan Zone C for required documents NOT already in known_doc_names."""
        prompt = f"""
        You are reading an Indian government (GeM) bid's ATC (Additional Terms and Conditions) section.
        Already identified documents: {known_doc_names}

        Read the following ATC text and list EVERY document, certificate, proof, undertaking, or submission 
        that a bidder must provide — that is NOT already in the above list.
        Return JSON: [{{"document_name": "...", "requirement_detail": "exact quote from text"}}]

        ATC TEXT:
        {zone_c_text[:20000]}
        """

    def _build_atc_prompt(
        self, atc_docs: List[str], full_list: List[str], atc_text: str
    ) -> str:
        """
        Build ATC resolution prompt.

        FIX: The old prompt forced the LLM to match vague placeholder names
        (e.g., 'Additional Doc Requested in ATC - 1') against real clause text,
        which caused misses when names didn't match headings.

        New approach:
        1. Ask LLM to FIRST identify ALL documents mentioned in the ATC text.
        2. Then match each identified document to the closest name in atc_docs.
        3. Return the clause text for each matched name.
        This handles the case where the ATC uses different terminology than the
        Zone A doc names.
        """
        all_docs_str = "\n".join(f"- {d}" for d in full_list)
        resolve_str = "\n".join(f"- {d}" for d in atc_docs)

        return f"""You are an expert GeM bid compliance analyst.

        FULL REQUIRED DOCUMENTS LIST (from bid header):
        {all_docs_str}

        DOCUMENTS TO RESOLVE (these need their requirements extracted from ATC):
        {resolve_str}

        ATC SECTION TEXT:
        {atc_text}

        TASK:
        Step 1 — Read the ATC text carefully and identify EVERY document, certificate,
                declaration, or submission requirement mentioned.
        Step 2 — For each document in "DOCUMENTS TO RESOLVE", find the BEST matching
                clause in the ATC text. Use semantic understanding, not just exact
                name matching (e.g., "Additional Doc Requested in ATC - 1" may
                correspond to "Company Registration Certificate" if that is the first
                item listed in the ATC).
        Step 3 — Extract the FULL clause text for each match (copy verbatim from ATC).
                If a document clearly is not in this ATC section, set
                detailed_requirement to "Not specified in ATC - Standard GeM format applies."

        Return JSON with key "atc_documents", each item:
        - "document_name": EXACT name from DOCUMENTS TO RESOLVE list (do not rephrase)
        - "detailed_requirement": verbatim ATC clause text (or "Not specified..." if absent)
        - "source_clause_number": clause/item number in ATC or null
        - "is_external_atc_required": true ONLY if the ATC text contains the phrase
        "Buyer uploaded ATC document Click here to view the file", else false

        Return ONLY the JSON object, no markdown, no explanation."""

    # =========================================================================
    # STAGE 5C — ZONE D: BoQ / Technical Specifications
    # =========================================================================

    def _extract_zone_d_boq(
        self, doc_name: str, zone_d_text: str, rfp_path: str
    ) -> ExtractedDocument:
        if zone_d_text.strip():
            return ExtractedDocument(
                document_name=doc_name,
                detailed_requirement=zone_d_text[:3000],
                source_zone="Zone D (Technical Specs)",
            )

        # Zone D not found via heading — try pdfplumber on last 30% of pages
        try:
            from app.modules.pdf_extractor import PDFExtractor
            ext = PDFExtractor()
            doc = fitz.open(rfp_path)
            total = len(doc)
            doc.close()
            start = max(1, int(total * 0.7))
            table_data = ext.extract_table_text_from_pages(
                rfp_path, list(range(start, total + 1))
            )
            if table_data:
                return ExtractedDocument(
                    document_name=doc_name,
                    detailed_requirement="\n".join(table_data.values())[:2000],
                    source_zone="Zone D (Technical Specs)",
                )
        except Exception as e:
            print(f"  [WARNING] BoQ extraction: {e}")

        return ExtractedDocument(
            document_name=doc_name,
            detailed_requirement=(
                "Technical specifications table not found — manual review required."
            ),
            source_zone="Zone D (Technical Specs)",
        )

    # =========================================================================
    # STAGE 5.5 — LLM BATCH DESCRIPTION ENRICHMENT
    # =========================================================================

    def _enrich_descriptions_with_llm(
        self,
        documents: List[ExtractedDocument],
        bid_metadata: Dict,
    ) -> List[ExtractedDocument]:
        """
        ONE LLM call that generates rich 50-150 word descriptions for ALL
        extracted documents.

        This is what makes the UI Description column match Image 2 quality:
          "Bidder must demonstrate minimum average annual turnover of ₹X crores
           over the last 3 financial years, certified by a CA with UDIN.
           [Source: 'minimum average annual financial turnover of the bidder...']"

        Input:  raw zone-extracted text (detailed_requirement)
        Output: rich_description, verbatim_quote, and validation metadata
        """
        if not documents:
            return documents

        # Build one entry per document
        entries = []
        for idx, doc in enumerate(documents, 1):
            entries.append(
                f"DOCUMENT {idx}:\n"
                f"Name: {doc.document_name}\n"
                f"Zone: {doc.source_zone}\n"
                f"Raw Text:\n{doc.detailed_requirement[:600]}\n"
            )

        meta_str = ""
        if bid_metadata:
            meta_lines = [f"  {k}: {v}" for k, v in bid_metadata.items() if v]
            if meta_lines:
                meta_str = (
                    "BID METADATA (inject exact values into descriptions):\n"
                    + "\n".join(meta_lines)
                    + "\n\n"
                )

        prompt = (
            f"{meta_str}"
            "You are an expert compliance analyst for Indian GeM bids.\n\n"
            "For each document below, write a RICH DESCRIPTION (50-150 words) covering:\n"
            "1. What the document proves and why it is required\n"
            "2. Specific thresholds and values (use exact numbers from raw text or bid metadata)\n"
            "3. Issuing authority or format requirements\n"
            "4. Time periods, validity, or financial year requirements\n"
            "5. Key conditions or exceptions\n\n"
            "Also extract:\n"
            "- verbatim_quote: single most important exact phrase from the raw text "
            "(empty string if ambiguous)\n"
            "- validation_type: numeric_threshold | date_validity | count_threshold "
            "| multi_condition | document_existence\n"
            "- threshold: numeric value as float or null\n"
            "- unit: 'crores' | 'lakhs' | 'years' | null\n"
            "- years_required: integer or null\n"
            "- evidence_documents: list of 1-3 document types acceptable as proof\n\n"
            + "\n".join(entries)
            + '\nReturn ONLY this JSON:\n'
            '{\n'
            '  "documents": [\n'
            '    {\n'
            '      "document_name": "exact name as provided",\n'
            '      "rich_description": "50-150 word description",\n'
            '      "verbatim_quote": "exact phrase or empty string",\n'
            '      "validation_type": "document_existence",\n'
            '      "threshold": null,\n'
            '      "unit": null,\n'
            '      "years_required": null,\n'
            '      "evidence_documents": []\n'
            '    }\n'
            '  ]\n'
            '}'
        )

        try:
            response = self.client.chat.completions.create(
                model=config.OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert RFP compliance analyst. Return valid JSON only.",
                    },
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.0,
                seed=42,
                max_tokens=config.OPENAI_MAX_TOKENS,
                timeout=config.OPENAI_TIMEOUT,
            )
            self._track_cost(response.usage)

            raw = json.loads(response.choices[0].message.content)
            enriched_list = raw.get("documents", [])

            # Build both exact and normalized-key lookup maps
            enriched_map_exact: Dict[str, Dict] = {
                item["document_name"].lower().strip(): item
                for item in enriched_list
                if "document_name" in item
            }
            all_returned_names = list(enriched_map_exact.keys())

            def _fuzzy_find(target_name: str) -> Optional[Dict]:
                """Try exact match first, then fuzzy match."""
                key = target_name.lower().strip()
                # 1. Exact match
                if key in enriched_map_exact:
                    return enriched_map_exact[key]
                # 2. Substring match (LLM truncated or expanded the name)
                for rname, ritem in enriched_map_exact.items():
                    if key in rname or rname in key:
                        return ritem
                # 3. Fuzzy match (catches minor rephrasing / punctuation differences)
                if all_returned_names:
                    close = difflib.get_close_matches(key, all_returned_names, n=1, cutoff=0.65)
                    if close:
                        return enriched_map_exact[close[0]]
                return None

            updated: List[ExtractedDocument] = []
            matched_count = 0
            for doc in documents:
                item = _fuzzy_find(doc.document_name)
                if item and item.get("rich_description"):
                    matched_count += 1
                    doc = doc.model_copy(
                        update={
                            "rich_description": item.get("rich_description", ""),
                            "verbatim_quote": item.get("verbatim_quote", ""),
                            "validation_type_hint": item.get("validation_type", "document_existence"),
                            "threshold_hint": item.get("threshold"),
                            "unit_hint": item.get("unit"),
                            "years_hint": item.get("years_required"),
                            "evidence_docs_hint": item.get("evidence_documents", []),
                        }
                    )
                else:
                    # Fallback: use raw zone text as description (not a stub)
                    doc = doc.model_copy(update={"rich_description": doc.detailed_requirement})
                updated.append(doc)

            print(f"  [OK] Enriched {matched_count}/{len(documents)} descriptions (fuzzy matching)")
            return updated  

        except Exception as e:
            print(f"  [WARNING] Description enrichment failed: {e} — using raw text")
            return [
                doc.model_copy(update={"rich_description": doc.detailed_requirement})
                for doc in documents
            ]

    # =========================================================================
    # STAGE 6 — CONVERT TO DOWNSTREAM REQUIREMENT FORMAT
    # =========================================================================

    def _convert_to_requirement_format(
        self,
        documents: list,
        bid_metadata: dict,
    ) -> list:
        """
        Post-processing override for validation_type.
        Deterministically corrects "document_existence" → "numeric_threshold",
        "date_validity", or "count_threshold" based on description keywords.
        """
        NUMERIC_KEYWORDS = [
            "turnover", "lakh", "crore", "threshold", "minimum average",
            "average annual", "financial turnover", "net worth",
            "rs.", "inr", "₹", "% of bid", "percentage",
        ]
        DATE_KEYWORDS = [
            "valid ", "validity", "expiry", "expir", "not expired",
            "issued within", "not older than",
        ]
        COUNT_KEYWORDS = [
            "number of", "at least", "minimum of", "service center",
            "years of experience", "years of past",
        ]

        requirements = []
        for i, doc in enumerate(documents, 1):
            rich = doc.rich_description if doc.rich_description else doc.detailed_requirement
            vq = doc.verbatim_quote or ""

            #override only when LLM left the default "document_existence"
            vtype = doc.validation_type_hint
            if vtype == "document_existence":
                desc_lower = (rich + " " + doc.detailed_requirement).lower()
                if any(kw in desc_lower for kw in NUMERIC_KEYWORDS):
                    vtype = "numeric_threshold"
                elif any(kw in desc_lower for kw in DATE_KEYWORDS):
                    vtype = "date_validity"
                elif any(kw in desc_lower for kw in COUNT_KEYWORDS):
                    vtype = "count_threshold"

            context = rich[:300] + (f' [Source: "{vq[:120]}"]' if vq else "")

            requirements.append({
                "criterion_id": str(i),
                "document_name": doc.document_name,
                "description": rich,
                "validation_type": vtype,           # ← uses corrected type
                "threshold": doc.threshold_hint,
                "unit": doc.unit_hint,
                "years_required": doc.years_hint,
                "calculation": "average" if "average" in rich.lower() else None,
                "conditions": [],
                "logic": None,
                "context": context,
                "criticality": "Mandatory",
                "evidence_documents": doc.evidence_docs_hint,
                "verbatim_quote": vq,
                "source_zone": doc.source_zone,
                "is_external_atc_required": doc.is_external_atc_required,
            })
        return requirements

    # =========================================================================
    # FALLBACK — Old table-based extraction (non-GeM / legacy PDFs)
    # =========================================================================

    def _fallback_old_extraction(self, rfp_path: str) -> List[Dict]:
        print("  Running old table-based extraction (fallback)...")
        hot_pages = self._scout_hot_pages(rfp_path)
        table_md = self._extract_tables_docling(rfp_path, hot_pages)
        if not table_md.strip():
            table_md = self._text_fallback(rfp_path, hot_pages)
        if not table_md.strip():
            print("[FAIL] No content extracted in fallback")
            return []
        return self._extract_with_openai_fallback(table_md)

    def _scout_hot_pages(self, rfp_path: str) -> List[int]:
        doc = fitz.open(rfp_path)
        total = len(doc)
        scores: Dict[int, int] = {}
        for i in range(total):
            text = doc[i].get_text("text").lower()
            score = sum(2 for kw in self._HOT_KEYWORDS if kw in text)
            score += sum(boost for phrase, boost in self._HEADER_BOOSTS if phrase in text)
            scores[i + 1] = score
        doc.close()
        top_n = max(10, total - 10) if total <= 30 else (20 if total <= 100 else 40)
        scored = sorted(
            [(p, s) for p, s in scores.items() if s > 0], key=lambda x: x[1], reverse=True
        )
        hot = sorted([p for p, _ in scored[:top_n]])
        return hot or list(range(1, min(16, total + 1)))

    def _extract_tables_docling(self, rfp_path: str, hot_pages: List[int]) -> str:
        converter = self._get_converter()
        tables: List[str] = []
        for page_num in hot_pages:
            try:
                result = converter.convert(rfp_path, page_range=(page_num, page_num))
                for table in result.document.tables:
                    try:
                        md = table.export_to_markdown()
                        if md and len(md.strip()) > 20:
                            tables.append(f"\n--- TABLE (Page {page_num}) ---\n{md}")
                    except Exception:
                        pass
                del result
                gc.collect()
            except Exception as e:
                print(f"  [WARNING] Docling page {page_num}: {e}")
                try:
                    from app.modules.pdf_extractor import PDFExtractor
                    ext = PDFExtractor()
                    data = ext.extract_table_text_from_pages(rfp_path, [page_num])
                    if data:
                        tables.append(
                            "\n".join(
                                f"--- TABLE (Page {p}, pdfplumber) ---\n{t}"
                                for p, t in data.items()
                            )
                        )
                except Exception:
                    pass
        return "\n".join(tables)

    def _text_fallback(self, rfp_path: str, hot_pages: Optional[List[int]]) -> str:
        try:
            doc = fitz.open(rfp_path)
            total = len(doc)
            pages = hot_pages or list(range(1, min(21, total + 1)))
            parts = [
                f"--- PAGE {p} ---\n{doc[p-1].get_text('text').strip()}"
                for p in pages
                if 1 <= p <= total and doc[p - 1].get_text("text").strip()
            ]
            doc.close()
            return "\n\n".join(parts)
        except Exception as e:
            print(f"  [WARNING] Text fallback: {e}")
            return ""

    def _extract_with_openai_fallback(self, content: str) -> List[Dict]:
        max_chars = config.MAX_INPUT_TOKENS * 5
        content = content[:max_chars] if len(content) > max_chars else content
        try:
            response = self.client.chat.completions.create(
                model=config.OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert RFP compliance analyst. Return valid JSON only.",
                    },
                    {"role": "user", "content": self._build_fallback_prompt(content)},
                ],
                response_format={"type": "json_object"},
                temperature=0.0,
                seed=42,
                max_tokens=config.OPENAI_MAX_TOKENS,
                timeout=config.OPENAI_TIMEOUT,
            )
            self._track_cost(response.usage)
            raw = json.loads(response.choices[0].message.content)
            return self._validate_and_clean(raw.get("required_documents", []))
        except Exception as e:
            print(f"  [FAIL] Fallback extraction: {e}")
            return []

    def _build_fallback_prompt(self, content: str) -> str:
        return f"""Extract all compliance requirements from this RFP content.

Return JSON with key "required_documents", each item:
- "document_name": concise name < 100 chars
- "description": 50-150 word detailed description
- "validation_type": numeric_threshold | date_validity | count_threshold | multi_condition | document_existence
- "threshold": float or null
- "unit": "crores" | "lakhs" | null
- "years_required": integer or null
- "calculation": "average" | "sum" | "minimum" | null
- "conditions": [] or list for multi_condition
- "logic": "AND" | "OR" | null
- "context": issuing authority or special conditions
- "criticality": "Mandatory" | "Important"
- "evidence_documents": list of acceptable doc types
- "verbatim_quote": exact quote or empty string

RFP CONTENT:
{content}

Return ONLY the JSON object."""

    def _validate_and_clean(self, raw_docs: List[Dict]) -> List[Dict]:
        validated, seen = [], set()
        banned = ["shall be", "will be", "must be", "should be"]
        for item in raw_docs:
            name = item.get("document_name", "").strip()
            if not name or len(name) < 5 or len(name) > 200:
                continue
            if any(ph in name.lower() for ph in banned) or name.lower() in seen:
                continue
            for key in ["threshold", "unit", "calculation", "years_required", "logic"]:
                item.setdefault(key, None)
            item.setdefault("validation_type", "document_existence")
            item.setdefault("criticality", "Mandatory")
            item.setdefault("conditions", [])
            item.setdefault("evidence_documents", [])
            item.setdefault("verbatim_quote", "")
            desc = item.get("description", "")
            vq = item.get("verbatim_quote", "")
            item["context"] = desc[:200] + (f' [Source: "{vq[:100]}"]' if vq else "")
            item["criterion_id"] = str(len(validated) + 1)
            seen.add(name.lower())
            validated.append(item)
        return validated

    # =========================================================================
    # UTILITIES
    # =========================================================================

    def _track_cost(self, usage) -> None:
        if not getattr(config, "ENABLE_COST_TRACKING", True) or not usage:
            return
        pricing = {
            "gpt-4o":      {"input": 0.0025, "output": 0.01},
            "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
            "gpt-4-turbo": {"input": 0.01, "output": 0.03},
        }
        p = pricing.get(config.OPENAI_MODEL, pricing["gpt-4o"])
        self.extraction_cost += (
            usage.prompt_tokens / 1000 * p["input"]
            + usage.completion_tokens / 1000 * p["output"]
        )

    def _get_converter(self):
        if self._converter is None:
            print("  Loading Docling converter...")
            from docling.document_converter import DocumentConverter, PdfFormatOption
            from docling.datamodel.pipeline_options import PdfPipelineOptions
            from docling.datamodel.base_models import InputFormat
            opts = PdfPipelineOptions()
            opts.do_ocr = getattr(config, "DOCLING_DO_OCR", False)
            opts.do_table_structure = True
            opts.table_structure_options.do_cell_matching = True
            opts.images_scale = 1.0
            self._converter = DocumentConverter(
                format_options={
                    InputFormat.PDF: PdfFormatOption(pipeline_options=opts)
                }
            )
            print("[OK] Docling ready")
        return self._converter

    def _hash_file(self, path: str) -> str:
        try:
            with open(path, "rb") as f:
                return hashlib.md5(f.read(65536)).hexdigest()
        except Exception:
            return hashlib.md5(path.encode()).hexdigest()
