"""Candidate generation using rules/regex, label-proximity, and semantic search"""
import re
from typing import List, Dict, Tuple, Optional
from sentence_transformers import SentenceTransformer
import numpy as np
from .preprocessor import Preprocessor


class CandidateGenerator:
    """Generates extraction candidates for each field"""
    
    def __init__(self, embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.preprocessor = Preprocessor()
        self.embedding_model = SentenceTransformer(embedding_model_name)
        self.label_cache = {}  # Cache embeddings for labels
    
    def generate_candidates(self, 
                          processed_data: Dict,
                          label: str,
                          extraction_schema: Dict[str, str],
                          top_k: int = 5) -> Dict[str, List[Dict]]:
        """
        Generate candidates for each field in extraction_schema
        
        Args:
            processed_data: Preprocessed text data
            extraction_schema: Dictionary mapping field names to descriptions
            label: Document label
            top_k: Number of top candidates to return per field
            
        Returns:
            Dictionary mapping field names to lists of candidates with scores
        """
        candidates = {}
        
        # Get embedding for label context (cache it)
        if label not in self.label_cache:
            label_embedding = self.embedding_model.encode([label])[0]
            self.label_cache[label] = label_embedding
        else:
            label_embedding = self.label_cache[label]
        
        # Generate candidates for each field
        for field_name, field_description in extraction_schema.items():
            field_candidates = []
            
            # 1. Rule-based/Regex candidates
            regex_candidates = self._regex_candidates(
                processed_data, field_name, field_description
            )
            field_candidates.extend(regex_candidates)
            
            # 2. Semantic search candidates
            semantic_candidates = self._semantic_search(
                processed_data, field_name, field_description, 
                label_embedding, top_k
            )
            field_candidates.extend(semantic_candidates)
            
            # 3. Label-proximity candidates (if we have previous examples)
            # This would require a memory system - simplified for now
            
            # Deduplicate and rank candidates
            field_candidates = self._deduplicate_candidates(field_candidates)
            field_candidates = sorted(field_candidates, key=lambda x: x['score'], reverse=True)
            
            candidates[field_name] = field_candidates[:top_k]
        
        return candidates
    
    def _regex_candidates(self, 
                         processed_data: Dict,
                         field_name: str,
                         field_description: str) -> List[Dict]:
        """Generate candidates using regex patterns"""
        candidates = []
        full_text = processed_data['normalized_full_text']
        processed_blocks = processed_data['processed_blocks']
        
        # Common regex patterns based on field name
        patterns = self._get_regex_patterns(field_name, field_description)
        
        for pattern, match_type in patterns:
            matches = re.finditer(pattern, full_text, re.IGNORECASE)
            for match in matches:
                # Select matched text; support named groups for precise extraction
                matched_text = match.group()
                try:
                    field_lower = field_name.lower()
                    groupindex = getattr(match.re, 'groupindex', {})
                    if 'city' in groupindex and ('cidade' in field_lower or 'city' in field_lower):
                        matched_text = match.group('city')
                    elif 'state' in groupindex and (
                        'estado' in field_lower or 'uf' in field_lower or 'state' in field_lower
                    ):
                        matched_text = match.group('state')
                    elif 'address' in groupindex and ('endereco' in field_lower or 'endereço' in field_lower or 'address' in field_lower):
                        matched_text = match.group('address')
                except Exception:
                    pass
                
                # Find the block(s) containing this match
                for block_info in processed_blocks:
                    if matched_text.lower() in block_info['normalized']:
                        # For regex matches, set candidate text to the matched substring (not the entire block)
                        candidates.append({
                            'text': matched_text,
                            'normalized': self.preprocessor.normalize_text(matched_text),
                            'bbox': block_info['bbox'],
                            'score': 0.4,  # Base score for regex match
                            'method': 'regex',
                            'pattern': pattern,
                            'match_type': match_type
                        })
                        break
        
        return candidates
    
    def _get_regex_patterns(self, field_name: str, field_description: str) -> List[Tuple[str, str]]:
        """Get regex patterns based on field name and description"""
        patterns = []
        field_lower = field_name.lower()
        desc_lower = field_description.lower()
        
        # CPF pattern
        if 'cpf' in field_lower or 'cpf' in desc_lower:
            patterns.append((r'\d{3}\.?\d{3}\.?\d{3}-?\d{2}', 'cpf'))
        
        # CNPJ pattern
        if 'cnpj' in field_lower:
            patterns.append((r'\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}', 'cnpj'))
        
        # Email pattern
        if 'email' in field_lower or 'e-mail' in desc_lower:
            patterns.append((r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', 'email'))
        
        # Phone pattern
        if 'telefone' in field_lower or 'phone' in field_lower or 'celular' in field_lower:
            patterns.append((r'\(?\d{2}\)?\s?\d{4,5}-?\d{4}', 'phone'))
        
        # CEP (Brazilian postal code)
        if 'cep' in field_lower or 'cep' in desc_lower or 'postal' in desc_lower:
            patterns.append((r'\b\d{5}-?\d{3}\b', 'cep'))
        
        # State (UF)
        uf_codes = r'(?:AC|AL|AP|AM|BA|CE|DF|ES|GO|MA|MT|MS|MG|PA|PB|PR|PE|PI|RJ|RN|RS|RO|RR|SC|SP|SE|TO)'
        if 'estado' in field_lower or 'uf' in field_lower or 'state' in field_lower:
            patterns.append((rf'\b{uf_codes}\b', 'state'))
        
        # City (look for "City - UF" or "City, UF")
        if 'cidade' in field_lower or 'city' in field_lower:
            patterns.append((rf'(?P<city>[A-Za-zÀ-ÿ]+(?:\s+[A-Za-zÀ-ÿ]+)*)\s*[,\-]\s*(?P<state>{uf_codes})', 'city_state'))
        
        # Address (common street types with number)
        if 'endereco' in field_lower or 'endereço' in field_lower or 'address' in field_lower:
            street_types = r'(?:rua|avenida|av\.?|travessa|alameda|rodovia|rod\.?|estrada|praça|praca|largo)'
            patterns.append((rf'(?P<address>\b{street_types}\s+[\wÀ-ÿ\.\- ]+?\s*,?\s*\d+[\w\-\/]*?)', 'address'))
            # Address possibly followed by CEP
            patterns.append((rf'(?P<address>\b{street_types}\s+[\wÀ-ÿ\.\- ]+?\s*,?\s*\d+[\w\-\/]*?).*?\b\d{{5}}-?\d{{3}}\b', 'address'))

        # Date patterns
        if 'data' in field_lower or 'date' in field_lower or 'nascimento' in field_lower:
            patterns.append((r'\d{1,2}/\d{1,2}/\d{2,4}', 'date'))
            patterns.append((r'\d{1,2}-\d{1,2}-\d{2,4}', 'date'))
        
        # Money/Currency
        if 'valor' in field_lower or 'preço' in field_lower or 'money' in field_lower:
            patterns.append((r'R\$\s?\d+[.,]\d{2}', 'currency'))
            patterns.append((r'\d+[.,]\d{2}', 'number'))
        
        # Generic number patterns
        if 'numero' in field_lower or 'número' in field_lower or 'number' in field_lower:
            patterns.append((r'\d+', 'number'))
        
        return patterns
    
    def _semantic_search(self,
                        processed_data: Dict,
                        field_name: str,
                        field_description: str,
                        label_embedding: np.ndarray,
                        top_k: int) -> List[Dict]:
        """Generate candidates using semantic search"""
        candidates = []
        
        # Create query embedding (field name + description + label context)
        query_text = f"{field_name} {field_description}"
        query_embedding = self.embedding_model.encode([query_text])[0]
        
        # Get embeddings for all text blocks
        processed_blocks = processed_data['processed_blocks']
        if not processed_blocks:
            return candidates
        
        block_texts = [b['normalized'] for b in processed_blocks]
        block_embeddings = self.embedding_model.encode(block_texts)
        
        # Calculate cosine similarity
        similarities = np.dot(block_embeddings, query_embedding) / (
            np.linalg.norm(block_embeddings, axis=1) * np.linalg.norm(query_embedding)
        )
        
        # Also consider label proximity (optional)
        label_similarities = np.dot(block_embeddings, label_embedding) / (
            np.linalg.norm(block_embeddings, axis=1) * np.linalg.norm(label_embedding)
        )
        
        # Combined score (weighted)
        combined_scores = 0.7 * similarities + 0.3 * label_similarities
        
        # Get top candidates
        top_indices = np.argsort(combined_scores)[::-1][:top_k]
        
        for idx in top_indices:
            block_info = processed_blocks[idx]
            candidates.append({
                'text': block_info['original'].text,
                'normalized': block_info['normalized'],
                'bbox': block_info['bbox'],
                'score': float(combined_scores[idx]),
                'method': 'semantic',
                'similarity': float(similarities[idx])
            })
        
        return candidates
    
    def _deduplicate_candidates(self, candidates: List[Dict]) -> List[Dict]:
        """Remove duplicate candidates, keeping the highest scoring one"""
        seen = {}
        for candidate in candidates:
            key = candidate['normalized']
            if key not in seen or candidate['score'] > seen[key]['score']:
                seen[key] = candidate
        return list(seen.values())


