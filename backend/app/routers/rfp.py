"""
RFP Analysis routes
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from typing import List, Optional
import shutil
from sqlalchemy.orm import Session
import json
import uuid
from pathlib import Path
from app.auth import get_current_user
from app.models import User, AnalysisHistory
from app.database import get_db
from app.schemas import (
    AnalysisResult, DocumentMatch, AnalysisHistoryItem, 
    AnalysisHistoryDetail, RFPAnalysisResult, BatchAnalysisResult
)
from app.dependencies import get_list_extractor, get_document_matcher, get_rag_matcher
from app.modules.utils import validate_file_extension, clear_directory, format_results_for_display, get_summary_stats
from app import config

router = APIRouter(prefix="/api/rfp", tags=["RFP"])

@router.post("/analyze", response_model=BatchAnalysisResult)
async def analyze_rfp(
    rfp_files: List[UploadFile] = File(...),  #  accepts multiple RFPs
    provided_files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
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
        print(f"\nIngesting {len(provided_files)} supporting documents (ONCE for all RFPs)...")
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
    print(f"BATCH ANALYSIS: {len(rfp_files)} RFPs vs {len(provided_files)} Documents")
    print(f"{'='*70}\n")
    
    for rfp_idx, rfp_file in enumerate(rfp_files, 1):
        print(f"\n{'='*70}")
        print(f"RFP {rfp_idx}/{len(rfp_files)}: {rfp_file.filename}")
        print(f"{'='*70}")
        
        # Save current RFP file
        rfp_path = user_rfp_dir / rfp_file.filename
        with rfp_path.open("wb") as buffer:
            shutil.copyfileobj(rfp_file.file, buffer)
        
        try:
            # STEP 1: Quick file validation (DoclingExtractor handles its own extraction)
            import os
            rfp_file_size = os.path.getsize(str(rfp_path))
            if rfp_file_size < 500:
                print(f"Skipping {rfp_file.filename} - file too small ({rfp_file_size} bytes)")
                rfp_results.append(RFPAnalysisResult(
                    rfp_filename=rfp_file.filename,
                    total=0, present=0, review=0, missing=0,
                    completion_rate=0.0, matches=[], extraction_cost=0.0
                ))
                continue

            print(f"[OK] RFP file validated: {rfp_file.filename} ({rfp_file_size/1024:.1f} KB)")
            
            # STEP 2: Extract required documents from THIS RFP
            required_docs = list_extractor.extract_required_documents(str(rfp_path))

            # ── GeM: Capture bid metadata + external ATC warning ─────────────────────────
            bid_metadata = getattr(list_extractor, "bid_metadata", {})
            has_external_atc = getattr(list_extractor, "has_external_atc", False)
            external_atc_msg = getattr(list_extractor, "external_atc_message", None)

            if bid_metadata:
                print(f"Bid metadata: {list(bid_metadata.keys())}")

            if has_external_atc:
                print(f"External ATC: {external_atc_msg}")
                # Store warning in results_json later

            if not required_docs:
                print(f"No required documents found in {rfp_file.filename}")
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
            
            print(f"[OK] Found {len(required_docs)} required documents")
            
            # STEP 3: MATCH against provided documents
            if config.USE_RAG_MATCHING:
                print(f"RAG matching for {rfp_file.filename}...")
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
                batch_id=batch_id,  # Link to batch
                rfp_filename=rfp_file.filename,
                rfp_file_path=str(rfp_path),
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
                    ],
                    "bid_metadata": bid_metadata,
                    "external_atc_warning": external_atc_msg or "",
                })
            )
            db.add(analysis_record)
            db.commit()
            db.refresh(analysis_record)
            
            # Add to results
            rfp_results.append(RFPAnalysisResult(
                rfp_filename=rfp_file.filename,
                total=stats['total'],
                present=stats['present'],
                review=stats['review'],
                missing=stats['missing'],
                completion_rate=stats['completion_rate'],
                matches=matches,
                extraction_cost=rfp_cost,
                has_external_atc=getattr(list_extractor, 'has_external_atc', False),         
                external_atc_warning=getattr(list_extractor, 'external_atc_message', None),  
                atc_document_url=getattr(list_extractor, 'atc_document_url', None),          
                analysis_id=analysis_record.id,
            ))
            
            total_batch_cost += rfp_cost
            
            print(f"{rfp_file.filename} - {stats['present']}/{stats['total']} matched ({stats['completion_rate']:.1f}%)")
            print(f"Cost: ${rfp_cost:.6f}")
            
        except Exception as e:
            print(f"Error processing {rfp_file.filename}: {e}")
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
    print(f"BATCH ANALYSIS COMPLETE")
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

@router.post("/re-analyze-atc/{analysis_id}", response_model=RFPAnalysisResult)
async def re_analyze_with_atc(
    analysis_id: int,
    atc_file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    list_extractor=Depends(get_list_extractor),
    rag_matcher=Depends(get_rag_matcher),
):
    """
    Fallback Pass 2: called only when auto-download failed (auth_required/timeout).
    User uploads the ATC PDF manually — we re-run ONLY Zone C resolution + matching
    for ATC-flagged documents and merge results back.
    """
    analysis = db.query(AnalysisHistory).filter(
        AnalysisHistory.id == analysis_id,
        AnalysisHistory.user_id == current_user.id,
    ).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    # Save uploaded ATC file
    user_rfp_dir = config.UPLOAD_RFP_DIR / str(current_user.id)
    atc_path = user_rfp_dir / f"_manual_atc_{atc_file.filename}"
    with atc_path.open("wb") as buf:
        shutil.copyfileobj(atc_file.file, buf)

    # Extract ATC text
    from app.modules.pdf_extractor import PDFExtractor
    pdf_ext = PDFExtractor()
    try:
        atc_pages = pdf_ext.extract_pages(str(atc_path))
        atc_text = "\n".join(atc_pages.values())
        print(f"[OK] Manual ATC extracted: {atc_file.filename} ({len(atc_pages)} pages)")
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Could not extract ATC file: {e}")

    # Inject and re-resolve
    list_extractor.set_external_atc_content(atc_text)

    rfp_path = analysis.rfp_file_path
    if not rfp_path or not Path(rfp_path).exists():
        raise HTTPException(
            status_code=410,
            detail="Original RFP file no longer on disk. Please re-upload the full bid.",
        )

    # Load saved results
    saved = json.loads(analysis.results_json or "{}")
    existing_matches = saved.get("matches", [])
    bid_metadata = saved.get("bid_metadata", {})

    # Identify ATC-pending documents
    atc_patterns = getattr(
        config, "GEM_ATC_DOC_PATTERNS",
        ["Requested in ATC", "Additional Doc", "OEM Authorization Certificate"],
    )
    atc_doc_names = [
        m["required_document"] for m in existing_matches
        if any(p.lower() in m["required_document"].lower() for p in atc_patterns)
        or m.get("pending_atc", False)
    ]
    if not atc_doc_names:
        raise HTTPException(status_code=400, detail="No ATC-pending documents in this analysis")

    # Re-run Zone C resolution
    pages = list_extractor._extract_full_text(rfp_path)
    zones = list_extractor._segment_zones(pages)
    zones = list_extractor._handle_external_atc(rfp_path, "\n".join(pages.values()), zones)

    full_doc_list = [m["required_document"] for m in existing_matches]
    atc_documents = list_extractor._resolve_atc_with_llm(atc_doc_names, full_doc_list, zones["zone_c"])
    atc_documents = list_extractor._enrich_descriptions_with_llm(atc_documents, bid_metadata)
    atc_requirements = list_extractor._convert_to_requirement_format(atc_documents, bid_metadata)

    # Re-match ATC docs (embeddings already ingested — no re-ingestion cost)
    atc_raw_results = rag_matcher.find_matches(
        requirements=atc_requirements, user_id=current_user.id, db=db
    )
    atc_formatted = format_results_for_display(atc_raw_results)
    atc_result_map = {r["Required Document"]: r for r in atc_formatted}

    # Merge updated ATC results into existing matches
    merged = []
    for m in existing_matches:
        name = m["required_document"]
        if name in atc_result_map:
            new = atc_result_map[name]
            merged.append({
                "required_document": name,
                "status":            new["Status"],
                "matched_file":      new["Matched File"],
                "confidence":        float(new.get("Confidence Score", 0.0)),
                "description":       new.get("Description", ""),
                "pending_atc":       False,
            })
        else:
            merged.append(m)

    # Recalculate stats
    all_fmt = [
        {
            "Required Document": m["required_document"],
            "Status":            m["status"],
            "Matched File":      m["matched_file"],
            "Confidence Score":  str(m.get("confidence", 0.0)),
            "Description":       m.get("description", ""),
        }
        for m in merged
    ]
    stats = get_summary_stats(all_fmt)

    # Update DB record
    analysis.num_matched = stats["present"]
    analysis.num_review = stats["review"]
    analysis.num_missing = stats["missing"]
    analysis.completion_rate = stats["completion_rate"]
    analysis.results_json = json.dumps({
        "matches": merged,
        "bid_metadata": bid_metadata,
    })
    db.commit()

    # Build response
    matches_out = [
        DocumentMatch(
            required_document=m["required_document"],
            status=m["status"],
            matched_file=m.get("matched_file") or "N/A",
            confidence_score=float(m.get("confidence", 0.0)),
            description=m.get("description", ""),
            pending_atc=m.get("pending_atc", False),
        )
        for m in merged
    ]
    return RFPAnalysisResult(
        rfp_filename=analysis.rfp_filename,
        total=stats["total"],
        present=stats["present"],
        review=stats["review"],
        missing=stats["missing"],
        completion_rate=stats["completion_rate"],
        matches=matches_out,
        extraction_cost=rag_matcher.matching_cost,
        has_external_atc=False,
        external_atc_warning=None,
        atc_document_url=None,
        analysis_id=analysis_id,
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
