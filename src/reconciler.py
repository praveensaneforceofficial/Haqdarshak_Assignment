"""
Source Reconciler implementing IReconciler (Single Responsibility Principle).
Reconciles records across multiple documents, detects conflicts, and preserves both claims.
"""

from typing import Dict, Any, List
from src.interfaces import IReconciler
from src.schemas import SchemeFieldRecord, ConflictEntry

class SchemeReconciler(IReconciler):
    """
    Compares two source extractions. 
    Under Haqdarshak's policy: Never quietly overwrite conflicting records.
    """

    def reconcile(
        self,
        primary_records: Dict[str, SchemeFieldRecord],
        secondary_records: Dict[str, SchemeFieldRecord],
        primary_name: str = "Official Circular",
        secondary_name: str = "MyScheme Portal"
    ) -> Dict[str, SchemeFieldRecord]:
        reconciled: Dict[str, SchemeFieldRecord] = {}
        all_fields = set(primary_records.keys()).union(set(secondary_records.keys()))

        for field in all_fields:
            p_rec = primary_records.get(field)
            s_rec = secondary_records.get(field)

            # If only one source has it
            if not p_rec or p_rec.status == "not_found":
                if s_rec and s_rec.status == "found":
                    reconciled[field] = s_rec
                else:
                    reconciled[field] = p_rec or s_rec
                continue

            if not s_rec or s_rec.status == "not_found":
                reconciled[field] = p_rec
                continue

            # Both sources found a value: normalize and compare
            p_val = str(p_rec.value).strip().lower()
            s_val = str(s_rec.value).strip().lower()

            # Agreement condition
            is_agreed = (
                p_val == s_val or
                (p_val in s_val and len(p_val) > 10) or
                (s_val in p_val and len(s_val) > 10)
            )

            if is_agreed:
                agreed_rec = p_rec.model_copy(deep=True)
                agreed_rec.note = f"Corroborated across {primary_name} and {secondary_name}."
                agreed_rec.confidence = min(1.0, float(p_rec.confidence) + 0.05) if isinstance(p_rec.confidence, (int, float)) else "high"
                reconciled[field] = agreed_rec
            else:
                # Discrepancy detected: Keep both values and evidence
                conflict_record = SchemeFieldRecord(
                    scheme_ref=p_rec.scheme_ref,
                    field=field,
                    value=f"CONFLICT: {primary_name} ['{p_rec.value}'] vs {secondary_name} ['{s_rec.value}']",
                    status="conflict",
                    confidence="medium",
                    note=f"Discrepancy detected between {primary_name} and {secondary_name}. Both retained for human reviewer decision.",
                    conflicts=[
                        ConflictEntry(
                            value=p_rec.value,
                            evidence=p_rec.evidence,
                            confidence=p_rec.confidence,
                            source_name=primary_name
                        ),
                        ConflictEntry(
                            value=s_rec.value,
                            evidence=s_rec.evidence,
                            confidence=s_rec.confidence,
                            source_name=secondary_name
                        )
                    ]
                )
                reconciled[field] = conflict_record

        return reconciled
