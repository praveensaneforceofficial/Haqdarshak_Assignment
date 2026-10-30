"""
Concrete Extractor implementations adhering to ISchemeExtractor (SOLID Principles: SRP, OCP, LSP).
Includes both OpenAI LLM Extractor and Deterministic Rule-Based Extractor.
"""

import os
import re
import json
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List
from openai import OpenAI
from src.interfaces import ISchemeExtractor
from src.schemas import SchemeFieldRecord, EvidenceItem

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

class RuleBasedSchemeExtractor(ISchemeExtractor):
    """
    Deterministic rule-based extractor for offline execution, baseline benchmarks,
    and fast reliable parsing across multilingual circulars.
    """

    def __init__(self, capture_date: Optional[str] = None):
        self.capture_date = capture_date or datetime.now().strftime("%Y-%m-%d")

    def _find_exact_quote(self, text: str, pattern: str) -> Optional[Tuple[str, str, str]]:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if not match:
            return None
        
        start, end = match.span()
        line_start = text.rfind("\n", 0, start)
        line_start = 0 if line_start == -1 else line_start + 1
        line_end = text.find("\n", end)
        line_end = len(text) if line_end == -1 else line_end
        
        quote = text[line_start:line_end].strip()
        matched_val = match.group(1) if match.groups() else match.group(0).strip()
        
        preceding_text = text[:start]
        section_matches = list(re.finditer(r"(?:^|\n)(?:(\d+\.?[^\n]*)|(SUBJECT:[^\n]*)|(विषय:[^\n]*))", preceding_text, re.IGNORECASE))
        location = section_matches[-1].group(0).strip() if section_matches else "Header / Overview"
        
        return matched_val, quote, location

    def extract(self, text: str, source_ref: str, scheme_id: Optional[str] = None) -> Dict[str, SchemeFieldRecord]:
        records: Dict[str, SchemeFieldRecord] = {}
        scheme_ref = scheme_id or source_ref

        # 1. Scheme Name
        name_patterns = [
            r'NAEM OF SCHEME\s*[:]\s*([^\n]+)',
            r'Scheme Title\s*[:]\s*([^\n]+)',
            r'(?:योजना का नाम|विषय)\s*[:]\s*["“\']?([^"”\'\n]+)["”\']?',
            r'(?:Operational Guidelines for|IMPLEMENTAT1ON OF|IMPLEMENTATION OF)\s*["“\']([^"”\']+)["”\']'
        ]
        for pat in name_patterns:
            res = self._find_exact_quote(text, pat)
            if res:
                val, quote, loc = res
                clean_name = val.strip().replace("“", "").replace("”", "").replace('"', "")
                records["scheme_name"] = SchemeFieldRecord(
                    scheme_ref=scheme_ref,
                    field="scheme_name",
                    value=clean_name,
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
                note="Scheme title could not be resolved from source text."
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
                note="Department name not found."
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
                note="Benefit type could not be classified."
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
                note="Application procedure not found."
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
                note="No explicit deadline stated."
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
                note="No official website link declared."
            )

        return records


class OpenAISchemeExtractor(ISchemeExtractor):
    """
    LLM-powered Scheme Extractor utilizing OpenAI GPT-4o-mini with structured output
    and strict grounding requirements (Haqdarshak Principle: Evidence citation).
    """

    def __init__(self, api_key: str, model_name: str = "gpt-4o-mini", capture_date: Optional[str] = None):
        self.client = OpenAI(api_key=api_key)
        self.model_name = model_name
        self.capture_date = capture_date or datetime.now().strftime("%Y-%m-%d")

    def extract(self, text: str, source_ref: str, scheme_id: Optional[str] = None) -> Dict[str, SchemeFieldRecord]:
        scheme_ref = scheme_id or source_ref

        system_prompt = """
You are an expert AI Scheme Research Analyst for Haqdarshak.
Your task is to extract structured facts about government welfare schemes from government circulars, notifications, and portal snippets.

CRITICAL PRINCIPLES:
1. Every fact MUST point back to its source: provide the EXACT verbatim quote from the text and the section/page location.
2. If you cannot find a field in the text, leave value as null and set status to "not_found" with a short note explaining why. DO NOT GUESS OR HALLUCINATE.
3. Extract these fields:
- scheme_name
- department
- benefit_type (e.g. Direct Cash, Scholarship, Social Security Pension, Subsidy)
- benefit_amount (e.g. Rs. 1,500 per month)
- benefit_frequency (e.g. Monthly, Quarterly, Annual, One-time)
- eligibility_conditions (array of strings)
- documents_required (array of strings)
- how_to_apply (string summary of procedure)
- deadline (date string or 'Open throughout the year' / 'Rolling')
- official_link (url string or null)

Output MUST be a valid JSON object where keys are the field names, and values are objects with:
{
  "value": string | array | null,
  "status": "found" | "not_found",
  "confidence": "high" | "medium" | "low",
  "note": string | null,
  "evidence": {
    "exact_text": "verbatim quote from source text",
    "location": "section heading or page"
  }
}
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Document Source Reference: {source_ref}\n\nDocument Text:\n{text}"}
                ],
                temperature=0.0
            )

            raw_json = response.choices[0].message.content
            parsed = json.loads(raw_json)

            records: Dict[str, SchemeFieldRecord] = {}
            for field in TARGET_FIELDS:
                item = parsed.get(field, {})
                ev_data = item.get("evidence")
                evidence_obj = None
                if ev_data and ev_data.get("exact_text"):
                    evidence_obj = EvidenceItem(
                        exact_text=ev_data.get("exact_text"),
                        location=ev_data.get("location", "Body"),
                        source_ref=source_ref,
                        capture_date=self.capture_date
                    )
                
                records[field] = SchemeFieldRecord(
                    scheme_ref=scheme_ref,
                    field=field,
                    value=item.get("value"),
                    evidence=evidence_obj,
                    confidence=item.get("confidence", "high"),
                    status=item.get("status", "found" if item.get("value") else "not_found"),
                    note=item.get("note")
                )

            return records

        except Exception as e:
            # Fallback to rule-based extractor if API call fails
            print(f"[Warning] OpenAI Extraction failed: {e}. Falling back to RuleBasedSchemeExtractor.")
            fallback = RuleBasedSchemeExtractor(capture_date=self.capture_date)
            return fallback.extract(text, source_ref, scheme_id)
