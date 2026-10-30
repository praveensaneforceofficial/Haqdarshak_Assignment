"""
Haqdarshak Scheme Knowledge Base - Main Pipeline Demo
Built on SOLID Architecture (Single Responsibility, Open/Closed, Liskov, Interface Segregation, Dependency Inversion).
Supports OpenAI GPT-4o-mini Extraction with strict evidence citations and Deterministic Rule-Based fallback.
"""

import os
import sys
import json
import argparse
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Ensure UTF-8 output on Windows console
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from src.extractors import OpenAISchemeExtractor, RuleBasedSchemeExtractor
from src.verifier import ExactEvidenceVerifier
from src.reconciler import SchemeReconciler
from src.pipeline import SchemePipeline
from src.evaluate import SchemeEvaluator, print_evaluation_report

def run_demo(use_openai: bool = True, api_key: str = None):
    # Safely retrieve key from parameter or environment
    resolved_api_key = api_key or os.getenv("OPENAI_API_KEY", "")
    model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    print("\n" + "=" * 80)
    print(" HAQDARSHAK SCHEME KNOWLEDGE BASE - AI EXTRACTION PIPELINE")
    print(f" Architecture: SOLID Principles | Model: OpenAI {model_name} + Grounding Verifier")
    print("=" * 80)

    # 1. Dependency Inversion: Inject Concrete Extractor, Verifier, and Reconciler
    verifier = ExactEvidenceVerifier()
    reconciler = SchemeReconciler()

    if use_openai and resolved_api_key:
        print(f"[Engine] Initializing OpenAISchemeExtractor ({model_name})...")
        extractor = OpenAISchemeExtractor(api_key=resolved_api_key, model_name=model_name)
    else:
        print("[Engine] Initializing RuleBasedSchemeExtractor (Deterministic / Offline)...")
        extractor = RuleBasedSchemeExtractor()

    pipeline = SchemePipeline(
        extractor=extractor,
        verifier=verifier,
        reconciler=reconciler
    )

    data_dir = "data"

    # 1. English Circular Extraction
    print("\n[1/4] Processing Document 1: English Government Circular (Madhya Pradesh)...")
    with open(os.path.join(data_dir, "doc_1_english_circular.txt"), "r", encoding="utf-8") as f:
        doc1_text = f.read()
    rec1 = pipeline.process_document(doc1_text, "doc_1_english_circular.txt", scheme_id="SCHEME-MP-001")
    print(f"Extracted Scheme: '{rec1['scheme_name'].value}'")
    print(f"Benefit: {rec1['benefit_amount'].value} ({rec1['benefit_frequency'].value})")
    if rec1['benefit_amount'].evidence:
        print(f"Evidence: \"{rec1['benefit_amount'].evidence.exact_text}\" -> Location: {rec1['benefit_amount'].evidence.location}")

    # 2. Hindi Circular Extraction
    print("\n[2/4] Processing Document 2: Hindi Government Resolution (Uttar Pradesh)...")
    with open(os.path.join(data_dir, "doc_2_hindi_circular.txt"), "r", encoding="utf-8") as f:
        doc2_text = f.read()
    rec2 = pipeline.process_document(doc2_text, "doc_2_hindi_circular.txt", scheme_id="SCHEME-UP-002")
    print(f"Extracted Scheme (Hindi): '{rec2['scheme_name'].value}'")
    print(f"Benefit: {rec2['benefit_amount'].value} ({rec2['benefit_frequency'].value})")
    if rec2['benefit_amount'].evidence:
        print(f"Evidence: \"{rec2['benefit_amount'].evidence.exact_text}\" -> Location: {rec2['benefit_amount'].evidence.location}")

    # 3. Scanned OCR Circular Extraction
    print("\n[3/4] Processing Document 4: Scanned Noisy OCR Document (Rajasthan Pension)...")
    with open(os.path.join(data_dir, "doc_4_scanned_noisy_ocr.txt"), "r", encoding="utf-8") as f:
        doc4_text = f.read()
    rec4 = pipeline.process_document(doc4_text, "doc_4_scanned_noisy_ocr.txt", scheme_id="SCHEME-RJ-003")
    print(f"Extracted Scheme: '{rec4['scheme_name'].value}'")
    print(f"Benefit: {rec4['benefit_amount'].value}")
    print(f"Deadline: {rec4['deadline'].value}")

    # 4. Multi-Source Conflict Reconciliation
    print("\n[4/4] Cross-referencing Multi-Source Documents for Conflict Detection...")
    with open(os.path.join(data_dir, "doc_3_myscheme_portal_conflict.txt"), "r", encoding="utf-8") as f:
        doc3_text = f.read()
    
    reconciled = pipeline.process_and_reconcile(
        primary_text=doc1_text,
        primary_source_ref="doc_1_english_circular.txt",
        secondary_text=doc3_text,
        secondary_source_ref="doc_3_myscheme_portal_conflict.txt",
        scheme_id="SCHEME-MP-001",
        primary_name="Official MP WCD Circular",
        secondary_name="MyScheme National Portal"
    )

    print("\n>>> Detected Discrepancies (Preserving Both Sources for Human Verification):")
    for field_name, record in reconciled.items():
        if record.status == "conflict":
            print(f"\n* Field: [{field_name.upper()}] - STATUS: CONFLICT")
            print(f"  Note: {record.note}")
            if record.conflicts:
                for c in record.conflicts:
                    print(f"  - Source: {c.source_name}")
                    print(f"    Value: {c.value}")
                    if c.evidence:
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
    evaluator = SchemeEvaluator(pipeline)
    report = evaluator.evaluate()
    print_evaluation_report(report)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Haqdarshak Scheme Knowledge Base Pipeline")
    parser.add_argument("--offline", action="store_true", help="Run in deterministic offline mode without OpenAI API")
    parser.add_argument("--api-key", type=str, default=None, help="OpenAI API Key (or set via .env file)")
    args = parser.parse_args()

    run_demo(use_openai=not args.offline, api_key=args.api_key)
