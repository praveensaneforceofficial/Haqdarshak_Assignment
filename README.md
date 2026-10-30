# Haqdarshak Scheme Knowledge Base: AI-Assisted Extraction & Evidence Verification Pipeline

This repository implements **Problem Option A1: Field Extraction with Evidence** for Haqdarshak's Scheme Knowledge Base.

---

## 1. Problem Statement Summary

Haqdarshak empowers last-mile community agents (Haqdarshaks) to connect eligible citizens across India to ~5,000 welfare schemes. Maintaining accurate eligibility criteria, benefit amounts, required documents, and deadlines is mission-critical: a single erroneous deadline or benefit figure directly harms a vulnerable family.

Today, research teams manually scan government circulars, PDF gazettes, and portal updates. This is slow, lacks clear data provenance, and risks discrepancies reaching field agents. 

### The Solution:
An AI-assisted first-pass extraction pipeline grounded in **two non-negotiable principles**:
1. **Human-in-the-Loop:** AI creates a verifiable draft; no scheme goes live without human approval.
2. **Strict Provenance & Zero Silent Assumptions:** Every extracted value is tied to an exact textual quote, source location (page/section), and capture date. If information is missing or disputed across sources (e.g. state circular vs. MyScheme portal), the system flags a **conflict**, retains all values, and presents them to the reviewer.

---

## 2. Repository Structure

```
.
├── data/
│   ├── doc_1_english_circular.txt        # MP State Gov circular (English)
│   ├── doc_2_hindi_circular.txt          # UP Agriculture Dept order (Hindi - Devanagari)
│   ├── doc_3_myscheme_portal_conflict.txt # Contradicting MyScheme portal listing
│   ├── doc_4_scanned_noisy_ocr.txt       # Rajasthan Pension scan with OCR noise
│   ├── ground_truth.json                 # Hand-curated ground truth benchmark
│   └── evaluation_report.json            # Generated benchmark evaluation metrics
├── src/
│   ├── schemas.py                        # Pydantic schemas adhering to Haqdarshak spec
│   ├── extractor.py                      # Multilingual extraction & conflict reconciliation engine
│   └── evaluate.py                       # Automated field-level accuracy & provenance evaluator
├── main.py                               # End-to-end execution script
├── WALKTHROUGH.md                        # Script & answers for the 10-minute presentation
└── README.md
```

---

## 3. How to Run

### Requirements
- Python 3.9+
- `pydantic`

### Installation
```bash
pip install pydantic
```

### Execution
Run the end-to-end pipeline demonstration:
```bash
python main.py
```

This runs extraction across all synthetic documents (English, Hindi, and OCR noisy scans), performs multi-source conflict reconciliation between the state circular and the MyScheme portal, saves structured JSON outputs with evidence to `output_records.json`, and outputs the field-level evaluation benchmark.

To run evaluation only:
```bash
python -m src.evaluate
```

---

## 4. Haqdarshak Field Specification & Schema

Every extracted field conforms strictly to the schema required in the brief:

```json
{
  "scheme_ref": "SCHEME-MP-001",
  "field": "benefit_amount",
  "value": "Rs. 1,500 per month",
  "evidence": {
    "exact_text": "Eligible girl students enrolled in higher secondary education shall receive direct financial assistance of Rs. 1,500 per month.",
    "location": "2. FINANCIAL BENEFIT:",
    "source_ref": "doc_1_english_circular.txt",
    "capture_date": "2026-10-30"
  },
  "confidence": 0.95,
  "status": "found",
  "note": null
}
```

### Conflict Representation (Preserving Disagreeing Sources):
When sources contradict each other (e.g., MP Official Circular says Rs. 1,500/month; MyScheme says Rs. 1,250/month), the system **never silently overwrites**:

```json
{
  "scheme_ref": "SCHEME-MP-001",
  "field": "benefit_amount",
  "value": "CONFLICT: Official MP WCD Circular ['Rs. 1,500 per month'] vs MyScheme National Portal ['Rs. 1,250 per month']",
  "status": "conflict",
  "confidence": "medium",
  "note": "Discrepancy detected between Official MP WCD Circular and MyScheme National Portal. Both retained for human reviewer decision.",
  "conflicts": [
    {
      "source_name": "Official MP WCD Circular",
      "value": "Rs. 1,500 per month",
      "evidence": {
        "exact_text": "...shall receive direct financial assistance of Rs. 1,500 per month...",
        "location": "2. FINANCIAL BENEFIT:",
        "source_ref": "doc_1_english_circular.txt",
        "capture_date": "2026-10-30"
      },
      "confidence": 0.95
    },
    {
      "source_name": "MyScheme National Portal",
      "value": "Rs. 1,250 per month",
      "evidence": {
        "exact_text": "- Financial subsidy of Rs. 1,250 per month disbursed bi-annually...",
        "location": "Header / Overview",
        "source_ref": "doc_3_myscheme_portal_conflict.txt",
        "capture_date": "2026-10-30"
      },
      "confidence": 0.95
    }
  ]
}
```

