"""Text preprocessing: normalization, tokenization, block grouping, hashing"""
import re
import hashlib
from typing import List, Dict, Tuple
from collections import defaultdict
from .text_extractor import TextBlock


class Preprocessor:
    """Preprocesses text blocks for extraction"""
    
    def __init__(self):
        self.normalization_patterns = [
            (r'\s+', ' '),  # Multiple spaces to single space
            (r'[^\w\s\.\-\/\(\)]', ''),  # Remove special chars (keep basic punctuation)
        ]
    
    def normalize_text(self, text: str) -> str:
        """Normalize text by removing special chars and standardizing whitespace"""
        normalized = text.strip()
        for pattern, replacement in self.normalization_patterns:
            normalized = re.sub(pattern, replacement, normalized)
        return normalized.lower()
    
    def tokenize(self, text: str) -> List[str]:
        """Simple tokenization by whitespace"""
        normalized = self.normalize_text(text)
        return [token for token in normalized.split() if token]
    
    def group_blocks(self, blocks: List[TextBlock], 
                    max_distance: float = 20.0) -> List[List[TextBlock]]:
        """
        Group text blocks that are close together (likely part of same line/field)
        
        Args:
            blocks: List of text blocks
            max_distance: Maximum distance in pixels to consider blocks as grouped
            
        Returns:
            List of block groups
        """
        if not blocks:
            return []
        
        # Sort blocks by vertical position (top to bottom)
        sorted_blocks = sorted(blocks, key=lambda b: (b.bbox[1], b.bbox[0]))
        
        groups = []
        current_group = [sorted_blocks[0]]
        
        for block in sorted_blocks[1:]:
            # Check if block is on same line as last block in current group
            last_block = current_group[-1]
            
            # Calculate vertical distance
            vertical_dist = abs(block.bbox[1] - last_block.bbox[1])
            
            # Calculate horizontal distance (if on same line)
            if vertical_dist < max_distance:
                horizontal_dist = block.bbox[0] - last_block.bbox[2]
                if horizontal_dist < max_distance * 2:  # Same line
                    current_group.append(block)
                    continue
            
            # New group
            groups.append(current_group)
            current_group = [block]
        
        groups.append(current_group)
        return groups
    
    def create_block_hash(self, block: TextBlock) -> str:
        """Create a hash for a text block (for caching/deduplication)"""
        content = f"{block.text}_{block.bbox}_{block.font}_{block.size}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def extract_features(self, blocks: List[TextBlock]) -> Dict:
        """
        Extract features from blocks for matching
        
        Returns:
            Dictionary with processed text, tokens, groups, and hashes
        """
        # Normalize and tokenize all blocks
        processed_blocks = []
        for block in blocks:
            normalized = self.normalize_text(block.text)
            tokens = self.tokenize(block.text)
            block_hash = self.create_block_hash(block)
            
            processed_blocks.append({
                'original': block,
                'normalized': normalized,
                'tokens': tokens,
                'hash': block_hash,
                'bbox': block.bbox,
                'font': block.font,
                'size': block.size
            })
        
        # Group blocks
        groups = self.group_blocks(blocks)
        group_texts = [' '.join([b.text for b in group]) for group in groups]
        
        return {
            'processed_blocks': processed_blocks,
            'groups': groups,
            'group_texts': group_texts,
            'full_text': ' '.join([b.text for b in blocks]),
            'normalized_full_text': self.normalize_text(' '.join([b.text for b in blocks]))
        }


