"""
Abstract interfaces defining the contracts for the Scheme Knowledge Base system (SOLID Principles: ISP & DIP).
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from src.schemas import SchemeFieldRecord

class ISchemeExtractor(ABC):
    """Interface Segregation: Single responsibility for extracting raw scheme fields from source."""
    
    @abstractmethod
    def extract(self, text: str, source_ref: str, scheme_id: Optional[str] = None) -> Dict[str, SchemeFieldRecord]:
        """Extracts target fields from raw document text."""
        pass

class IEvidenceVerifier(ABC):
    """Interface Segregation: Validates factual grounding of extracted evidence in source text."""
    
    @abstractmethod
    def verify(self, record: SchemeFieldRecord, source_text: str) -> bool:
        """Verifies whether the quote exists verbatim in the source text."""
        pass

class IReconciler(ABC):
    """Interface Segregation: Cross-references multiple sources and detects conflicts."""
    
    @abstractmethod
    def reconcile(
        self,
        primary_records: Dict[str, SchemeFieldRecord],
        secondary_records: Dict[str, SchemeFieldRecord],
        primary_name: str = "Official Circular",
        secondary_name: str = "MyScheme Portal"
    ) -> Dict[str, SchemeFieldRecord]:
        """Reconciles two record sets and flags conflicts while preserving both claims."""
        pass

class IEvaluator(ABC):
    """Interface Segregation: Computes benchmark metrics against ground truth."""
    
    @abstractmethod
    def evaluate(self, data_dir: str, ground_truth_file: str) -> Dict[str, Any]:
        """Calculates field-by-field accuracy and conflict recall."""
        pass
