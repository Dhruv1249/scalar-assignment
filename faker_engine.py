"""Consistent fake entity replacement engine.

Implements Non-Negotiable #2:
Maintains referential integrity across the document by caching real-to-fake mappings
in a persistent dictionary structure `{entity_type: {original_text: fake_replacement}}`.
Every occurrence of the same real entity maps to the exact same fake replacement.

Supports configurable Faker locales (default en_US) per technology guidelines,
allowing locale specification via CLI flags without hardcoding regional assumptions.
All code documentation is provided via docstrings — no inline comments.
"""
from collections import defaultdict
from typing import Dict, Any, Callable
from faker import Faker

class FakerEngine:
    """Generates consistent realistic fake data replacements using the Faker library."""
    
    def __init__(self, locale: str = "en_US", seed: int = 42):
        """Initialize Faker instance with requested locale and seed for reproducibility."""
        self.locale = locale
        self.fake = Faker(locale)
        Faker.seed(seed)
        self.mapping: Dict[str, Dict[str, str]] = defaultdict(dict)
        self._setup_generators()

    def _setup_generators(self) -> None:
        """Register entity generation functions for all supported PII types."""
        self.generators: Dict[str, Callable[[], str]] = {
            "PERSON": self.fake.name,
            "EMAIL_ADDRESS": self.fake.email,
            "PHONE_NUMBER": lambda: f"+1-{self.fake.numerify('###-###-####')}",
            "LOCATION": lambda: f"{self.fake.street_address()}, {self.fake.city()}",
            "ORGANIZATION": lambda: f"{self.fake.company()} {self.fake.company_suffix()}",
            "CREDIT_CARD": self.fake.credit_card_number,
            "US_SSN": self.fake.ssn,
            "IP_ADDRESS": self.fake.ipv4,
            "DATE_OF_BIRTH": lambda: self.fake.date_of_birth().strftime("%B %d, %Y"),
            "IN_PAN": lambda: self.fake.bothify("?????####?").upper(),
            "IN_CIN": lambda: f"U{self.fake.numerify('#####')}MH{self.fake.numerify('####')}PTC{self.fake.numerify('######')}",
            "IN_DIN": lambda: self.fake.numerify("########"),
        }

    def get_replacement(self, original_text: str, entity_type: str) -> str:
        """Retrieve cached fake value or generate and store a new consistent fake value.
        
        Ensures identical original strings of the same entity type receive identical
        fake replacements across all occurrences within a document execution (Non-Negotiable #2).
        """
        stripped_original = original_text.strip()
        if not stripped_original:
            return original_text
            
        if stripped_original not in self.mapping[entity_type]:
            generator_func = self.generators.get(entity_type)
            if generator_func:
                fake_value = generator_func()
            else:
                fake_value = f"[REDACTED_{entity_type}]"
                
            self.mapping[entity_type][stripped_original] = fake_value
            
        return self.mapping[entity_type][stripped_original]

    def get_mapping_dict(self) -> Dict[str, Dict[str, str]]:
        """Return deep copy of current entity mapping lookup table."""
        return {etype: dict(map_dict) for etype, map_dict in self.mapping.items()}
