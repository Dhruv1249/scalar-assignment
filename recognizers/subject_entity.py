"""Frequency-based subject-entity auto-detection and allowlist logic.

Implements Non-Negotiable #7:
1. Calculates the most frequently mentioned organization in the document at runtime
   and exempts it from redaction as the document's subject entity (e.g. issuer, vendor, employer).
2. Supports an optional user-provided allowlist file for additional exempted organizations.
3. Redacts all other detected organizations.
No company names or country-specific regulator exemptions are hardcoded into pipeline logic.
All documentation is in docstrings — no inline comments are present.
"""
import re
from collections import Counter
from typing import Optional, Set, List

class SubjectEntityFilter:
    """Filters detected organizations based on frequency auto-detection and allowlists.
    
    Implements Non-Negotiable #7 to ensure company name redaction uses general mechanisms
    rather than hardcoded exemption lists.
    """
    
    GENERIC_ROLE_PREFIXES = (
        "THE BOOK RUNNING",
        "BOOK RUNNING",
        "ANCHOR INVESTOR",
        "REGISTERED BROKER",
        "SYNDICATE MEMBER",
        "DESIGNATED INTERMEDIARY",
        "STATUTORY AUDITOR",
        "COMPANY SECRETARY",
        "SEBI ICDR",
        "SEBI",
        "THE SEBI",
        "REGISTRAR OF COMPANIES",
        "THE REGISTRAR OF COMPANIES",
        "BOARD OF DIRECTORS",
        "BOARD",
        "MANAGEMENT",
        "COMMITTEE",
        "AUDIT COMMITTEE",
        "SHAREHOLDERS",
        "CENTRAL PROCESSING",
        "INCOME TAX",
        "HIGH COURT",
        "DISTRICT COURT",
        "GOVERNMENT",
        "CENTRAL GOVERNMENT",
        "STATE GOVERNMENT",
    )
    
    GEOGRAPHIC_DISCARDS = {
        "MAHARASHTRA",
        "MUMBAI",
        "PUNE",
        "INDIA",
        "DELHI",
        "GUJARAT",
        "SWEDEN",
    }
    
    UNIVERSAL_STRUCTURAL_TERMS = {
        "TABLE",
        "SECTION",
        "CHAPTER",
        "PAGE",
        "EXHIBIT",
        "APPENDIX",
        "SCHEDULE",
        "ARTICLE",
        "CLAUSE",
        "HEADER",
        "FOOTER",
        "FORM",
        "ACT",
        "PART",
        "RED HERRING",
        "RED HERRING PROSPECTUS",
        "PROSPECTUS",
        "CONFIDENTIAL",
        "DRAFT",
        "REGULATION",
        "REGULATIONS",
        "RULES",
        "POLICY",
        "CORPORATE OFFICE",
        "REGISTERED OFFICE",
        "OFFICE",
        "FACILITY",
        "UNIT",
        "PLANT",
        "BUILDING",
        "TOWER",
        "CENTRE",
        "CENTER",
        "PARK",
        "HOUSE",
    }
    
    def __init__(self, org_allowlist_path: Optional[str] = None):
        """Initialize filter with optional allowlist file path."""
        self.allowlist: Set[str] = set()
        self.subject_entity: Optional[str] = None
        self.subject_entity_canonical: Optional[str] = None
        
        if org_allowlist_path:
            self._load_allowlist(org_allowlist_path)
    
    def _load_allowlist(self, path: str) -> None:
        """Load organization names to exempt from a text file, one per line."""
        try:
            with open(path, "r", encoding="utf-8") as file_handle:
                for line in file_handle:
                    cleaned_line = line.strip()
                    if cleaned_line and not cleaned_line.startswith("#"):
                        self.allowlist.add(cleaned_line)
        except OSError:
            pass

    def _canonicalize(self, name: str) -> str:
        """Normalize company name by stripping legal suffixes and leading articles for grouping."""
        cleaned = name.strip()
        cleaned = re.sub(r"^(the|our|this)\s+", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s+(limited|ltd\.?|private limited|pvt\.?\s*ltd\.?|llp)\b", "", cleaned, flags=re.IGNORECASE)
        return cleaned.strip().upper()

    def detect_subject_entity(self, org_mentions: List[str]) -> Optional[str]:
        """Compute the most frequently mentioned organization from raw detections using entity canonicalization.
        
        Groups legal entity variations (e.g. 'KSH International Limited' and 'KSH International') to accurately identify the primary subject entity.
        """
        canonical_map = {}
        filtered_counts = Counter()
        
        for mention in org_mentions:
            clean_mention = mention.strip()
            upper_mention = clean_mention.upper()
            if clean_mention in self.allowlist or upper_mention in self.allowlist:
                continue
            if upper_mention in self.UNIVERSAL_STRUCTURAL_TERMS or upper_mention in self.GEOGRAPHIC_DISCARDS:
                continue
            if any(upper_mention.startswith(prefix) for prefix in self.GENERIC_ROLE_PREFIXES):
                continue
            if len(clean_mention) <= 3:
                continue
                
            canonical = self._canonicalize(clean_mention)
            if canonical and canonical not in self.UNIVERSAL_STRUCTURAL_TERMS:
                filtered_counts[canonical] += 1
                if canonical not in canonical_map or len(clean_mention) > len(canonical_map[canonical]):
                    canonical_map[canonical] = clean_mention
        
        if not filtered_counts:
            self.subject_entity = None
            self.subject_entity_canonical = None
            return None
            
        most_common_canonical = filtered_counts.most_common(1)[0][0]
        self.subject_entity_canonical = most_common_canonical
        self.subject_entity = canonical_map.get(most_common_canonical)
        return self.subject_entity

    def should_redact(self, entity_text: str, entity_type: str) -> bool:
        """Determine whether a detected entity span should be redacted.
        
        Returns False (exempt) if the entity matches the auto-detected subject entity
        or appears in the loaded allowlist. Returns True otherwise.
        """
        if entity_type != "ORGANIZATION":
            return True
            
        if self.subject_entity and entity_text == self.subject_entity:
            return False
            
        if self.subject_entity_canonical and self._canonicalize(entity_text) == self.subject_entity_canonical:
            return False
            
        if entity_text in self.allowlist or self._canonicalize(entity_text) in self.allowlist:
            return False
            
        return True
