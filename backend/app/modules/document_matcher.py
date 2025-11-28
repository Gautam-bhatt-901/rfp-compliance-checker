"""
Enhanced Document Matching Module
HYBRID APPROACH: LLM-based matching with fallback
Multi-Strategy Approach(fallback): Filename + Content + Fuzzy + Keyword + Abbreviation matching
"""

from sentence_transformers import SentenceTransformer, util
import torch
from typing import List, Dict, Tuple, Optional, Union
from app import config
import re
from fuzzywuzzy import fuzz, process
from collections import defaultdict
import PyPDF2
import docx
from openai import OpenAI
from anthropic import Anthropic
import json

class DocumentMatcher:
    """Enhanced document matcher with multiple matching strategies"""
    
    def __init__(self):
        """Initialize with better model and matching strategies"""

        # Initialize LLM clients (same as ListExtractor)
        self.llm_available = False
        self.active_provider = None
        self.matching_cost = 0.0
        
        # Try OpenAI first
        if config.OPENAI_API_KEY:
            try:
                self.openai_client = OpenAI(api_key=config.OPENAI_API_KEY)
                self.active_provider = 'openai'
                self.llm_available = True
                print("✓ OpenAI client initialized for matching")
            except Exception as e:
                print(f"⚠️ OpenAI initialization failed: {e}")
        
        # Try Anthropic as fallback
        if not self.llm_available and config.ANTHROPIC_API_KEY:
            try:
                self.anthropic_client = Anthropic(api_key=config.ANTHROPIC_API_KEY)
                self.active_provider = 'anthropic'
                self.llm_available = True
                print("✓ Anthropic client initialized for matching")
            except Exception as e:
                print(f"⚠️ Anthropic initialization failed: {e}")

        # Initialize traditional matching components (lazy load)
        self.model = None
        self.device = None
        self.traditional_initialized = False

        # Abbreviation mappings for better matching
        self.abbreviations = {
            'pan': ['permanent account number', 'pan card'],
            'gst': ['goods and services tax', 'gst certificate', 'gstin'],
            'cv': ['curriculum vitae', 'resume', 'bio data'],
            'emd': ['earnest money deposit', 'bid security'],
            'iso': ['international organization for standardization'],
            'msme': ['micro small medium enterprise'],
            'tin': ['taxpayer identification number'],
            'vat': ['value added tax'],
            'pf': ['provident fund', 'epf'],
            'esi': ['employee state insurance'],
            'itr': ['income tax return'],
            'aoa': ['articles of association'],
            'moa': ['memorandum of association'],
        }
        
        # Document type synonyms
        self.synonyms = {
            'certificate': ['cert', 'certification', 'certificate'],
            'license': ['licence', 'license', 'permit'],
            'statement': ['stmt', 'statement', 'declaration'],
            'proof': ['evidence', 'proof', 'verification'],
            'letter': ['letter', 'communication', 'correspondence'],
            'form': ['form', 'format', 'template', 'proforma'],
            'copy': ['copy', 'photocopy', 'xerox', 'duplicate'],
            'agreement': ['agreement', 'contract', 'deed'],
            'report': ['report', 'returns', 'statement'],
        }

        # Determine matching strategy
        if config.USE_LLM_MATCHING and self.llm_available:
            print(f"✓ LLM-based matching enabled (Provider: {self.active_provider.upper()})")
        else:
            print("⚠️ LLM matching unavailable or disabled. Initializing traditional matching...")
            self._initialize_traditional_matching()
    
    def _initialize_traditional_matching(self):
        """Lazy load traditional matching components (fallback)"""
        if self.traditional_initialized:
            return
        
        print(f"Loading Sentence Transformer model: {config.SENTENCE_TRANSFORMER_MODEL}")
        self.model = SentenceTransformer(config.SENTENCE_TRANSFORMER_MODEL)
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.model.to(self.device)
        print(f"✓ Traditional matching initialized on {self.device}")
        self.traditional_initialized = True

    def match_documents(
        self,
        required_docs: List[Union[str, Dict]],
        provided_docs: List[str],
        provided_paths: Optional[List[str]] = None
    ) -> List[Dict]:    
        """
        Enhanced matching with LLM-first approach
    
        Args:
            required_docs: List of required document names from RFP
            provided_docs: List of provided document filenames
            provided_paths: Optional full paths to documents for content analysis
        
        Returns:
            List of matching results with confidence scores
        """
        print("\n" + "="*70)
        print("🔍 ENHANCED DOCUMENT MATCHING")
        print("="*70)
        
        normalized_required_docs = []
        
        for doc in required_docs:
            if isinstance(doc, str):
                # Legacy/SpaCy fallback format
                normalized_required_docs.append({
                    "document_name": doc,
                    "context": "No specific context provided.",
                    "criticality": "Unknown"
                })
            elif isinstance(doc, dict):
                # New Structured format
                normalized_required_docs.append(doc)

        # Extract document content if paths provided (used by both LLM and traditional)
        document_contents = {}
        if provided_paths and config.USE_CONTENT_MATCHING:
            print("📄 Analyzing document contents...")
            for idx, path in enumerate(provided_paths):
                try:
                    content = self._extract_document_content(path)
                    if content:
                        document_contents[provided_docs[idx]] = content
                except Exception as e:
                    print(f" ⚠️ Could not extract content from {provided_docs[idx]}: {e}")
        
        # PRIMARY: Try LLM-based matching
        if config.USE_LLM_MATCHING and self.llm_available:
            try:
                print(f"\n🤖 Using LLM-based matching ({self.active_provider.upper()})...")
                results = self._match_with_llm(
                    normalized_required_docs,
                    provided_docs,
                    document_contents,
                    provided_paths
                )
                
                if results and len(results) == len(required_docs):
                    print(f"✓ LLM matching successful: {len(results)} matches computed")
                    if self.matching_cost > 0:
                        print(f"💰 API Cost: ${self.matching_cost:.4f}")
                    print("="*70 + "\n")
                    return results
                else:
                    print("⚠️ LLM matching returned incomplete results. Falling back...")
                    
            except Exception as e:
                print(f"❌ LLM matching failed: {e}")
                if not config.ENABLE_TRADITIONAL_FALLBACK:
                    print("❌ Fallback disabled. Returning empty results.")
                    return self._generate_empty_results(required_docs)
                print("→ Falling back to traditional matching...")
        
        # FALLBACK: Traditional matching
        if not self.traditional_initialized:
            self._initialize_traditional_matching()
        
        print("\n🔧 Using traditional multi-strategy matching...")
        results = self._match_with_traditional_methods(
            required_docs,
            provided_docs,
            document_contents,
            provided_paths
        )
        
        print("="*70 + "\n")
        return results
    
    def _match_with_llm(
        self,
        required_docs: List[Dict],
        provided_docs: List[str],
        document_contents: Dict[str, str],
        provided_paths: Optional[List[str]]
    ) -> List[Dict]:
        """
        Perform document matching using LLM reasoning
        
        Returns:
            List of results in same format as traditional matching
        """
        results = []
        
        # Process in batches to avoid token limits
        batch_size = config.LLM_MATCHING_BATCH_SIZE
        
        for i in range(0, len(required_docs), batch_size):
            batch_required = required_docs[i:i+batch_size]
            
            # Build matching prompt
            prompt = self._build_matching_prompt(
                batch_required,
                provided_docs,
                document_contents
            )
            
            # Get LLM response
            if self.active_provider == 'openai':
                matches = self._match_with_openai(prompt)
            elif self.active_provider == 'anthropic':
                matches = self._match_with_anthropic(prompt)
            else:
                return []
            
            # Convert LLM response to standard format
            batch_results = self._format_llm_results(
                batch_required,
                matches,
                provided_docs
            )
            results.extend(batch_results)
        
        return results
    
    def _build_matching_prompt(
        self,
        required_docs: List[Dict],
        provided_docs: List[str],
        document_contents: Dict[str, str]
    ) -> str:
        """
        Build comprehensive prompt for LLM document matching
        
        Prompt engineering optimized for accuracy
        """
        
        # Prepare provided documents list with metadata
        provided_info = []
        required_list = []
        for idx, doc in enumerate(provided_docs):
            doc_clean = self._clean_filename(doc)
            
            # Include content preview if available
            content_preview = ""
            if doc in document_contents:
                content = document_contents[doc][:10000]  # First 10000 chars
                content_preview = f"\n   Content Preview: {content}..."
            
            provided_info.append(f"{idx + 1}. Filename: {doc}\n   Cleaned Name: {doc_clean}{content_preview}")
        
        provided_list = "\n".join(provided_info)
        
        for doc in required_docs:
            name = doc.get('document_name', 'Unknown Document')
            context = doc.get('context', '')
            criticality = doc.get('criticality', 'Optional')
            
            # Create a rich description for the LLM
            entry = f"- DOCUMENT: {name}\n"
            entry += f"  IMPORTANCE: {criticality}\n"
            if context and len(context) > 5:
                entry += f"  RFP CONTEXT: {context}\n"
            
            required_list.append(entry)
            
        required_list = "\n".join(required_list)
        
        # Build comprehensive prompt with instructions and examples
        prompt = f"""You are a strict Compliance Auditor. Match provided files to required documents.

## INPUT DATA
### REQUIRED DOCUMENTS (From RFP):
{required_list}

### PROVIDED FILES (User Uploads):
{provided_list}

## MATCHING RULES:
1. **Context is King:** Use the "RFP CONTEXT" to understand specific requirements (e.g., if Context says "Issued by CA", look for CA stamps in the file content).
2. **Criticality:** If a document is "Mandatory", you must be stricter in verification.
3. **One-to-Many:** One provided file (e.g., "All_Docs.pdf") can match multiple requirements.
4. **Content Verification:** If a file is named "Doc1.pdf" but the content preview shows it is a "GST Certificate", match it to GST.

## OUTPUT FORMAT:
Return JSON with matches:
{{
  "matches": [
    {{
      "required_document": "Exact name from REQUIRED DOCUMENTS list",
      "matched_file": "Exact filename from PROVIDED FILES list OR null",
      "confidence": "high|medium|low|no_match",
      "reasoning": "Explain why it matches based on context/content"
    }}
  ]
}}
"""
        return prompt
    
    def _match_with_openai(self, prompt: str) -> Dict:
        """Call OpenAI API for matching"""
        try:
            response = self.openai_client.chat.completions.create(
                model=config.OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert document matching system. Always return valid JSON. Be precise and conservative in matching - prefer 'no_match' over incorrect matches."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                response_format={"type": "json_object"},  # Force JSON output
                temperature=config.LLM_MATCHING_TEMPERATURE,
                max_tokens=config.LLM_MATCHING_MAX_TOKENS,
                timeout=config.LLM_MATCHING_TIMEOUT
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # Track costs
            if config.ENABLE_COST_TRACKING:
                usage = response.usage
                pricing = {
                    'gpt-4o': {'input': 0.0025, 'output': 0.01},
                    'gpt-4-turbo': {'input': 0.01, 'output': 0.03},
                }
                model_pricing = pricing.get(config.OPENAI_MODEL, pricing['gpt-4o'])
                cost = (usage.prompt_tokens / 1000 * model_pricing['input'] +
                        usage.completion_tokens / 1000 * model_pricing['output'])
                self.matching_cost += cost
            
            return result
            
        except json.JSONDecodeError as e:
            print(f" ⚠️ JSON parsing error: {e}")
            return {"matches": []}
        except Exception as e:
            print(f" ❌ OpenAI matching error: {e}")
            return {"matches": []}
        
    def _match_with_anthropic(self, prompt: str) -> Dict:
        """Call Anthropic API for matching"""
        try:
            response = self.anthropic_client.messages.create(
                model=config.ANTHROPIC_MODEL,
                max_tokens=config.ANTHROPIC_MAX_TOKENS,
                temperature=config.LLM_MATCHING_TEMPERATURE,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            response_text = response.content[0].text.strip()
            
            # Clean markdown code blocks if present
            if "```json" in response_text:
                response_text = response_text.split("```json").split("```")[1].strip()
            elif "```" in response_text:
                response_text = response_text.split("``````")[0].strip()
            
            result = json.loads(response_text)
            
            # Track costs
            if config.ENABLE_COST_TRACKING:
                usage = response.usage
                pricing = {
                    'claude-3-5-sonnet-20241022': {'input': 0.003, 'output': 0.015},
                }
                model_pricing = pricing.get(config.ANTHROPIC_MODEL, pricing['claude-3-5-sonnet-20241022'])
                cost = (usage.input_tokens / 1000 * model_pricing['input'] +
                        usage.output_tokens / 1000 * model_pricing['output'])
                self.matching_cost += cost
            
            return result
            
        except json.JSONDecodeError as e:
            print(f" ⚠️ JSON parsing error: {e}")
            return {"matches": []}
        except Exception as e:
            print(f" ❌ Anthropic matching error: {e}")
            return {"matches": []}

    def _format_llm_results(
        self,
        required_docs: List[Dict],
        llm_response: Dict,
        provided_docs: List[str]
    ) -> List[Dict]:
        """
        Convert LLM JSON response to standard result format
        
        Maintains exact same format as traditional matching
        """
        results = []
        matches_data = llm_response.get('matches', [])
        
        # Create lookup for quick validation
        provided_set = set(provided_docs)
        
        for required_doc_obj in required_docs:
            # Extract the name to use as the key
            req_name = required_doc_obj.get('document_name', 'Unknown')

            # Find corresponding match in LLM response
            match_entry = None
            for match in matches_data:
                if match.get('required_document') == req_name:
                    match_entry = match
                    break
            
            if not match_entry:
                # LLM didn't return match for this doc - mark as missing
                results.append({
                    'Required Document': req_name,
                    'Status': config.STATUS_MISSING,
                    'Matched File': "N/A",
                    'Confidence Score': "0.00",
                    'Semantic': "0.00",
                    'Fuzzy': "0.00",
                    'Content': "0.00"
                })
                continue
            
            # Extract LLM response fields
            matched_file = match_entry.get('matched_file')
            confidence_level = match_entry.get('confidence', 'no_match')
            reasoning = match_entry.get('reasoning', '')
            
            # Validate matched file exists in provided list
            if matched_file is None or matched_file.lower() == 'null' or matched_file.lower() == 'none':
                matched_file = "N/A"
                confidence_level = 'no_match'
                
            # Validate matched file exists in provided list (if not N/A)
            if matched_file != "N/A" and matched_file not in provided_set:
                # Try to fuzzy find the filename if LLM made a typo
                best_match = process.extractOne(matched_file, provided_set)
                if best_match and best_match[1] > 90:
                    matched_file = best_match[0]
                else:
                    print(f" ⚠️ LLM matched to non-existent file: {matched_file}")
                    matched_file = "N/A"
                    confidence_level = 'no_match'
            
            # Convert confidence level to numeric score
            confidence_map = {
                'high': config.LLM_CONFIDENCE_HIGH,
                'medium': config.LLM_CONFIDENCE_MEDIUM,
                'low': config.LLM_CONFIDENCE_LOW,
                'no_match': config.LLM_CONFIDENCE_NONE
            }
            numeric_confidence = confidence_map.get(confidence_level, 0.0)
            
            # Determine status based on confidence
            if numeric_confidence >= config.SIMILARITY_THRESHOLD_HIGH:
                status = config.STATUS_PRESENT
            elif numeric_confidence >= config.SIMILARITY_THRESHOLD_LOW:
                status = config.STATUS_REVIEW
            else:
                status = config.STATUS_MISSING
                matched_file = "N/A"
            
            # Format result (exact same format as traditional)
            results.append({
                'Required Document': req_name,
                'Status': status,
                'Matched File': matched_file if matched_file else "N/A",
                'Confidence Score': f"{numeric_confidence:.2f}",
                'Criticality': required_doc_obj.get('criticality', 'Optional'),
                'Semantic': f"{numeric_confidence:.2f}",  # LLM score used for all sub-scores
                'Fuzzy': f"{numeric_confidence:.2f}",
                'Content': f"{numeric_confidence:.2f}",
                'Reasoning': reasoning
            })
        
        return results
    
    def _match_with_traditional_methods(
        self,
        required_docs: List[str],
        provided_docs: List[str],
        document_contents: Dict[str, str],
        provided_paths: Optional[List[str]]
    ) -> List[Dict]:
        """
        Traditional multi-strategy matching (original implementation)
        
        Used as fallback when LLM matching fails
        """
        results = []
        
        # Precompute embeddings for efficiency
        required_embeddings = self._get_embeddings(required_docs)
        provided_docs_clean = [self._clean_filename(doc) for doc in provided_docs]
        provided_embeddings = self._get_embeddings(provided_docs_clean)
        
        # Match each required document
        for idx, required_doc in enumerate(required_docs):
            print(f"\n📋 Matching: '{required_doc}'")
            
            # Compute all scoring strategies
            semantic_scores = self._compute_semantic_scores(
                required_embeddings[idx], 
                provided_embeddings
            )
            fuzzy_scores = self._compute_fuzzy_scores(required_doc, provided_docs_clean)
            keyword_scores = self._compute_keyword_scores(required_doc, provided_docs_clean)
            abbrev_scores = self._compute_abbreviation_scores(required_doc, provided_docs_clean)
            content_scores = self._compute_content_scores(
                required_doc, 
                provided_docs, 
                document_contents
            )
            
            # Combine all scores with weighted average
            combined_scores = self._combine_scores(
                semantic_scores,
                fuzzy_scores,
                keyword_scores,
                abbrev_scores,
                content_scores
            )
            
            # Find best match
            best_idx = max(range(len(combined_scores)), key=lambda i: combined_scores[i])
            best_score = combined_scores[best_idx]
            
            print(f" → Best match: {provided_docs[best_idx]} (score: {best_score:.3f})")
            print(f" → Breakdown - Semantic: {semantic_scores[best_idx]:.2f}, "
                f"Fuzzy: {fuzzy_scores[best_idx]:.2f}, "
                f"Keyword: {keyword_scores[best_idx]:.2f}, "
                f"Abbrev: {abbrev_scores[best_idx]:.2f}, "
                f"Content: {content_scores[best_idx]:.2f}")
            
            # Determine status with dynamic thresholding
            status, matched_file = self._determine_status(
                best_score,
                provided_docs[best_idx],
                required_doc,
                provided_docs[best_idx] in document_contents
            )
            
            results.append({
                'Required Document': required_doc,
                'Status': status,
                'Matched File': matched_file,
                'Confidence Score': f"{best_score:.2f}",
                'Semantic': f"{semantic_scores[best_idx]:.2f}",
                'Fuzzy': f"{fuzzy_scores[best_idx]:.2f}",
                'Content': f"{content_scores[best_idx]:.2f}"
            })
        
        return results

    def _get_embeddings(self, texts: List[str]) -> torch.Tensor:
        """Get sentence embeddings"""
        return self.model.encode(
            texts,
            convert_to_tensor=True,
            show_progress_bar=False
        )
    
    def _compute_semantic_scores(
        self,
        required_embedding: torch.Tensor,
        provided_embeddings: torch.Tensor
    ) -> List[float]:
        """Compute semantic similarity scores"""
        similarities = util.cos_sim(required_embedding, provided_embeddings)[0]
        return [float(s) for s in similarities]
    
    def _compute_fuzzy_scores(
        self,
        required_doc: str,
        provided_docs: List[str]
    ) -> List[float]:
        """Compute fuzzy string matching scores"""
        scores = []
        required_lower = required_doc.lower()
        
        for provided_doc in provided_docs:
            provided_lower = provided_doc.lower()
            
            # Use multiple fuzzy matching algorithms
            ratio = fuzz.ratio(required_lower, provided_lower) / 100.0
            partial = fuzz.partial_ratio(required_lower, provided_lower) / 100.0
            token_sort = fuzz.token_sort_ratio(required_lower, provided_lower) / 100.0
            token_set = fuzz.token_set_ratio(required_lower, provided_lower) / 100.0
            
            # Take weighted average
            combined = (ratio * 0.3 + partial * 0.2 + token_sort * 0.25 + token_set * 0.25)
            scores.append(combined)
        
        return scores
    
    def _compute_keyword_scores(
        self,
        required_doc: str,
        provided_docs: List[str]
    ) -> List[float]:
        """Compute keyword overlap scores"""
        scores = []
        required_keywords = set(self._extract_keywords(required_doc))
        
        for provided_doc in provided_docs:
            provided_keywords = set(self._extract_keywords(provided_doc))
            
            if not required_keywords:
                scores.append(0.0)
                continue
            
            # Jaccard similarity
            intersection = required_keywords & provided_keywords
            union = required_keywords | provided_keywords
            score = len(intersection) / len(union) if union else 0.0
            scores.append(score)
        
        return scores
    
    def _compute_abbreviation_scores(
        self,
        required_doc: str,
        provided_docs: List[str]
    ) -> List[float]:
        """Score based on abbreviation expansion"""
        scores = []
        required_expanded = self._expand_abbreviations(required_doc.lower())
        
        for provided_doc in provided_docs:
            provided_expanded = self._expand_abbreviations(provided_doc.lower())
            
            # Check if expanded terms match
            if any(term in provided_expanded for term in required_expanded.split()):
                # Use fuzzy match on expanded text
                score = fuzz.token_set_ratio(required_expanded, provided_expanded) / 100.0
            else:
                score = 0.0
            
            scores.append(score)
        
        return scores
    
    def _compute_content_scores(
        self,
        required_doc: str,
        provided_docs: List[str],
        document_contents: Dict[str, str]
    ) -> List[float]:
        """Score based on document content analysis"""
        scores = []
        required_keywords = set(self._extract_keywords(required_doc))
        
        for provided_doc in provided_docs:
            if provided_doc not in document_contents:
                scores.append(0.0)
                continue
            
            content = document_contents[provided_doc].lower()
            
            # Check keyword presence in content
            keyword_matches = sum(1 for kw in required_keywords if kw in content)
            keyword_score = keyword_matches / len(required_keywords) if required_keywords else 0.0
            
            # Semantic similarity with content
            if len(content) > 50:  # Only if sufficient content
                content_sample = content[:1000]  # First 1000 chars
                required_embedding = self._get_embeddings([required_doc])
                content_embedding = self._get_embeddings([content_sample])
                semantic_score = float(util.cos_sim(required_embedding, content_embedding)[0][0])
            else:
                semantic_score = 0.0
            
            # Combined content score
            combined = (keyword_score * 0.6 + semantic_score * 0.4)
            scores.append(combined)
        
        return scores
    
    def _combine_scores(
        self,
        semantic: List[float],
        fuzzy: List[float],
        keyword: List[float],
        abbrev: List[float],
        content: List[float]
    ) -> List[float]:
        """Combine multiple scoring strategies with adaptive weighting"""
        combined = []
        
        for i in range(len(semantic)):
            # Detect match quality signals
            has_high_content = content[i] > 0.4
            has_high_semantic = semantic[i] > 0.7
            has_exact_keyword = keyword[i] > 0.8
            has_abbreviation = abbrev[i] > 0.5
            
            # Context-aware weighting
            if has_high_content and has_high_semantic:
                # Strong multi-signal match - trust it
                weights = {
                    'semantic': 0.30,
                    'fuzzy': 0.15,
                    'keyword': 0.15,
                    'abbrev': 0.10,
                    'content': 0.30
                }
            elif has_exact_keyword or has_abbreviation:
                # Specific terminology match - boost keyword/abbrev
                weights = {
                    'semantic': 0.25,
                    'fuzzy': 0.15,
                    'keyword': 0.25,
                    'abbrev': 0.20,
                    'content': 0.15
                }
            elif content[i] > 0.3:
                # Good content available
                weights = {
                    'semantic': 0.20,
                    'fuzzy': 0.15,
                    'keyword': 0.15,
                    'abbrev': 0.10,
                    'content': 0.40
                }
            else:
                # Filename-based matching only
                weights = {
                    'semantic': 0.35,
                    'fuzzy': 0.30,
                    'keyword': 0.20,
                    'abbrev': 0.15,
                    'content': 0.00
                }
            
            score = (
                semantic[i] * weights['semantic'] +
                fuzzy[i] * weights['fuzzy'] +
                keyword[i] * weights['keyword'] +
                abbrev[i] * weights['abbrev'] +
                content[i] * weights['content']
            )
            
            # Boost score if multiple signals agree (confidence multiplier)
            high_scores = sum([
                semantic[i] > 0.6,
                fuzzy[i] > 0.6,
                keyword[i] > 0.5,
                content[i] > 0.4
            ])
            
            if high_scores >= 3:
                score *= 1.15  # 15% boost for consensus
            elif high_scores >= 2:
                score *= 1.08  # 8% boost for partial agreement
            
            # Cap at 1.0
            combined.append(min(score, 1.0))
        
        return combined
    
    def _determine_status(
        self,
        score: float,
        matched_file: str,
        required_doc: str,
        has_content: bool
    ) -> Tuple[str, str]:
        """Determine match status with dynamic thresholds"""
        # Adjust thresholds based on whether content was analyzed
        if has_content:
            # More confident with content analysis
            if score >= 0.70:
                return config.STATUS_PRESENT, matched_file
            elif score >= 0.55:
                return config.STATUS_REVIEW, matched_file
            else:
                return config.STATUS_MISSING, "N/A"
        else:
            # More conservative without content
            if score >= 0.80:
                return config.STATUS_PRESENT, matched_file
            elif score >= 0.65:
                return config.STATUS_REVIEW, matched_file
            else:
                return config.STATUS_MISSING, "N/A"
    
    def _extract_document_content(self, file_path: str) -> str:
        """Extract text content from document"""
        content = ""
        
        try:
            if file_path.lower().endswith('.pdf'):
                with open(file_path, 'rb') as f:
                    pdf_reader = PyPDF2.PdfReader(f)
                    for page in pdf_reader.pages[:5]:  # First 5 pages only
                        content += page.extract_text() + " "
            
            elif file_path.lower().endswith(('.docx', '.doc')):
                doc = docx.Document(file_path)
                for para in doc.paragraphs[:50]:  # First 50 paragraphs
                    content += para.text + " "
            
            elif file_path.lower().endswith('.txt'):
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read(5000)  # First 5000 chars
        
        except Exception as e:
            print(f"    Error extracting content: {e}")
        
        return content.strip()
    
    def _clean_filename(self, filename: str) -> str:
        """Enhanced filename cleaning"""
        # Remove file extension
        name = filename.rsplit('.', 1)[0]
        
        # Replace separators with spaces
        name = name.replace('_', ' ').replace('-', ' ').replace('.', ' ')
        
        # Remove common file naming patterns
        name = re.sub(r'(scan|copy|document|file|doc|img|image)\s*\d*', '', name, flags=re.IGNORECASE)
        
        # Remove dates
        name = re.sub(r'\d{1,4}[-/]\d{1,2}[-/]\d{1,4}', '', name)
        name = re.sub(r'\d{8}', '', name)
        
        # Remove version numbers
        name = re.sub(r'v\d+|\bver\s*\d+', '', name, flags=re.IGNORECASE)
        
        # Remove extra whitespace
        name = ' '.join(name.split())
        
        return name.strip()
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract meaningful keywords from text"""
        # Remove common stopwords
        stopwords = {'the', 'a', 'an', 'of', 'for', 'in', 'on', 'at', 'to', 'and', 'or', 'is', 'are'}
        
        # Tokenize and filter
        words = re.findall(r'\b\w+\b', text.lower())
        keywords = [w for w in words if w not in stopwords and len(w) > 2]
        
        return keywords
    
    def _expand_abbreviations(self, text: str) -> str:
        """Expand known abbreviations"""
        expanded = text
        
        for abbrev, expansions in self.abbreviations.items():
            if abbrev in text.lower():
                # Add all expansions
                expanded += " " + " ".join(expansions)
        
        return expanded
    
    # Keep backward compatibility
    def compute_similarity(self, text1: str, text2: str) -> float:
        """Legacy method for backward compatibility"""
        embeddings = self.model.encode([text1, text2], convert_to_tensor=True)
        similarity = util.cos_sim(embeddings[0], embeddings[1])
        return float(similarity[0][0])
    
    def find_best_match(
        self,
        required_doc: str,
        provided_docs: List[str]
    ) -> Tuple[str, float]:
        """Legacy method for backward compatibility"""
        if not provided_docs:
            return "N/A", 0.0
        
        provided_docs_clean = [self._clean_filename(doc) for doc in provided_docs]
        
        best_score = 0.0
        best_match = "N/A"
        
        for idx, provided_doc in enumerate(provided_docs_clean):
            score = self.compute_similarity(required_doc, provided_doc)
            if score > best_score:
                best_score = score
                best_match = provided_docs[idx]
        
        return best_match, best_score
    
    def _generate_empty_results(self, required_docs: List[str]) -> List[Dict]:
        """Generate empty results when matching fails completely"""
        return [
            {
                'Required Document': doc,
                'Status': config.STATUS_MISSING,
                'Matched File': "N/A",
                'Confidence Score': "0.00",
                'Semantic': "0.00",
                'Fuzzy': "0.00",
                'Content': "0.00"
            }
            for doc in required_docs
        ]

