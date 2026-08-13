"""Unit tests for Faker engine mapping consistency and locale configuration.

Implements tests for Non-Negotiable #2:
Verifies that identical original entity strings receive consistent fake replacements
across multiple lookups within a document execution session.
Also validates format-preserving phone number generation (Bug #6 fix).
No inline comments are present in the codebase — documentation is in docstrings.
"""
import pytest
from faker_engine import FakerEngine

def test_mapping_consistency_same_entity() -> None:
    """Verify that looking up the same original entity returns identical fake values."""
    engine = FakerEngine(locale="en_US", seed=100)
    first_lookup = engine.get_replacement("John Doe", "PERSON")
    second_lookup = engine.get_replacement("John Doe", "PERSON")
    assert first_lookup == second_lookup

def test_different_entities_produce_different_replacements() -> None:
    """Verify that different input strings produce distinct fake values."""
    engine = FakerEngine(locale="en_US", seed=100)
    first_name = engine.get_replacement("John Doe", "PERSON")
    second_name = engine.get_replacement("Jane Smith", "PERSON")
    assert first_name != second_name

def test_email_mapping_consistency() -> None:
    """Verify consistent replacement for email addresses."""
    engine = FakerEngine(locale="en_US", seed=100)
    email_a = engine.get_replacement("john.doe@example.com", "EMAIL_ADDRESS")
    email_b = engine.get_replacement("john.doe@example.com", "EMAIL_ADDRESS")
    assert email_a == email_b

def test_configurable_locale() -> None:
    """Verify that custom locales are instantiated properly."""
    engine_us = FakerEngine(locale="en_US", seed=42)
    engine_gb = FakerEngine(locale="en_GB", seed=42)
    val_us = engine_us.get_replacement("Main Street", "LOCATION")
    val_gb = engine_gb.get_replacement("Main Street", "LOCATION")
    assert isinstance(val_us, str)
    assert isinstance(val_gb, str)

def test_phone_format_preservation_indian_mobile() -> None:
    """Verify Indian +91 phone numbers preserve their format structure."""
    engine = FakerEngine(locale="en_US", seed=42)
    original = "+91 22 30752929"
    fake = engine.get_replacement(original, "PHONE_NUMBER")
    assert fake.startswith("+91")
    assert len(fake) == len(original)
    for i, char in enumerate(original):
        if not char.isdigit() and char != '+':
            assert fake[i] == char, f"Separator at position {i} not preserved: '{fake[i]}' != '{char}'"

def test_phone_format_preservation_landline() -> None:
    """Verify Indian landline numbers with leading zero preserve format."""
    engine = FakerEngine(locale="en_US", seed=42)
    original = "022-68052182"
    fake = engine.get_replacement(original, "PHONE_NUMBER")
    assert fake.startswith("0")
    assert fake[3] == "-"
    assert len(fake) == len(original)

def test_phone_format_preservation_consistency() -> None:
    """Verify format-preserving phone replacement maintains mapping consistency."""
    engine = FakerEngine(locale="en_US", seed=42)
    original = "+91-20-26234000"
    first = engine.get_replacement(original, "PHONE_NUMBER")
    second = engine.get_replacement(original, "PHONE_NUMBER")
    assert first == second
    assert first.startswith("+91")
    assert first[3] == "-"
    assert first[6] == "-"
