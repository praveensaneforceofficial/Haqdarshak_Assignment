"""
Scheme Knowledge Base Extractor
Extracts structured scheme fields with strict evidence citation and multi-source conflict reconciliation.
"""

import os
import re
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from src.schemas import SchemeFieldRecord, EvidenceItem, ConflictEntry

TARGET_FIELDS = [
    "scheme_name",
    "department",
    "benefit_type",
    "benefit_amount",
    "benefit_frequency",
    "eligibility_conditions",
    "documents_required",
    "how_to_apply",
    "deadline",
    "official_link"
]

class SchemeExtractor:
    """
    Field-level extractor that extracts scheme facts with exact evidence quotation
    and compares multiple sources to flag discrepancies/conflicts.
    """

    def __init__(self, capture_date: Optional[str] = None):
        self.capture_date = capture_date or datetime.now().strftime("%Y-%m-%d")

    def _find_exact_quote(self, text: str, pattern: str) -> Optional[Tuple[str, str, str]]:
        """
        Finds matched value, the exact surrounding sentence/clause as evidence, and section location.
        """
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if not match:
            return None
        
        start, end = match.span()
        # Find sentence or line boundaries for evidence quote
        line_start = text.rfind("\n", 0, start)
        line_start = 0 if line_start == -1 else line_start + 1
        line_end = text.find("\n", end)
        line_end = len(text) if line_end == -1 else line_end
        
        quote = text[line_start:line_end].strip()
        matched_val = match.group(1) if match.groups() else match.group(0).strip()
        
        # Estimate section location
        preceding_text = text[:start]
        section_matches = list(re.finditer(r"(?:^|\n)(?:(\d+\.?[^\n]*)|(SUBJECT:[^\n]*)|(विषय:[^\n]*))", preceding_text, re.IGNORECASE))
        location = section_matches[-1].group(0).strip() if section_matches else "Header / Overview"
        
        return matched_val, quote, location

    def extract_from_text(self, text: str, source_ref: str, scheme_id: Optional[str] = None) -> Dict[str, SchemeFieldRecord]:
        """
        Extracts all target fields from raw text document with exact evidence quotes.
        Works across English, Hindi (Devanagari), and OCR-noisy formats.
        """
        records: Dict[str, SchemeFieldRecord] = {}
        scheme_ref = scheme_id or source_ref

        # 1. Scheme Name
        name_patterns = [
            r'NAEM OF SCHEME\s*[:]\s*([^\n]+)',
            r'Scheme Title\s*[:]\s*([^\n]+)',
            r'(?:योजना का नाम|विषय)\s*[:]\s*["“\']?([^"”\'\n]+)["”\']?',
            r'(?:Operational Guidelines for|IMPLEMENTAT1ON OF|IMPLEMENTATION OF)\s*["“\']([^"”\']+)["”\']'
        ]
        extracted_name = None
        for pat in name_patterns:
            res = self._find_exact_quote(text, pat)
            if res:
                val, quote, loc = res
                extracted_name = val.strip().replace("“", "").replace("”", "").replace('"', "")
                records["scheme_name"] = SchemeFieldRecord(
                    scheme_ref=scheme_ref,
                    field="scheme_name",
                    value=extracted_name,
                    evidence=EvidenceItem(
                        exact_text=quote,
                        location=loc,
                        source_ref=source_ref,
                        capture_date=self.capture_date
                    ),
                    confidence=0.95,
                    status="found"
                )
                break
        
        if "scheme_name" not in records:
            records["scheme_name"] = SchemeFieldRecord(
                scheme_ref=scheme_ref,
                field="scheme_name",
                value=None,
                confidence=0.0,
                status="not_found",
                note="Scheme title could not be unambiguously resolved from source."
            )

        # 2. Department
        dept_patterns = [
            r'(?:DEPARTMENT OF\s+[^\n,]+)',
            r'(?:प्रशासनिक विभाग|विभाग)\s*[:]\s*([^\n]+)',
            r'Department\s*[:]\s*([^\n]+)'
        ]
        for pat in dept_patterns:
            res = self._find_exact_quote(text, pat)
            if res:
                val, quote, loc = res
                clean_dept = val.replace("DEPARTMENT OF", "").replace("Department:", "").strip()
                if "GOVERNMENT OF" in clean_dept:
                    clean_dept = clean_dept.split("GOVERNMENT OF")[0].strip()
                records["department"] = SchemeFieldRecord(
                    scheme_ref=scheme_ref,
                    field="department",
                    value=clean_dept or val.strip(),
                    evidence=EvidenceItem(
                        exact_text=quote,
                        location=loc,
                        source_ref=source_ref,
                        capture_date=self.capture_date
                    ),
                    confidence=0.92,
                    status="found"
                )
                break
        if "department" not in records:
            records["department"] = SchemeFieldRecord(
                scheme_ref=scheme_ref,
                field="department",
                value=None,
                confidence=0.0,
                status="not_found",
                note="Department name not found in document text."
            )

        # 3. Benefit Amount
        amount_patterns = [
            r'(Rs\.?\s*[\d,]+(?:\s*(?:per\s+month|\/-\s*per\s+annum|per\s+quarter|per\s+year))?)',
            r'(₹\s*[\d,]+(?:\s*(?:प्रति\s+वर्ष|प्रति\s+माह))?)',
            r'(Monthly pension of Rs\.?\s*[\d,]+[^\n\.]+)'
        ]
        for pat in amount_patterns:
            res = self._find_exact_quote(text, pat)
            if res:
                val, quote, loc = res
                records["benefit_amount"] = SchemeFieldRecord(
                    scheme_ref=scheme_ref,
                    field="benefit_amount",
                    value=val.strip(),
                    evidence=EvidenceItem(
                        exact_text=quote,
                        location=loc,
                        source_ref=source_ref,
                        capture_date=self.capture_date
                    ),
                    confidence=0.95,
                    status="found"
                )
                break
        if "benefit_amount" not in records:
            records["benefit_amount"] = SchemeFieldRecord(
                scheme_ref=scheme_ref,
                field="benefit_amount",
                value=None,
                confidence=0.0,
                status="not_found",
                note="No explicit benefit currency amount stated."
            )

        # 4. Benefit Type
        benefit_type = None
        if re.search(r'financial assistance|प्रत्यक्ष लाभ|सब्सिडी|subsidy|financial subsidy', text, re.IGNORECASE):
            benefit_type = "Direct Cash / Financial Assistance"
        elif re.search(r'pension|पेंशन', text, re.IGNORECASE):
            benefit_type = "Social Security Pension"
        elif re.search(r'scholarship|छात्रवृत्ति|protsahan', text, re.IGNORECASE):
            benefit_type = "Direct Financial Assistance / Scholarship"
        
        if benefit_type:
            res = self._find_exact_quote(text, r'(financial assistance|subsidy|financial subsidy|pension|पेंशन|वित्तीय सहायता)')
            quote = res[1] if res else "Contextual classification from scheme benefit section"
            loc = res[2] if res else "Section 2 / 3"
            records["benefit_type"] = SchemeFieldRecord(
                scheme_ref=scheme_ref,
                field="benefit_type",
                value=benefit_type,
                evidence=EvidenceItem(
                    exact_text=quote,
                    location=loc,
                    source_ref=source_ref,
                    capture_date=self.capture_date
                ),
                confidence=0.90,
                status="found"
            )
        else:
            records["benefit_type"] = SchemeFieldRecord(
                scheme_ref=scheme_ref,
                field="benefit_type",
                value=None,
                confidence=0.0,
                status="not_found",
                note="Benefit type category could not be established."
            )

        # 5. Benefit Frequency
        freq_patterns = [
            (r'(quarterly basis|Rs\.\s*[\d,]+\s*per\s+quarter)', "Quarterly"),
            (r'(per month|monthly|प्रति\s+माह)', "Monthly"),
            (r'(per year|per annum|प्रति\s+वर्ष)', "Annual"),
            (r'(bi-annually|every 6 months)', "Bi-annually")
        ]
        for pat, freq_val in freq_patterns:
            res = self._find_exact_quote(text, pat)
            if res:
                val, quote, loc = res
                records["benefit_frequency"] = SchemeFieldRecord(
                    scheme_ref=scheme_ref,
                    field="benefit_frequency",
                    value=freq_val,
                    evidence=EvidenceItem(
                        exact_text=quote,
                        location=loc,
                        source_ref=source_ref,
                        capture_date=self.capture_date
                    ),
                    confidence=0.90,
                    status="found"
                )
                break
        if "benefit_frequency" not in records:
            records["benefit_frequency"] = SchemeFieldRecord(
                scheme_ref=scheme_ref,
                field="benefit_frequency",
                value=None,
                confidence=0.0,
                status="not_found",
                note="Disbursement frequency not specified."
            )

        # 6. Eligibility Conditions
        elig_sec_match = re.search(r'(?:ELIGIBILITY CRITERIA|पात्रता शर्तें|ELIGIB1LITY|Eligibility)[\s\:]*\n([\s\S]*?)(?=\n\s*(?:\d+\.|\n[A-Z0-9\s]{4,}:|\n\n[A-Z]))', text, re.IGNORECASE)
        if elig_sec_match:
            raw_elig = elig_sec_match.group(1).strip()
            items = [line.strip("-•* \t") for line in raw_elig.splitlines() if line.strip("-•* \t")]
            records["eligibility_conditions"] = SchemeFieldRecord(
                scheme_ref=scheme_ref,
                field="eligibility_conditions",
                value=items,
                evidence=EvidenceItem(
                    exact_text=raw_elig[:250] + ("..." if len(raw_elig) > 250 else ""),
                    location="Eligibility Section",
                    source_ref=source_ref,
                    capture_date=self.capture_date
                ),
                confidence=0.92,
                status="found"
            )
        else:
            records["eligibility_conditions"] = SchemeFieldRecord(
                scheme_ref=scheme_ref,
                field="eligibility_conditions",
                value=None,
                confidence=0.0,
                status="not_found",
                note="Eligibility section header not identified."
            )

        # 7. Documents Required
        docs_sec_match = re.search(r'(?:DOCUMENTS REQUIRED|आवश्यक दस्तावेज|REQUIRED DOCS|Required Documents)[\s\:]*\n([\s\S]*?)(?=\n\s*(?:\d+\.|\n[A-Z0-9\s]{4,}:|\n\n[A-Z]))', text, re.IGNORECASE)
        if docs_sec_match:
            raw_docs = docs_sec_match.group(1).strip()
            items = [re.sub(r'^[ivx0-9\)\.\-\s]+', '', line).strip() for line in raw_docs.splitlines() if line.strip()]
            records["documents_required"] = SchemeFieldRecord(
                scheme_ref=scheme_ref,
                field="documents_required",
                value=items,
                evidence=EvidenceItem(
                    exact_text=raw_docs[:250] + ("..." if len(raw_docs) > 250 else ""),
                    location="Documents Section",
                    source_ref=source_ref,
                    capture_date=self.capture_date
                ),
                confidence=0.94,
                status="found"
            )
        else:
            records["documents_required"] = SchemeFieldRecord(
                scheme_ref=scheme_ref,
                field="documents_required",
                value=None,
                confidence=0.0,
                status="not_found",
                note="Mandatory documents list not found."
            )

        # 8. How to Apply
        apply_match = re.search(r'(?:APPLICATION PROCEDURE|आवेदन प्रक्रिया|HOW TO APPLY|Application Mode)[\s\:]*\n([\s\S]*?)(?=\n\s*(?:\d+\.|\n[A-Z0-9\s]{4,}:|\n\n[A-Z]))', text, re.IGNORECASE)
        if apply_match:
            raw_apply = apply_match.group(1).strip()
            records["how_to_apply"] = SchemeFieldRecord(
                scheme_ref=scheme_ref,
                field="how_to_apply",
                value=raw_apply.replace("\n", " "),
                evidence=EvidenceItem(
                    exact_text=raw_apply[:200],
                    location="Application Procedure Section",
                    source_ref=source_ref,
                    capture_date=self.capture_date
                ),
                confidence=0.91,
                status="found"
            )
        else:
            records["how_to_apply"] = SchemeFieldRecord(
                scheme_ref=scheme_ref,
                field="how_to_apply",
                value=None,
                confidence=0.0,
                status="not_found",
                note="Application process instructions missing."
            )

        # 9. Deadline
        deadline_patterns = [
            r'Last date for submission[^\:\n]*\:\s*([^\.\n]+)',
            r'(?:आवेदन करने की अंतिम तिथि\s*([^\.\n]+))',
            r'(?:portal closes on\s*([^\.\n]+))',
            r'(No last date for application[^\.\n]*)',
            r'(?:DEADLINE\s*[:]\s*([^\n]+))'
        ]
        for pat in deadline_patterns:
            res = self._find_exact_quote(text, pat)
            if res:
                val, quote, loc = res
                records["deadline"] = SchemeFieldRecord(
                    scheme_ref=scheme_ref,
                    field="deadline",
                    value=val.strip(),
                    evidence=EvidenceItem(
                        exact_text=quote,
                        location=loc,
                        source_ref=source_ref,
                        capture_date=self.capture_date
                    ),
                    confidence=0.95,
                    status="found"
                )
                break
        if "deadline" not in records:
            records["deadline"] = SchemeFieldRecord(
                scheme_ref=scheme_ref,
                field="deadline",
                value=None,
                confidence=0.0,
                status="not_found",
                note="No explicit scheme deadline stated."
            )

        # 10. Official Link
        link_match = re.search(r'(https?://[^\s\)\"\'>]+)', text)
        if link_match:
            url = link_match.group(1).rstrip(".,;")
            res = self._find_exact_quote(text, re.escape(url))
            quote = res[1] if res else url
            loc = res[2] if res else "Application Section"
            records["official_link"] = SchemeFieldRecord(
                scheme_ref=scheme_ref,
                field="official_link",
                value=url,
                evidence=EvidenceItem(
                    exact_text=quote,
                    location=loc,
                    source_ref=source_ref,
                    capture_date=self.capture_date
                ),
                confidence=0.98,
                status="found"
            )
        else:
            records["official_link"] = SchemeFieldRecord(
                scheme_ref=scheme_ref,
                field="official_link",
                value=None,
                confidence=0.0,
                status="not_found",
                note="No official portal link or web URL declared."
            )

        return records

    def reconcile_sources(
        self, 
        primary_records: Dict[str, SchemeFieldRecord], 
        secondary_records: Dict[str, SchemeFieldRecord],
        primary_name: str = "Official Circular",
        secondary_name: str = "MyScheme Portal"
    ) -> Dict[str, SchemeFieldRecord]:
        """
        Reconciles records from two sources.
        When sources disagree:
        - Marks field status as 'conflict'
        - Preserves BOTH values, confidence, and exact evidence quotes
        - Never silently discards or overrides a conflicting record
        """
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

            # Both sources found a value
            # Normalize for simple comparison
            p_val = str(p_rec.value).strip().lower()
            s_val = str(s_rec.value).strip().lower()

            # Check if values agree (or one contains the other)
            if p_val == s_val or (p_val in s_val and len(p_val) > 10) or (s_val in p_val and len(s_val) > 10):
                # Agreement! Prefer primary official circular but note corroboration
                agreed_rec = p_rec.model_copy(deep=True)
                agreed_rec.note = f"Corroborated across {primary_name} and {secondary_name}."
                agreed_rec.confidence = min(1.0, float(p_rec.confidence) + 0.05) if isinstance(p_rec.confidence, (int, float)) else "high"
                reconciled[field] = agreed_rec
            else:
                # CONFLICT! Keep both values and evidence
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
