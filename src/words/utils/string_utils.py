"""
String utilities for fuzzy matching.

Provides Levenshtein distance, typo detection, similarity scoring,
and normalization helpers for validation workflows.
"""

import Levenshtein
from rapidfuzz import fuzz


class FuzzyMatcher:
    """Fuzzy string matching utilities."""

    @staticmethod
    def levenshtein_distance(s1: str, s2: str) -> int:
        """Calculate Levenshtein distance (case-insensitive)."""
        return Levenshtein.distance(s1.lower(), s2.lower())

    @staticmethod
    def is_typo(s1: str, s2: str, threshold: int = 2) -> bool:
        """Check if strings differ by a small typo within threshold."""
        distance = FuzzyMatcher.levenshtein_distance(s1, s2)
        return 0 < distance <= threshold

    @staticmethod
    def similarity_ratio(s1: str, s2: str) -> float:
        """Calculate similarity ratio (0-100)."""
        return float(fuzz.ratio(s1.lower(), s2.lower()))

    @staticmethod
    def normalize_text(text: str) -> str:
        """Normalize text for comparison."""
        return text.strip().lower()
