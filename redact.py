"""CLI entry point and orchestrator for general-purpose PII redaction pipeline.

Orchestrates document reading across paragraphs, tables, headers, footers, and footnotes,
chunked Presidio PII entity detection for high performance, runtime subject entity auto-detection,
allowlisting, consistent fake replacement generation, format-preserving writeback,
and JSON detection artifact emission.
No inline comments are present in the codebase — documentation is in docstrings.
"""
import argparse
import json
import os
import sys
from typing import List, Dict, Any, Tuple

from document_handler import DocumentHandler, DocumentSegment
from pii_detector import PIIDetector
from faker_engine import FakerEngine
from recognizers.subject_entity import SubjectEntityFilter

def parse_arguments() -> argparse.Namespace:
    """Parse and return command-line arguments."""
    parser = argparse.ArgumentParser(description="General-purpose PII Redaction CLI Tool for DOCX Documents.")
    parser.add_argument("input_doc", help="Path to input .docx document")
    parser.add_argument("-o", "--output", default="redacted_output.docx", help="Path to save redacted output .docx")
    parser.add_argument("--locale", default="en_US", help="Faker locale string for fake entity generation (default: en_US)")
    parser.add_argument("--recognizer-pack", action="append", help="Optional locale recognizer pack to register (e.g. 'in')")
    parser.add_argument("--org-allowlist", help="Path to text file containing organization allowlist entries")
    parser.add_argument("--score-threshold", type=float, default=0.5, help="Confidence threshold score for PII detection (default: 0.5)")
    return parser.parse_args()

def main() -> None:
    """Execute main redaction pipeline workflow."""
    args = parse_arguments()
    
    if not os.path.exists(args.input_doc):
        print(f"Error: Input file '{args.input_doc}' does not exist.", file=sys.stderr, flush=True)
        sys.exit(1)
        
    print(f"Reading document '{args.input_doc}'...", flush=True)
    doc_handler = DocumentHandler(args.input_doc)
    segments = doc_handler.extract_all_segments()
    print(f"Extracted {len(segments)} text segments.", flush=True)
    
    detector = PIIDetector(
        spacy_model="en_core_web_lg",
        recognizer_packs=args.recognizer_pack,
    )
    
    org_filter = SubjectEntityFilter(org_allowlist_path=args.org_allowlist)
    
    chunks: List[Tuple[str, List[DocumentSegment]]] = []
    current_chunk_segments: List[DocumentSegment] = []
    current_length = 0
    
    for segment in segments:
        current_chunk_segments.append(segment)
        current_length += len(segment.text)
        if current_length >= 2500:
            combined_text = "\n".join(seg.text for seg in current_chunk_segments)
            chunks.append((combined_text, current_chunk_segments))
            current_chunk_segments = []
            current_length = 0
            
    if current_chunk_segments:
        combined_text = "\n".join(seg.text for seg in current_chunk_segments)
        chunks.append((combined_text, current_chunk_segments))
        
    print(f"Detecting PII across {len(chunks)} text chunks...", flush=True)
    raw_detections: List[Dict[str, Any]] = []
    org_mentions: List[str] = []
    seen_spans: set = set()
    
    for idx, (combined_text, chunk_segs) in enumerate(chunks):
        results = detector.detect(
            text=combined_text,
            score_threshold=args.score_threshold,
        )
        
        for result in results:
            span_text = combined_text[result.start:result.end].strip()
            if not span_text or len(span_text) < 2:
                continue
                
            dedup_key = (result.entity_type, span_text)
            if dedup_key not in seen_spans:
                seen_spans.add(dedup_key)
                detection_record = {
                    "entity_type": result.entity_type,
                    "text": span_text,
                    "score": result.score,
                    "start": result.start,
                    "end": result.end,
                }
                raw_detections.append(detection_record)
                
                if result.entity_type == "ORGANIZATION":
                    org_mentions.append(span_text)

    subject_entity = org_filter.detect_subject_entity(org_mentions)
    print(f"Auto-detected Subject Entity (Exempt): {subject_entity or 'None'}", flush=True)
    
    filtered_detections: List[Dict[str, Any]] = []
    for detection in raw_detections:
        if org_filter.should_redact(detection["text"], detection["entity_type"]):
            filtered_detections.append(detection)
            
    faker_engine = FakerEngine(locale=args.locale, seed=42)
    
    replacement_mapping: Dict[str, str] = {}
    for detection in filtered_detections:
        orig_text = detection["text"]
        etype = detection["entity_type"]
        fake_replacement = faker_engine.get_replacement(orig_text, etype)
        replacement_mapping[orig_text] = fake_replacement
        detection["replacement"] = fake_replacement
        
    output_path = os.path.abspath(args.output)
    output_dir = os.path.dirname(output_path) or "."
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"Applying replacements to document...", flush=True)
    doc_handler.apply_replacements(replacement_mapping, output_path)
    
    detected_entities_path = os.path.join(output_dir, "detected_entities.json")
    mapping_log_path = os.path.join(output_dir, "mapping_log.json")
    
    with open(detected_entities_path, "w", encoding="utf-8") as file_handle:
        json.dump(filtered_detections, file_handle, indent=2, ensure_ascii=False)
        
    with open(mapping_log_path, "w", encoding="utf-8") as file_handle:
        json.dump(faker_engine.get_mapping_dict(), file_handle, indent=2, ensure_ascii=False)
        
    print(f"Redaction complete.", flush=True)
    print(f"Input Document: {args.input_doc}", flush=True)
    print(f"Output Document: {output_path}", flush=True)
    print(f"Total Unique PII Redacted: {len(replacement_mapping)}", flush=True)
    print(f"Detections Artifact: {detected_entities_path}", flush=True)

if __name__ == "__main__":
    main()
