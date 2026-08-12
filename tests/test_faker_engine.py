"""Unit tests for Faker engine mapping consistency and locale configuration.

Implements tests for Non-Negotiable #2:
Verifies that identical original entity strings receive consistent fake replacements
across multiple lookups within a document execution session.
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
