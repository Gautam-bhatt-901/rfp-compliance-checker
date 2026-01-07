"""
HYBRID RAG + LLM VERIFICATION Document Matcher

Combines vector search with intelligent LLM reasoning.
Optimized for Compliance Documents using Semantic Bridging.
"""

import os
import time
import json
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text

# LangChain & OpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from openai import OpenAI
from anthropic import Anthropic

# App modules
from app.models import DocumentChunk
from app import config

class RAGMatcher:
    def __init__(self, pdf_extractor=None):
        """Initialize Hybrid RAG + LLM matcher"""
        
        # 1. Initialize Embeddings (Vector Search)
        # We use text-embedding-3-small for better cost/performance ratio
        self.embeddings = OpenAIEmbeddings(
            openai_api_key=config.OPENAI_API_KEY,
            model="text-embedding-3-small" 
        )

        # 2. Initialize LLM Clients (Verification)
        self.llm_available = False
        self.active_provider = None
        self.openai_client = None
        self.anthropic_client = None

        # Try OpenAI First
        if config.OPENAI_API_KEY:
            try:
                self.openai_client = OpenAI(api_key=config.OPENAI_API_KEY)
                self.llm_available = True
                self.active_provider = 'openai'
                print("✓ OpenAI LLM initialized for verification")
            except Exception as e:
                print(f"⚠️ OpenAI LLM init failed: {e}")

        # Try Anthropic Fallback
        if not self.llm_available and config.ANTHROPIC_API_KEY:
            try:
                self.anthropic_client = Anthropic(api_key=config.ANTHROPIC_API_KEY)
                self.llm_available = True
                self.active_provider = 'anthropic'
                print("✓ Anthropic LLM initialized for verification")
            except Exception as e:
                print(f"⚠️ Anthropic LLM init failed: {e}")

        # 3. Text Splitter (Chunking)
        # Larger chunks are better for compliance docs to keep context together
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1500,       # Increased size for better context
            chunk_overlap=300,     # Overlap to prevent cutting sentences
            separators=["\n\n", "\n", ". ", " ", ""],
            length_function=len,
        )

        # 4. Load PDF Extractor
        if pdf_extractor:
            self.pdf_extractor = pdf_extractor
        else:
            from app.modules.pdf_extractor import PDFExtractor
            self.pdf_extractor = PDFExtractor()

        # Cost Tracking
        self.ingestion_cost = 0.0
        self.matching_cost = 0.0

        # Initialize ComplianceValidator
        try:
            from app.modules.compliance_validator import ComplianceValidator
            self.validator = ComplianceValidator()
            print("✓ ComplianceValidator initialized")
        except Exception as e:
            print(f"⚠️  ComplianceValidator initialization failed: {e}")
            self.validator = None
        
        print(f"✓ Hybrid RAG Matcher initialized")

    def ingest_user_documents(
        self, 
        file_paths: List[str], 
        user_id: int, 
        db: Session, 
        clear_existing: bool = True
    ) -> Dict[str, Any]:
        """
        Reads user files, chunks them, creates embeddings, and saves to DB.
        """
        print(f"\n{'='*70}")
        print(f"📚 INGESTING DOCUMENTS FOR USER {user_id}")
        print(f"{'='*70}")
        start_time = time.time()

        # 1. Clear old chunks for this user
        if clear_existing:
            try:
                deleted_count = db.query(DocumentChunk).filter(
                    DocumentChunk.user_id == user_id
                ).delete()
                db.commit()
                print(f"🗑️ Cleared {deleted_count} old chunks")
            except Exception as e:
                db.rollback()
                print(f"⚠️ Error clearing old chunks: {e}")

        all_chunks = []
        stats = {
            'total_files': len(file_paths),
            'processed_files': 0,
            'failed_files': 0,
            'total_chunks': 0,
            'cost': 0.0
        }

        # 2. Process Files
        for file_path in file_paths:
            try:
                filename = os.path.basename(file_path)
                print(f"\n📄 Processing: {filename}")
                
                chunks = self._extract_and_chunk_file(file_path, filename)
                
                if not chunks:
                    print(f" ⚠️ No content extracted from {filename}")
                    stats['failed_files'] += 1
                    continue
                
                print(f" ✓ Extracted {len(chunks)} chunks")
                all_chunks.extend(chunks)
                stats['processed_files'] += 1
                
            except Exception as e:
                print(f" ❌ Error processing {filename}: {e}")
                stats['failed_files'] += 1

        if not all_chunks:
            print("\n⚠️ No chunks to embed")
            return stats

        # 3. Create Embeddings & Save
        print(f"\n🔮 Embedding {len(all_chunks)} chunks...")
        embedded_chunks = self._embed_chunks_batch(all_chunks, user_id, db)
        
        stats['total_chunks'] = len(embedded_chunks)
        
        # Estimated Cost for text-embedding-3-small ($0.02 per 1M tokens)
        # Approx 1 token = 4 chars
        total_chars = sum(len(c['content']) for c in all_chunks)
        stats['cost'] = (total_chars / 4 / 1000000) * 0.02 
        self.ingestion_cost = stats['cost']

        elapsed_time = time.time() - start_time
        print(f"\n{'='*70}")
        print(f"✅ INGESTION COMPLETE in {elapsed_time:.2f}s")
        print(f" Cost: ${stats['cost']:.6f}")
        print(f"{'='*70}\n")
        
        return stats

    def _extract_and_chunk_file(self, file_path: str, filename: str) -> List[Dict]:
        """
        Extract and chunk file with Markdown table preservation
        Handles tables from PyMuPDF4LLM output
        """
        chunks = []
        
        # 1. Quick Validation
        if not os.path.exists(file_path):
            print(f" ❌ Error: File not found: {file_path}")
            return []
        if os.path.getsize(file_path) == 0:
            print(f" ⚠️ Warning: Skipping empty file: {filename}")
            return []

        try:
            # 2. Delegate logic for text extractor
            # PDFs (real pages) and DOCX/TXT (simulated pages) automatically.
            pages_dict = self.pdf_extractor.extract_pages(file_path)

            # 3. Process the output
            if not pages_dict:
                print(f" ⚠️ No content extracted from {filename}")
                return []

            for page_num, page_text in pages_dict.items():
                # Clean whitespace
                if not page_text or len(page_text.strip()) < 50:
                    continue
                
                # Check if page contains Markdown tables
                has_markdown_table = config.MARKDOWN_TABLE_DETECTION and self._has_markdown_table(page_text)
            
                if has_markdown_table and config.TABLE_AS_SINGLE_CHUNK:
                    # Extract Markdown tables separately
                    table_chunks, remaining_text = self._extract_markdown_tables(page_text)
                    
                    # Add table chunks (keep tables intact)
                    for i, table_chunk in enumerate(table_chunks):
                        if len(table_chunk) <= config.TABLE_MAX_CHARS:
                            # Table fits in single chunk
                            chunks.append({
                                'content': table_chunk,
                                'source_filename': filename,
                                'page_number': page_num,
                                'metadata': {
                                    'source': filename,
                                    'page': page_num,
                                    'type': 'markdown_table',
                                    'table_index': i
                                }
                            })
                        else:
                            # Table too large, split by rows
                            print(f"  ⚠️  Large table on page {page_num}, splitting by rows")
                            sub_chunks = self._chunk_large_markdown_table(table_chunk)
                            for j, sub_chunk in enumerate(sub_chunks):
                                chunks.append({
                                    'content': sub_chunk,
                                    'source_filename': filename,
                                    'page_number': page_num,
                                    'metadata': {
                                        'source': filename,
                                        'page': page_num,
                                        'type': 'markdown_table_fragment',
                                        'table_index': i,
                                        'fragment_index': j
                                    }
                                })
                    
                    # Chunk remaining text normally
                    if remaining_text.strip():
                        text_chunks = self.text_splitter.split_text(remaining_text)
                        for i, chunk_text in enumerate(text_chunks):
                            chunks.append({
                                'content': chunk_text,
                                'source_filename': filename,
                                'page_number': page_num,
                                'metadata': {
                                    'source': filename,
                                    'page': page_num,
                                    'type': 'text',
                                    'chunk_index': i
                                }
                            })
                else:
                    # No tables or table chunking disabled
                    page_chunks = self.text_splitter.split_text(page_text)
                    for i, chunk_text in enumerate(page_chunks):
                        chunks.append({
                            'content': chunk_text,
                            'source_filename': filename,
                            'page_number': page_num,
                            'metadata': {
                                'source': filename,
                                'page': page_num,
                                'type': 'mixed',
                                'chunk_index': i
                            }
                        })
        
        except Exception as e:
            print(f"  ❌ Extraction error for {filename}: {e}")
            import traceback
            traceback.print_exc()
            return []
        
        return chunks

    def _has_markdown_table(self, text: str) -> bool:
        """
        Check if text contains Markdown table
        Pattern: | col1 | col2 |\n|------|------|\n| val1 | val2 |
        """
        import re
        # Look for table header separator: |------|------|
        pattern = r'\|[-\s:|]+\|'
        return bool(re.search(pattern, text))

    def _extract_markdown_tables(self, text: str) -> Tuple[List[str], str]:
        """
        Extract Markdown tables from text
        Returns: (list of complete tables, remaining text)
        """
        import re
        
        tables = []
        remaining_text = text
        
        # Pattern matches complete Markdown tables
        # Matches: header row + separator row + data rows
        table_pattern = r'(\|[^\n]+\|\n\|[-\s:|]+\|\n(?:\|[^\n]+\|\n?)+)'
        matches = re.finditer(table_pattern, text)
        
        for match in matches:
            table_content = match.group(0).strip()
            # Fix any malformed table formatting
            table_content = self._fix_markdown_table(table_content)
            tables.append(table_content)
            # Remove from remaining text
            remaining_text = remaining_text.replace(match.group(0), '', 1)
        
        return tables, remaining_text

    def _fix_markdown_table(self, table_text: str) -> str:
        """
        Fix common Markdown table formatting issues
        Ensures all rows start and end with |
        """
        lines = table_text.split('\n')
        fixed_lines = []
        
        for line in lines:
            if '|' in line:
                line = line.strip()
                # Ensure line starts with |
                if not line.startswith('|'):
                    line = '| ' + line
                # Ensure line ends with |
                if not line.endswith('|'):
                    line = line + ' |'
                fixed_lines.append(line)
        
        return '\n'.join(fixed_lines)

    def _chunk_large_markdown_table(self, table_text: str, max_chars: int = None) -> List[str]:
        """
        Split large Markdown table while preserving header in each chunk
        This ensures every chunk has context
        """
        if max_chars is None:
            max_chars = config.TABLE_MAX_CHARS
        
        lines = table_text.strip().split('\n')
        
        # If table is small enough or malformed, return as-is
        if len(lines) < 3 or len(table_text) <= max_chars:
            return [table_text]
        
        # Extract components
        header = lines[0]  # | Role | Experience | Qualification |
        separator = lines[1]  # |------|------------|---------------|
        data_rows = lines[2:]  # Actual data rows
        
        chunks = []
        current_chunk = [header, separator]
        current_size = len(header) + len(separator)
        
        for row in data_rows:
            row_size = len(row)
            
            # Check if adding this row exceeds limit
            if current_size + row_size > max_chars and len(current_chunk) > 2:
                # Save current chunk
                chunks.append('\n'.join(current_chunk))
                # Start new chunk with header
                current_chunk = [header, separator, row]
                current_size = len(header) + len(separator) + row_size
            else:
                # Add row to current chunk
                current_chunk.append(row)
                current_size += row_size
        
        # Add last chunk
        if len(current_chunk) > 2:
            chunks.append('\n'.join(current_chunk))
        
        return chunks

    def _embed_chunks_batch(
        self, 
        chunks: List[Dict], 
        user_id: int, 
        db: Session, 
        batch_size: int = 100
    ) -> List[DocumentChunk]:
        """Embed and save chunks in batches to avoid timeouts"""
        saved_chunks = []

        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            try:
                texts = [chunk['content'] for chunk in batch]
                vectors = self.embeddings.embed_documents(texts)

                db_chunks = []
                for chunk_data, vector in zip(batch, vectors):
                    db_chunk = DocumentChunk(
                        user_id=user_id,
                        source_filename=chunk_data['source_filename'],
                        page_number=chunk_data.get('page_number'),
                        content=chunk_data['content'],
                        metadata_=chunk_data.get('metadata', {}),
                        embedding=vector
                    )
                    db_chunks.append(db_chunk)

                db.add_all(db_chunks)
                db.commit()
                saved_chunks.extend(db_chunks)
                
            except Exception as e:
                print(f" ❌ Embedding batch failed: {e}")
                db.rollback()

        return saved_chunks

    def find_matches(
        self, 
        requirements: List[Dict], 
        user_id: int, 
        db: Session
    ) -> List[Dict]:
        """
        Main Matching Function
        1. Builds a semantic query for each requirement.
        2. Retrieves top chunks from DB (RAG).
        3. Verifies match with LLM.
        """
        print(f"\n{'='*70}")
        print(f"🔍 HYBRID MATCHING: {len(requirements)} REQUIREMENTS")
        print(f"{'='*70}")
        
        results = []
        query_start_time = time.time()

        for idx, req in enumerate(requirements, 1):
            # Normalize Input
            if isinstance(req, dict):
                reqname = req.get('document_name', 'Unknown')
                reqcontext = req.get('context', '')
                reqcriticality = req.get('criticality', 'Mandatory')
                full_requirement = req  # Keep full structured requirement
            else:
                reqname = str(req)
                reqcontext = ""
                reqcriticality = "Mandatory"
                full_requirement = {
                    'document_name': reqname,
                    'validation_type': 'document_existence',
                    'context': reqcontext,
                    'criticality': reqcriticality
                }
            
            print(f"  [{idx}/{len(requirements)}] {reqname}")
            
            try:
                # Build semantic query
                query_text = self._build_semantic_search_query(reqname, reqcontext)
                query_vector = self.embeddings.embed_query(query_text)
                self.matching_cost += 0.000001  # Tiny embedding cost
                
                # Retrieve top chunks
                top_chunks = db.query(DocumentChunk).filter(
                    DocumentChunk.user_id == user_id
                ).order_by(
                    DocumentChunk.embedding.l2_distance(query_vector)
                ).limit(5).all()
                
                if not top_chunks:
                    results.append(self._create_missing_result(reqname, reqcontext, reqcriticality))
                    continue
                
                # Extract chunk text and filenames
                chunk_texts = [chunk.content for chunk in top_chunks]
                chunk_filenames = [chunk.source_filename for chunk in top_chunks]
                
                # Use ComplianceValidator if available
                if self.validator and full_requirement.get('validation_type') != 'document_existence':
                    print(f"    → Using validation for {full_requirement.get('validation_type')}")
                    
                    validation_result = self.validator.validate_requirement(
                        requirement=full_requirement,
                        document_chunks=chunk_texts,
                        filenames=chunk_filenames
                    )
                    
                    # Convert validation result to match result format
                    result = self._convert_validation_to_result(
                        validation_result, 
                        reqname, 
                        reqcontext, 
                        reqcriticality,
                        chunk_filenames
                    )
                
                # Fallback to LLM verification
                elif self.llm_available:
                    result = self._llm_verify_match(reqname, reqcontext, reqcriticality, top_chunks)
                
                # Last resort: distance-based matching
                else:
                    result = self.distance_based_match(
                        reqname, reqcontext, reqcriticality, 
                        top_chunks[0], query_vector, db
                    )
                
                print(f"    → {result['Status']}: {result['Matched File']}")
                results.append(result)
            
            except Exception as e:
                print(f"  ✗ Error: {e}")
                results.append(self._create_missing_result(reqname, reqcontext, reqcriticality, str(e)))

        elapsed = time.time() - query_start_time
        print(f"\n✅ MATCHING COMPLETE in {elapsed:.2f}s")
        return results

    def _build_semantic_search_query(self, req_name: str, req_context: str) -> str:
        """
        Constructs a query that looks for the CONTENT of the document,
        not just the title.
        """
        clean_name = req_name.replace("Required", "").replace("Mandatory", "").strip().lower()
        
        # Semantic Keyword Bridge
        # Maps document types to the words likely found INSIDE them
        semantic_map = {
            "certificate": "certify grant valid registration number issued by authority",
            "license": "permit license granted to valid until authorized",
            "financial": "balance sheet profit loss auditor report assets liabilities turnover",
            "audit": "independent auditor report financial statement true and fair view",
            "tax": "income tax return assessment year acknowledgement pan",
            "gst": "goods and services tax registration form gstin",
            "pan": "permanent account number income tax department",
            "incorporation": "certificate of incorporation registrar of companies",
            "agreement": "this agreement made between witness whereof signed by",
            "experience": "completion certificate successfully completed work order satisfactory performance",
            "turnover": "annual turnover chartered accountant financial year",
            "affidavit": "solemnly affirm oath notary public declare",
            "undertaking": "i hereby declare undertake confirm",
            "cv": "curriculum vitae resume experience education skills profile",
            "iso": "international standard organization quality management system",
            "power of attorney": "appoint constitute attorney lawful"
        }

        keywords = ""
        for key, val in semantic_map.items():
            if key in clean_name:
                keywords += f" {val}"

        # Final Query: Name + Bridge Keywords + Context
        # Example: "GST Certificate goods services tax gstin Must be valid 2024"
        query = f"{clean_name} {keywords} {req_context}"
        return query

    def _llm_verify_match(
        self, 
        req_name: str, 
        req_context: str, 
        req_criticality: str, 
        chunks: List[DocumentChunk]
    ) -> Dict:
        """Use LLM to decide if the retrieved chunks actually meet the requirement"""
        
        # Prepare context from chunks
        evidence_text = ""
        for i, chunk in enumerate(chunks[:3], 1): # Look at top 3 chunks
            evidence_text += f"\n--- [File: {chunk.source_filename} | Page: {chunk.page_number}] ---\n"
            evidence_text += chunk.content[:800] # Truncate to save tokens
            evidence_text += "\n"

        prompt = f"""
        You are a Compliance Auditor. Check if the user's documents contain the required proof.

        REQUIRED DOCUMENT: "{req_name}"
        CONTEXT/DETAILS: "{req_context}"
        CRITICALITY: {req_criticality}

        USER'S EVIDENCE (Retrieved Snippets):
        {evidence_text}

        DECISION RULES:
        1. SEARCH: Does the evidence text clearly discuss the required topic?
        2. MATCH: Is it the specific TYPE of document requested? (e.g., specific ISO standard)
        3. OUTPUT:
           - If match found: Return status "high" (Present) or "medium" (Review).
           - If evidence is unrelated/weak: Return status "low" or "nomatch".
        
        Output JSON only:
        {{
            "matched_file": "Exact filename from evidence or null",
            "confidence": "high|medium|low|nomatch",
            "reasoning": "One sentence explanation"
        }}
        """

        try:
            response_text = ""
            
            # Call OpenAI
            if self.active_provider == 'openai':
                response = self.openai_client.chat.completions.create(
                    model=config.OPENAI_MODEL,
                    messages=[
                        {"role": "system", "content": "You are a JSON-only output machine."},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.0
                )
                response_text = response.choices[0].message.content

            # Call Anthropic
            elif self.active_provider == 'anthropic':
                response = self.anthropic_client.messages.create(
                    model=config.ANTHROPIC_MODEL,
                    max_tokens=500,
                    messages=[{"role": "user", "content": prompt}]
                )
                response_text = response.content[0].text

            # Parse
            data = json.loads(response_text)
            conf = data.get("confidence", "nomatch")
            
            # Score Mapping
            score_map = {'high': 0.95, 'medium': 0.75, 'low': 0.45, 'nomatch': 0.15}
            score = score_map.get(conf, 0.0)

            # Status Determination
            if score >= 0.70:
                status = config.STATUS_PRESENT
            elif score >= 0.40:
                status = config.STATUS_REVIEW
            else:
                status = config.STATUS_MISSING

            return {
                'Required Document': req_name,
                'Description': req_context,
                'Status': status,
                'Matched File': data.get('matched_file') or "N/A",
                'Confidence Score': f"{score:.2f}",
                'Reasoning': data.get('reasoning', 'LLM decision'),
                'Criticality': req_criticality
            }

        except Exception as e:
            print(f"LLM Verification failed: {e}")
            # Fallback to simple logic
            return self._create_missing_result(req_name, req_context, req_criticality, "LLM Error")

    def _distance_based_match(self, req_name, req_context, req_criticality, chunk, query_vector, db):
        """Fallback if LLM is unavailable: Use Vector Distance"""
        if not query_vector or not db:
            score = 0.5
        else:
            # Calculate distance (0 is identical)
            distance = db.query(
                DocumentChunk.embedding.l2_distance(query_vector)
            ).filter(DocumentChunk.id == chunk.id).scalar()
            
            # Convert to similarity score (0 to 1)
            # OpenAI text-embedding-3-small distance usually 0.5 - 1.2 for non-exact
            score = max(0.0, 1.0 - (distance / 1.2))

        if score >= 0.60:
            status = config.STATUS_PRESENT
        elif score >= 0.45:
            status = config.STATUS_REVIEW
        else:
            status = config.STATUS_MISSING

        return {
            'Required Document': req_name,
            'Description': req_context,
            'Status': status,
            'Matched File': chunk.source_filename if status != config.STATUS_MISSING else "N/A",
            'Confidence Score': f"{score:.2f}",
            'Reasoning': f"Vector Similarity Match (Score: {score:.2f})",
            'Criticality': req_criticality
        }

    def _create_missing_result(self, name, context, criticality, reason="No match found"):
        return {
            'Required Document': name,
            'Description': context,
            'Status': config.STATUS_MISSING,
            'Matched File': 'N/A',
            'Confidence Score': '0.00',
            'Reasoning': reason,
            'Criticality': criticality
        }

    def get_total_cost(self) -> float:
        return self.ingestion_cost + self.matching_cost

    def _convert_validation_to_result(
        self, 
        validation: Dict, 
        req_name: str, 
        req_context: str, 
        req_criticality: str,
        chunk_filenames: List[str]
    ) -> Dict:
        """
        Convert ComplianceValidator result to RAGMatcher result format
        """
        
        status_map = {
            'compliant': config.STATUS_PRESENT,
            'non_compliant': config.STATUS_REVIEW,
            'insufficient_data': config.STATUS_REVIEW,
            'not_found': config.STATUS_MISSING
        }
        
        status = status_map.get(validation['status'], config.STATUS_MISSING)
        matched_file = validation.get('matched_file', 'N/A')
        confidence = validation.get('confidence', 0.0)
        reasoning = validation.get('reasoning', 'Validation completed')
        
        if not matched_file or matched_file in ['', 'None', 'null', None]:
            # Try to get filename from extracted_data
            extracted_data = validation.get('extracted_data', {})
            if isinstance(extracted_data, dict):
                # Try primary_source from extracted data
                matched_file = extracted_data.get('primary_source', '')
            
            # If still empty, use first chunk filename as fallback
            if not matched_file and chunk_filenames and len(chunk_filenames) > 0:
                matched_file = chunk_filenames[0]
            
            # Last resort
            if not matched_file:
                matched_file = 'N/A'
        
        # Additional safety check - convert Python None to string 'N/A'
        if matched_file is None or str(matched_file).lower() == 'none':
            matched_file = 'N/A'

        return {
            'Required Document': req_name,
            'Description': req_context,
            'Status': status,
            'Matched File': matched_file,
            'Confidence Score': f"{confidence:.2f}",
            'Reasoning': reasoning,
            'Criticality': req_criticality
        }
