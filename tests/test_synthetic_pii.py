"""Unit tests for synthetic PII detection validation.

Validates zero-instance categories (SSN, credit card, IP address, DOB) against synthetic test strings
per Non-Negotiable #3 (DOB only with context) and Non-Negotiable #4 (Credit card Luhn validation).
No inline comments are present in the codebase — documentation is in docstrings.
"""
import pytest
from pii_detector import PIIDetector

@pytest.fixture(scope="module")
def detector() -> PIIDetector:
    """Fixture providing initialized PIIDetector instance."""
    return PIIDetector(spacy_model="en_core_web_lg")

def test_dob_detection_context_aware(detector: PIIDetector) -> None:
    """Verify DOB detection fires when context keywords exist, per Non-Negotiable #3."""
    dob_text = "The applicant was born on 05/12/1985 in Delhi."
    results = detector.detect(dob_text, score_threshold=0.5)
    dob_matches = [res for res in results if res.entity_type == "DATE_OF_BIRTH"]
    assert len(dob_matches) > 0

def test_general_date_not_redacted_as_dob(detector: PIIDetector) -> None:
    """Verify general financial dates are not redacted as DOB, per Non-Negotiable #3."""
    financial_date_text = "For the fiscal year ended March 31, 2025, revenues increased."
    results = detector.detect(financial_date_text, score_threshold=0.5)
    dob_matches = [res for res in results if res.entity_type == "DATE_OF_BIRTH"]
    assert len(dob_matches) == 0

def test_us_ssn_detection(detector: PIIDetector) -> None:
    """Verify US SSN pattern detection on synthetic strings."""
    ssn_text = "Contact taxpayer with SSN 219-09-8970 for clarification."
    results = detector.detect(ssn_text, score_threshold=0.5)
    ssn_matches = [res for res in results if res.entity_type == "US_SSN"]
    assert len(ssn_matches) > 0

def test_credit_card_luhn_validation(detector: PIIDetector) -> None:
    """Verify credit card recognizer requires valid Luhn checksum per Non-Negotiable #4."""
    invalid_digit_sequence = "Dimension code 081944444444444 is specified."
    results = detector.detect(invalid_digit_sequence, score_threshold=0.5)
    cc_matches = [res for res in results if res.entity_type == "CREDIT_CARD"]
    assert len(cc_matches) == 0

def test_ip_address_detection(detector: PIIDetector) -> None:
    """Verify IP address detection on synthetic strings."""
    ip_text = "Server connection established from 192.168.1.100 port 80."
    results = detector.detect(ip_text, score_threshold=0.5)
    ip_matches = [res for res in results if res.entity_type == "IP_ADDRESS"]
    assert len(ip_matches) > 0
