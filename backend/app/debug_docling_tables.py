"""
debug_docling_tables.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Standalone diagnostic script — NO app imports, runs anywhere.

Shows EXACTLY what Docling extracts and hands to the LLM:
  1. Scout results  → which pages scored and why
  2. Raw table dump → every cell Docling found per table
  3. Markdown view  → the exact string sent to the LLM
  4. Miss analysis  → pages that scored low but may have tables

Usage:
  python debug_docling_tables.py your_rfp.pdf --save > debug_output.txt 2>&1 (to save output to a file)
  python debug_docling_tables.py path/to/rfp.pdf
  python debug_docling_tables.py path/to/rfp.pdf --all-pages
  python debug_docling_tables.py path/to/rfp.pdf --pages 5 8 12 15
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import sys
import argparse
import time
from pathlib import Path


# ── same keywords as docling_extractor.py ─────────────────────
HOT_KEYWORDS = [
    'checklist', 'annexure', 'appendix', 'submission', 'mandatory', 'criteria',
    'eligibility', 'eligibility requirement', 'qualification', 'enclosure',
    'documents required', 'technical bid', 'financial bid', 'format',
    'required documents', 'technical qualification', 'documentary evidence',
    'undertaking', 'certificate', 'proof', 'supporting documents'
]

HEADER_BOOSTS = [
    ('eligibility criteria',       10),
    ('qualification criteria',     10),
    ('documents to be submitted',   8),
    ('list of documents',           8),
    ('mandatory documents',         8),
    ('pre-qualification',           6),
    ('technical bid requirements',  6),
    ('financial bid requirements',  6),
]


# ══════════════════════════════════════════════════════════════
# 1. SCOUT — show all page scores
# ══════════════════════════════════════════════════════════════
def run_scout(pdf_path: str) -> list[int]:
    import fitz

    doc = fitz.open(pdf_path)
    total = len(doc)
    scores: dict[int, dict] = {}

    print(f"\n{'═'*60}")
    print(f"STAGE 1 — SCOUT RESULTS  ({total} total pages)")
    print(f"{'═'*60}")
    print(f"{'Page':<6} {'Score':<7} {'Matched Keywords'}")
    print(f"{'─'*6} {'─'*7} {'─'*44}")

    for i in range(total):
        text_lower = doc[i].get_text("text").lower()
        score = 0
        matched = []

        for kw in HOT_KEYWORDS:
            if kw in text_lower:
                score += 2
                matched.append(kw)

        for phrase, boost in HEADER_BOOSTS:
            if phrase in text_lower:
                score += boost
                matched.append(f"{phrase}(+{boost})")

        scores[i + 1] = {'score': score, 'matched': matched}

        if score > 0:
            kw_display = ', '.join(matched[:5])
            if len(matched) > 5:
                kw_display += f" +{len(matched)-5} more"
            print(f"  p{i+1:<4} {score:<7} {kw_display}")

    doc.close()

    # Dynamic selection
    if total <= 30:
        top_n = max(10, total - 10)
    elif total <= 100:
        top_n = 20
    else:
        top_n = 40

    scored = [(p, s['score']) for p, s in scores.items() if s['score'] > 0]
    scored.sort(key=lambda x: x[1], reverse=True)
    hot = sorted([p for p, _ in scored[:top_n]])

    if not hot:
        hot = list(range(1, min(16, total + 1)))
        print(f"\n  ⚠ No pages scored — defaulting to pages 1-{hot[-1]}")

    print(f"\n  ✓ Selected {len(hot)} hot pages: {hot}")
    return hot


# ══════════════════════════════════════════════════════════════
# 2. DOCLING TABLE EXTRACTION — raw dump
# ══════════════════════════════════════════════════════════════
def run_docling(pdf_path: str, page_list: list[int]) -> str:
    """
    Runs Docling on the given pages and prints:
      - How many tables found per page range
      - Raw cell-by-cell dump of every table
      - Final markdown sent to LLM
    Returns the final markdown string.
    """
    from docling.document_converter import DocumentConverter, PdfFormatOption
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.datamodel.base_models import InputFormat

    # Build converter (same settings as docling_extractor.py)
    opts = PdfPipelineOptions()
    opts.do_ocr = False
    opts.do_table_structure = True
    opts.table_structure_options.do_cell_matching = True
    opts.images_scale = 1.0

    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=opts)
        }
    )

    print(f"\n{'═'*60}")
    print(f"STAGE 2 — DOCLING EXTRACTION  (pages: {page_list})")
    print(f"{'═'*60}")

    ranges = pages_to_ranges(page_list)
    all_markdown_parts: list[str] = []
    total_tables = 0

    for page_num in page_list:          # ONE PAGE AT A TIME
        print(f"\n  >> Processing page {page_num} ...")
        start_t = time.time()
        try:
            result = converter.convert(pdf_path, page_range=(page_num, page_num))
            doc = result.document
            elapsed = time.time() - start_t
            n_tables = len(doc.tables)
            total_tables += n_tables
            print(f"     Docling finished in {elapsed:.1f}s -> {n_tables} table(s)")

            for t_idx, table in enumerate(doc.tables, 1):
                page_no = table.prov[0].page_no if table.prov else "?"

                print(f"\n    +-- TABLE {t_idx} on page {page_no} -----")
                try:
                    grid = table.data.grid
                    print(f"    |  Grid: {len(grid)} rows x {len(grid[0]) if grid else 0} cols")
                    for r_idx, row in enumerate(grid):
                        cells = [f"[{cell.text.strip()[:30]}]" if cell and cell.text else "[EMPTY]"
                                for cell in row]
                        prefix = "HDR" if r_idx == 0 else f"R{r_idx:02d}"
                        print(f"    |  {prefix}: {'  '.join(cells)}")
                except Exception as e:
                    print(f"    |  (could not dump grid: {e})")

                md = table.export_to_markdown()
                print(f"    |  Markdown ({len(md)} chars):")
                for line in md.strip().split('\n'):
                    print(f"    |    {line}")
                print(f"    +------------------------------------------")

                if md.strip():
                    all_markdown_parts.append(
                        f"\n--- TABLE {t_idx} (Page {page_no}) ---\n{md}"
                    )

            # Free memory after each page
            del result
            import gc
            gc.collect()

        except Exception as e:
            print(f"    [FAIL] Docling failed for page {page_num}: {e}")
            print(f"      -> This page will fall back to pdfplumber in production")


    # ── FINAL MARKDOWN SENT TO LLM ────────────────────────────────
    final_markdown = "\n".join(all_markdown_parts)

    print(f"\n{'═'*60}")
    print(f"STAGE 3 — FINAL MARKDOWN SENT TO LLM")
    print(f"{'═'*60}")
    print(f"  Total tables found : {total_tables}")
    print(f"  Total characters   : {len(final_markdown)}")
    print(f"  Estimated tokens   : ~{len(final_markdown)//4}")
    print(f"\n{'─'*60}")
    print(final_markdown if final_markdown.strip() else "  ⚠ EMPTY — nothing would be sent to LLM")
    print(f"{'─'*60}")

    return final_markdown


# ══════════════════════════════════════════════════════════════
# 3. PDFPLUMBER COMPARISON — side by side
# ══════════════════════════════════════════════════════════════
def run_pdfplumber(pdf_path: str, page_list: list[int]):
    """
    Runs pdfplumber on the same pages so you can compare what it finds
    vs what Docling finds — helps identify if the miss is a Docling issue
    or a page selection issue.
    """
    try:
        import pdfplumber
    except ImportError:
        print("\n  ⚠ pdfplumber not installed — skipping comparison")
        return

    print(f"\n{'═'*60}")
    print(f"STAGE 4 — PDFPLUMBER COMPARISON  (same pages)")
    print(f"{'═'*60}")

    with pdfplumber.open(pdf_path) as pdf:
        total_pdf = len(pdf.pages)
        for page_num in page_list:
            zero_idx = page_num - 1
            if zero_idx < 0 or zero_idx >= total_pdf:
                continue

            page = pdf.pages[zero_idx]
            tables = page.extract_tables({
                "vertical_strategy":   "text",
                "horizontal_strategy": "text",
                "intersection_y_tolerance": 10
            })

            print(f"\n  Page {page_num}: {len(tables)} table(s) via pdfplumber")
            for t_idx, table in enumerate(tables, 1):
                print(f"    Table {t_idx}: {len(table)} rows × {len(table[0]) if table else 0} cols")
                for r_idx, row in enumerate(table[:5]):   # show first 5 rows
                    cells = [f"[{str(c or '').strip()[:25]}]" for c in row]
                    print(f"      {'HDR' if r_idx==0 else f'R{r_idx:02d}'}: {'  '.join(cells)}")
                if len(table) > 5:
                    print(f"      ... {len(table)-5} more rows")


# ══════════════════════════════════════════════════════════════
# 4. FULL PAGE TEXT — check if table is actually text or image
# ══════════════════════════════════════════════════════════════
def check_page_text(pdf_path: str, page_list: list[int]):
    """
    For each hot page shows how much native text was found.
    Very low char count = image/scanned page → Docling needs OCR=True.
    """
    import fitz

    print(f"\n{'═'*60}")
    print(f"STAGE 5 — PAGE TEXT DENSITY CHECK")
    print(f"{'═'*60}")
    print(f"  (Low char count = scanned page → set DOCLING_DO_OCR=true)")
    print(f"\n  {'Page':<6} {'Chars':<8} {'Words':<8} {'Diagnosis'}")
    print(f"  {'─'*6} {'─'*8} {'─'*8} {'─'*30}")

    doc = fitz.open(pdf_path)
    for p in page_list:
        if 1 <= p <= len(doc):
            text = doc[p - 1].get_text("text")
            chars = len(text.strip())
            words = len(text.split())
            if chars < 50:
                diag = "⚠ SCANNED/IMAGE — needs OCR"
            elif chars < 300:
                diag = "⚠ Low text — table may be image-based"
            else:
                diag = "✓ Native text OK"
            print(f"  p{p:<5} {chars:<8} {words:<8} {diag}")
    doc.close()


# ══════════════════════════════════════════════════════════════
# UTILITIES
# ══════════════════════════════════════════════════════════════
def pages_to_ranges(pages: list[int]) -> list[tuple[int, int]]:
    if not pages:
        return []
    ranges, start, prev = [], pages[0], pages[0]
    for p in pages[1:]:
        if p != prev + 1:
            ranges.append((start, prev))
            start = p
        prev = p
    ranges.append((start, prev))
    return ranges


def write_output(markdown: str, pdf_path: str):
    """Save the full LLM input to a .txt file for easy inspection."""
    out_path = Path(pdf_path).stem + "_docling_debug.txt"
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write("═" * 60 + "\n")
        f.write("EXACT CONTENT SENT TO LLM\n")
        f.write("═" * 60 + "\n")
        f.write(markdown)
    print(f"\n  💾 Full LLM input saved → {out_path}")


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser(
        description="Diagnose Docling table extraction for an RFP PDF"
    )
    parser.add_argument("pdf_path", help="Path to the RFP PDF file")
    parser.add_argument(
        "--all-pages", action="store_true",
        help="Skip scout, run Docling on ALL pages"
    )
    parser.add_argument(
        "--pages", nargs="+", type=int, metavar="N",
        help="Override scout: specify exact page numbers e.g. --pages 5 8 12"
    )
    parser.add_argument(
        "--no-pdfplumber", action="store_true",
        help="Skip the pdfplumber comparison stage"
    )
    parser.add_argument(
        "--save", action="store_true",
        help="Save the full LLM input to a .txt file"
    )
    args = parser.parse_args()

    pdf_path = args.pdf_path
    if not Path(pdf_path).exists():
        print(f"✗ File not found: {pdf_path}")
        sys.exit(1)

    print(f"\n{'═'*60}")
    print(f"DOCLING TABLE DIAGNOSTIC")
    print(f"File: {Path(pdf_path).name}")
    print(f"{'═'*60}")

    # Decide which pages to process
    if args.pages:
        hot_pages = sorted(args.pages)
        print(f"\n  Mode: MANUAL  →  pages {hot_pages}")
        # Still run scout for reference
        run_scout(pdf_path)
    elif args.all_pages:
        import fitz
        doc = fitz.open(pdf_path)
        hot_pages = list(range(1, len(doc) + 1))
        doc.close()
        print(f"\n  Mode: ALL PAGES  →  {len(hot_pages)} pages")
    else:
        hot_pages = run_scout(pdf_path)

    # Text density check (always run — tells you if OCR is needed)
    check_page_text(pdf_path, hot_pages)

    # Docling extraction with full dump
    final_markdown = run_docling(pdf_path, hot_pages)

    # pdfplumber comparison
    if not args.no_pdfplumber:
        run_pdfplumber(pdf_path, hot_pages)

    # Save output
    if args.save:
        write_output(final_markdown, pdf_path)

    # Final verdict
    print(f"\n{'═'*60}")
    print(f"DIAGNOSTIC SUMMARY")
    print(f"{'═'*60}")
    if not final_markdown.strip():
        print("  ✗ PROBLEM: No tables extracted at all")
        print("  POSSIBLE CAUSES:")
        print("    1. Tables are image-based → set DOCLING_DO_OCR=true and re-run")
        print("    2. Table pages scored 0 → use --pages N to force specific pages")
        print("    3. PDF has no real tables (inline text formatted as table)")
        print("    QUICK TEST: python debug_docling_tables.py file.pdf --all-pages")
    else:
        n_tables = final_markdown.count("--- TABLE")
        print(f"  ✓ {n_tables} table(s) extracted, {len(final_markdown)} chars sent to LLM")
        if n_tables > 0:
            print("  → If LLM still misses items, check the table dump above:")
            print("    • Are all rows visible? (missing rows = pdfplumber fallback needed)")
            print("    • Are column headers clear? (vague headers confuse the LLM)")
            print("    • Run with --save to get the full LLM input in a .txt file")


if __name__ == "__main__":
    main()
