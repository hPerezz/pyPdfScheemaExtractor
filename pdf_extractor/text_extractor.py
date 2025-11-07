"""Text extraction from PDF using PyMuPDF and pdfplumber"""
import fitz  # PyMuPDF
import pdfplumber
from typing import List, Dict, Tuple, Optional
import io


class TextBlock:
    """Represents a text block with its properties"""
    def __init__(self, text: str, bbox: Tuple[float, float, float, float], 
                 font: Optional[str] = None, size: Optional[float] = None):
        self.text = text
        self.bbox = bbox  # (x0, y0, x1, y1)
        self.font = font
        self.size = size
    
    def __repr__(self):
        return f"TextBlock(text='{self.text[:30]}...', bbox={self.bbox}, font={self.font}, size={self.size})"


class TextExtractor:
    """Extracts text blocks from PDF with metadata"""
    
    def __init__(self):
        self.use_pymupdf = True  # Prefer PyMuPDF for better performance
    
    def extract(self, pdf_bytes: bytes) -> List[TextBlock]:
        """
        Extract text blocks from PDF bytes
        
        Args:
            pdf_bytes: PDF file as bytes
            
        Returns:
            List of TextBlock objects
        """
        try:
            if self.use_pymupdf:
                return self._extract_pymupdf(pdf_bytes)
            else:
                return self._extract_pdfplumber(pdf_bytes)
        except Exception as e:
            # Fallback to pdfplumber if PyMuPDF fails
            if self.use_pymupdf:
                try:
                    return self._extract_pdfplumber(pdf_bytes)
                except Exception:
                    raise Exception(f"Failed to extract text from PDF: {e}")
            else:
                raise
    
    def _extract_pymupdf(self, pdf_bytes: bytes) -> List[TextBlock]:
        """Extract using PyMuPDF (fitz)"""
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        blocks = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            
            # Get text blocks with layout information
            text_dict = page.get_text("dict")
            
            for block in text_dict["blocks"]:
                if "lines" in block:  # Text block
                    for line in block["lines"]:
                        for span in line["spans"]:
                            text = span["text"].strip()
                            if text:
                                bbox = span["bbox"]  # (x0, y0, x1, y1)
                                font = span.get("font", None)
                                size = span.get("size", None)
                                
                                blocks.append(TextBlock(
                                    text=text,
                                    bbox=bbox,
                                    font=font,
                                    size=size
                                ))
        
        doc.close()
        return blocks
    
    def _extract_pdfplumber(self, pdf_bytes: bytes) -> List[TextBlock]:
        """Extract using pdfplumber (fallback)"""
        pdf_file = io.BytesIO(pdf_bytes)
        blocks = []
        
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                words = page.extract_words()
                
                for word in words:
                    text = word.get("text", "").strip()
                    if text:
                        bbox = (
                            word.get("x0", 0),
                            word.get("top", 0),
                            word.get("x1", 0),
                            word.get("bottom", 0)
                        )
                        blocks.append(TextBlock(
                            text=text,
                            bbox=bbox,
                            font=word.get("fontname"),
                            size=word.get("size")
                        ))
        
        return blocks


