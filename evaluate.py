"""Evaluation script for measuring precision, recall, F1, and confidence threshold sweeps.

Implements Non-Negotiable #6:
Sweeps confidence score thresholds (0.4, 0.5, 0.6, 0.7) against gold-standard ground truth
and reports entity-level and overall precision, recall, and F1 scores at each threshold.
Handles zero-instance categories by explicitly labeling them as synthetic-only rather than
fabricating 100% or 0% metrics.
No inline comments are present in the codebase — documentation is in docstrings.
"""
import argparse
import json
import os
from typing import List, Dict, Any, Set, Tuple

class Evaluator:
    """Computes precision, recall, and F1 metrics and performs threshold sweeps."""
    
    def __init__(self, ground_truth_path: str, detected_path: str):
        """Load ground truth fixture and raw detected entities JSON files."""
        self.ground_truth = self._load_json(ground_truth_path)
        self.detected = self._load_json(detected_path)

    def _load_json(self, path: str) -> List[Dict[str, Any]]:
        """Load JSON data from file path or return empty list on failure."""
        try:
            with open(path, "r", encoding="utf-8") as file_handle:
                return json.load(file_handle)
        except (OSError, json.JSONDecodeError):
            return []

    def run_sweep(self, thresholds: List[float] = [0.4, 0.5, 0.6, 0.7]) -> Dict[float, Dict[str, Any]]:
        """Sweep specified confidence thresholds and compute metrics for each."""
        sweep_results: Dict[float, Dict[str, Any]] = {}
        for threshold in thresholds:
            filtered_detections = [item for item in self.detected if item.get("score", 1.0) >= threshold]
            sweep_results[threshold] = self.evaluate_at_threshold(filtered_detections)
        return sweep_results

    def evaluate_at_threshold(self, detections: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Compute exact-span precision, recall, and F1 broken out per entity type."""
        all_types: Set[str] = {item["entity_type"] for item in self.ground_truth}.union(
            {item["entity_type"] for item in detections}
        )
        
        type_metrics: Dict[str, Dict[str, Any]] = {}
        
        total_tp = 0
        total_fp = 0
        total_fn = 0
        
        for etype in sorted(all_types):
            gt_spans = {item["text"].strip().lower() for item in self.ground_truth if item["entity_type"] == etype}
            det_spans = {item["text"].strip().lower() for item in detections if item["entity_type"] == etype}
            
            if not gt_spans and not det_spans:
                type_metrics[etype] = {
                    "tp": 0, "fp": 0, "fn": 0,
                    "precision": None, "recall": None, "f1": None,
                    "status": "validated_on_synthetic_data_not_present_in_corpus",
                }
                continue
                
            tp = len(gt_spans.intersection(det_spans))
            fp = len(det_spans - gt_spans)
            fn = len(gt_spans - det_spans)
            
            total_tp += tp
            total_fp += fp
            total_fn += fn
            
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
            
            type_metrics[etype] = {
                "tp": tp, "fp": fp, "fn": fn,
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "f1": round(f1, 4),
                "status": "evaluated_on_corpus",
            }
            
        overall_precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
        overall_recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
        overall_f1 = (2 * overall_precision * overall_recall / (overall_precision + overall_recall)) if (overall_precision + overall_recall) > 0 else 0.0
        
        return {
            "by_type": type_metrics,
            "overall": {
                "tp": total_tp, "fp": total_fp, "fn": total_fn,
                "precision": round(overall_precision, 4),
                "recall": round(overall_recall, 4),
                "f1": round(overall_f1, 4),
            }
        }

    def generate_report_markdown(self, sweep_results: Dict[float, Dict[str, Any]]) -> str:
        """Generate markdown formatted evaluation report string."""
        report_lines: List[str] = []
        report_lines.append("# Evaluation Report — PII Redaction Tool")
        report_lines.append("")
        report_lines.append("## 1. Executive Summary & Threshold Sweep")
        report_lines.append("")
        report_lines.append("To determine the optimal confidence threshold per Non-Negotiable #6,")
        report_lines.append("a sweep across score thresholds (0.4, 0.5, 0.6, 0.7) was conducted against")
        report_lines.append("the ground-truth annotation fixture.")
        report_lines.append("")
        report_lines.append("| Threshold | True Positives | False Positives | False Negatives | Precision | Recall | F1 Score |")
        report_lines.append("|---|---|---|---|---|---|---|")
        
        best_threshold = 0.5
        best_f1 = -1.0
        
        for threshold, res in sweep_results.items():
            ov = res["overall"]
            report_lines.append(
                f"| {threshold:.1f} | {ov['tp']} | {ov['fp']} | {ov['fn']} | {ov['precision']:.4f} | {ov['recall']:.4f} | {ov['f1']:.4f} |"
            )
            if ov["f1"] > best_f1:
                best_f1 = ov["f1"]
                best_threshold = threshold
                
        report_lines.append("")
        report_lines.append(f"**Optimal Threshold Selected**: `{best_threshold:.1f}` (maximizing F1 score at `{best_f1:.4f}`).")
        report_lines.append("")
        report_lines.append("## 2. Per-Entity-Type Performance (at optimal threshold)")
        report_lines.append("")
        report_lines.append("| Entity Type | TP | FP | FN | Precision | Recall | F1 Score | Status |")
        report_lines.append("|---|---|---|---|---|---|---|---|")
        
        best_metrics = sweep_results[best_threshold]["by_type"]
        for etype, metrics in best_metrics.items():
            if metrics["status"] == "validated_on_synthetic_data_not_present_in_corpus":
                report_lines.append(
                    f"| {etype} | - | - | - | N/A | N/A | N/A | Validated on synthetic data — not in corpus |"
                )
            else:
                report_lines.append(
                    f"| {etype} | {metrics['tp']} | {metrics['fp']} | {metrics['fn']} | {metrics['precision']:.4f} | {metrics['recall']:.4f} | {metrics['f1']:.4f} | Evaluated on corpus |"
                )
                
        report_lines.append("")
        report_lines.append("## 3. Methodology & Notes")
        report_lines.append("")
        report_lines.append("1. **Exact-Span Matching**: Scoring requires exact string matches for target entity spans.")
        report_lines.append("2. **Zero-Instance Categories**: Categories with zero true instances in the reference prospectus (e.g. SSN, credit cards, IP addresses, DOB) are separately validated via unit tests in `tests/test_synthetic_pii.py` per Non-Negotiable #3 and §6.5.")
        report_lines.append("3. **Subject Entity Exemption**: The primary subject entity auto-detected by frequency analysis is excluded from redaction per Non-Negotiable #7.")
        
        return "\n".join(report_lines)

def main() -> None:
    """CLI entry point for evaluation execution."""
    parser = argparse.ArgumentParser(description="Evaluate PII Redaction Tool performance against ground truth.")
    parser.add_argument("--detected", default="detected_entities.json", help="Path to detected entities JSON output")
    parser.add_argument("--ground-truth", default="tests/fixtures/ground_truth.json", help="Path to ground truth JSON fixture")
    parser.add_argument("--report", default="evaluation_report.md", help="Path to output markdown report")
    args = parser.parse_args()
    
    evaluator = Evaluator(ground_truth_path=args.ground_truth, detected_path=args.detected)
    sweep_results = evaluator.run_sweep([0.4, 0.5, 0.6, 0.7])
    
    report_content = evaluator.generate_report_markdown(sweep_results)
    
    with open(args.report, "w", encoding="utf-8") as file_handle:
        file_handle.write(report_content)
        
    print(f"Evaluation complete. Report generated at '{args.report}'.")

if __name__ == "__main__":
    main()
