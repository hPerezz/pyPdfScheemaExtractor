"""Scoring and validation of extraction candidates"""
import re
from typing import List, Dict, Optional
import numpy as np


class ScorerValidator:
    """Scores and validates extraction candidates"""
    
    def __init__(self):
        self.validation_patterns = {
            'cpf': r'^\d{3}\.?\d{3}\.?\d{3}-?\d{2}$',
            'cnpj': r'^\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}$',
            'email': r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$',
            'phone': r'^\(?\d{2}\)?\s?\d{4,5}-?\d{4}$',
            'date': r'^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}$',
            'cep': r'^\d{5}-?\d{3}$',
        }
        self.uf_set = set([
            'AC','AL','AP','AM','BA','CE','DF','ES','GO','MA','MT','MS','MG','PA','PB','PR','PE','PI','RJ','RN','RS','RO','RR','SC','SP','SE','TO'
        ])
    
    def score_candidate(self,
                       candidate: Dict,
                       field_name: str,
                       field_description: str,
                       all_candidates: List[Dict],
                       document_context: Dict) -> float:
        """
        Calculate combined score for a candidate [0, 1]
        
        Combines:
        - Regex match score
        - Semantic similarity
        - Positional match (if available)
        - Value validation
        """
        scores = []
        
        # 1. Base score from candidate generator
        base_score = candidate.get('score', 0.0)
        scores.append(('base', base_score, 0.2))
        
        # 2. Regex/pattern validation
        regex_score = self._regex_validation(candidate, field_name, field_description)
        scores.append(('regex', regex_score, 0.25))
        
        # 3. Semantic similarity (if available)
        semantic_score = candidate.get('similarity', 0.0)
        if semantic_score > 0:
            # Normalize to [0, 1] (similarity is already in reasonable range)
            semantic_score = max(0, min(1, (semantic_score + 1) / 2))
        scores.append(('semantic', semantic_score, 0.25))
        
        # 4. Positional match (distance from expected position)
        positional_score = self._positional_score(candidate, all_candidates, document_context)
        scores.append(('positional', positional_score, 0.15))
        
        # 5. Value validation
        validation_score = self._validate_value(candidate['text'], field_name, field_description)
        scores.append(('validation', validation_score, 0.15))
        
        # Weighted sum
        total_score = sum(weight * score for _, score, weight in scores)
        return min(1.0, max(0.0, total_score))
    
    def _regex_validation(self, candidate: Dict, field_name: str, field_description: str) -> float:
        """Check if candidate matches expected pattern"""
        text = candidate['normalized']
        field_lower = field_name.lower()
        desc_lower = field_description.lower()
        
        # Check against known patterns
        for pattern_type, pattern in self.validation_patterns.items():
            if pattern_type in field_lower or pattern_type in desc_lower:
                if re.match(pattern, text, re.IGNORECASE):
                    return 1.0
        
        # If candidate came from regex method, give it a boost
        if candidate.get('method') == 'regex':
            return 0.8
        
        return 0.5
    
    def _positional_score(self, 
                         candidate: Dict,
                         all_candidates: List[Dict],
                         document_context: Dict) -> float:
        """
        Score based on position relative to other candidates
        For now, simpler heuristic - prefer candidates that appear in logical order
        """
        # Simplified: if this is the first candidate, give it a slight boost
        # In a more sophisticated system, we'd track expected positions per label
        if len(all_candidates) > 0 and candidate == all_candidates[0]:
            return 0.7
        
        return 0.5  # Neutral score
    
    def _validate_value(self, text: str, field_name: str, field_description: str) -> float:
        """Validate that the extracted value makes sense for the field"""
        # Basic validations
        text_lower = text.lower().strip()
        
        # Empty check
        if not text_lower:
            return 0.0
        
        # Length checks
        field_lower = field_name.lower()
        
        # CPF should be ~14 chars
        if 'cpf' in field_lower:
            cleaned = re.sub(r'[^\d]', '', text)
            if len(cleaned) == 11:
                return 1.0
            return 0.3
        
        # CNPJ should be ~18 chars
        if 'cnpj' in field_lower:
            cleaned = re.sub(r'[^\d]', '', text)
            if len(cleaned) == 14:
                return 1.0
            return 0.3
        
        # CEP must match CEP token pattern; don't accept generic 8-digit sequences (avoids dates)
        if 'cep' in field_lower:
            if re.search(r'\b\d{5}-?\d{3}\b', text):
                return 1.0
            return 0.3
        
        # State/UF: two-letter code in set
        if 'estado' in field_lower or 'uf' in field_lower or 'state' in field_lower:
            val = text.strip().upper()
            if val in self.uf_set:
                return 1.0
            return 0.3
        
        # City: alphabetic words with spaces, reasonable length
        if 'cidade' in field_lower or 'city' in field_lower:
            if re.match(r'^[A-Za-zÀ-ÿ]+(?:\s+[A-Za-zÀ-ÿ]+)*$', text.strip()) and len(text.strip()) >= 3:
                return 0.9
            return 0.3
        
        # Address: contains street type and a number
        if 'endereco' in field_lower or 'endereço' in field_lower or 'address' in field_lower:
            if re.search(r'\b(rua|avenida|av\.?|travessa|alameda|rodovia|rod\.?|estrada|praça|praca|largo)\b', text_lower) and re.search(r'\b\d+[\w\-\/]*\b', text_lower):
                return 0.9
            return 0.3
        
        # Email validation
        if 'email' in field_lower or 'e-mail' in field_lower:
            if '@' in text and '.' in text.split('@')[-1]:
                return 1.0
            return 0.3
        
        # Date validation
        if 'data' in field_lower or 'date' in field_lower:
            if re.match(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', text):
                return 1.0
            return 0.3
        
        # Default: non-empty text gets some score
        return 0.6
    
    def select_best_candidate(self,
                             candidates: List[Dict],
                             field_name: str,
                             field_description: str,
                             document_context: Dict) -> Optional[Dict]:
        """
        Select the best candidate for a field
        
        Returns:
            Best candidate dict with added 'final_score', or None
        """
        if not candidates:
            return None
        
        # Score all candidates
        scored_candidates = []
        for candidate in candidates:
            final_score = self.score_candidate(
                candidate, field_name, field_description, candidates, document_context
            )
            candidate_copy = candidate.copy()
            candidate_copy['final_score'] = final_score
            scored_candidates.append(candidate_copy)
        
        # Return best candidate
        best = max(scored_candidates, key=lambda x: x['final_score'])
        return best


