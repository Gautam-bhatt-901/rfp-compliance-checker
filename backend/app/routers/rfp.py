"""
RFP Analysis routes
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from typing import List
import shutil
from sqlalchemy.orm import Session
import json
import uuid

from app.auth import get_current_user
from app.models import User, AnalysisHistory
from app.database import get_db
from app.schemas import (
    AnalysisResult, DocumentMatch, AnalysisHistoryItem, 
    AnalysisHistoryDetail, RFPAnalysisResult, BatchAnalysisResult
)
from app.dependencies import get_pdf_extractor, get_list_extractor, get_document_matcher, get_rag_matcher
from app.modules.utils import validate_file_extension, clear_directory, format_results_for_display, get_summary_stats
from app import config

router = APIRouter(prefix="/api/rfp", tags=["RFP"])

@router.post("/analyze", response_model=BatchAnalysisResult)
async def analyze_rfp(
    rfp_files: List[UploadFile] = File(...),  #  accepts multiple RFPs
    provided_files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    pdf_extractor = Depends(get_pdf_extractor),
    list_extractor = Depends(get_list_extractor),
    rag_matcher = Depends(get_rag_matcher)
):
    """
    Analyze MULTIPLE RFPs against provided documents
    Each RFP is matched independently against ALL provided documents
    """
    
    # Generate batch ID for grouping
    batch_id = str(uuid.uuid4())[:8]
    
    # Validate all RFP files
    for rfp_file in rfp_files:
        if not validate_file_extension(rfp_file.filename, config.ALLOWED_EXTENSIONS):
            raise HTTPException(
                status_code=400,
                detail=f"RFP file {rfp_file.filename} format not supported. Allowed: {config.ALLOWED_EXTENSIONS}"
            )
    
    # Validate provided documents
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
    
    # Save ALL provided documents ONCE (shared across all RFPs)
    provided_paths = []
    provided_filenames = []
    for file in provided_files:
        file_path = user_docs_dir / file.filename
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        provided_paths.append(str(file_path))
        provided_filenames.append(file.filename)
    
    # INGEST USER DOCUMENTS ONCE (for RAG matching)
    if config.USE_RAG_MATCHING:
        print(f"\n🔮 Ingesting {len(provided_files)} supporting documents (ONCE for all RFPs)...")
        ingestion_stats = rag_matcher.ingest_user_documents(
            file_paths=provided_paths,
            user_id=current_user.id,
            db=db,
            clear_existing=True
        )
        print(f"✓ Ingestion complete: {ingestion_stats}")
    
    # Process EACH RFP independently
    rfp_results = []
    total_batch_cost = 0.0
    
    print(f"\n{'='*70}")
    print(f"🔍 BATCH ANALYSIS: {len(rfp_files)} RFPs vs {len(provided_files)} Documents")
    print(f"{'='*70}\n")
    
    for rfp_idx, rfp_file in enumerate(rfp_files, 1):
        print(f"\n{'='*70}")
        print(f"📋 RFP {rfp_idx}/{len(rfp_files)}: {rfp_file.filename}")
        print(f"{'='*70}")
        
        # Save current RFP file
        rfp_path = user_rfp_dir / rfp_file.filename
        with rfp_path.open("wb") as buffer:
            shutil.copyfileobj(rfp_file.file, buffer)
        
        try:
            # STEP 1: Extract text from RFP
            rfp_pages = pdf_extractor.extract_pages(str(rfp_path))
            full_text_check = " ".join(rfp_pages.values())
            
            if not rfp_pages or len(full_text_check.strip()) < 50:
                print(f"⚠️ Skipping {rfp_file.filename} - insufficient text")
                # Add empty result
                rfp_results.append(RFPAnalysisResult(
                    rfp_filename=rfp_file.filename,
                    total=0,
                    present=0,
                    review=0,
                    missing=0,
                    completion_rate=0.0,
                    matches=[],
                    extraction_cost=0.0
                ))
                continue
            
            print(f"✓ Extracted {len(rfp_pages)} pages from {rfp_file.filename}")
            
            # STEP 2: Extract required documents from THIS RFP
            required_docs = list_extractor.extract_required_documents(rfp_pages)
            
            if not required_docs:
                print(f"⚠️ No required documents found in {rfp_file.filename}")
                rfp_results.append(RFPAnalysisResult(
                    rfp_filename=rfp_file.filename,
                    total=0,
                    present=0,
                    review=0,
                    missing=0,
                    completion_rate=0.0,
                    matches=[],
                    extraction_cost=0.0
                ))
                continue
            
            print(f"✓ Found {len(required_docs)} required documents")
            
            # STEP 3: MATCH against provided documents
            if config.USE_RAG_MATCHING:
                print(f"🔮 RAG matching for {rfp_file.filename}...")
                results = rag_matcher.find_matches(
                    requirements=required_docs,
                    user_id=current_user.id,
                    db=db
                )
                
                # Calculate costs
                extraction_cost = getattr(list_extractor, 'extraction_cost', 0.0)
                rag_total_cost = rag_matcher.get_total_cost()
                validation_cost = 0.0
                if hasattr(rag_matcher, 'validator') and rag_matcher.validator:
                    validation_cost = rag_matcher.validator.get_total_cost()
                rfp_cost = extraction_cost + rag_total_cost + validation_cost
                
            else:
                # Fallback to traditional matching
                from app.dependencies import get_document_matcher
                document_matcher = get_document_matcher()
                results = document_matcher.match_documents(
                    required_docs,
                    provided_filenames,
                    provided_paths=provided_paths
                )
                extraction_cost = getattr(list_extractor, 'extraction_cost', 0.0)
                matching_cost = getattr(document_matcher, 'matching_cost', 0.0)
                rfp_cost = extraction_cost + matching_cost
            
            # Format results
            formatted_results = format_results_for_display(results)
            stats = get_summary_stats(formatted_results)
            
            # Convert to response format
            matches = [
                DocumentMatch(
                    required_document=r['Required Document'],
                    status=r['Status'],
                    matched_file=r.get('Matched File') or "N/A",
                    confidence_score=float(r.get('Confidence Score', 0.0)),
                    description = r.get("Description", "")
                )
                for r in formatted_results
            ]
            
            # Store THIS RFP's analysis in history
            analysis_record = AnalysisHistory(
                user_id=current_user.id,
                batch_id=batch_id,  # NEW: Link to batch
                rfp_filename=rfp_file.filename,
                num_provided_docs=len(provided_filenames),
                num_required_docs=stats['total'],
                num_matched=stats['present'],
                num_review=stats['review'],
                num_missing=stats['missing'],
                completion_rate=stats['completion_rate'],
                api_cost=rfp_cost,
                results_json=json.dumps({
                    'matches': [
                        {
                            'required_document': r['Required Document'],
                            'status': r['Status'],
                            'matched_file': r['Matched File'],
                            'confidence': float(r.get('Confidence Score', 0.0)),
                            'description': r.get('Description', '')
                        }
                        for r in formatted_results
                    ]
                })
            )
            db.add(analysis_record)
            db.commit()
            
            # Add to results
            rfp_results.append(RFPAnalysisResult(
                rfp_filename=rfp_file.filename,
                total=stats['total'],
                present=stats['present'],
                review=stats['review'],
                missing=stats['missing'],
                completion_rate=stats['completion_rate'],
                matches=matches,
                extraction_cost=rfp_cost
            ))
            
            total_batch_cost += rfp_cost
            
            print(f"✅ {rfp_file.filename} - {stats['present']}/{stats['total']} matched ({stats['completion_rate']:.1f}%)")
            print(f"💰 Cost: ${rfp_cost:.6f}")
            
        except Exception as e:
            print(f"❌ Error processing {rfp_file.filename}: {e}")
            # Add error result
            rfp_results.append(RFPAnalysisResult(
                rfp_filename=rfp_file.filename,
                total=0,
                present=0,
                review=0,
                missing=0,
                completion_rate=0.0,
                matches=[],
                extraction_cost=0.0
            ))
    
    print(f"\n{'='*70}")
    print(f"✅ BATCH ANALYSIS COMPLETE")
    print(f"{'='*70}")
    print(f" Batch ID: {batch_id}")
    print(f" Total RFPs Processed: {len(rfp_results)}")
    print(f" Total Cost: ${total_batch_cost:.6f}")
    print(f"{'='*70}\n")
    
    return BatchAnalysisResult(
        batch_id=batch_id,
        total_rfps=len(rfp_results),
        total_cost=total_batch_cost,
        rfp_results=rfp_results
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

@router.get("/history/batch/{batch_id}", response_model=List[AnalysisHistoryDetail])
async def get_batch_analysis(
    batch_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all RFP analyses from a specific batch"""
    analyses = db.query(AnalysisHistory).filter(
        AnalysisHistory.batch_id == batch_id,
        AnalysisHistory.user_id == current_user.id
    ).all()
    
    if not analyses:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    return analyses

@router.get("/history/{analysis_id}", response_model=AnalysisHistoryDetail)
async def get_analysis_detail(
    analysis_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed analysis results for single RFP"""
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