---

## 5. Evaluation & Quality Gate Proposal

Running the benchmark on synthetic test sets produces the following field-level evaluation:

```
================================================================================
HAQDARSHAK SCHEME KNOWLEDGE BASE - EVALUATION METRICS REPORT
================================================================================
Overall Field-Level Accuracy:        95.0%
Evidence Grounding / Provenance:     100.0% (Quotes verified in source)
Conflict Detection Recall:           100.0%
Conflicting Fields Caught:           department, benefit_frequency, documents_required, eligibility_conditions, official_link, benefit_amount, deadline
--------------------------------------------------------------------------------
FIELD NAME                   | ACCURACY (%)    | GATE STATUS
--------------------------------------------------------------------------------
scheme_name                  |        90.0%   | PASS [Ready]
department                   |        95.0%   | PASS [Ready]
benefit_type                 |       100.0%   | PASS [Ready]
benefit_amount               |        95.0%   | PASS [Ready]
benefit_frequency            |       100.0%   | PASS [Ready]
eligibility_conditions       |       100.0%   | PASS [Ready]
documents_required           |        75.0%   | REVIEW NEEDED
how_to_apply                 |       100.0%   | PASS [Ready]
deadline                     |        95.0%   | PASS [Ready]
official_link                |       100.0%   | PASS [Ready]
================================================================================
```

### Recommended Decision Gate (Before running on 5,000 schemes):
1. **Tier-1 Critical Fields (Gate: >= 98% Accuracy, 100% Provenance):**
   - `benefit_amount`, `eligibility_conditions`, `deadline`, `documents_required`.
   - If any Tier-1 field fails exact citation matching, the entire record must require human intervention.
2. **Tier-2 Informational Fields (Gate: >= 90% Accuracy):**
   - `department`, `how_to_apply`, `official_link`.
3. **Golden Benchmark Gate:**
   - Run the pipeline on a representative stratification of 100 diverse schemes (20 central, 80 state schemes across 8 regional languages). Only proceed to full scale when the 100-scheme pilot achieves >95% field-level accuracy and 0 ungrounded hallucinations.

---

## 6. AI Model Choice & Cost Estimation

- **Primary Recommended Model:** `gemini-1.5-flash` or `gpt-4o-mini`
- **Average Token Budget per Scheme:**
  - Input: ~3,000 tokens (Government circular / notification text + system instructions + JSON schema)
  - Output: ~800 tokens (Structured field records with exact quotes)
- **Cost Analysis:**
  - Gemini 1.5 Flash: $0.075 per 1M input tokens, $0.30 per 1M output tokens
  - Cost per scheme: `(0.003 * 0.075) + (0.0008 * 0.30) ≈ $0.00047` (~ ₹0.04 INR per scheme).
  - Processing all 5,000 schemes costs: **~$2.35 USD (under ₹200 INR)**.
  - Adding multi-pass verification / re-ranking adds ~2x: **~$5.00 USD total**.
  - Extremely cost-effective for grassroots social impact.

---

## 7. Deliberate Trade-offs & What Was Left Out

1. **Complex Eligibility Rule Engine:** We extract eligibility criteria as structured bulleted conditions with source quotes, rather than compiling them into executable boolean logic trees (e.g. `(age >= 18 AND income <= 250000)`). Turning criteria into computable decision graphs requires a separate validation layer.
2. **Direct PDF OCR Layer:** We ingested pre-extracted and OCR-scanned text rather than bundling heavy native OCR engines (Tesseract/PaddleOCR) in this prototype to keep it lightweight and immediately runnable across environments.
3. **Automated Conflict Resolution:** We deliberately rejected building an AI heuristic that chooses which source is "right". When government documents and portals disagree, only a human researcher can determine whether the portal is outdated or an amendment was issued.
