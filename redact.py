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
from collections import defaultdict
from typing import List, Dict, Any, Tuple, Set

from document_handler import DocumentHandler, DocumentSegment
from pii_detector import PIIDetector
from faker_engine import FakerEngine
from recognizers.subject_entity import SubjectEntityFilter

STRUCTURAL_LABEL_DENYLIST: Set[str] = {
    "email", "e-mail", "telephone", "tel", "fax", "phone", "address",
    "website", "contact", "name", "company", "corporate office",
    "registered office", "office", "board", "committee", "management",
    "director", "directors", "sr", "jr", "mr", "mrs", "ms", "dr",
    "senior", "junior", "chief", "head", "chairman", "chairperson",
}

def _resolve_overlapping_spans(detections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Resolve overlapping character spans by keeping the longest span."""
    grouped: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
    for det in detections:
        grouped[det.get("chunk_idx", 0)].append(det)
        
    resolved: List[Dict[str, Any]] = []
    for chunk_idx, chunk_dets in grouped.items():
        chunk_dets.sort(key=lambda d: (d["start"], -(d["end"] - d["start"])))
        accepted_spans: List[Dict[str, Any]] = []
        for det in chunk_dets:
            overlap = False
            for acc in accepted_spans:
                if max(det["start"], acc["start"]) < min(det["end"], acc["end"]):
                    overlap = True
                    break
            if not overlap:
                accepted_spans.append(det)
                resolved.append(det)
    return resolved

def _deduplicate_by_type_priority(detections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Deduplicate detections by exact text, keeping the highest priority entity type."""
    priority_order = [
        "EMAIL_ADDRESS", "PHONE_NUMBER", "CREDIT_CARD", "US_SSN",
        "IP_ADDRESS", "IN_PAN", "IN_CIN", "IN_DIN", "DATE_OF_BIRTH",
        "PERSON", "LOCATION", "ORGANIZATION"
    ]
    priority_map = {etype: idx for idx, etype in enumerate(priority_order)}
    
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for det in detections:
        grouped[det["text"]].append(det)
        
    deduplicated: List[Dict[str, Any]] = []
    for text, group in grouped.items():
        best_det = min(group, key=lambda d: priority_map.get(d["entity_type"], len(priority_order)))
        deduplicated.append(best_det)
        
    return deduplicated

def _normalize_person_names(replacement_mapping: Dict[str, str], filtered_detections: List[Dict[str, Any]]) -> None:
    """Normalize person name variants to use consistent fake values across case and substring variations.
    
    First unifies case variants (UPPERCASE vs mixed-case) of the same name to
    share one fake value, preferring the mixed-case variant as canonical.
    Then maps shorter substring names to their longer form's fake value.
    """
    person_entries = [(det["text"], det) for det in filtered_detections if det["entity_type"] == "PERSON"]
    person_names = {name for name, _ in person_entries}
    
    canonical_map: Dict[str, str] = {}
    for name in sorted(person_names, key=lambda n: (n.lower(), n.isupper())):
        lower = name.lower()
        if lower not in canonical_map:
            canonical_map[lower] = name
    
    for name in person_names:
        lower = name.lower()
        canonical = canonical_map.get(lower, name)
        if canonical != name and canonical in replacement_mapping and name in replacement_mapping:
            replacement_mapping[name] = replacement_mapping[canonical]
    
    sorted_names = sorted(
        [n for n in person_names if n in replacement_mapping],
        key=len, reverse=True
    )
    for i, longer_name in enumerate(sorted_names):
        for shorter_name in sorted_names[i + 1:]:
            if shorter_name.lower() in longer_name.lower():
                replacement_mapping[shorter_name] = replacement_mapping[longer_name]
                
    for det in filtered_detections:
        if det["text"] in replacement_mapping:
            det["replacement"] = replacement_mapping[det["text"]]

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
    
    for idx, (combined_text, chunk_segs) in enumerate(chunks):
        results = detector.detect(
            text=combined_text,
            score_threshold=args.score_threshold,
        )
        
        for result in results:
            span_text = combined_text[result.start:result.end].strip()
            if not span_text or len(span_text) < 2:
                continue
            if "\n" in span_text:
                continue
                
            detection_record = {
                "chunk_idx": idx,
                "entity_type": result.entity_type,
                "text": span_text,
                "score": result.score,
                "start": result.start,
                "end": result.end,
            }
            raw_detections.append(detection_record)
            
    resolved_detections = _resolve_overlapping_spans(raw_detections)
    dedup_detections = _deduplicate_by_type_priority(resolved_detections)
    
    valid_detections: List[Dict[str, Any]] = []
    for det in dedup_detections:
        if det["entity_type"] == "PERSON" and det["text"].lower().strip() in STRUCTURAL_LABEL_DENYLIST:
            continue
        valid_detections.append(det)

    org_mentions: List[str] = [det["text"] for det in valid_detections if det["entity_type"] == "ORGANIZATION"]

    subject_entity = org_filter.detect_subject_entity(org_mentions)
    print(f"Auto-detected Subject Entity (Exempt): {subject_entity or 'None'}", flush=True)
    
    filtered_detections: List[Dict[str, Any]] = []
    for detection in valid_detections:
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
        
    _normalize_person_names(replacement_mapping, filtered_detections)
        
    output_path = os.path.abspath(args.output)
    output_dir = os.path.dirname(output_path) or "."
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"Applying replacements to document...", flush=True)
    doc_handler.apply_replacements(replacement_mapping, output_path)
    
    detected_entities_path = os.path.join(output_dir, "detected_entities.json")
    mapping_log_path = os.path.join(output_dir, "mapping_log.json")
    
    with open(detected_entities_path, "w", encoding="utf-8") as file_handle:
        json.dump(filtered_detections, file_handle, indent=2, ensure_ascii=False)
        
    normalized_mapping: Dict[str, Dict[str, str]] = {}
    for det in filtered_detections:
        etype = det["entity_type"]
        if etype not in normalized_mapping:
            normalized_mapping[etype] = {}
        normalized_mapping[etype][det["text"]] = replacement_mapping.get(det["text"], det.get("replacement", ""))
    with open(mapping_log_path, "w", encoding="utf-8") as file_handle:
        json.dump(normalized_mapping, file_handle, indent=2, ensure_ascii=False)
        
    print(f"Redaction complete.", flush=True)
    print(f"Input Document: {args.input_doc}", flush=True)
    print(f"Output Document: {output_path}", flush=True)
    print(f"Total Unique PII Redacted: {len(replacement_mapping)}", flush=True)
    print(f"Detections Artifact: {detected_entities_path}", flush=True)

if __name__ == "__main__":
    main()
