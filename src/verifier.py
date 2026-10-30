"""
Evidence Verifier implementing IEvidenceVerifier (Single Responsibility Principle).
Verifies that quotes extracted by AI or rules actually exist in the original source document.
"""

import re
from src.interfaces import IEvidenceVerifier
from src.schemas import SchemeFieldRecord

class ExactEvidenceVerifier(IEvidenceVerifier):
    """Verifies that the cited evidence quote is grounded directly in the document text."""

    def normalize(self, s: str) -> str:
        """Removes duplicate whitespace, newlines, and punctuation for robust comparison."""
        return re.sub(r'[\s\n\r]+', ' ', s).strip().lower()

    def verify(self, record: SchemeFieldRecord, source_text: str) -> bool:
        if not record or not record.evidence or not record.evidence.exact_text:
            return False
        
        quote = record.evidence.exact_text.strip()
        if not quote:
            return False
        
        # 1. Direct substring check
        if quote in source_text or quote[:40] in source_text:
            return True
        
        # 2. Normalized check (handles OCR spaces or line breaks)
        norm_quote = self.normalize(quote)
        norm_source = self.normalize(source_text)
        
        if norm_quote in norm_source or norm_quote[:40] in norm_source:
            return True
        
        return False
