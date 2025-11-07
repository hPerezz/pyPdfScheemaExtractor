"""Main extraction orchestrator"""
from typing import Dict
from .text_extractor import TextExtractor
from .preprocessor import Preprocessor
from .candidate_generator import CandidateGenerator
from .scorer_validator import ScorerValidator
from .decision_engine import DecisionEngine


class PDFExtractor:
    """Main orchestrator for PDF extraction"""
    
    def __init__(self):
        self.text_extractor = TextExtractor()
        self.preprocessor = Preprocessor()
        self.candidate_generator = CandidateGenerator()
        self.scorer_validator = ScorerValidator()
        self.decision_engine = DecisionEngine()
    
    def extract(self,
               label: str,
               extraction_schema: Dict[str, str],
               pdf_bytes: bytes) -> Dict[str, str]:
        """
        Main extraction method
        
        Args:
            label: Document label (type identifier)
            extraction_schema: Dictionary mapping field names to descriptions
            pdf_bytes: PDF file as bytes
            
        Returns:
            Dictionary mapping field names to extracted values
        """
        # 1. Extract text blocks
        text_blocks = self.text_extractor.extract(pdf_bytes)
        
        # 2. Preprocess
        processed_data = self.preprocessor.extract_features(text_blocks)
        processed_data['full_text'] = ' '.join([b.text for b in text_blocks])
        
        # 3. Generate candidates for each field
        candidates = self.candidate_generator.generate_candidates(
            processed_data, label, extraction_schema
        )
        
        # 4. Score and validate candidates
        field_results = {}
        for field_name, field_candidates in candidates.items():
            best_candidate = self.scorer_validator.select_best_candidate(
                field_candidates,
                field_name,
                extraction_schema[field_name],
                processed_data
            )
            field_results[field_name] = best_candidate
        
        # 5. Decision engine (accept/normalize/LLM)
        final_values = self.decision_engine.process_extraction(
            field_results, label, extraction_schema, processed_data
        )
        
        return final_values


