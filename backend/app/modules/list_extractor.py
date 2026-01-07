"""
List Extraction Module - OPTIMIZED with LLM-First Approach
Priority: API LLM (GPT-4/Claude) → spaCy fallback
Extracts required documents from RFP text using cloud LLMs
"""

import re
import json
from typing import List, Dict, Optional, Union
from openai import OpenAI
from anthropic import Anthropic
from app import config
import numpy as np

from app.modules.pdf_extractor import PDFExtractor 

class ListExtractor:
    """
    Extracts required document lists from RFP text with LLM-first approach:
    1. API LLM (GPT-4/Claude) for high accuracy
    2. spaCy fallback only if LLM fails
    """
    
    def __init__(self):
        """Initialize API LLM clients (spaCy lazy-loaded only when needed)"""
        
        # Initialize API LLM clients first
        self.llm_available = False
        self.active_provider = None
        self.extraction_cost = 0.0
        
        # Try OpenAI
        if config.OPENAI_API_KEY:
            try:
                self.openai_client = OpenAI(api_key=config.OPENAI_API_KEY)
                self.active_provider = 'openai'
                self.llm_available = True
                print("[OK] OpenAI GPT-4 client initialized")
            except Exception as e:
                print(f"[WARNING] OpenAI initialization failed: {e}")
        
        # Try Anthropic if OpenAI not available
        if not self.llm_available and config.ANTHROPIC_API_KEY:
            try:
                self.anthropic_client = Anthropic(api_key=config.ANTHROPIC_API_KEY)
                self.active_provider = 'anthropic'
                self.llm_available = True
                print("[OK] Anthropic Claude client initialized")
            except Exception as e:
                print(f"[WARNING] Anthropic initialization failed: {e}")
        
        # Lazy loading for spaCy (only load if LLM fails)
        self.nlp = None
        self.phrase_matcher = None
        self.spacy_loaded = False
        
        if not self.llm_available:
            print("[WARNING] No API LLM available. Will use spaCy fallback.")
            self._initialize_spacy()
    
    def _initialize_spacy(self):
        """Lazy load spaCy model (only when needed as fallback)"""
        if self.spacy_loaded:
            return
        
        print("🔄 Loading spaCy model (fallback mode)...")
        try:
            import spacy
            from spacy.matcher import PhraseMatcher
            
            try:
                self.nlp = spacy.load(config.SPACY_MODEL)
            except OSError:
                print(f"Downloading spaCy model: {config.SPACY_MODEL}")
                import os
                os.system(f"python -m spacy download {config.SPACY_MODEL}")
                self.nlp = spacy.load(config.SPACY_MODEL)
            
            # Create phrase matcher for document keywords
            self.phrase_matcher = PhraseMatcher(self.nlp.vocab, attr="LOWER")
            patterns = [self.nlp.make_doc(keyword) for keyword in config.DOCUMENT_KEYWORDS]
            self.phrase_matcher.add("DOCUMENT_KEYWORDS", patterns)
            
            self.spacy_loaded = True
            print("[OK] spaCy model loaded successfully")
        except Exception as e:
            print(f"[FAIL] spaCy initialization failed: {e}")
            raise
    
    def extract_required_documents(self, rfp_text_or_pages: Union[str, Dict[int, str]]) -> List[str]:
        """
        Main method to extract all required documents from RFP
        PRIORITY: API LLM first → spaCy fallback
        
        Args:
            rfp_text: Full text extracted from RFP document
        
        Returns:
            Deduplicated list of required document names
        """
        print("\n" + "="*70)
        print("📋 STARTING DOCUMENT EXTRACTION (LLM-FIRST MODE)")
        print("="*70)
        
        # STAGE 1: Prepare the context
        if isinstance(rfp_text_or_pages, dict):
            # Input is paginated, use smart selection
            final_context_text = self._scout_relevant_sections(rfp_text_or_pages)
        else:
            # Input is string (legacy), fallback to truncation but warn
            print("[WARNING] Warning: Non-paginated input received. Using truncation.")
            final_context_text = rfp_text_or_pages[:config.MAX_INPUT_TOKENS * 4]

        # STAGE 2: Try API LLM extraction
        if self.llm_available:
            print(f"\n🤖 STAGE 1: API LLM extraction ({self.active_provider.upper()})...")
            try:
                llm_results = self.extract_with_llm(final_context_text, [])
                
                if llm_results and len(llm_results) >= 3:
                    print(f" [OK] LLM extraction successful: {len(llm_results)} documents found")
                    
                    # Show cost
                    if self.extraction_cost > 0:
                        print(f" 💰 API Cost: ${self.extraction_cost:.4f}")
                    
                    print("="*70 + "\n")
                    return llm_results
                else:
                    print(f" [WARNING] LLM returned insufficient results ({len(llm_results)} docs)")
                    print(" → Falling back to spaCy...")       
            except Exception as e:
                print(f" [FAIL] LLM extraction failed: {e}")
                print(" → Falling back to spaCy...")
        else:
            print("\n[WARNING] No API LLM available, using spaCy extraction...")
        
        # STAGE 3: spaCy fallback (ONLY IF LLM FAILS)
        print(f"\n🔍 STAGE 2: spaCy fallback extraction...")
        
        # Initialize spaCy if not already loaded
        if not self.spacy_loaded:
            self._initialize_spacy()
        
        spacy_results = self._extract_with_spacy(final_context_text)
        print(f" → Found {len(spacy_results)} documents with spaCy")
        print("="*70 + "\n")
        
        return spacy_results
    
    def _scout_relevant_sections(self, pages: Dict[int, str], pdf_path: str = None) -> str:
        """
        The 'Scout' Algorithm:
        Identifies and merges the most relevant parts of the RFP.
        """
        total_pages = len(pages)
        if total_pages == 0:
            return ""
        
        print(f"🔍 Scouting {total_pages} pages for requirements...")

        # --- Configuration ---
        # Keywords that signal a requirements section
        hot_keywords = [
            'checklist', 'annexure', 'appendix', 'submission', 'mandatory', 'criteria',
            'eligibility', 'eligibility requirement','qualification', 'enclosure', 'documents required', 
            'technical bid', 'financial bid', 'format', 'required documents', 'technical qualification'
            'documentary evidence', 'undertaking', 'certificate', 'proof', 'supporting documents'
        ]
        
        # --- Scoring ---
        page_scores = {}
        for p_num, text in pages.items():
            text_lower = text.lower()
            score = 0
            
            # Keyword density scoring
            for kw in hot_keywords:
                if kw in text_lower:
                    score += 2
            # Boost for headers
            if "eligibility criteria" in text_lower or "qualification criteria" in text_lower:
                score += 10 # High boost for explicit criteria pages
            
            page_scores[p_num] = score

        # --- OPTIMIZATION: Table Sniper ---
        # If we have the PDF path, let's re-extract tables from the "hottest" pages
        if pdf_path:
            # Find pages that likely have eligibility tables (Score > 5)
            hot_pages = [p for p, s in page_scores.items() if s >= 6]
            
            if hot_pages:
                print(f"🎯 Table Sniper: Targeting {len(hot_pages)} high-value pages for improved table extraction...")
                extractor = PDFExtractor()
                # Run pdfplumber ONLY on these specific pages
                table_data = extractor.extract_table_text_from_pages(pdf_path, hot_pages)
                
                # Merge the good table data back into our text context
                for p_num, table_text in table_data.items():
                    print(f"   [OK] Injected structured table into Page {p_num}")
                    # We append the table at the top of the page text so LLM sees it first
                    pages[p_num] = table_text + "\n\n" + pages[p_num]

        # --- Selection Strategy ---
        selected_indices = set()
        
        # DYNAMIC SELECTION BASED ON DOCUMENT SIZE
        if total_pages <= 30:
            top_scorers_count = max(10, total_pages - 10)
        elif total_pages <= 100:
            top_scorers_count = 20
        else:
            top_scorers_count = 40
            
        remaining_pages = [p for p in page_scores.keys() if p not in selected_indices]
        sorted_pages = sorted(remaining_pages, key=lambda x: page_scores[x], reverse=True)
        selected_indices.update(sorted_pages[:top_scorers_count])
        
        # Sort and merge final text
        final_indices = sorted(list(selected_indices))
        final_context_parts = []
        for i in final_indices:
            final_context_parts.append(f"--- PAGE {i} ---")
            final_context_parts.append(pages[i])
            
        return "\n\n".join(final_context_parts)
    
    def extract_with_llm(self, rfp_text: str, spacy_candidates: List[str]) -> List[Dict]:
        """
        Enhanced LLM extraction with structured requirement parsing
        Extracts validation rules, not just document names
        """
        
        max_chars = config.MAX_INPUT_TOKENS * 5
        if len(rfp_text) > max_chars:
            print(f"  ⚠ Truncating RFP text from {len(rfp_text)} to {max_chars} chars")
            rfp_text = rfp_text[:max_chars]
        
        # Build enhanced prompt with validation rules
        prompt = self._build_extraction_prompt(rfp_text)
        
        # Get LLM response
        raw_documents = []
        if self.active_provider == "openai":
            raw_documents = self._extract_with_openai(prompt)
        elif self.active_provider == "anthropic":
            raw_documents = self._extract_with_anthropic(prompt)
        else:
            return []
        
        print(f"  → Raw LLM extraction: {len(raw_documents)} items")
        
        # Validate and clean
        validated_documents = self._validate_and_clean_documents(raw_documents)
        
        print(f"  → After validation: {len(validated_documents)} valid requirements")
        
        return validated_documents
    
    def _build_extraction_prompt(self, rfp_text: str, spacy_candidates: List[str] = None) -> str:
        """
        Enhanced prompt that extracts structured requirements with validation rules
        """
        
        prompt = f"""You are an expert RFP compliance analyst extracting ALL compliance requirements from the provided RFP document.


PRIMARY OBJECTIVE

Extract EVERY compliance requirement, eligibility criterion, and mandatory document mentioned in the RFP text.
Your goal: COMPLETENESS first, then add detail.

IMPORTANT: Do NOT skip requirements just because you're uncertain about details.
Better to extract with minimal info than to miss a requirement entirely.

WHAT TO EXTRACT

Extract if the RFP mentions:
 Financial requirements (turnover, net worth, revenue)
 Experience requirements (years in business, project count)
 Certifications and licenses (ISO, CMMI, industry-specific)
 Registration documents (company registration, tax registrations)
 Workforce requirements (employee count, technical staff)
 Legal documents (PAN, GST, incorporation certificates)
 Project references and work orders
 Technical qualifications and accreditations
 Any document explicitly listed in "documents to be submitted" sections


REQUIREMENT CATEGORIZATION

Classify each requirement by validation_type:

1. numeric_threshold - Has specific number/amount
   Examples: "turnover ≥ ₹50 Cr", "net worth > 0", "5+ years experience"
2. date_validity - Time-based or expiry checking
   Examples: "valid certification", "license not expired", "current as of bid date"
3. count_threshold - Counting items/resources
   Examples: "minimum 100 employees", "at least 10 projects", "5+ engineers"
4. multi_condition - Multiple requirements together (AND/OR)
   Examples: "ISO 9001 AND ISO 27001", "CMMI Level 3 OR equivalent"
5. document_existence - Simple document submission
   Examples: "PAN copy", "GST certificate", "registration document"

DOCUMENT NAME EXTRACTION

PRIORITY ORDER for naming:
1st: Use EXACT phrase from RFP if clear
   RFP says "Chartered Accountant Certificate" → Use exactly that
2nd: Use commonly recognized term if RFP uses abbreviations
   RFP says "CA cert" → Expand to "Chartered Accountant Certificate"
3rd: Create descriptive name that captures the requirement
   RFP says "proof of turnover" → "Annual Turnover Certificate"

GUIDANCE:
- Preserve RFP terminology when specific
- Expand abbreviations for clarity
- Make names descriptive enough to understand requirement
- Keep concise (under 100 characters)

DESCRIPTION GUIDELINES

Aim for 50-150 words including:

MUST HAVE (if mentioned in RFP):
 What is being verified
 Specific thresholds or criteria
 Time periods or validity requirements
 How to calculate/verify

NICE TO HAVE (if mentioned):
 Special conditions or exclusions
 Acceptable evidence document types
 Issuing authority requirements

If RFP provides minimal detail, write what you know (even if brief).
If RFP provides extensive detail, capture the key points comprehensively.


VERBATIM QUOTE (OPTIONAL)

Include verbatim_quote when possible:
- Helps prove the requirement exists
- Provides context for validation
- Useful for traceability

If you can find an exact phrase from the RFP that describes this requirement, include it.
If the requirement is implied or synthesized from multiple places, you may leave it empty.


OUTPUT FORMAT
Return a JSON object with this structure:

{{
  "required_documents": [
    {{
      "criterion_id": "1",
      "document_name": "Name extracted from RFP",
      "description": "Comprehensive description 50-150 words",
      "validation_type": "numeric_threshold|date_validity|count_threshold|multi_condition|document_existence",
      "threshold": 50.0,
      "unit": "crores",
      "years_required": 3,
      "calculation": "average",
      "conditions": [],
      "logic": null,
      "context": "Additional notes",
      "criticality": "Mandatory",
      "evidence_documents": ["Doc type 1", "Doc type 2"],
      "verbatim_quote": "Exact text from RFP or empty string if not available"
    }}
  ]
}}

FIELD REQUIREMENTS:
- criterion_id: Sequential number (required)
- document_name: Short descriptive name (required)
- description: Detailed explanation (required, aim for 50+ words)
- validation_type: One of the 5 types above (required)
- threshold: Numeric value if applicable (null otherwise)
- unit: Unit of measurement if applicable (null otherwise)
- years_required: Number of years if applicable (null otherwise)
- calculation: "average"|"sum"|"minimum"|"maximum"|"age_from_incorporation"|null
- conditions: Array of conditions for multi_condition type (empty array otherwise)
- logic: "AND"|"OR" for multi_condition (null otherwise)
- context: Additional clarifications (can be empty string)
- criticality: "Mandatory"|"Important" based on RFP language
- evidence_documents: Array of acceptable document types (can be empty)
- verbatim_quote: Exact RFP text or empty string (optional but recommended)

EXAMPLES (Reference Only)

Example 1 - Financial Requirement:
{{
  "criterion_id": "1",
  "document_name": "Annual Revenue Certificate from Statutory Auditor",
  "description": "The bidding organization must demonstrate average annual revenue of at least ₹100 crores over the last three completed financial years (2021-22, 2022-23, 2023-24). Revenue should be calculated as the arithmetic mean across all three years. Certificate must be issued by a practicing Chartered Accountant registered with ICAI, on letterhead, with UDIN number and firm details. The certificate should specifically mention revenue from IT services or relevant business domain.",
  "validation_type": "numeric_threshold",
  "threshold": 100.0,
  "unit": "crores",
  "years_required": 3,
  "calculation": "average",
  "conditions": [],
  "logic": null,
  "context": "Revenue must be from IT services domain. CA must provide UDIN.",
  "criticality": "Mandatory",
  "evidence_documents": ["Chartered Accountant Certificate", "Audited Financial Statements", "ITR Acknowledgements"],
  "verbatim_quote": "average annual turnover of INR 100 Crores during last three financial years"
}}

Example 2 - Certification with Validity:
{{
  "criterion_id": "2",
  "document_name": "ISO/IEC 27001:2013 Information Security Certification",
  "description": "Valid ISO/IEC 27001:2013 certification for Information Security Management System. Certificate must be current and valid as of the bid submission date, issued by a certification body accredited by NABCB or equivalent international accreditation forum member. Scope should cover information security management and IT services. If certificate is under surveillance or recertification, surveillance audit reports must be included.",
  "validation_type": "date_validity",
  "threshold": null,
  "unit": null,
  "years_required": null,
  "calculation": null,
  "conditions": [],
  "logic": null,
  "context": "Must be from NABCB/IAF accredited body. Scope should include IT services.",
  "criticality": "Mandatory",
  "evidence_documents": ["ISO 27001 Certificate"],
  "verbatim_quote": "valid ISO/IEC 27001:2013 certification issued by NABCB accredited body"
}}

Example 3 - Simple Document:
{{
  "criterion_id": "3",
  "document_name": "Permanent Account Number (PAN)",
  "description": "Copy of Permanent Account Number (PAN) card or certificate issued by Income Tax Department for the bidding organization. PAN should be active and valid.",
  "validation_type": "document_existence",
  "threshold": null,
  "unit": null,
  "years_required": null,
  "calculation": null,
  "conditions": [],
  "logic": null,
  "context": "Organizational PAN required, not individual.",
  "criticality": "Mandatory",
  "evidence_documents": ["PAN Card", "PAN Certificate"],
  "verbatim_quote": "Copy of PAN"
}}

Example 4 - Multiple Conditions:
{{
  "criterion_id": "4",
  "document_name": "Quality and Maturity Certifications",
  "description": "The bidder must possess all three certifications: ISO 9001:2015 for Quality Management, ISO/IEC 20000-1:2018 for IT Service Management, and CMMI Level 3 or higher for process maturity. All certificates must be valid as of bid submission date and issued by accredited certification bodies.",
  "validation_type": "multi_condition",
  "threshold": null,
  "unit": null,
  "years_required": null,
  "calculation": null,
  "conditions": ["ISO 9001:2015", "ISO/IEC 20000-1:2018", "CMMI Level 3 or above"],
  "logic": "AND",
  "context": "All three certifications are mandatory. Must be from accredited bodies.",
  "criticality": "Mandatory",
  "evidence_documents": ["ISO 9001 Certificate", "ISO 20000 Certificate", "CMMI Appraisal Certificate"],
  "verbatim_quote": "ISO 9001:2015, ISO/IEC 20000-1:2018, and CMMI Level 3 or higher"
}}

NOTE: These examples show the structure and level of detail. Your actual extractions should reflect the specific RFP content provided below.

EXTRACTION CHECKLIST

Before finalizing your output, verify:

 Did I extract ALL requirements mentioned? (Completeness check)
 Did I categorize validation_type correctly for each?
 Did I include threshold values where numbers are mentioned?
 Did I write descriptions with sufficient detail?
 Did I use RFP terminology in document names?
 Did I include verbatim_quote where I found clear RFP text?
 Did I set criticality based on RFP language (must/shall/mandatory)?


RFP TEXT TO ANALYZE
{rfp_text}


RETURN YOUR JSON OUTPUT BELOW (no markdown, no expalination)           
"""
        
        return prompt
    
    def _extract_with_openai(self, prompt: str) -> List[str]:
        """Extract using OpenAI GPT-4o"""
        try:
            response = self.openai_client.chat.completions.create(
                model=config.OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert RFP document analyst. Extract required documents with high precision. Always return valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                response_format={"type": "json_object"},  # Force JSON output
                temperature=config.OPENAI_TEMPERATURE,
                max_tokens=config.OPENAI_MAX_TOKENS,
                timeout=config.OPENAI_TIMEOUT
            )
            
            # Parse response
            result = json.loads(response.choices[0].message.content)
            documents = result.get('required_documents', [])
            
            # Track costs
            if config.ENABLE_COST_TRACKING:
                self._track_cost_openai(response.usage)
            
            return documents
            
        except json.JSONDecodeError as e:
            print(f" [WARNING] JSON parsing error: {e}")
            return self._fallback_extraction(response.choices[0].message.content)
        except Exception as e:
            print(f" [FAIL] OpenAI error: {e}")
            return []
    
    def _extract_with_anthropic(self, prompt: str) -> List[str]:
        """Extract using Anthropic Claude"""
        try:
            response = self.anthropic_client.messages.create(
                model=config.ANTHROPIC_MODEL,
                max_tokens=config.ANTHROPIC_MAX_TOKENS,
                temperature=config.ANTHROPIC_TEMPERATURE,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            # Parse response
            response_text = response.content[0].text.strip()
            
            # Clean markdown code blocks if present
            if '```json' in response_text:
                response_text = response_text.split('```json').split('```')[1].strip()
            elif '```' in response_text:
                response_text = response_text.split('``````')[0].strip()
            
            result = json.loads(response_text)
            documents = result.get('required_documents', [])
            
            # Track costs
            if config.ENABLE_COST_TRACKING:
                self._track_cost_anthropic(response.usage)
            
            return documents
            
        except json.JSONDecodeError as e:
            print(f" [WARNING] JSON parsing error: {e}")
            return self._fallback_extraction(response_text)
        except Exception as e:
            print(f" [FAIL] Claude error: {e}")
            return []
    
    def _fallback_extraction(self, response_text: str) -> List[str]:
        """Fallback extraction if JSON parsing fails"""
        documents = []
        
        # Try to find JSON in response
        json_match = re.search(r'\{.*"required_documents".*\}', response_text, re.DOTALL)
        if json_match:
            try:
                result = json.loads(json_match.group())
                return result.get('required_documents', [])
            except:
                pass
        
        # Try to find quoted strings or list items
        quoted = re.findall(r'"([^"]{5,200})"', response_text)
        documents.extend(quoted)
        
        return documents[:50]  # Limit to reasonable number
    
    def _track_cost_openai(self, usage):
        """Track OpenAI API costs"""
        pricing = {
            "gpt-5": {"input": 0.00075, "output": 0.006},
            "gpt-5-mini": {"input": 0.00025, "output": 0.002},
            'gpt-4o': {'input': 0.0025, 'output': 0.01},
            'gpt-4-turbo': {'input': 0.01, 'output': 0.03},
            'gpt-4': {'input': 0.03, 'output': 0.06},
            'gpt-3.5-turbo': {'input': 0.0005, 'output': 0.0015}
        }
        
        model_pricing = pricing.get(config.OPENAI_MODEL, pricing['gpt-4o'])
        input_cost = (usage.prompt_tokens / 1000) * model_pricing['input']
        output_cost = (usage.completion_tokens / 1000) * model_pricing['output']
        self.extraction_cost += input_cost + output_cost
    
    def _track_cost_anthropic(self, usage):
        """Track Anthropic API costs"""
        pricing = {
            'claude-3-5-sonnet-20241022': {'input': 0.003, 'output': 0.015},
            'claude-3-opus': {'input': 0.015, 'output': 0.075},
            'claude-3-sonnet': {'input': 0.003, 'output': 0.015}
        }
        
        model_pricing = pricing.get(config.ANTHROPIC_MODEL, pricing['claude-3-5-sonnet-20241022'])
        input_cost = (usage.input_tokens / 1000) * model_pricing['input']
        output_cost = (usage.output_tokens / 1000) * model_pricing['output']
        self.extraction_cost += input_cost + output_cost
    
    # ============ SPACY FALLBACK METHODS (Lazy Loaded) ============
    
    def _extract_with_spacy(self, text: str) -> List[str]:
        """Fast extraction using spaCy and regex (fallback only)"""
        all_documents = []
        
        all_documents.extend(self.extract_by_sections(text))
        all_documents.extend(self.extract_by_patterns(text))
        all_documents.extend(self.extract_by_keywords(text))
        
        # Deduplicate
        seen = set()
        unique_documents = []
        for doc in all_documents:
            doc_lower = doc.lower()
            if doc_lower not in seen and len(doc_lower) > 5:
                seen.add(doc_lower)
                unique_documents.append(doc)
        
        return unique_documents
    
    def extract_by_patterns(self, text: str) -> List[str]:
        """Extract document names using regex patterns"""
        documents = []
        
        for pattern in config.LIST_PATTERNS:
            matches = re.finditer(pattern, text, re.MULTILINE)
            for match in matches:
                start_pos = match.end()
                remaining_text = text[start_pos:]
                line_end = remaining_text.find('\n')
                if line_end == -1:
                    line_end = min(len(remaining_text), 200)
                
                document_name = remaining_text[:line_end].strip()
                document_name = self._clean_document_name(document_name)
                
                if self._is_valid_document_name(document_name):
                    documents.append(document_name)
        
        return documents
    
    def extract_by_keywords(self, text: str) -> List[str]:
        """Extract based on keyword matching"""
        doc = self.nlp(text[:10000])  # Limit to first 10k chars
        documents = []
        
        for sent in doc.sents:
            matches = self.phrase_matcher(self.nlp(sent.text))
            if matches:
                cleaned_sent = self._clean_document_name(sent.text)
                if self._is_valid_document_name(cleaned_sent):
                    documents.append(cleaned_sent)
        
        return documents
    
    def extract_by_sections(self, text: str) -> List[str]:
        """Extract from common RFP sections"""
        documents = []
        section_patterns = [
            r'(?:required\s+documents?|submission\s+requirements?)',
            r'(?:attachment|exhibit|appendix)',
            r'(?:checklist|list\s+of\s+documents?)',
            r'(?:eligibility|qualification)',
        ]
        
        for pattern in section_patterns:
            sections = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
            for section in sections:
                section_text = text[section.end():section.end()+1500]
                documents.extend(self.extract_by_patterns(section_text))
        
        return documents
    
    def _clean_document_name(self, text: str) -> str:
        """Clean document name"""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove common prefixes
        text = re.sub(r'^(submit|provide|include|attach)\s+', '', text, flags=re.IGNORECASE)
        
        # Remove common suffixes
        text = re.sub(r'\s+(required|mandatory)$', '', text, flags=re.IGNORECASE)
        
        # Remove trailing punctuation
        text = re.sub(r'[,;:]+$', '', text)
        
        return text.strip()
    
    def _is_valid_document_name(self, text: str) -> bool:
        """Validate document name"""
        if not text or len(text) < 5 or len(text) > 200:
            return False
        
        text_lower = text.lower()
        
        # Check for document keywords
        has_keyword = any(kw in text_lower for kw in config.DOCUMENT_KEYWORDS)
        has_pattern = bool(re.search(r'(certificate|license|form|letter|proof)', text_lower))
        
        return has_keyword or has_pattern
    
    def _validate_and_clean_documents(self, raw_documents: List[Dict]) -> List[Dict]:
        """
        Validate and clean extracted documents with enhanced checks.
        """
        if not raw_documents:
            return []
        
        validated = []
        seen = set()
        
        for idx, item in enumerate(raw_documents):
            # Ensure required fields
            if not item.get('document_name'):
                print(f"[WARNING]  Skipping item {idx+1}: Missing document_name")
                continue
            
            # Normalize for deduplication
            doc_name = item['document_name'].strip()
            doc_name_lower = doc_name.lower()
            
            # Skip if already seen
            if doc_name_lower in seen:
                print(f"[WARNING]  Skipping duplicate: {doc_name}")
                continue
            
            # Validate verbatim_quote exists 
            verbatim_quote = item.get('verbatim_quote', '').strip()
            if not verbatim_quote:
                print(f"[WARNING]  WARNING: Missing verbatim_quote for '{doc_name}'")
                print(f"   This requirement may not be properly grounded in RFP text")
            elif len(verbatim_quote) < 10:
                print(f"[WARNING]  WARNING: Very short verbatim_quote ({len(verbatim_quote)} chars) for '{doc_name}'")
            
            # Set defaults
            item.setdefault('validation_type', 'document_existence')
            item.setdefault('criticality', 'Mandatory')
            item.setdefault('threshold', None)
            item.setdefault('unit', None)
            item.setdefault('calculation', None)
            item.setdefault('years_required', None)
            item.setdefault('conditions', [])
            item.setdefault('logic', None)
            item.setdefault('evidence_documents', [])
            
            # Generate or enhance context
            if not item.get('context'):
                item['context'] = item.get('description', '')[:200]
            
            # Append verbatim_quote to context for downstream matching
            if verbatim_quote:
                item['context'] = f"{item.get('context', '')} [Source: \"{verbatim_quote}\"]"
            
            # Compose rich description if missing or too short
            description = item.get('description', '')
            word_count = len(description.split())
            
            if word_count < 30:
                print(f"[WARNING] Short description ({word_count} words) for '{doc_name}'")
                # Attempt to enrich
                item['description'] = self.compose_rich_description(item)
                print(f"   → Enhanced to {len(item['description'].split())} words")
            
            # Validate document_name length
            if len(doc_name) < 5:
                print(f"[WARNING]  Skipping: Document name too short: '{doc_name}'")
                continue
            
            if len(doc_name) > 200:
                print(f"[WARNING]  Truncating long document name: {doc_name[:50]}...")
                item['document_name'] = doc_name[:200]
            
            # Filter banned phrases
            banned_phrases = ['shall be', 'will be', 'must be', 'should be']
            if any(phrase in doc_name_lower for phrase in banned_phrases):
                print(f"[WARNING]  Skipping: Contains banned phrase: '{doc_name}'")
                continue
            
            # Add to validated list
            seen.add(doc_name_lower)
            item['criterion_id'] = str(len(validated) + 1)
            validated.append(item)
        
        print(f"[OK] Validated {len(validated)} unique requirements (from {len(raw_documents)} raw)")
        
        return validated

    
    def compose_rich_description(self, item: Dict) -> str:
        """
        Compose a rich, detailed description from multiple fields.
        Combines description, context, validation details, and thresholds.
        """
        parts = []
        
        # 1. Main description
        desc = item.get("description", "")
        if desc:
            parts.append(desc)
        
        # 2. Add validation details
        validation_type = item.get("validation_type", "")
        
        if validation_type == "numeric_threshold":
            threshold = item.get("threshold")
            unit = item.get("unit", "")
            calculation = item.get("calculation", "")
            years = item.get("years_required")
            
            details = []
            if threshold and unit:
                details.append(f"Threshold: {threshold} {unit}")
            if years:
                details.append(f"Period: {years} years")
            if calculation:
                calc_map = {
                    "average": "Average value over period",
                    "sum": "Total cumulative value",
                    "minimum": "Minimum value in any year",
                    "maximum": "Maximum value achieved"
                }
                details.append(calc_map.get(calculation, calculation))
            
            if details:
                parts.append(" | ".join(details))
        
        elif validation_type == "date_validity":
            threshold = item.get("threshold")
            unit = item.get("unit", "")
            if threshold and unit:
                parts.append(f"Validity: Minimum {threshold} {unit} required")
        
        elif validation_type == "count_threshold":
            threshold = item.get("threshold")
            unit = item.get("unit", "")
            if threshold and unit:
                parts.append(f"Required Count: At least {threshold} {unit}")
        
        elif validation_type == "multi_condition":
            conditions = item.get("conditions", [])
            logic = item.get("logic", "AND")
            if conditions:
                parts.append(f"Conditions ({logic}): {' + '.join(conditions)}")
        
        # 3. Add context (additional clarifications)
        context = item.get("context", "")
        if context and context != desc:  # Avoid duplication
            parts.append(f"Note: {context}")
        
        # 4. Add evidence documents suggestion
        evidence = item.get("evidence_documents", [])
        if evidence and len(evidence) > 0:
            evidence_str = ", ".join(evidence[:3])  # Limit to first 3
            if len(evidence) > 3:
                evidence_str += ", etc."
            parts.append(f"Acceptable Evidence: {evidence_str}")
        
        # 5. Add criticality indicator
        criticality = item.get("criticality", "")
        if criticality:
            parts.append(f"[{criticality}]")
        
        # Combine all parts with proper spacing
        rich_description = " • ".join(parts) if parts else "No description available"
        
        return rich_description

