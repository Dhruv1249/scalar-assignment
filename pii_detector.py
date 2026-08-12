"""Presidio AnalyzerEngine wrapper and recognizer registry.

Implements detection orchestration per AGENTS.md requirements:
1. No external LLM API calls at redaction time (Non-Negotiable #1).
2. Configurable spaCy model backend (default en_core_web_lg).
3. Core locale-agnostic recognizers registered by default.
4. Optional locale packs loaded dynamically based on CLI flags (Non-Negotiable #8).
5. Clean extensibility contract for registering additional PII types (Non-Negotiable #9).
All documentation resides in docstrings — no inline comments.
"""
from typing import List, Optional
from presidio_analyzer import AnalyzerEngine, RecognizerResult
from presidio_analyzer.nlp_engine import NlpEngineProvider

from recognizers.core import get_core_recognizers

class PIIDetector:
    """Wrapper around Presidio AnalyzerEngine with custom recognizer registrations."""
    
    def __init__(
        self,
        spacy_model: str = "en_core_web_lg",
        recognizer_packs: Optional[List[str]] = None,
    ):
        """Initialize NLP engine, Presidio analyzer, core recognizers, and optional packs."""
        nlp_config = {
            "nlp_engine_name": "spacy",
            "models": [{"lang_code": "en", "model_name": spacy_model}],
        }
        nlp_engine = NlpEngineProvider(nlp_configuration=nlp_config).create_engine()
        self.analyzer = AnalyzerEngine(nlp_engine=nlp_engine)
        
        for recognizer in get_core_recognizers():
            self.analyzer.registry.add_recognizer(recognizer)
            
        self.active_packs = recognizer_packs or []
        if recognizer_packs:
            for pack_name in recognizer_packs:
                self._register_pack(pack_name)
    
    def _register_pack(self, pack_name: str) -> None:
        """Dynamically import and register recognizers from a named locale pack."""
        if pack_name == "in":
            from recognizers.packs.in_locale import InLocaleRecognizers
            pack = InLocaleRecognizers()
            for recognizer in pack.get_recognizers():
                self.analyzer.registry.add_recognizer(recognizer)
        else:
            raise ValueError(f"Unsupported recognizer pack: '{pack_name}'")

    def detect(
        self,
        text: str,
        score_threshold: float = 0.5,
        entities: Optional[List[str]] = None,
    ) -> List[RecognizerResult]:
        """Perform PII entity detection over input text span.
        
        Returns scored RecognizerResult instances matching or exceeding score_threshold.
        """
        if entities:
            target_entities = entities
        else:
            target_entities = [
                "PERSON",
                "EMAIL_ADDRESS",
                "PHONE_NUMBER",
                "LOCATION",
                "ORGANIZATION",
                "CREDIT_CARD",
                "US_SSN",
                "IP_ADDRESS",
                "DATE_OF_BIRTH",
            ]
            if "in" in self.active_packs:
                target_entities.extend(["IN_PAN", "IN_CIN", "IN_DIN"])
                
        return self.analyzer.analyze(
            text=text,
            language="en",
            entities=target_entities,
            score_threshold=score_threshold,
        )
