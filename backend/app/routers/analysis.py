import os
import shutil
from typing import List
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from app.auth import get_current_user
from app.config import settings
from app.modules.pdf_extractor import PDFExtractor
from app.modules.list_extractor import ListExtractor
from app.modules.document_matcher import DocumentMatcher

router = APIRouter(prefix="/api/analysis", tags=["Analysis"])

def save_upload_file(upload_file: UploadFile, destination: str) -> str:
    try:
        file_path = os.path.join(destination, upload_file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(upload_file.file, buffer)
        return file_path
    finally:
        upload_file.file.close()

@router.post("/process")
async def process_rfp(
    rfp_file: UploadFile = File(...),
    candidate_files: List[UploadFile] = File(...),
    current_user: dict = Depends(get_current_user)
):
    # Create unique session dir for this request
    session_id = os.urandom(4).hex()
    session_dir = os.path.join(settings.UPLOAD_DIR, session_id)
    rfp_dir = os.path.join(session_dir, "rfp")
    docs_dir = os.path.join(session_dir, "docs")
    
    os.makedirs(rfp_dir, exist_ok=True)
    os.makedirs(docs_dir, exist_ok=True)
    
    try:
        # 1. Save Files
        rfp_path = save_upload_file(rfp_file, rfp_dir)
        provided_paths = []
        provided_filenames = []
        
        for cf in candidate_files:
            path = save_upload_file(cf, docs_dir)
            provided_paths.append(path)
            provided_filenames.append(cf.filename)
            
        # 2. Initialize Modules
        # Note: In production, consider dependency injection for these
        pdf_extractor = PDFExtractor()
        list_extractor = ListExtractor()
        doc_matcher = DocumentMatcher()
        
        # 3. Extract RFP Text
        rfp_pages = pdf_extractor.extract_pages(rfp_path)
        
        # 4. Extract Requirements
        required_docs = list_extractor.extract_required_documents(rfp_pages)
        
        if not required_docs:
            return {"status": "warning", "message": "No required documents found in RFP", "results": []}
            
        # 5. Match Documents
        results = doc_matcher.match_documents(
            required_docs,
            provided_filenames,
            provided_paths=provided_paths
        )
        
        # 6. Calculate Stats
        total = len(results)
        present = sum(1 for r in results if 'Present' in str(r.get('Status')))
        missing = total - present
        
        return {
            "status": "success",
            "summary": {
                "total": total,
                "present": present,
                "missing": missing,
                "completion_rate": round((present/total)*100, 1) if total > 0 else 0
            },
            "results": results
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    finally:
        # Cleanup
        if os.path.exists(session_dir):
            shutil.rmtree(session_dir)