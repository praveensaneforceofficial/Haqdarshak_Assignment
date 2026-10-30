"""
Haqdarshak Scheme Knowledge Base - Main Pipeline Demo
Demonstrates:
1. Extraction across English, Hindi, and Scanned OCR government documents.
2. Exact source quotation and page/section location attribution.
3. Multi-source cross-referencing and conflict detection (preserving both values).
4. Automated field-level accuracy and provenance evaluation.
"""

import os
import sys
import json

# Ensure UTF-8 output on Windows console
if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from src.extractor import SchemeExtractor
from src.evaluate import evaluate_pipeline, print_evaluation_report

def run_demo():
    print("\n" + "=" * 80)
    print(" HAQDARSHAK SCHEME KNOWLEDGE BASE - AI EXTRACTION PIPELINE")
    print("=" * 80)

    extractor = SchemeExtractor()
    data_dir = "data"

    # 1. English Circular Extraction
    print("\n[1/4] Processing Document 1: English Government Circular (Madhya Pradesh)...")
    with open(os.path.join(data_dir, "doc_1_english_circular.txt"), "r", encoding="utf-8") as f:
        doc1_text = f.read()
    rec1 = extractor.extract_from_text(doc1_text, "doc_1_english_circular.txt", scheme_id="SCHEME-MP-001")
    print(f"Extracted Scheme: '{rec1['scheme_name'].value}'")
    print(f"Benefit: {rec1['benefit_amount'].value} ({rec1['benefit_frequency'].value})")
    print(f"Evidence: \"{rec1['benefit_amount'].evidence.exact_text}\" -> Location: {rec1['benefit_amount'].evidence.location}")

    # 2. Hindi Circular Extraction
    print("\n[2/4] Processing Document 2: Hindi Government Resolution (Uttar Pradesh)...")
    with open(os.path.join(data_dir, "doc_2_hindi_circular.txt"), "r", encoding="utf-8") as f:
        doc2_text = f.read()
    rec2 = extractor.extract_from_text(doc2_text, "doc_2_hindi_circular.txt", scheme_id="SCHEME-UP-002")
    print(f"Extracted Scheme (Hindi): '{rec2['scheme_name'].value}'")
    print(f"Benefit: {rec2['benefit_amount'].value} ({rec2['benefit_frequency'].value})")
    print(f"Evidence: \"{rec2['benefit_amount'].evidence.exact_text}\" -> Location: {rec2['benefit_amount'].evidence.location}")

    # 3. Scanned OCR Circular Extraction
    print("\n[3/4] Processing Document 4: Scanned Noisy OCR Document (Rajasthan Pension)...")
    with open(os.path.join(data_dir, "doc_4_scanned_noisy_ocr.txt"), "r", encoding="utf-8") as f:
        doc4_text = f.read()
    rec4 = extractor.extract_from_text(doc4_text, "doc_4_scanned_noisy_ocr.txt", scheme_id="SCHEME-RJ-003")
    print(f"Extracted Scheme: '{rec4['scheme_name'].value}'")
    print(f"Benefit: {rec4['benefit_amount'].value}")
    print(f"Deadline: {rec4['deadline'].value}")

    # 4. Conflict Reconciliation Demo (Doc 1 Official vs Doc 3 MyScheme Portal)
    print("\n[4/4] Cross-referencing Multi-Source Documents for Conflict Detection...")
    with open(os.path.join(data_dir, "doc_3_myscheme_portal_conflict.txt"), "r", encoding="utf-8") as f:
        doc3_text = f.read()
    rec3 = extractor.extract_from_text(doc3_text, "doc_3_myscheme_portal_conflict.txt", scheme_id="SCHEME-MP-001")
    
    reconciled = extractor.reconcile_sources(
        primary_records=rec1,
        secondary_records=rec3,
        primary_name="Official MP WCD Circular",
        secondary_name="MyScheme National Portal"
    )

    print("\n>>> Detected Discrepancies (Preserving Both Sources for Human Verification):")
    for field_name, record in reconciled.items():
        if record.status == "conflict":
            print(f"\n* Field: [{field_name.upper()}] - STATUS: CONFLICT")
            print(f"  Note: {record.note}")
            for c in record.conflicts:
                print(f"  - Source: {c.source_name}")
                print(f"    Value: {c.value}")
                print(f"    Evidence Quote: \"{c.evidence.exact_text}\"")
                print(f"    Location: {c.evidence.location}")

    # Export records to JSON
    export_payload = {
        "doc_1_english": {k: v.to_dict() for k, v in rec1.items()},
        "doc_2_hindi": {k: v.to_dict() for k, v in rec2.items()},
        "doc_4_scanned": {k: v.to_dict() for k, v in rec4.items()},
        "reconciled_scheme_mp_001": {k: v.to_dict() for k, v in reconciled.items()}
    }
    with open("output_records.json", "w", encoding="utf-8") as f:
        json.dump(export_payload, f, indent=2, ensure_ascii=False)
    print("\n[✓] Exported all structured scheme records with evidence citations to 'output_records.json'.")

    # Run Automated Evaluation Suite
    print("\nRunning Evaluation Benchmark against Hand-Checked Ground Truth...")
    report = evaluate_pipeline()
    print_evaluation_report(report)

if __name__ == "__main__":
    run_demo()
