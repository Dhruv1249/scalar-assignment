"""FastAPI backend application for PII Redaction API.

Exposes RESTful endpoints for document upload, PII detection, redaction,
and file download. Uses DocumentHandler, PIIDetector, FakerEngine, and
SubjectEntityFilter from core pipeline.
No inline comments are present in the codebase — documentation is in docstrings.
"""
import io
import os
import tempfile
from typing import Optional, List
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from document_handler import DocumentHandler
from pii_detector import PIIDetector
from faker_engine import FakerEngine
from recognizers.subject_entity import SubjectEntityFilter

app = FastAPI(
    title="PII Redaction Service API",
    description="Containerized backend API for auto-detecting and redacting PII in DOCX files.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    """Health check endpoint returning service operational status."""
    return {"status": "ok", "service": "pii-redactor-backend"}

@app.post("/api/redact")
async def redact_document(
    file: UploadFile = File(...),
    locale: str = Form("en_US"),
    recognizer_pack: Optional[str] = Form(None),
    score_threshold: float = Form(0.5),
    org_allowlist_text: Optional[str] = Form(None),
):
    """Accept uploaded .docx file, run PII redaction pipeline, and return redacted document with stats."""
    if not file.filename.endswith(".docx"):
        raise HTTPException(status_code=400, detail="Only .docx files are supported.")
        
    temp_dir = tempfile.mkdtemp()
    input_path = os.path.join(temp_dir, "input.docx")
    output_path = os.path.join(temp_dir, "redacted_output.docx")
    allowlist_path = None
    
    try:
        content = await file.read()
        with open(input_path, "wb") as f:
            f.write(content)
            
        if org_allowlist_text and org_allowlist_text.strip():
            allowlist_path = os.path.join(temp_dir, "allowlist.txt")
            with open(allowlist_path, "w", encoding="utf-8") as f:
                f.write(org_allowlist_text)
                
        doc_handler = DocumentHandler(input_path)
        segments = doc_handler.extract_all_segments()
        
        packs = [recognizer_pack] if recognizer_pack else None
        detector = PIIDetector(spacy_model="en_core_web_lg", recognizer_packs=packs)
        org_filter = SubjectEntityFilter(org_allowlist_path=allowlist_path)
        
        chunks = []
        current_chunk_segments = []
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
            
        raw_detections = []
        org_mentions = []
        seen_spans = set()
        
        for combined_text, _ in chunks:
            results = detector.detect(text=combined_text, score_threshold=score_threshold)
            for result in results:
                span_text = combined_text[result.start:result.end].strip()
                if not span_text or len(span_text) < 2:
                    continue
                dedup_key = (result.entity_type, span_text)
                if dedup_key not in seen_spans:
                    seen_spans.add(dedup_key)
                    raw_detections.append({
                        "entity_type": result.entity_type,
                        "text": span_text,
                        "score": result.score,
                    })
                    if result.entity_type == "ORGANIZATION":
                        org_mentions.append(span_text)
                        
        subject_entity = org_filter.detect_subject_entity(org_mentions)
        
        filtered_detections = []
        for det in raw_detections:
            if org_filter.should_redact(det["text"], det["entity_type"]):
                filtered_detections.append(det)
                
        faker_engine = FakerEngine(locale=locale, seed=42)
        replacement_mapping = {}
        type_counts = {}
        
        for det in filtered_detections:
            orig = det["text"]
            etype = det["entity_type"]
            fake_val = faker_engine.get_replacement(orig, etype)
            replacement_mapping[orig] = fake_val
            type_counts[etype] = type_counts.get(etype, 0) + 1
            
        doc_handler.apply_replacements(replacement_mapping, output_path)
        
        filename_base = os.path.splitext(file.filename)[0]
        download_filename = f"{filename_base}_redacted.docx"
        
        return FileResponse(
            path=output_path,
            filename=download_filename,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "X-Subject-Entity": subject_entity or "None",
                "X-Total-PII-Count": str(len(replacement_mapping)),
                "Access-Control-Expose-Headers": "X-Subject-Entity, X-Total-PII-Count",
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
