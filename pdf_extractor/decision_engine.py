"""Decision engine for extraction with LLM fallback"""
from typing import Dict, List, Optional, Tuple
from .config import T_HIGH, T_LOW
from .llm_client import LLMClient


class DecisionEngine:
    """Decides whether to accept, normalize, or use LLM for extraction"""
    
    def __init__(self):
        self.llm_client = LLMClient()
        # Tracks whether the LLM was used in the most recent call to process_extraction
        self.used_llm_last_call = False
    
    def process_extraction(self,
                          field_results: Dict[str, Dict],
                          label: str,
                          extraction_schema: Dict[str, str],
                          document_context: Dict) -> Dict[str, any]:
        """
        Process extraction results and decide on final values
        
        Args:
            field_results: Dictionary mapping field names to candidate results
            label: Document label
            extraction_schema: Original extraction schema
            document_context: Document context (full text, etc.)
            
        Returns:
            Dictionary with extracted values
        """
        final_values = {}
        # Reset LLM usage flag for this run
        self.used_llm_last_call = False
        pending_fields = []
        
        # Process each field
        for field_name, candidate_result in field_results.items():
            if candidate_result is None:
                pending_fields.append(field_name)
                continue
            
            score = candidate_result.get('final_score', 0.0)
            
            if score >= T_HIGH:
                # High confidence - accept directly
                final_values[field_name] = self._normalize_value(
                    candidate_result['text'], field_name
                )
            
            elif score >= T_LOW:
                # Medium confidence - use deterministic normalization
                final_values[field_name] = self._normalize_with_mini_model(
                    candidate_result['text'], field_name, 
                    extraction_schema.get(field_name, '')
                )
            
            else:
                # Low confidence - try deterministic acceptance for strictly-formattable fields (e.g., CPF)
                if self._deterministic_accept(field_name, candidate_result.get('text', '')):
                    final_values[field_name] = self._normalize_value(
                        candidate_result.get('text', ''), field_name
                    )
                else:
                    # Collect for LLM
                    pending_fields.append(field_name)
        
        # If we have pending fields, call LLM once with minimal context
        if pending_fields:
            llm_results = self._call_llm(
                pending_fields, extraction_schema, label, 
                document_context, final_values
            )
            final_values.update(llm_results)
            self.used_llm_last_call = True
        
        return final_values
    
    def _deterministic_accept(self, field_name: str, value: str) -> bool:
        """Return True when a field can be confidently accepted without LLM despite low score."""
        field_lower = field_name.lower()
        # CPF: accept when there are exactly 11 digits
        if 'cpf' in field_lower:
            digits = ''.join(filter(str.isdigit, value or ''))
            return len(digits) == 11
        # DATE: accept when value matches common date formats (DD/MM/YYYY or DD-MM-YYYY or D/M/YY etc.)
        if 'data' in field_lower or 'date' in field_lower:
            import re
            text = (value or '').strip()
            if re.match(r'^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}$', text):
                return True
        # CEP: must match CEP pattern (avoid misclassifying dates with 8 digits)
        if 'cep' in field_lower:
            import re
            text = (value or '').strip()
            return re.search(r'\b\d{5}-?\d{3}\b', text) is not None
        # State/UF: two-letter code in known set
        if 'estado' in field_lower or 'uf' in field_lower or 'state' in field_lower:
            val = (value or '').strip().upper()
            if val in {
                'AC','AL','AP','AM','BA','CE','DF','ES','GO','MA','MT','MS','MG','PA','PB','PR','PE','PI','RJ','RN','RS','RO','RR','SC','SP','SE','TO'
            }:
                return True
        # Address: contains a street type and a number
        if 'endereco' in field_lower or 'endereço' in field_lower or 'address' in field_lower:
            import re
            tl = (value or '').lower()
            if re.search(r'\b(rua|avenida|av\.|travessa|alameda|rodovia|rod\.|estrada|praça|praca|largo)\b', tl) and re.search(r'\b\d+[\w\-\/]*\b', tl):
                return True
        return False
    
    def _normalize_value(self, value: str, field_name: str) -> str:
        """Simple normalization for high-confidence values"""
        # Clean up whitespace
        normalized = ' '.join(value.split())
        
        # Apply field-specific normalization
        field_lower = field_name.lower()
        
        if 'cpf' in field_lower:
            # Format CPF: XXX.XXX.XXX-XX
            digits = ''.join(filter(str.isdigit, normalized))
            if len(digits) == 11:
                return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"
        
        if 'cnpj' in field_lower:
            # Format CNPJ: XX.XXX.XXX/XXXX-XX
            digits = ''.join(filter(str.isdigit, normalized))
            if len(digits) == 14:
                return f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:]}"
        
        if ('data' in field_lower) or ('date' in field_lower) or ('data_nascimento' in field_lower) or ('nascimento' in field_lower):
            # Normalize dates to DD/MM/YYYY when possible
            import re
            text = normalized.replace('-', '/').strip()
            # Remove common leading labels like "Nascimento:", "Data:", "Data de Nascimento:"
            text = re.sub(r'^(?:nascimento|data(?:\s+de\s+nascimento)?|date)\s*:\s*', '', text, flags=re.IGNORECASE)
            # Also strip any generic single-word label followed by colon (defensive)
            text = re.sub(r'^[A-Za-zÀ-ÿ]+\s*:\s*', '', text)
            m = re.match(r'^(\d{1,2})/(\d{1,2})/(\d{2,4})$', text)
            if m:
                d, mth, y = m.groups()
                day = d.zfill(2)
                month = mth.zfill(2)
                year = y if len(y) == 4 else ('20' + y if int(y) <= 50 else '19' + y)
                return f"{day}/{month}/{year}"
        
        if 'cep' in field_lower:
            # Extract CEP token from anywhere in the text and format as 99999-999
            import re
            m = re.search(r'\b(\d{5}-?\d{3})\b', normalized)
            if m:
                digits = ''.join(filter(str.isdigit, m.group(1)))
                return f"{digits[:5]}-{digits[5:]}"
            # Fallback: if the whole text is just digits and has 8 digits
            digits = ''.join(filter(str.isdigit, normalized))
            if len(digits) == 8:
                return f"{digits[:5]}-{digits[5:]}"
        
        if 'estado' in field_lower or 'uf' in field_lower or 'state' in field_lower:
            return normalized.upper()[:2]
        
        if 'endereco' in field_lower or 'endereço' in field_lower or 'address' in field_lower:
            # Basic cleanup; could be enhanced with more formatting rules
            return normalized
        
        return normalized
    
    def _normalize_with_mini_model(self, 
                                   value: str,
                                   field_name: str,
                                   field_description: str) -> str:
        """
        Deterministic normalization using rules (mini-model)
        More sophisticated than simple normalization but no LLM needed
        """
        normalized = self._normalize_value(value, field_name)
        
        # Additional normalization based on field description
        desc_lower = field_description.lower()
        
        # If description mentions specific format, try to match it
        if 'formato' in desc_lower or 'format' in desc_lower:
            # Could extract format hints from description
            pass
        
        return normalized
    
    def _call_llm(self,
                  pending_fields: List[str],
                  extraction_schema: Dict[str, str],
                  label: str,
                  document_context: Dict,
                  extracted_so_far: Dict[str, str]) -> Dict[str, str]:
        """
        Call LLM once with minimal context for all pending fields
        
        Args:
            pending_fields: List of field names that need LLM extraction
            extraction_schema: Original extraction schema
            label: Document label
            document_context: Document context
            extracted_so_far: Fields already extracted (for context)
            
        Returns:
            Dictionary mapping field names to extracted values
        """
        # Build minimal context
        pending_schema = {field: extraction_schema[field] for field in pending_fields}
        
        # Get relevant text snippets (not full document)
        full_text = document_context.get('full_text', '')
        # Limit context size to reduce costs
        text_snippet = full_text[:3000] if len(full_text) > 3000 else full_text
        
        # Call LLM
        results = self.llm_client.extract_fields(
            label=label,
            fields=pending_schema,
            document_text=text_snippet,
            extracted_context=extracted_so_far
        )
        
        return results

