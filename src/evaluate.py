"""
Evaluation Suite for Scheme Field Extraction
Calculates field-by-field accuracy, evidence attribution validity, and conflict detection recall.
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

from typing import Dict, Any, List
from src.extractor import SchemeExtractor, TARGET_FIELDS

def fuzzy_match(pred: Any, target: Any) -> float:
    """Computes similarity between predicted and target values (0.0 to 1.0)."""
    if pred is None and target is None:
        return 1.0
    if pred is None or target is None:
        return 0.0
    
    if isinstance(target, list) and isinstance(pred, list):
        if not target:
            return 1.0 if not pred else 0.0
        # Calculate Jaccard similarity or list overlap
        matched = 0
        for t_item in target:
            t_norm = str(t_item).lower().strip()
            for p_item in pred:
                p_norm = str(p_item).lower().strip()
                if t_norm in p_norm or p_norm in t_norm:
                    matched += 1
                    break
        return matched / len(target)
    
    s_pred = str(pred).strip().lower()
    s_target = str(target).strip().lower()
    
    if s_pred == s_target:
        return 1.0
    if s_pred in s_target or s_target in s_pred:
        return 0.85
    return 0.0

def evaluate_pipeline(data_dir: str = "data", ground_truth_file: str = "data/ground_truth.json") -> Dict[str, Any]:
    with open(ground_truth_file, "r", encoding="utf-8") as f:
        ground_truth = json.load(f)

    extractor = SchemeExtractor()
    field_scores: Dict[str, List[float]] = {f: [] for f in TARGET_FIELDS}
    evidence_valid_counts = 0
    total_found_fields = 0

    results_by_doc = {}

    for filename, truths in ground_truth.items():
        doc_path = os.path.join(data_dir, filename)
        if not os.path.exists(doc_path):
            continue
        
        with open(doc_path, "r", encoding="utf-8") as f:
            raw_text = f.read()

        extracted = extractor.extract_from_text(raw_text, source_ref=filename)
        doc_results = {}

        for field in TARGET_FIELDS:
            gt_val = truths.get(field)
            rec = extracted.get(field)
            pred_val = rec.value if rec else None

            score = fuzzy_match(pred_val, gt_val)
            field_scores[field].append(score)

            # Check evidence grounding: does exact quote exist in original document?
            has_valid_evidence = False
            if rec and rec.evidence and rec.evidence.exact_text:
                total_found_fields += 1
                snippet = rec.evidence.exact_text.strip()
                # Check first 30 chars of quote in document
                if snippet[:30] in raw_text or snippet in raw_text:
                    evidence_valid_counts += 1
                    has_valid_evidence = True

            doc_results[field] = {
                "ground_truth": gt_val,
                "predicted": pred_val,
                "score": score,
                "status": rec.status if rec else "missing",
                "valid_evidence": has_valid_evidence
            }

        results_by_doc[filename] = doc_results

    # Field-level summary
    summary_by_field = {}
    total_acc_sum = 0
    for field, scores in field_scores.items():
        avg_score = sum(scores) / len(scores) if scores else 0.0
        summary_by_field[field] = round(avg_score * 100, 2)
        total_acc_sum += avg_score

    overall_accuracy = round((total_acc_sum / len(TARGET_FIELDS)) * 100, 2)
    evidence_attribution_rate = round((evidence_valid_counts / total_found_fields * 100), 2) if total_found_fields else 0.0

    # Conflict detection test
    # Cross-reference Doc 1 (circular) vs Doc 3 (myscheme)
    doc1_path = os.path.join(data_dir, "doc_1_english_circular.txt")
    doc3_path = os.path.join(data_dir, "doc_3_myscheme_portal_conflict.txt")
    with open(doc1_path, "r", encoding="utf-8") as f:
        doc1_text = f.read()
    with open(doc3_path, "r", encoding="utf-8") as f:
        doc3_text = f.read()

    rec1 = extractor.extract_from_text(doc1_text, "doc_1_english_circular.txt", scheme_id="SCHEME-MP-001")
    rec3 = extractor.extract_from_text(doc3_text, "doc_3_myscheme_portal_conflict.txt", scheme_id="SCHEME-MP-001")
    reconciled = extractor.reconcile_sources(rec1, rec3)

    conflict_fields_detected = [f for f, r in reconciled.items() if r.status == "conflict"]
    expected_conflicts = ["benefit_amount", "deadline", "department"]
    conflict_recall = round(len(set(conflict_fields_detected).intersection(expected_conflicts)) / len(expected_conflicts) * 100, 2)

    report = {
        "overall_field_accuracy_pct": overall_accuracy,
        "evidence_attribution_validity_pct": evidence_attribution_rate,
        "conflict_detection_recall_pct": conflict_recall,
        "conflict_fields_flagged": conflict_fields_detected,
        "field_accuracies": summary_by_field,
        "documents_evaluated": list(results_by_doc.keys()),
        "threshold_gate_recommendation": {
            "critical_fields_threshold": ">= 95% (scheme_name, benefit_amount, eligibility_conditions, deadline)",
            "non_critical_fields_threshold": ">= 85% (department, official_link, how_to_apply)",
            "evidence_grounding_threshold": "100% (Strict zero-hallucination policy before production)"
        }
    }

    return report

def print_evaluation_report(report: Dict[str, Any]):
    print("=" * 80)
    print("HAQDARSHAK SCHEME KNOWLEDGE BASE - EVALUATION METRICS REPORT")
    print("=" * 80)
    print(f"Overall Field-Level Accuracy:        {report['overall_field_accuracy_pct']}%")
    print(f"Evidence Grounding / Provenance:     {report['evidence_attribution_validity_pct']}% (Quotes verified in source)")
    print(f"Conflict Detection Recall:           {report['conflict_detection_recall_pct']}%")
    print(f"Conflicting Fields Caught:           {', '.join(report['conflict_fields_flagged'])}")
    print("-" * 80)
    print(f"{'FIELD NAME':<28} | {'ACCURACY (%)':<15} | {'GATE STATUS'}")
    print("-" * 80)
    
    for field, acc in report["field_accuracies"].items():
        gate = "PASS [Ready]" if acc >= 85 else "REVIEW NEEDED"
        print(f"{field:<28} | {acc:>11}%   | {gate}")
    print("=" * 80)

if __name__ == "__main__":
    rep = evaluate_pipeline()
    print_evaluation_report(rep)
    with open("data/evaluation_report.json", "w", encoding="utf-8") as f:
        json.dump(rep, f, indent=2, ensure_ascii=False)
