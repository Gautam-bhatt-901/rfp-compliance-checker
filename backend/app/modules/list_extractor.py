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
                llm_results = self.extract_with_llm(final_context_text, [])
                
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
                count = text_lower.count(kw)
                score += count * 2  # Base weight
                
                # Boost for headers (simple heuristic: keyword followed by newline or colon)
                if f"{kw}:" in text_lower or f"{kw}\n" in text_lower:
                    score += 5
            
            page_scores[p_num] = score

        # --- Selection Strategy ---
        selected_indices = set()
        
        # DYNAMIC SELECTION BASED ON DOCUMENT SIZE
        if total_pages <= 30:
            # Small docs: Use most pages
            intro_pages = min(5, total_pages)
            end_pages = min(5, total_pages)
            top_scorers_count = max(10, total_pages - 10)
        elif total_pages <= 100:
            # Medium docs: Balanced selection
            intro_pages = 5
            end_pages = 5
            top_scorers_count = 20
        else:
            # Large docs: Aggressive selection
            intro_pages = 10
            end_pages = 10
            top_scorers_count = 40  # INCREASED from 5 to 40
        
        # 1. Include intro pages
        for i in range(1, min(intro_pages + 1, total_pages + 1)):
            selected_indices.add(i)
        
        # 2. Include end pages
        for i in range(max(1, total_pages - end_pages + 1), total_pages + 1):
            selected_indices.add(i)
        
        # 3. Select Top N Scoring Pages
        remaining_pages = [p for p in page_scores.keys() if p not in selected_indices]
        sorted_pages = sorted(remaining_pages, key=lambda x: page_scores[x], reverse=True)
        
        # IMPORTANT: Take more high-scoring pages for large documents
        top_scorers = sorted_pages[:top_scorers_count]
        selected_indices.update(top_scorers)
        
        # 4. Add neighbors for high scoring pages
        neighbors = set()
        for p in top_scorers[:20]:  # Only add neighbors for top 20 scorers
            if p + 1 <= total_pages:
                neighbors.add(p + 1)
            if p - 1 >= 1:
                neighbors.add(p - 1)
        selected_indices.update(neighbors)
        
        # 5. SAFETY CHECK: If we have too many pages, estimate text size
        final_indices = sorted(list(selected_indices))
        
        # Estimate total characters
        estimated_chars = 0
        for p in final_indices:
            estimated_chars += len(pages[p])
        
        # If exceeds limit, prioritize highest scoring pages
        max_chars_allowed = config.MAX_INPUT_TOKENS * 5
        if estimated_chars > max_chars_allowed:
            print(f"⚠️ Estimated {estimated_chars} chars exceeds limit. Prioritizing high-score pages...")
            
            # Re-sort by score and take top pages until under limit
            sorted_by_score = sorted(final_indices, key=lambda x: page_scores[x], reverse=True)
            final_indices = []
            current_chars = 0
            
            for page_num in sorted_by_score:
                page_chars = len(pages[page_num])
                if current_chars + page_chars <= max_chars_allowed:
                    final_indices.append(page_num)
                    current_chars += page_chars
                else:
                    break
            
            final_indices = sorted(final_indices)
        
        print(f"✓ Selected {len(final_indices)} relevant pages (from {total_pages} total)")
        print(f"✓ Coverage: {len(final_indices)/total_pages*100:.1f}% of document")
        
        # Construct the final text
        combined_text = ""
        for p in final_indices:
            combined_text += f"\n--- [PAGE {p}] ---\n"
            combined_text += pages[p]
        
        print(f"✓ Combined text length: {len(combined_text):,} characters")
        
        return combined_text
    
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
        
        prompt = f"""You are an expert RFP analyst. Extract COMPLIANCE REQUIREMENTS with validation rules.

CRITICAL: Extract REQUIREMENTS (compliance criteria), NOT just document names.

For each requirement, determine:
1. What is being verified (turnover, certification, employee count, etc.)
2. What is the threshold/rule (≥ 50 Cr, valid certification, 100+ employees)
3. How to validate (average of 3 years, check expiry date, count total)
4. What documents would prove it

REQUIREMENT TYPES:
- numeric_threshold: Financial values, counts with minimum/maximum (e.g., "turnover ≥ ₹50 Cr")
- date_validity: Time-based validation (e.g., "certification valid as of date")
- count_threshold: Counting items (e.g., "at least 100 employees")
- multi_condition: Multiple sub-requirements with AND/OR (e.g., "ISO 9001 AND ISO 20000 AND CMMI")
- document_existence: Simple document presence (e.g., "PAN card copy")

EXTRACTION RULES:
1. If requirement has numeric threshold (₹, Rs, crores, lakhs, years, count):
   → validation_type = "numeric_threshold"
   → Extract threshold value, unit, calculation method

2. If requirement mentions validity, expiry, "as of date", "current":
   → validation_type = "date_validity"

3. If requirement says "at least X", "minimum X", where X is a count:
   → validation_type = "count_threshold"

4. If requirement has multiple parts with AND/OR:
   → validation_type = "multi_condition"
   → List all conditions

5. If simple document requirement:
   → validation_type = "document_existence"

RFP TEXT:
{rfp_text}

Example OUTPUT FORMAT (JSON object):
{{
  "required_documents": [
    {{
      "criterion_id": "1",
      "document_name": "Company Registration Certificate",
      "description": "Company registered under Companies Act with 5+ years operation",
      "validation_type": "date_validity",
      "threshold": 5,
      "unit": "years",
      "calculation": "age_from_incorporation",
      "context": "Must be registered company with 5+ years of operations",
      "criticality": "Mandatory",
      "evidence_documents": ["Certificate of Registration", "MoA", "Incorporation Certificate"]
    }},
    {{
      "criterion_id": "2",
      "document_name": "CA Certificate - Annual Turnover",
      "description": "Average annual turnover ≥ Rs. 50 crores over last 3 financial years",
      "validation_type": "numeric_threshold",
      "threshold": 50,
      "unit": "crores",
      "years_required": 3,
      "calculation": "average",
      "context": "From business of providing technical manpower only",
      "criticality": "Mandatory",
      "evidence_documents": ["CA Certificate", "Audited Balance Sheet", "Financial Statement"]
    }},
    {{
      "criterion_id": "3",
      "document_name": "CA Certificate - Net Worth",
      "description": "Positive net worth for each of 3 financial years",
      "validation_type": "numeric_threshold",
      "threshold": 0,
      "unit": "crores",
      "years_required": 3,
      "calculation": "minimum",
      "context": "Net worth must be positive (> 0) for all 3 years",
      "criticality": "Mandatory",
      "evidence_documents": ["CA Certificate", "Audited Balance Sheet"]
    }},
    {{
      "criterion_id": "4",
      "document_name": "Certifications (CMMI, ISO 9001, ISO 20000)",
      "description": "SEI CMMI level 3+, ISO 9001, and ISO/IEC 20000 certifications",
      "validation_type": "multi_condition",
      "conditions": ["SEI CMMI Level 3 or above", "ISO 9001", "ISO/IEC 20000"],
      "logic": "AND",
      "context": "All certifications must be valid at time of submission",
      "criticality": "Mandatory",
      "evidence_documents": ["CMMI Certificate", "ISO 9001 Certificate", "ISO 20000 Certificate"]
    }},
    {{
      "criterion_id": "5",
      "document_name": "Employee Count Summary",
      "description": "At least 100 professionals on payroll",
      "validation_type": "count_threshold",
      "threshold": 100,
      "unit": "employees",
      "context": "Summary of employee count duly certified by HR",
      "criticality": "Mandatory",
      "evidence_documents": ["HR Employee Count Summary", "Payroll Summary"]
    }}
  ]
}}

CRITICAL RULES:
- Extract threshold VALUES (numbers only, no text)
- Specify calculation method: "average", "sum", "minimum", "maximum", "age_from_incorporation"
- For multi_condition, list ALL sub-requirements in conditions array
- Set criticality: "Mandatory" or "Important" based on RFP language
- Keep document_name concise (< 100 chars)
- Keep description clear and actionable

Return ONLY the JSON object, no markdown formatting, no explanations.
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
    
    def _validate_and_clean_documents(self, requirements: List[Union[str, Dict]]) -> List[Dict]:
        """
        Enhanced validation for structured requirements
        """
        validated = []
        
        for item in requirements:
            if not isinstance(item, dict):
                # Legacy format - convert to simple document_existence
                item = {
                    'document_name': str(item),
                    'validation_type': 'document_existence',
                    'criticality': 'Mandatory'
                }
            
            # Ensure required fields
            if 'document_name' not in item or not item['document_name']:
                continue
            
            doc_name = str(item['document_name']).strip()
            
            # Skip if too short or has banned phrases
            if len(doc_name) < 5 or len(doc_name) > 200:
                continue
            
            banned_phrases = [
                'shall be', 'will be', 'must be', 'should be', 
                'responsible for', 'in case of', 'reserves the right'
            ]
            
            if any(phrase in doc_name.lower() for phrase in banned_phrases):
                continue
            
            # Ensure validation_type is set
            if 'validation_type' not in item:
                # Infer from description or name
                desc = item.get('description', doc_name).lower()
                
                if any(word in desc for word in ['turnover', 'revenue', 'net worth', 'value', 'crores', 'lakhs']):
                    item['validation_type'] = 'numeric_threshold'
                elif any(word in desc for word in ['valid', 'expiry', 'expire', 'certification', 'certificate']):
                    item['validation_type'] = 'date_validity'
                elif any(word in desc for word in ['at least', 'minimum', 'employees', 'professionals', 'count']):
                    item['validation_type'] = 'count_threshold'
                elif 'and' in desc or 'or' in desc:
                    item['validation_type'] = 'multi_condition'
                else:
                    item['validation_type'] = 'document_existence'
            
            # Set defaults
            if 'criticality' not in item:
                item['criticality'] = 'Mandatory'
            
            if 'context' not in item:
                item['context'] = item.get('description', '')
            
            validated.append(item)
        
        # Deduplicate by document_name
        seen = set()
        deduplicated = []
        for item in validated:
            key = item['document_name'].lower().strip()
            if key not in seen:
                seen.add(key)
                deduplicated.append(item)
        
        return deduplicated
