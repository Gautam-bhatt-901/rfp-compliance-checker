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
                print("✓ OpenAI GPT-4 client initialized")
            except Exception as e:
                print(f"⚠️ OpenAI initialization failed: {e}")
        
        # Try Anthropic if OpenAI not available
        if not self.llm_available and config.ANTHROPIC_API_KEY:
            try:
                self.anthropic_client = Anthropic(api_key=config.ANTHROPIC_API_KEY)
                self.active_provider = 'anthropic'
                self.llm_available = True
                print("✓ Anthropic Claude client initialized")
            except Exception as e:
                print(f"⚠️ Anthropic initialization failed: {e}")
        
        # Lazy loading for spaCy (only load if LLM fails)
        self.nlp = None
        self.phrase_matcher = None
        self.spacy_loaded = False
        
        if not self.llm_available:
            print("⚠️ No API LLM available. Will use spaCy fallback.")
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
            print("✓ spaCy model loaded successfully")
        except Exception as e:
            print(f"❌ spaCy initialization failed: {e}")
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
            print("⚠️ Warning: Non-paginated input received. Using truncation.")
            final_context_text = rfp_text_or_pages[:config.MAX_INPUT_TOKENS * 4]

        # STAGE 2: Try API LLM extraction
        if self.llm_available:
            print(f"\n🤖 STAGE 1: API LLM extraction ({self.active_provider.upper()})...")
            try:
                llm_results = self._extract_with_llm(final_context_text, [])
                
                if llm_results and len(llm_results) >= 3:
                    print(f" ✓ LLM extraction successful: {len(llm_results)} documents found")
                    
                    # Show cost
                    if self.extraction_cost > 0:
                        print(f" 💰 API Cost: ${self.extraction_cost:.4f}")
                    
                    print("="*70 + "\n")
                    return llm_results
                else:
                    print(f" ⚠️ LLM returned insufficient results ({len(llm_results)} docs)")
                    print(" → Falling back to spaCy...")       
            except Exception as e:
                print(f" ❌ LLM extraction failed: {e}")
                print(" → Falling back to spaCy...")
        else:
            print("\n⚠️ No API LLM available, using spaCy extraction...")
        
        # STAGE 3: spaCy fallback (ONLY IF LLM FAILS)
        print(f"\n🔍 STAGE 2: spaCy fallback extraction...")
        
        # Initialize spaCy if not already loaded
        if not self.spacy_loaded:
            self._initialize_spacy()
        
        spacy_results = self._extract_with_spacy(final_context_text)
        print(f" → Found {len(spacy_results)} documents with spaCy")
        print("="*70 + "\n")
        
        return spacy_results
    
    def _scout_relevant_sections(self, pages: Dict[int, str]) -> str:
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
            'checklist', 'annexure', 'appendix', 'submission', 'mandatory', 
            'eligibility', 'qualification', 'enclosure', 'documents required', 
            'technical bid', 'financial bid', 'format'
        ]
        
        # --- Scoring ---
        page_scores = {}
        for p_num, text in pages.items():
            text_lower = text.lower()
            score = 0
            
            # Keyword density scoring
            for kw in hot_keywords:
                count = text_lower.count(kw)
                score += count * 2  # Base weight
                
                # Boost for headers (simple heuristic: keyword followed by newline or colon)
                if f"{kw}:" in text_lower or f"{kw}\n" in text_lower:
                    score += 5
            
            page_scores[p_num] = score

        # --- Selection Strategy ---
        selected_indices = set()
        
        # 1. Always include First 3 pages (Introduction / TOC)
        for i in range(1, min(4, total_pages + 1)):
            selected_indices.add(i)
            
        # 2. Always include Last 3 pages (Often Checklists/Annexures)
        for i in range(max(1, total_pages - 2), total_pages + 1):
            selected_indices.add(i)
            
        # 3. Select Top N Scoring Pages from the middle
        # Filter out pages we already selected
        remaining_pages = [p for p in page_scores.keys() if p not in selected_indices]
        
        # Sort remaining by score
        sorted_pages = sorted(remaining_pages, key=lambda x: page_scores[x], reverse=True)
        
        # Take top 5 highest scoring pages
        top_scorers = sorted_pages[:5]
        selected_indices.update(top_scorers)
        
        # --- Context Expansion ---
        # If we picked page 50, page 51 might continue the list. 
        # Add neighbors for high scoring pages.
        neighbors = set()
        for p in top_scorers:
            if p + 1 <= total_pages: neighbors.add(p + 1)
            if p - 1 >= 1: neighbors.add(p - 1)
        
        selected_indices.update(neighbors)

        # --- Synthesis ---
        # Sort indices to maintain document flow
        final_indices = sorted(list(selected_indices))
        
        print(f"✓ Selected {len(final_indices)} relevant pages: {final_indices}")
        
        # Construct the final text with markers
        combined_text = ""
        for p in final_indices:
            combined_text += f"\n--- [PAGE {p}] ---\n"
            combined_text += pages[p]
            
        return combined_text
    
    def _extract_with_llm(
        self,
        rfp_text: str,
        spacy_candidates: List[str]
    ) -> List[Dict]:
        """
        Universal LLM extraction with validation
        Works across different RFP formats
        """
        
        # Truncate text if too long
        max_chars = config.MAX_INPUT_TOKENS * 3  # Rough estimate
        if len(rfp_text) > max_chars:
            print(f" ℹ️ Truncating RFP text from {len(rfp_text)} to {max_chars} chars")
            rfp_text = rfp_text[:max_chars]
        
        # Build universal prompt
        prompt = self._build_extraction_prompt(rfp_text, spacy_candidates)
        
        # Get raw extraction from LLM
        raw_documents = []
        if self.active_provider == 'openai':
            raw_documents = self._extract_with_openai(prompt)
        elif self.active_provider == 'anthropic':
            raw_documents = self._extract_with_anthropic(prompt)
        else:
            return []
        
        print(f" → Raw LLM extraction: {len(raw_documents)} items")
        
        # Apply universal validation
        validated_documents = self._validate_and_clean_documents(raw_documents)
        print(f" → After validation: {len(validated_documents)} valid documents")
        
        # If validation removed too many, try with lower temperature
        if len(validated_documents) < 3 and len(raw_documents) > 5:
            print(f" ⚠️ Warning: Heavy filtering detected. Check RFP format.")
        
        return validated_documents
    
    def _build_extraction_prompt(self, rfp_text: str, spacy_candidates: List[str]) -> str:
        """
        Universal extraction prompt that works across different RFP formats
        Uses two-stage thinking: identify → validate
        """

        prompt = f"""You are an expert RFP document analyst. Your task is to extract a comprehensive list of REQUIRED DOCUMENTS that a bidder must submit.

## CORE DEFINITION:
A **SUBMITTABLE DOCUMENT** is something tangible that:
- Can be physically or digitally attached/submitted
- Has a clear document type (certificate, form, letter, statement, etc.)
- Can be identified by a noun phrase (not a sentence or instruction)
- Would appear in a document checklist
 
## UNIVERSAL EXTRACTION RULES (Work for ANY RFP format):
 
### ✅ EXTRACT (Document Names):
- Certificates: "Tax Clearance Certificate", "ISO Certification"
- Forms: "Bid Security Form", "Technical Proposal Form"
- Copies: "Copy of Registration", "Photocopy of PAN Card"
- Statements: "Audited Financial Statement", "Bank Statement"
- Letters: "Letter of Intent", "Experience Letter"
- Reports: "Annual Report", "Audit Report"
- Proofs: "Proof of turnover", "Address Proof"
- CVs/Resumes: "CV of Project Manager", "Resume with experience"
- Agreements: "Partnership Deed", "Contract Agreement"
- Licenses: "Business License", "Trade License"
 
### ❌ DO NOT EXTRACT (Not Documents):
- **Instructions**: "The bidder shall submit", "Firm should provide"
- **Criteria**: "Average turnover should be", "Experience of 5 years"
- **Process descriptions**: "Technical evaluation will be done"
- **Section headers only**: "Eligibility Criteria" (unless followed by specific doc)
- **Incomplete phrases**: "Position K-1 (Partner" (missing the document part)
- **List markers alone**: "a)", "1.", "ii)"
- **Generic phrases**: "supporting documents", "relevant papers"
- **Evaluation text**: "Marks will be awarded for"
 
## DECISION FRAMEWORK:
For each potential item, ask:
1. **Is this a NOUN PHRASE?** (Yes = might be document, No = reject)
2. **Can this be PHYSICALLY SUBMITTED?** (Yes = might be document, No = reject)
3. **Does it NAME a specific document TYPE?** (Yes = extract, No = reject)
4. **Is it COMPLETE?** (Yes = extract, No = reject)
 
## YOUR TASK:
Read this RFP carefully. Extract ONLY the names of submittable documents.
 
**RFP TEXT:**
{rfp_text}

## OUTPUT FORMAT:
Return valid JSON with this structure:
{{
  "required_documents": [
    {{
      "document_name": "Exact Document Name",
      "category": "Legal|Financial|Technical|Other",
      "criticality": "Mandatory|Important|Optional",
      "context": "Brief quote from RFP defining this requirement"
    }}
  ]
}}

## CRITICALITY RULES:
- "Mandatory": Terms like 'shall', 'must', 'essential', 'eligibility criteria'.
- "Important": Terms like 'should', 'highly recommended'.
- "Optional": Terms like 'if applicable', 'where available'.

*Other rules*:
- Return ONLY the JSON object
- No explanations before or after
- Each item must be a DOCUMENT NAME (noun phrase)
- Maximum 150 characters per document name
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
            print(f" ⚠️ JSON parsing error: {e}")
            return self._fallback_extraction(response.choices[0].message.content)
        except Exception as e:
            print(f" ❌ OpenAI error: {e}")
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
            print(f" ⚠️ JSON parsing error: {e}")
            return self._fallback_extraction(response_text)
        except Exception as e:
            print(f" ❌ Claude error: {e}")
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
    
    def _validate_and_clean_documents(self, documents: List[Union[str,Dict]]) -> List[Dict]:
        """
        Universal validator that works across different RFP formats
        Uses multiple validation strategies
        """
        validated = []
        # RULE 1: Banned Triggers - if a string contains these, it's likely a clause, not a doc
        banned_phrases = [
            "shall be", "will be", "must be", "should be", 
            "responsible for", "liable for", "subject to", 
            "discrepancy between", "in case of", "event of", 
            "reserves the right", "termination of", "execution of",
            "during the execution", "period of contract", "time of billing",
            "documents to be submitted", "list of documents",
            "liquidated damages", "penalty @", "payment shall",
            "contractor shall", "bidder shall", "service provider shall"
            ]
            
        # RULE 2: Must contain at least one document-type keyword
        valid_indicators = [
            'certificate', 'cert', 'form', 'letter', 'document', 'doc',
            'statement', 'report', 'proof', 'copy', 'copies','photocopy',
            'cv', 'resume', 'agreement', 'deed', 'license', 'licence',
            'permit', 'authorization', 'clearance', 'registration','appendix',
            'pan', 'gst', 'tin', 'vat', 'emd', 'annexure', 'format',
            'template', 'bio', 'profile', 'details', 'list','evidence',
            'sheet', 'balance', 'turnover', 'financial', 'audit','return',
            'completion', 'work order', 'contract', 'undertaking','order',
            'affidavit', 'declaration', 'testimonial', 'reference','proforma',
            'biodata', 'plan', 'esi', 'epf', 'emd', 'fdr', 'power of attorney"'
            ]

        seen_names = set()
            
        for item in documents:
            # --- NORMALIZATION (The Fix for the Error) ---
            # Check if item is a Dictionary (New Format) or String (Old Format)
            if isinstance(item, dict):
                doc_name = item.get('document_name', '')
                # Handle case where LLM returns None or non-string for name
                if not isinstance(doc_name, str):
                    doc_name = str(doc_name) if doc_name else ""
                
                criticality = item.get('criticality', 'Mandatory')
                context = item.get('context', '')
            else:
                # Handle String (Legacy/Fallback)
                doc_name = str(item)
                criticality = "Unknown"
                context = ""

            # Clean the name (Now safe because doc_name is guaranteed to be a string)
            doc_name_clean = doc_name.strip().strip('.,;-:')
            doc_lower = doc_name_clean.lower()

            # --- FILTER 1: Length Checks ---
            if len(doc_name_clean.split()) > 15: # Too long = sentence
                continue
            if len(doc_name_clean) < 3: # Too short = noise
                continue

            # --- FILTER 2: Banned Phrases ---
            if any(phrase in doc_lower for phrase in banned_phrases):
                continue

            # --- FILTER 3: Must look like a document ---
            has_indicator = any(ind in doc_lower for ind in valid_indicators)
            is_special = any(x in doc_lower for x in ['iso', 'bis', 'itr', 'net worth'])
            
            if not (has_indicator or is_special):
                # If it doesn't look like a document, only allow if it's short
                if len(doc_name_clean.split()) > 6:
                    continue

            # --- FILTER 4: Deduplication ---
            if doc_lower in seen_names:
                continue
            
            seen_names.add(doc_lower)
            
            # Add to validated list
            validated.append({
                "document_name": doc_name_clean,
                "criticality": criticality,
                "context": context
            })
            
        return validated
