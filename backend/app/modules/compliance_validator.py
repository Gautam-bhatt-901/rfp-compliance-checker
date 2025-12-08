"""
Compliance Validation Module
Extracts structured data and validates against RFP requirements
Provides High accuracy through intelligent data extraction
"""

import re
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from openai import OpenAI
from anthropic import Anthropic
from app import config

class ComplianceValidator:
    """
    Validates compliance by extracting structured data and checking thresholds
    """
    
    def __init__(self):
        """Initialize LLM clients for validation"""
        self.llm_available = False
        self.active_provider = None
        self.validation_cost = 0.0
        
        # Initialize OpenAI
        if config.OPENAI_API_KEY:
            try:
                self.openai_client = OpenAI(api_key=config.OPENAI_API_KEY)
                self.active_provider = "openai"
                self.llm_available = True
                print("✓ OpenAI initialized for validation")
            except Exception as e:
                print(f"OpenAI init failed: {e}")
        
        # Fallback to Anthropic
        if not self.llm_available and config.ANTHROPIC_API_KEY:
            try:
                self.anthropic_client = Anthropic(api_key=config.ANTHROPIC_API_KEY)
                self.active_provider = "anthropic"
                self.llm_available = True
                print("✓ Anthropic initialized for validation")
            except Exception as e:
                print(f"Anthropic init failed: {e}")
        
        if not self.llm_available:
            print("⚠️  No LLM available for validation - accuracy will be limited")
    
    def validate_requirement(
        self, 
        requirement: Dict, 
        document_chunks: List[str],
        filenames: List[str]
    ) -> Dict:
        """
        Main validation method - routes to appropriate validator
        
        Args:
            requirement: Structured requirement with validation_type
            document_chunks: Retrieved text chunks from RAG
            filenames: Source filenames for chunks
        
        Returns:
            Validation result with status, extracted data, reasoning
        """
        
        if not document_chunks or not any(chunk.strip() for chunk in document_chunks):
            return self._create_not_found_result(requirement)
        
        validation_type = requirement.get('validation_type', 'document_existence')
        
        # Route to appropriate validator
        if validation_type == 'numeric_threshold':
            return self.validate_numeric_requirement(requirement, document_chunks, filenames)
        
        elif validation_type == 'date_validity':
            return self.validate_date_requirement(requirement, document_chunks, filenames)
        
        elif validation_type == 'count_threshold':
            return self.validate_count_requirement(requirement, document_chunks, filenames)
        
        elif validation_type == 'multi_condition':
            return self.validate_multi_condition(requirement, document_chunks, filenames)
        
        else:  # document_existence or unknown
            return self.validate_document_existence(requirement, document_chunks, filenames)
    
    def validate_numeric_requirement(
        self, 
        requirement: Dict, 
        chunks: List[str],
        filenames: List[str]
    ) -> Dict:
        """
        Validate requirements with numeric thresholds
        Example: "Average turnover ≥ ₹50 Cr"
        """
        
        if not self.llm_available:
            return self._fallback_validation(requirement, chunks, filenames)
        
        # Build extraction prompt
        prompt = self._build_numeric_extraction_prompt(requirement, chunks, filenames)
        
        # Call LLM to extract data
        extracted = self._call_llm_json(prompt)
        
        if not extracted or 'error' in extracted:
            return self._create_insufficient_data_result(
                requirement, 
                filenames[0] if filenames else "N/A",
                "Could not extract numeric data"
            )
        
        # Validate extraction
        return self._validate_numeric_extraction(requirement, extracted, filenames)
    
    def validate_date_requirement(
        self, 
        requirement: Dict, 
        chunks: List[str],
        filenames: List[str]
    ) -> Dict:
        """
        Validate date-based requirements
        Example: "Certifications must be valid"
        """
        
        if not self.llm_available:
            return self._fallback_validation(requirement, chunks, filenames)
        
        prompt = self._build_date_extraction_prompt(requirement, chunks, filenames)
        extracted = self._call_llm_json(prompt)
        
        if not extracted or 'error' in extracted:
            return self._create_insufficient_data_result(
                requirement, 
                filenames[0] if filenames else "N/A",
                "Could not extract date information"
            )
        
        return self._validate_date_extraction(requirement, extracted, filenames)
    
    def validate_count_requirement(
        self, 
        requirement: Dict, 
        chunks: List[str],
        filenames: List[str]
    ) -> Dict:
        """
        Validate count-based requirements
        Example: "At least 100 employees"
        """
        
        if not self.llm_available:
            return self._fallback_validation(requirement, chunks, filenames)
        
        prompt = self._build_count_extraction_prompt(requirement, chunks, filenames)
        extracted = self._call_llm_json(prompt)
        
        if not extracted or 'error' in extracted:
            return self._create_insufficient_data_result(
                requirement, 
                filenames[0] if filenames else "N/A",
                "Could not extract count data"
            )
        
        return self._validate_count_extraction(requirement, extracted, filenames)
    
    def validate_multi_condition(
        self, 
        requirement: Dict, 
        chunks: List[str],
        filenames: List[str]
    ) -> Dict:
        """
        Validate requirements with multiple conditions (AND/OR logic)
        Example: "ISO 9001 AND ISO 20000 AND CMMI Level 3"
        """
        
        if not self.llm_available:
            return self._fallback_validation(requirement, chunks, filenames)
        
        prompt = self._build_multi_condition_prompt(requirement, chunks, filenames)
        extracted = self._call_llm_json(prompt)
        
        if not extracted or 'error' in extracted:
            return self._create_insufficient_data_result(
                requirement, 
                filenames[0] if filenames else "N/A",
                "Could not validate all conditions"
            )
        
        return self._validate_multi_condition_extraction(requirement, extracted, filenames)
    
    def validate_document_existence(
        self, 
        requirement: Dict, 
        chunks: List[str],
        filenames: List[str]
    ) -> Dict:
        """
        Simple document existence check
        """
        
        if not chunks or not any(chunk.strip() for chunk in chunks):
            return self._create_not_found_result(requirement)
        
        # Check content relevance
        req_keywords = self._extract_keywords(requirement.get('document_name', ''))
        
        relevance_score = 0.0
        best_chunk_idx = 0
        
        for idx, chunk in enumerate(chunks[:3]):  # Check top 3 chunks
            chunk_lower = chunk.lower()
            matches = sum(1 for kw in req_keywords if kw in chunk_lower)
            score = matches / len(req_keywords) if req_keywords else 0
            
            if score > relevance_score:
                relevance_score = score
                best_chunk_idx = idx
        
        if relevance_score >= 0.3:  # At least 30% keyword match
            return {
                'status': 'compliant',
                'matched_file': filenames[best_chunk_idx] if best_chunk_idx < len(filenames) else filenames[0],
                'confidence': min(0.95, relevance_score + 0.2),
                'reasoning': f"Document found with {relevance_score*100:.0f}% keyword match",
                'extracted_data': {}
            }
        else:
            return self._create_not_found_result(requirement)
    
    # ============================================================
    # PROMPT BUILDERS
    # ============================================================
    
    def _build_numeric_extraction_prompt(
        self, 
        requirement: Dict, 
        chunks: List[str],
        filenames: List[str]
    ) -> str:
        """Build prompt for numeric data extraction"""
        
        # Format chunks with source info
        evidence = self._format_chunks_with_sources(chunks, filenames)
        
        threshold = requirement.get('threshold', 'N/A')
        unit = requirement.get('unit', '')
        years_required = requirement.get('years_required', 1)
        calculation = requirement.get('calculation', 'value')
        
        prompt = f"""You are a data extraction specialist. Extract EXACT numeric values from documents.

REQUIREMENT:
{requirement.get('description', requirement.get('document_name', ''))}

VALIDATION RULES:
- Threshold: ≥ {threshold} {unit}
- Years/Instances Required: {years_required}
- Calculation: {calculation}

DOCUMENTS:
{evidence}

EXTRACTION TASK:
1. Find all relevant numeric values (turnover, revenue, net worth, etc.)
2. Extract EXACT values with their labels (e.g., "FY 2022-23: 52.30")
3. Note the source file and location
4. If multiple years required, extract all years

OUTPUT FORMAT (JSON only, no explanation):
{{
  "values_found": {{
    "FY2022-23": {{"value": 52.30, "unit": "crores", "source": "filename, page X"}},
    "FY2023-24": {{"value": 54.10, "unit": "crores", "source": "filename, page Y"}}
  }},
  "calculation_needed": "{calculation}",
  "primary_source": "Exact_Filename.pdf" (eg. 02_CA_Turnover.pdf)
}}

CRITICAL RULES:
- Extract ONLY values explicitly stated in documents
- Do NOT estimate or calculate - just extract
- If a year is missing, omit it from values_found
- Return empty values_found if no clear data found
- Be precise with numbers (include decimals if present)

Return ONLY valid JSON, no markdown or explanation.
"""
        
        return prompt
    
    def _build_date_extraction_prompt(
        self, 
        requirement: Dict, 
        chunks: List[str],
        filenames: List[str]
    ) -> str:
        """Build prompt for date extraction and validity checking"""
        
        evidence = self._format_chunks_with_sources(chunks, filenames)
        today = datetime.now().strftime('%Y-%m-%d')
        
        prompt = f"""You are a date validation specialist. Extract dates and check validity.

REQUIREMENT:
{requirement.get('description', requirement.get('document_name', ''))}

VALIDATION RULES:
- Must be valid as of: {today}
- Certificate/License must not be expired

DOCUMENTS:
{evidence}

EXTRACTION TASK:
1. Find certificate/license issue date and expiry date
2. Extract validity period
3. Determine if currently valid

OUTPUT FORMAT (JSON only):
{{
  "certificates_found": [
    {{
      "name": "ISO 9001:2015",
      "issue_date": "2023-04-01",
      "expiry_date": "2026-03-31",
      "is_currently_valid": true,
      "source": "04_Certifications.pdf"
    }}
  ],
  "primary_source": "04_Certifications.pdf"
}}

CRITICAL RULES:
- Extract EXACT dates from documents (format: YYYY-MM-DD)
- If expiry date > {today}, set is_currently_valid = true
- If no expiry date found, check for "valid until" or similar text
- Return empty certificates_found if no dates found

Return ONLY valid JSON.
"""
        
        return prompt
    
    def _build_count_extraction_prompt(
        self, 
        requirement: Dict, 
        chunks: List[str],
        filenames: List[str]
    ) -> str:
        """Build prompt for count extraction"""
        
        evidence = self._format_chunks_with_sources(chunks, filenames)
        threshold = requirement.get('threshold', 0)
        
        prompt = f"""You are a count extraction specialist. Extract employee/resource counts.

REQUIREMENT:
{requirement.get('description', requirement.get('document_name', ''))}

VALIDATION RULES:
- Minimum count required: {threshold}

DOCUMENTS:
{evidence}

EXTRACTION TASK:
1. Find total count (employees, resources, professionals, etc.)
2. Extract any breakdown by category/experience
3. Note the source

OUTPUT FORMAT (JSON only):
{{
  "total_count": 148,
  "breakdown": {{
    "Senior (9y+)": 25,
    "Mid-Level (6-9y)": 45,
    "Junior (3-6y)": 52,
    "Entry-Level (0-3y)": 26
  }},
  "primary_source": "06_HR_Employee_Count.pdf"
}}

CRITICAL RULES:
- Extract the TOTAL count clearly stated
- Include breakdown if available
- If multiple counts found (different dates), use the most recent
- Return null for total_count if not clearly stated

Return ONLY valid JSON.
"""
        
        return prompt
    
    def _build_multi_condition_prompt(
        self, 
        requirement: Dict, 
        chunks: List[str],
        filenames: List[str]
    ) -> str:
        """Build prompt for multi-condition validation"""
        
        evidence = self._format_chunks_with_sources(chunks, filenames)
        conditions = requirement.get('conditions', [])
        logic = requirement.get('logic', 'AND')
        
        conditions_text = "\n".join([f"  - {cond}" for cond in conditions])
        
        prompt = f"""You are a compliance checker. Verify if ALL required conditions are met.

REQUIREMENT:
{requirement.get('description', requirement.get('document_name', ''))}

CONDITIONS REQUIRED ({logic} logic):
{conditions_text}

DOCUMENTS:
{evidence}

VALIDATION TASK:
For each condition, check if evidence exists in documents.

OUTPUT FORMAT (JSON only):
{{
  "conditions_met": {{
    "SEI CMMI Level 3": {{"found": true, "details": "CMMI Level 3 certified, valid until 2026-03-31", "source": "04_Cert.pdf"}},
    "ISO 9001": {{"found": true, "details": "ISO 9001:2015 certified", "source": "04_Cert.pdf"}},
    "ISO/IEC 20000": {{"found": false, "details": "Not found", "source": null}}
  }},
  "all_conditions_met": false,
  "primary_source": "04_Certifications.pdf"
}}

CRITICAL RULES:
- Check EACH condition independently
- Set found=true ONLY if clear evidence exists
- For certifications, check if currently valid
- all_conditions_met = true only if ALL found=true (for AND logic)

Return ONLY valid JSON.
"""
        
        return prompt
    
    # ============================================================
    # VALIDATION LOGIC
    # ============================================================
    
    def _validate_numeric_extraction(
        self, 
        requirement: Dict, 
        extracted: Dict,
        filenames: List[str]
    ) -> Dict:
        """Validate numeric extraction against threshold"""
        
        values_found = extracted.get('values_found', {})
        
        primary_source = extracted.get('primary_source')
        if not primary_source and filenames:
            primary_source = filenames[0]
        if not primary_source:
            primary_source = 'N/A'
        
        if not values_found:
            return self._create_insufficient_data_result(
                requirement,
                primary_source,  # Use validated primary_source
                "No numeric values found in documents"
            )
        
        # Extract numeric values
        numeric_values = []
        for year, data in values_found.items():
            if isinstance(data, dict) and 'value' in data:
                try:
                    numeric_values.append(float(data['value']))
                except (ValueError, TypeError):
                    continue
        
        if not numeric_values:
            return self._create_insufficient_data_result(
                requirement, 
                primary_source,
                "Could not parse numeric values"
            )
        
        # Perform calculation
        calculation = requirement.get('calculation', 'value')
        
        if calculation == 'average':
            calculated_value = sum(numeric_values) / len(numeric_values)
        elif calculation == 'sum':
            calculated_value = sum(numeric_values)
        elif calculation == 'minimum':
            calculated_value = min(numeric_values)
        elif calculation == 'maximum':
            calculated_value = max(numeric_values)
        else:
            calculated_value = numeric_values[0] if numeric_values else 0
        
        # Check against threshold
        threshold = float(requirement.get('threshold', 0))
        unit = requirement.get('unit', '')
        meets_requirement = calculated_value >= threshold
        
        # Build reasoning
        if calculation == 'average' and len(numeric_values) > 1:
            values_text = ", ".join([f"{list(values_found.keys())[i]}: {v}" for i, v in enumerate(numeric_values)])
            reasoning = f"Found {len(numeric_values)} years of data ({values_text}). Average: {calculated_value:.2f} {unit}. "
        else:
            reasoning = f"Extracted value: {calculated_value:.2f} {unit}. "
        
        if meets_requirement:
            excess = calculated_value - threshold
            
            #Prevent division by zero
            if threshold != 0:
                percentage = (excess / threshold) * 100
                reasoning += f"Exceeds threshold of {threshold} {unit} by {excess:.2f} {unit} ({percentage:.1f}%)."
            else:
                # Special handling for threshold = 0 (e.g., net worth > 0)
                reasoning += f"Meets requirement ({calculated_value:.2f} {unit} is greater than {threshold} {unit})."
        else:
            shortfall = threshold - calculated_value
            
            # Prevent division by zero
            if threshold != 0:
                percentage = (shortfall / threshold) * 100
                reasoning += f"Below threshold of {threshold} {unit} by {shortfall:.2f} {unit} ({percentage:.1f}% shortfall)."
            else:
                reasoning += f"Does not meet requirement ({calculated_value:.2f} {unit} is not greater than {threshold} {unit})."
        
        return {
            'status': 'compliant' if meets_requirement else 'non_compliant',
            'matched_file': primary_source,
            'confidence': 0.92 if meets_requirement else 0.88,
            'reasoning': reasoning,
            'extracted_data': {
                'values': values_found,
                'calculated': calculated_value,
                'threshold': threshold,
                'unit': unit,
                'primary_source': primary_source
            }
        }
    
    def _validate_date_extraction(
        self, 
        requirement: Dict, 
        extracted: Dict,
        filenames: List[str]
    ) -> Dict:
        """Validate date extraction"""
        primary_source = extracted.get('primary_source')
        if not primary_source and filenames:
            primary_source = filenames[0]
        if not primary_source:
            primary_source = 'N/A'
        
        certificates = extracted.get('certificates_found', [])
        
        if not certificates:
            return self._create_insufficient_data_result(
                requirement, 
                primary_source,
                "No certificates or dates found"
            )
        
        # Check if all certificates are valid
        all_valid = all(cert.get('is_currently_valid', False) for cert in certificates)
        
        cert_names = [cert.get('name', 'Unknown') for cert in certificates]
        
        if all_valid:
            reasoning = f"All required certifications found and valid: {', '.join(cert_names)}."
        else:
            invalid = [cert['name'] for cert in certificates if not cert.get('is_currently_valid', False)]
            reasoning = f"Some certifications invalid or expired: {', '.join(invalid)}."
        
        return {
            'status': 'compliant' if all_valid else 'non_compliant',
            'matched_file': primary_source,
            'confidence': 0.90 if all_valid else 0.85,
            'reasoning': reasoning,
            'extracted_data': {
                'certificates': certificates,
                'primary_source': primary_source
            }
        }
    
    def _validate_count_extraction(
        self, 
        requirement: Dict, 
        extracted: Dict,
        filenames: List[str]
    ) -> Dict:
        """Validate count extraction"""
        primary_source = extracted.get('primary_source')
        if not primary_source and filenames:
            primary_source = filenames[0]
        if not primary_source:
            primary_source = 'N/A'
        
        total_count = extracted.get('total_count')
        
        if total_count is None:
            return self._create_insufficient_data_result(
                requirement, 
                primary_source,
                "Could not find count information"
            )
        
        try:
            total_count = int(total_count)
        except (ValueError, TypeError):
            return self._create_insufficient_data_result(
                requirement, 
                primary_source,
                "Invalid count format"
            )
        
        threshold = int(requirement.get('threshold', 0))
        meets_requirement = total_count >= threshold
        
        breakdown = extracted.get('breakdown', {})
        breakdown_text = ""
        if breakdown:
            breakdown_text = " Breakdown: " + ", ".join([f"{k}: {v}" for k, v in breakdown.items()])
        
        if meets_requirement:
            excess = total_count - threshold
            
            # Prevent division by zero
            if threshold != 0:
                percentage = (excess / threshold) * 100
                reasoning = f"Total count: {total_count}.{breakdown_text} Exceeds requirement of {threshold} by {excess} ({percentage:.1f}%)."
            else:
                reasoning = f"Total count: {total_count}.{breakdown_text} Meets requirement (count > {threshold})."
        else:
            shortfall = threshold - total_count
            
            # Prevent division by zero
            if threshold != 0:
                percentage = (shortfall / threshold) * 100
                reasoning = f"Total count: {total_count}.{breakdown_text} Below requirement of {threshold} by {shortfall} ({percentage:.1f}% shortfall)."
            else:
                reasoning = f"Total count: {total_count}.{breakdown_text} Does not meet requirement."
        
        return {
            'status': 'compliant' if meets_requirement else 'non_compliant',
            'matched_file': primary_source,
            'confidence': 0.90 if meets_requirement else 0.85,
            'reasoning': reasoning,
            'extracted_data': {
                'total': total_count,
                'breakdown': breakdown,
                'threshold': threshold,
                'primary_source': primary_source
            }
        }
    
    def _validate_multi_condition_extraction(
        self, 
        requirement: Dict, 
        extracted: Dict,
        filenames: List[str]
    ) -> Dict:
        """Validate multi-condition extraction"""
        primary_source = extracted.get('primary_source')
        if not primary_source and filenames:
            primary_source = filenames[0]
        if not primary_source:
            primary_source = 'N/A'
        
        conditions_met = extracted.get('conditions_met', {})
        all_met = extracted.get('all_conditions_met', False)
        
        if not conditions_met:
            return self._create_insufficient_data_result(
                requirement, 
                primary_source,
                "Could not verify conditions"
            )
        
        met_conditions = [k for k, v in conditions_met.items() if v.get('found', False)]
        missing_conditions = [k for k, v in conditions_met.items() if not v.get('found', False)]
        
        if all_met:
            reasoning = f"All {len(met_conditions)} required conditions verified: {', '.join(met_conditions)}."
        else:
            reasoning = f"Met {len(met_conditions)}/{len(conditions_met)} conditions. Missing: {', '.join(missing_conditions)}."
        
        return {
            'status': 'compliant' if all_met else 'non_compliant',
            'matched_file': primary_source,
            'confidence': 0.90 if all_met else 0.75,
            'reasoning': reasoning,
            'extracted_data': {
                'conditions': conditions_met,
                'all_met': all_met,
                'primary_source': primary_source
            }
        }
    
    # ============================================================
    # HELPER METHODS
    # ============================================================
    
    def _call_llm_json(self, prompt: str) -> Dict:
        """Call LLM and parse JSON response"""
        
        try:
            if self.active_provider == "openai":
                response = self.openai_client.chat.completions.create(
                    model=config.OPENAI_MODEL,
                    messages=[
                        {"role": "system", "content": "You are a data extraction specialist. Always return valid JSON only, no markdown or explanation."},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.0,
                    max_tokens=2000
                )
                
                result = json.loads(response.choices[0].message.content)
                
                # Track cost
                if config.ENABLE_COST_TRACKING and hasattr(response, 'usage'):
                    self._track_cost_openai(response.usage)
                
                return result
            
            elif self.active_provider == "anthropic":
                response = self.anthropic_client.messages.create(
                    model=config.ANTHROPIC_MODEL,
                    max_tokens=2000,
                    temperature=0.0,
                    messages=[{"role": "user", "content": prompt}]
                )
                
                response_text = response.content[0].text.strip()
                
                # Clean markdown if present
                if "```json" in response_text:
                    response_text = response_text.split("```json").split("```")[1].strip()
                elif "```" in response_text:
                    response_text = response_text.split("``````")[0].strip()
                
                result = json.loads(response_text)
                
                # Track cost
                if config.ENABLE_COST_TRACKING and hasattr(response, 'usage'):
                    self._track_cost_anthropic(response.usage)
                
                return result
        
        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
            return {"error": "JSON parsing failed"}
        except Exception as e:
            print(f"LLM call failed: {e}")
            return {"error": str(e)}
    
    def _format_chunks_with_sources(self, chunks: List[str], filenames: List[str]) -> str:
        """Format chunks with source filenames"""
        
        formatted = []
        for i, chunk in enumerate(chunks[:5]):  # Limit to 5 chunks
            source = filenames[i] if i < len(filenames) else "Unknown"
            formatted.append(f"--- SOURCE: {source} ---\n{chunk[:1500]}")  # Limit chunk size
        
        return "\n\n".join(formatted)
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text"""
        
        # Remove common words
        stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
                     'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
                     'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
                     'should', 'could', 'may', 'might', 'must', 'can', 'certificate',
                     'copy', 'document', 'required', 'mandatory'}
        
        words = re.findall(r'\b\w+\b', text.lower())
        keywords = [w for w in words if w not in stopwords and len(w) > 2]
        
        return keywords[:10]  # Top 10 keywords
    
    def _fallback_validation(self, requirement: Dict, chunks: List[str], filenames: List[str]) -> Dict:
        """Fallback validation without LLM"""
        
        # Simple keyword matching
        req_text = requirement.get('description', requirement.get('document_name', '')).lower()
        keywords = self._extract_keywords(req_text)
        
        best_score = 0.0
        best_file = filenames[0] if filenames else "N/A"
        
        for i, chunk in enumerate(chunks[:3]):
            chunk_lower = chunk.lower()
            matches = sum(1 for kw in keywords if kw in chunk_lower)
            score = matches / len(keywords) if keywords else 0
            
            if score > best_score:
                best_score = score
                best_file = filenames[i] if i < len(filenames) else best_file
        
        if best_score >= 0.3:
            return {
                'status': 'compliant',
                'matched_file': best_file,
                'confidence': 0.65,
                'reasoning': f"Document found (keyword match: {best_score*100:.0f}%). LLM validation unavailable.",
                'extracted_data': {}
            }
        else:
            return self._create_not_found_result(requirement)
    
    def _create_not_found_result(self, requirement: Dict) -> Dict:
        """Create result for not found requirement"""
        
        return {
            'status': 'not_found',
            'matched_file': 'N/A',
            'confidence': 0.0,
            'reasoning': 'No relevant document found',
            'extracted_data': {}
        }
    
    def _create_insufficient_data_result(self, requirement: Dict, filename: str, reason: str) -> Dict:
        """Create result for insufficient data"""
        if not filename or filename == 'N/A' or filename == 'None':
            filename = 'N/A'

        return {
            'status': 'insufficient_data',
            'matched_file': filename,
            'confidence': 0.45,
            'reasoning': f"Document found but {reason.lower()}",
            'extracted_data': {}
        }
    
    def _track_cost_openai(self, usage):
        """Track OpenAI costs"""
        pricing = {
            'gpt-4o': {'input': 0.0025, 'output': 0.01},
            'gpt-4-turbo': {'input': 0.01, 'output': 0.03},
        }
        
        model_pricing = pricing.get(config.OPENAI_MODEL, pricing['gpt-4o'])
        cost = (usage.prompt_tokens / 1000 * model_pricing['input'] + 
                usage.completion_tokens / 1000 * model_pricing['output'])
        self.validation_cost += cost
    
    def _track_cost_anthropic(self, usage):
        """Track Anthropic costs"""
        pricing = {
            'claude-3-5-sonnet-20241022': {'input': 0.003, 'output': 0.015},
        }
        
        model_pricing = pricing.get(config.ANTHROPIC_MODEL, pricing['claude-3-5-sonnet-20241022'])
        cost = (usage.input_tokens / 1000 * model_pricing['input'] + 
                usage.output_tokens / 1000 * model_pricing['output'])
        self.validation_cost += cost
    
    def get_total_cost(self) -> float:
        """Get total validation cost"""
        return self.validation_cost
