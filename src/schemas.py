"""
Schema definition matching Haqdarshak Scheme Knowledge Base requirements.
"""

from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field

class EvidenceItem(BaseModel):
    exact_text: str = Field(description="The exact text it came from in the source")
    location: str = Field(description="Where in the source (page or section)")
    source_ref: str = Field(description="Source link or document placeholder reference")
    capture_date: str = Field(description="Date the evidence was captured")

class ConflictEntry(BaseModel):
    value: Any
    evidence: EvidenceItem
    confidence: Union[float, str]
    source_name: str

class SchemeFieldRecord(BaseModel):
    scheme_ref: str = Field(description="Which scheme this belongs to (ID or source doc)")
    field: str = Field(description="The field name, e.g. benefit_amount, deadline")
    value: Optional[Any] = Field(default=None, description="The extracted value, or None if not found")
    evidence: Optional[EvidenceItem] = Field(default=None, description="Exact text quote and location")
    confidence: Union[float, str] = Field(default="high", description="0-1 or high/medium/low")
    status: str = Field(default="found", description="'found', 'not_found', or 'conflict'")
    note: Optional[str] = Field(default=None, description="Optional explanation or discrepancy details")
    conflicts: Optional[List[ConflictEntry]] = Field(
        default=None, 
        description="When status=='conflict', retains all disagreeing values and their sources"
    )

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(exclude_none=True)
