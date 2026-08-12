# PII Redaction Tool

A general-purpose, high-performance Python CLI tool for detecting and redacting Personally Identifiable Information (PII) in Microsoft Word (`.docx`) documents. The tool replaces all detected PII entities with realistic fake alternatives consistently across the entire document while preserving formatting.

---

## 1. Overview & Architecture

The tool is built using **Microsoft Presidio** (`AnalyzerEngine`) orchestrated with **spaCy** (`en_core_web_lg`) for contextual Named Entity Recognition (NER), deterministic regex recognizers for structured PII, and **Faker** for consistent synthetic entity generation.

```
redact.py                       # CLI entry point & orchestrator
document_handler.py             # DOCX I/O (paragraphs, tables, headers, footers, footnotes)
pii_detector.py                 # Presidio AnalyzerEngine wrapper & recognizer registry
recognizers/
    core.py                     # Locale-agnostic recognizers (Email, Phone, SSN, Credit Card, IP, DOB)
    subject_entity.py           # Frequency-based subject entity auto-detection & allowlist logic
    packs/
        in_locale.py            # Optional Indian locale pack (PAN, CIN, DIN)
faker_engine.py                 # Consistent real->fake mapping engine with configurable locale
evaluate.py                     # Precision, recall, F1 metrics & confidence threshold sweep
tests/
    test_synthetic_pii.py       # Unit tests for SSN, credit card (Luhn), IP, DOB
    test_faker_engine.py        # Mapping consistency unit tests
    fixtures/
        ground_truth.json       # Gold-standard ground truth fixture for reference document
evaluation_report.md            # Detailed performance & threshold sweep report
requirements.txt                # Python package dependency manifest
```

---

## 2. Core Non-Negotiables & Scoping Principles

The architecture adheres strictly to ten non-negotiable design principles encoded in `AGENTS.md`:

1. **Zero Runtime LLM Dependencies**: No LLM API calls occur during redaction. All detection is deterministic, privacy-preserving, fast, and local.
2. **Document-Wide Consistency**: Identical real entities (e.g., "Kushal Subbayya Hegde" or "eric.bacha@hdfcbank.com") always resolve to the exact same fake replacement across every paragraph, table, header, footer, and footnote.
3. **Date of Birth Only (Not General Dates)**: DOB recognition is context-dependent (requiring proximity to keywords like `born`, `DOB`, `date of birth`). Financial, incorporation, appointment, or fiscal year dates are explicitly preserved.
4. **Luhn Checksum Validation for Credit Cards**: Digit sequence matching is paired with a Luhn algorithm validator to prevent false positives against image metadata dimensions or order numbers.
5. **Comprehensive Structural Scope**: Text extraction and format-preserving replacement cover body paragraphs, table cells, section headers, section footers, and XML-level footnotes (`word/footnotes.xml`).
6. **Corpus-Tuned Thresholds**: Confidence score thresholds are selected empirically via a 0.4–0.7 sweep in `evaluate.py` rather than arbitrarily asserted.
7. **General Subject Entity & Allowlist Mechanism**: The document's primary subject entity (e.g., the issuer company) is auto-detected at runtime via mention frequency analysis and exempted. Additional exemptions are supported via an `--org-allowlist` file. No company names are hardcoded.
8. **Opt-In Locale Recognizer Packs**: Region-specific identifier recognizers (e.g., Indian PAN, CIN, DIN) live in isolated pack modules (`recognizers/packs/in_locale.py`) and are registered only when requested via `--recognizer-pack in`.
9. **Extensibility Contract**: Adding support for a new PII type requires writing a single recognizer class and adding a single generator strategy in `faker_engine.py`.
10. **General-Purpose Code vs Document-Specific Fixtures**: All core modules (`redact.py`, `pii_detector.py`, `faker_engine.py`, `document_handler.py`) are strictly document-agnostic. Document-specific ground truth is isolated in `tests/fixtures/ground_truth.json`.

---

## 3. Installation & Setup

Using `uv` inside the Python virtual environment (`venv`):

```bash
# 1. Activate virtual environment
source venv/bin/activate

# 2. Install dependencies using uv
uv pip install -r requirements.txt

# 3. Download spaCy large English model
python -m spacy download en_core_web_lg
```

---

## 4. Usage Commands

### Redact a Document (Standard)
```bash
python redact.py "input.docx" -o "redacted_output.docx" --locale en_US
```

### Redact with Indian Locale Pack & Regulator Allowlist
```bash
python redact.py "Red Herring Prospectus.docx" \
    -o "Redacted Red Herring Prospectus.docx" \
    --locale en_US \
    --recognizer-pack in \
    --org-allowlist allowlists/regulators.txt \
    --score-threshold 0.7
```

### Run Unit Tests
```bash
pytest tests/ -v
```

### Run Evaluation & Threshold Sweep
```bash
python evaluate.py \
    --detected detected_entities.json \
    --ground-truth tests/fixtures/ground_truth.json \
    --report evaluation_report.md
```

---

## 5. Extensibility Guide

To add a new PII entity type (e.g., `DRIVER_LICENSE`):

1. **Add Recognizer**: Create a `PatternRecognizer` class in `recognizers/core.py` (or in a new pack under `recognizers/packs/`):
   ```python
   dl_recognizer = PatternRecognizer(
       supported_entity="DRIVER_LICENSE",
       patterns=[Pattern("DL", r"\b[A-Z]\d{7}\b", 0.8)],
   )
   ```
2. **Add Fake Generator**: Add a generator strategy entry in `faker_engine.py`:
   ```python
   "DRIVER_LICENSE": lambda: self.fake.bothify("?#######").upper()
   ```

No changes to `document_handler.py`, `redact.py`, or `evaluate.py` are required.
