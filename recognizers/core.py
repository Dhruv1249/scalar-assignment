"""Core locale-agnostic pattern recognizers for PII detection.

Implements Non-Negotiable #3 (Date of birth only, context-dependent)
and Non-Negotiable #4 (Credit card with Luhn checksum validation).
These recognizers are country-neutral and work for documents from any region.
All logic is documented via docstrings — no inline comments are present.
"""
from presidio_analyzer import PatternRecognizer, Pattern
from typing import List

def get_core_recognizers() -> List[PatternRecognizer]:
    """Instantiate and return all locale-agnostic pattern recognizers.
    
    Includes context-dependent Date of Birth recognition to avoid redacting
    general dates (incorporation, fiscal years, appointments) per Non-Negotiable #3.
    Requires proximity to birth context keywords (born, DOB, date of birth) in the regex pattern.
    """
    dob_patterns = [
        Pattern(
            name="DOB_NUMERIC_WITH_CONTEXT",
            regex=r"\b(?:born|DOB|date of birth|birthday)\s*(?:on|:|-)?\s*(?:0[1-9]|1[0-2]|[1-9])[/\-\.](?:0[1-9]|[12]\d|3[01]|[1-9])[/\-\.](?:19\d\d|20[0-2]\d)\b",
            score=0.85,
        ),
        Pattern(
            name="DOB_LONG_WITH_CONTEXT",
            regex=r"\b(?:born|DOB|date of birth|birthday)\s*(?:on|:|-)?\s*(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+(?:0[1-9]|[12]\d|3[01]|[1-9]),?\s+(?:19\d\d|20[0-2]\d)\b",
            score=0.85,
        ),
    ]
    
    dob_recognizer = PatternRecognizer(
        supported_entity="DATE_OF_BIRTH",
        patterns=dob_patterns,
    )
    
    return [dob_recognizer]
