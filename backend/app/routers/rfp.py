"""
RFP Analysis routes - UPDATED with history storage
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from typing import List
import shutil
from sqlalchemy.orm import Session
import json

from app.auth import get_current_user
from app.models import User, AnalysisHistory
from app.database import get_db
from app.schemas import AnalysisResult, DocumentMatch, AnalysisHistoryItem, AnalysisHistoryDetail
from app.dependencies import get_pdf_extractor, get_list_extractor, get_document_matcher, get_rag_matcher
from app.modules.utils import validate_file_extension, clear_directory, format_results_for_display, get_summary_stats
from app import config

router = APIRouter()

@router.post("/analyze", response_model=AnalysisResult)
async def analyze_rfp(
    rfp_file: UploadFile = File(...),
    provided_files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    pdf_extractor = Depends(get_pdf_extractor),
    list_extractor = Depends(get_list_extractor),
    rag_matcher = Depends(get_rag_matcher)
):
    """
    Analyze RFP compliance using RAG-based matching
    """
    # Validate files
    if not validate_file_extension(rfp_file.filename, config.ALLOWED_EXTENSIONS):
        raise HTTPException(
            status_code=400, 
            detail=f"RFP file format not supported. Allowed: {config.ALLOWED_EXTENSIONS}"
        )
    
    for file in provided_files:
        if not validate_file_extension(file.filename, config.ALLOWED_EXTENSIONS):
            raise HTTPException(
                status_code=400, 
                detail=f"File {file.filename} format not supported"
            )
    
    # Setup user directories
    user_rfp_dir = config.UPLOAD_RFP_DIR / str(current_user.id)
    user_docs_dir = config.UPLOAD_DOCS_DIR / str(current_user.id)
    user_rfp_dir.mkdir(parents=True, exist_ok=True)
    user_docs_dir.mkdir(parents=True, exist_ok=True)
    
    # Clear previous uploads
    clear_directory(str(user_rfp_dir))
    clear_directory(str(user_docs_dir))
    
    # Save RFP file
    rfp_path = user_rfp_dir / rfp_file.filename
    with rfp_path.open("wb") as buffer:
        shutil.copyfileobj(rfp_file.file, buffer)
    
    # Save provided documents
    provided_paths = []
    provided_filenames = []
    for file in provided_files:
        file_path = user_docs_dir / file.filename
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        provided_paths.append(str(file_path))
        provided_filenames.append(file.filename)
    
    # STEP 1: Extract text from RFP using pdf_extractor
    print(f"\n{'='*70}")
    print(f"🔍 ANALYZING RFP: {rfp_file.filename}")
    print(f"{'='*70}")
    
    rfp_pages = pdf_extractor.extract_pages(str(rfp_path))
    full_text_check = " ".join(rfp_pages.values())
    
    if not rfp_pages or len(full_text_check.strip()) < 50:
        raise HTTPException(
            status_code=400, 
            detail="Unable to extract sufficient text from RFP document"
        )
    
    print(f"✓ Extracted {len(rfp_pages)} pages from RFP")
    
    # STEP 2: Extract required documents from RFP
    required_docs = list_extractor.extract_required_documents(rfp_pages)
    
    if not required_docs:
        raise HTTPException(
            status_code=400, 
            detail="No required documents found in RFP"
        )
    
    print(f"✓ Found {len(required_docs)} required documents")
    
    # STEP 3: INGEST USER DOCUMENTS (RAG Pipeline)
    if config.USE_RAG_MATCHING:
        print(f"\n🔮 Using RAG-based matching...")
        
        # Ingest all provided documents
        ingestion_stats = rag_matcher.ingest_user_documents(
            file_paths=provided_paths,
            user_id=current_user.id,
            db=db,
            clear_existing=True
        )
        
        # STEP 4: FIND MATCHES using vector similarity
        results = rag_matcher.find_matches(
            requirements=required_docs,
            user_id=current_user.id,
            db=db
        )
        
        # Get costs
        extraction_cost = getattr(list_extractor, 'extraction_cost', 0.0)
        rag_total_cost = rag_matcher.get_total_cost()

        validation_cost = 0.0
        if hasattr(rag_matcher, 'validator') and rag_matcher.validator:
            validation_cost = rag_matcher.validator.get_total_cost()

        total_cost = extraction_cost + rag_total_cost + validation_cost
        
        print(f"  💰 Cost Breakdown:")
        print(f"     - Extraction: ${extraction_cost:.4f}")
        print(f"     - RAG Matching: ${rag_total_cost:.4f}")
        print(f"     - Validation: ${validation_cost:.4f}")
        print(f"     - Total: ${total_cost:.4f}")
        
    else:
        # Fallback to traditional matching
        print(f"\n⚠️  RAG disabled, using traditional matching...")
        from app.dependencies import get_document_matcher
        document_matcher = get_document_matcher()
        
        results = document_matcher.match_documents(
            required_docs,
            provided_filenames,
            provided_paths=provided_paths
        )
        
        extraction_cost = getattr(list_extractor, 'extraction_cost', 0.0)
        matching_cost = getattr(document_matcher, 'matching_cost', 0.0)
        total_cost = extraction_cost + matching_cost
    
    # Format results for response
    formatted_results = format_results_for_display(results)
    stats = get_summary_stats(formatted_results)
    
    # Convert to response format
    matches = [
        DocumentMatch(
            required_document = r['Required Document'],
            status = r['Status'],
            matched_file = r.get('Matched File') or "N/A",
            confidence_score = float(r.get('Confidence Score', 0.0))
        )
        for r in formatted_results
    ]
    
    # Store analysis in history
    analysis_record = AnalysisHistory(
        user_id=current_user.id,
        rfp_filename=rfp_file.filename,
        num_provided_docs=len(provided_filenames),
        num_required_docs=stats['total'],
        num_matched=stats['present'],
        num_review=stats['review'],
        num_missing=stats['missing'],
        completion_rate=stats['completion_rate'],
        api_cost=total_cost,
        results_json=json.dumps({
            'matches': [
                {
                    'required_document': r['Required Document'],
                    'status': r['Status'],
                    'matched_file': r['Matched File'],
                    'confidence': float(r.get('Confidence Score', 0.0))
                }
                for r in formatted_results
            ]
        })
    )
    
    db.add(analysis_record)
    db.commit()
    
    print(f"\n{'='*70}")
    print(f"✅ ANALYSIS COMPLETE")
    print(f"{'='*70}")
    print(f"  Total Requirements: {stats['total']}")
    print(f"  Matched: {stats['present']}")
    print(f"  Review Needed: {stats['review']}")
    print(f"  Missing: {stats['missing']}")
    print(f"  Completion: {stats['completion_rate']:.1f}%")
    print(f"  Total Cost: ${total_cost:.6f}")
    print(f"{'='*70}\n")
    
    return AnalysisResult(
        total=stats['total'],
        present=stats['present'],
        review=stats['review'],
        missing=stats['missing'],
        completion_rate=stats['completion_rate'],
        matches=matches,
        extraction_cost=total_cost
    )

@router.get("/history", response_model=List[AnalysisHistoryItem])
async def get_analysis_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 50
):
    """Get analysis history for current user"""
    history = db.query(AnalysisHistory).filter(
        AnalysisHistory.user_id == current_user.id
    ).order_by(AnalysisHistory.created_at.desc()).limit(limit).all()
    
    return history

@router.get("/history/{analysis_id}", response_model=AnalysisHistoryDetail)
async def get_analysis_detail(
    analysis_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed analysis results"""
    analysis = db.query(AnalysisHistory).filter(
        AnalysisHistory.id == analysis_id,
        AnalysisHistory.user_id == current_user.id
    ).first()
    
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    return analysis

@router.delete("/history/{analysis_id}")
async def delete_analysis(
    analysis_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete an analysis record"""
    analysis = db.query(AnalysisHistory).filter(
        AnalysisHistory.id == analysis_id,
        AnalysisHistory.user_id == current_user.id
    ).first()
    
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    db.delete(analysis)
    db.commit()
    
    return {"message": "Analysis deleted successfully"}
