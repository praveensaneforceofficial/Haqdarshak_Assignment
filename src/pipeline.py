"""
Scheme Extraction Pipeline Orchestrator (SOLID Principles: DIP & SRP).
Coordinates extraction, evidence verification, and multi-source conflict reconciliation.
"""

from typing import Dict, Any, Optional
from src.interfaces import ISchemeExtractor, IEvidenceVerifier, IReconciler
from src.schemas import SchemeFieldRecord

class SchemePipeline:
    """
    High-level orchestrator. Depends strictly on abstractions (interfaces),
    enabling full swappability of LLM extractors, verifiers, and reconcilers.
    """

    def __init__(
        self,
        extractor: ISchemeExtractor,
        verifier: IEvidenceVerifier,
        reconciler: IReconciler
    ):
        self.extractor = extractor
        self.verifier = verifier
        self.reconciler = reconciler

    def process_document(
        self,
        text: str,
        source_ref: str,
        scheme_id: Optional[str] = None
    ) -> Dict[str, SchemeFieldRecord]:
        """Extracts fields and verifies that each evidence citation is grounded in text."""
        records = self.extractor.extract(text, source_ref, scheme_id)

        # Verification step
        for field_name, record in records.items():
            if record.status == "found" and record.evidence:
                is_grounded = self.verifier.verify(record, text)
                if not is_grounded:
                    record.confidence = "low"
                    record.note = (record.note or "") + " [Warning: Citation could not be verified verbatim in source]"
        
        return records

    def process_and_reconcile(
        self,
        primary_text: str,
        primary_source_ref: str,
        secondary_text: str,
        secondary_source_ref: str,
        scheme_id: str,
        primary_name: str = "Official Circular",
        secondary_name: str = "MyScheme Portal"
    ) -> Dict[str, SchemeFieldRecord]:
        """Extracts from both sources and reconciles any discrepancies."""
        p_records = self.process_document(primary_text, primary_source_ref, scheme_id)
        s_records = self.process_document(secondary_text, secondary_source_ref, scheme_id)

        reconciled = self.reconciler.reconcile(
            primary_records=p_records,
            secondary_records=s_records,
            primary_name=primary_name,
            secondary_name=secondary_name
        )

        return reconciled
