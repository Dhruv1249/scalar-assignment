"""Indian locale-specific pattern recognizers (PAN, CIN, DIN).

Implements Non-Negotiable #8:
Locale-specific recognizers live in isolated pack modules and are registered
only when requested via command line arguments. Core detector logic remains
completely independent of this pack.
"""
from presidio_analyzer import PatternRecognizer, Pattern
from typing import List

class InLocaleRecognizers:
    """Recognizer pack providing patterns for Indian identifier formats."""
    
    def get_recognizers(self) -> List[PatternRecognizer]:
        """Instantiate and return list of Indian locale pattern recognizers."""
        pan_recognizer = PatternRecognizer(
            supported_entity="IN_PAN",
            patterns=[
                Pattern(
                    name="IN_PAN_PATTERN",
                    regex=r"\b[A-Z]{5}\d{4}[A-Z]\b",
                    score=0.85,
                )
            ],
            context=["PAN", "permanent account number", "tax ID", "income tax"],
        )
        
        cin_recognizer = PatternRecognizer(
            supported_entity="IN_CIN",
            patterns=[
                Pattern(
                    name="IN_CIN_PATTERN",
                    regex=r"\b[UL]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6}\b",
                    score=0.9,
                )
            ],
            context=["CIN", "corporate identity", "registration number", "RoC"],
        )
        
        din_recognizer = PatternRecognizer(
            supported_entity="IN_DIN",
            patterns=[
                Pattern(
                    name="IN_DIN_PATTERN",
                    regex=r"\b\d{8}\b",
                    score=0.65,
                )
            ],
            context=["DIN", "director identification number", "director identification"],
        )
        
        return [pan_recognizer, cin_recognizer, din_recognizer]
