"""
ATC Auto-Downloader

Extracts the hyperlink annotation from GeM bid PDFs pointing to an externally
uploaded ATC document, then silently downloads and returns its content.

Statuses returned by try_auto_download_atc():
  "auto_success"   → PDF downloaded and saved successfully
  "auth_required"  → GeM portal requires login (HTTP 401/403)
  "not_pdf"        → URL does not serve a PDF
  "no_link"        → Phrase found but no hyperlink annotation on that page
  "timeout"        → Server did not respond in time
  "not_detected"   → External ATC phrase not present in document at all
  "failed"         → Other network/HTTP error
"""

import hashlib
import tempfile
import time
from pathlib import Path
from typing import Optional, Tuple

import fitz  # PyMuPDF — already in requirements
import requests

# ── Configurable constants ─────────────────────────────────────────────────────
_EXTERNAL_ATC_PHRASE = "Buyer uploaded ATC document"
_DOWNLOAD_TIMEOUT_SEC = 20
_MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB hard cap

# Browser-like headers to reduce bot-rejection on CDN/portal servers
_DOWNLOAD_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/pdf,application/octet-stream,*/*",
    "Accept-Language": "en-US,en;q=0.9",
}


def extract_atc_url_from_pdf(rfp_path: str) -> Optional[str]:
    """
    Scan PDF pages for the external ATC phrase and return the hyperlink
    URI from that page's annotations.

    GeM PDFs embed a clickable URI annotation on the same page/line as:
    "Buyer uploaded ATC document Click here to view the file."

    Returns the URL string, or None if not found / no annotation present.
    """
    try:
        doc = fitz.open(rfp_path)

        for page_num, page in enumerate(doc):
            page_text = page.get_text("text")

            if _EXTERNAL_ATC_PHRASE.lower() not in page_text.lower():
                continue

            print(f"  ATC phrase found on page {page_num + 1} — scanning annotations...")

            # Method A: get_links() covers standard link annotations
            for link in page.get_links():
                uri = link.get("uri", "")
                if uri and uri.startswith("http"):
                    doc.close()
                    print(f"  URL extracted via get_links(): {uri[:80]}")
                    return uri

            # Method B: annots() covers widget / other annotation types
            for annot in page.annots():
                info = annot.info or {}
                uri = info.get("uri") or info.get("content", "")
                if uri and isinstance(uri, str) and uri.startswith("http"):
                    doc.close()
                    print(f"  URL extracted via annots(): {uri[:80]}")
                    return uri

            print(f"  [INFO] ATC phrase found on page {page_num + 1} but no URI annotation.")
            doc.close()
            return None  # Phrase found but no link — stop searching

        doc.close()

    except Exception as e:
        print(f"  [WARNING] URL extraction error: {e}")

    return None


def try_auto_download_atc(
    url: str, save_dir: Optional[str] = None
) -> Tuple[Optional[str], str]:
    """
    Download the ATC PDF from the extracted URL.

    Args:
        url:      The hyperlink URL from the bid PDF
        save_dir: Where to save the file (uses system temp dir if None)

    Returns:
        (local_file_path, status_string)
        local_file_path is None on any failure.
    """
    target_dir = Path(save_dir) if save_dir else Path(tempfile.gettempdir())
    target_dir.mkdir(parents=True, exist_ok=True)

    # Deterministic filename based on URL so we cache across runs
    url_hash = hashlib.md5(url.encode()).hexdigest()[:10]
    file_path = target_dir / f"_auto_atc_{url_hash}.pdf"

    # Return cached file if it already exists and is non-empty
    if file_path.exists() and file_path.stat().st_size > 500:
        print(f"  [OK] ATC already cached locally: {file_path.name}")
        return str(file_path), "auto_success"

    print(f"  Downloading ATC from: {url[:80]}...")
    t0 = time.time()

    try:
        resp = requests.get(
            url,
            headers=_DOWNLOAD_HEADERS,
            timeout=_DOWNLOAD_TIMEOUT_SEC,
            allow_redirects=True,
            stream=True,
        )

        if resp.status_code in (401, 403):
            print(f"  [INFO] GeM portal auth required (HTTP {resp.status_code})")
            return None, "auth_required"

        if resp.status_code != 200:
            print(f"  [WARNING] HTTP {resp.status_code} for ATC URL")
            return None, f"failed (HTTP {resp.status_code})"

        # Stream into memory with size cap
        content = b""
        for chunk in resp.iter_content(chunk_size=8192):
            content += chunk
            if len(content) > _MAX_FILE_SIZE_BYTES:
                print("  [WARNING] ATC file exceeds 50 MB — aborting download")
                return None, "failed (file too large)"

        # Verify PDF magic bytes
        if not content.startswith(b"%PDF"):
            ct = resp.headers.get("content-type", "unknown")
            print(f"  [WARNING] Downloaded content is not a PDF (Content-Type: {ct})")
            return None, "not_pdf"

        file_path.write_bytes(content)
        elapsed = time.time() - t0
        print(
            f"  [OK] ATC downloaded: {len(content)/1024:.1f} KB in {elapsed:.1f}s"
            f" → {file_path.name}"
        )
        return str(file_path), "auto_success"

    except requests.Timeout:
        print(f"  [WARNING] ATC download timed out after {_DOWNLOAD_TIMEOUT_SEC}s")
        return None, "timeout"

    except Exception as e:
        print(f"  [WARNING] ATC download error: {e}")
        return None, f"failed ({str(e)[:80]})"


def build_atc_status_message(status: str, url: Optional[str]) -> str:
    """
    Returns a user-facing message based on the download outcome.
    Used by the API response to drive frontend UI decisions.
    """
    url_line = f"\n ATC URL: {url}" if url else ""
    messages = {
        "auto_success": (
            "External ATC document was automatically downloaded and processed."
            + (f" (Source: {url})" if url else "")
        ),
        "auth_required": (
            "The external ATC document is behind GeM portal authentication and "
            "could not be downloaded automatically. Please download it from the "
            "link below and upload it here."
            + url_line
        ),
        "not_pdf": (
            "The external ATC link does not serve a downloadable PDF. "
            "Please retrieve the ATC document manually."
            + url_line
        ),
        "timeout": (
            "The ATC document server did not respond in time. "
            "Please upload the ATC PDF manually."
            + url_line
        ),
        "no_link": (
            "This bid references an external ATC document, but no hyperlink "
            "annotation was found in the PDF. Please locate and upload the ATC file."
        ),
        "not_detected": "",
    }
    return messages.get(status, f"ATC status: {status}.{url_line}")
