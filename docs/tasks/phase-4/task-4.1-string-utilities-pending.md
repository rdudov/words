# Task 4.1: String Utilities (Fuzzy Matching)

**Status:** 🔴 PENDING
**Phase:** 4 - Lesson System
**Priority:** P0 (Critical)
**Complexity:** 🟢 Simple
**Estimated Time:** 1-2 hours

## Related Use Cases

- **UC9:** Обработка ошибок и опечаток (Уровень 2 - проверка опечаток)

## Related Non-Functional Requirements

- **Constraints:** Проверка опечаток должна допускать расстояние не более 2 символов (requirements.md line 327)

## Description

### What

Утилиты для нечеткого сравнения строк с использованием алгоритма Левенштейна для обнаружения опечаток в ответах пользователей.

### Why

**Проблема:** Пользователи часто делают мелкие опечатки при вводе ответа (например, "helo" вместо "hello"). Отклонение такого ответа снижает мотивацию.

**Решение:** Реализовать нечеткое сравнение с порогом 2 символа (UC9 Level 2), чтобы обнаруживать и прощать мелкие опечатки.

**Business Value:**
- Улучшенный UX - меньше фрустрации от опечаток
- Более справедливая оценка знаний
- Соответствие требованиям UC9

### How

1. Создать класс `FuzzyMatcher` в `src/words/utils/string_utils.py`
2. Реализовать методы:
   - `levenshtein_distance()` - вычисление расстояния Левенштейна
   - `is_typo()` - проверка на опечатку (distance ≤ 2)
   - `similarity_ratio()` - процент схожести (0-100)
   - `normalize_text()` - нормализация для сравнения

## Files

### To Create

- `src/words/utils/string_utils.py` - FuzzyMatcher класс
- `src/words/utils/__init__.py` - экспорт утилит
- `tests/utils/test_string_utils.py` - unit тесты

## Implementation Details

### string_utils.py

```python
"""
String utilities for fuzzy matching and normalization.

Implements UC9 Level 2 - Typo detection using Levenshtein distance.
"""

import logging
import Levenshtein
from rapidfuzz import fuzz

logger = logging.getLogger(__name__)


class FuzzyMatcher:
    """
    Fuzzy string matching utilities.

    Used for typo detection in user answers (UC9 Level 2).
    """

    @staticmethod
    def levenshtein_distance(s1: str, s2: str) -> int:
        """
        Calculate Levenshtein distance between two strings.

        Args:
            s1: First string
            s2: Second string

        Returns:
            Integer distance (number of edits needed)

        Example:
            >>> FuzzyMatcher.levenshtein_distance("hello", "helo")
            1
            >>> FuzzyMatcher.levenshtein_distance("cat", "dog")
            3
        """
        return Levenshtein.distance(s1.lower(), s2.lower())

    @staticmethod
    def is_typo(s1: str, s2: str, threshold: int = 2) -> bool:
        """
        Check if two strings differ by a small typo.

        Implements UC9 Level 2: "Если расстояние мало (1-2 символа) — считать опечаткой"

        Args:
            s1: User answer
            s2: Expected answer
            threshold: Maximum distance to consider as typo (default: 2)

        Returns:
            True if strings differ by small typo, False otherwise

        Example:
            >>> FuzzyMatcher.is_typo("helo", "hello")
            True
            >>> FuzzyMatcher.is_typo("hello", "hello")
            False  # Exact match, not a typo
            >>> FuzzyMatcher.is_typo("cat", "dog")
            False  # Too different
        """
        distance = FuzzyMatcher.levenshtein_distance(s1, s2)
        # Distance must be > 0 (not exact match) and <= threshold
        return 0 < distance <= threshold

    @staticmethod
    def similarity_ratio(s1: str, s2: str) -> float:
        """
        Calculate similarity ratio between two strings.

        Args:
            s1: First string
            s2: Second string

        Returns:
            Similarity score (0-100)

        Example:
            >>> FuzzyMatcher.similarity_ratio("hello", "hello")
            100.0
            >>> FuzzyMatcher.similarity_ratio("hello", "helo")
            80.0
        """
        return fuzz.ratio(s1.lower(), s2.lower())

    @staticmethod
    def normalize_text(text: str) -> str:
        """
        Normalize text for comparison.

        Removes extra whitespace and converts to lowercase.

        Args:
            text: Input text

        Returns:
            Normalized text

        Example:
            >>> FuzzyMatcher.normalize_text("  Hello  World  ")
            "hello world"
        """
        return " ".join(text.strip().lower().split())
```

### __init__.py

```python
"""Utils module exports"""

from .string_utils import FuzzyMatcher

__all__ = ["FuzzyMatcher"]
```

## Integration Points

### Usage in Validation Service (Task 4.2)

```python
from src.words.utils import FuzzyMatcher

# UC9 Level 1: Exact match
if user_answer.lower() == expected_answer.lower():
    return ValidationResult(correct=True, method="exact")

# UC9 Level 2: Typo detection
if FuzzyMatcher.is_typo(user_answer, expected_answer, threshold=2):
    return ValidationResult(
        correct=True,
        method="fuzzy",
        comment="Небольшая опечатка исправлена"
    )

# UC9 Level 3: LLM validation
...
```

## Error Handling

### Edge Cases to Handle

1. **Empty strings:**
   ```python
   FuzzyMatcher.is_typo("", "hello")  # Should return False
   ```

2. **Unicode characters:**
   ```python
   FuzzyMatcher.is_typo("привет", "превет")  # Should work with Cyrillic
   ```

3. **Mixed case:**
   ```python
   FuzzyMatcher.is_typo("Hello", "hello")  # Should normalize
   ```

4. **Extra whitespace:**
   ```python
   FuzzyMatcher.normalize_text("  hello   world  ")  # "hello world"
   ```

## Testing

### Unit Tests

```python
# tests/utils/test_string_utils.py

import pytest
from src.words.utils import FuzzyMatcher


class TestLevenshteinDistance:
    """Test Levenshtein distance calculation"""

    def test_identical_strings(self):
        assert FuzzyMatcher.levenshtein_distance("hello", "hello") == 0

    def test_one_character_diff(self):
        assert FuzzyMatcher.levenshtein_distance("hello", "helo") == 1

    def test_completely_different(self):
        distance = FuzzyMatcher.levenshtein_distance("cat", "dog")
        assert distance == 3

    def test_case_insensitive(self):
        assert FuzzyMatcher.levenshtein_distance("Hello", "hello") == 0


class TestIsTypo:
    """Test typo detection (UC9 Level 2)"""

    def test_small_typo_detected(self):
        assert FuzzyMatcher.is_typo("helo", "hello") == True

    def test_exact_match_not_typo(self):
        # UC9: exact match handled separately (Level 1)
        assert FuzzyMatcher.is_typo("hello", "hello") == False

    def test_too_different_not_typo(self):
        assert FuzzyMatcher.is_typo("cat", "dog") == False

    def test_threshold_2_characters(self):
        # 2 characters difference - still a typo
        assert FuzzyMatcher.is_typo("helo", "hello") == True  # 1 char
        assert FuzzyMatcher.is_typo("heo", "hello") == True   # 2 chars
        assert FuzzyMatcher.is_typo("heo", "hello", threshold=2) == True

    def test_cyrillic_support(self):
        assert FuzzyMatcher.is_typo("превет", "привет") == True


class TestSimilarityRatio:
    """Test similarity scoring"""

    def test_identical_returns_100(self):
        assert FuzzyMatcher.similarity_ratio("hello", "hello") == 100.0

    def test_completely_different_low_score(self):
        score = FuzzyMatcher.similarity_ratio("cat", "dog")
        assert score < 50

    def test_small_typo_high_score(self):
        score = FuzzyMatcher.similarity_ratio("hello", "helo")
        assert score > 80


class TestNormalizeText:
    """Test text normalization"""

    def test_removes_extra_whitespace(self):
        assert FuzzyMatcher.normalize_text("  hello   world  ") == "hello world"

    def test_converts_to_lowercase(self):
        assert FuzzyMatcher.normalize_text("Hello World") == "hello world"

    def test_strips_whitespace(self):
        assert FuzzyMatcher.normalize_text("   hello   ") == "hello"

    def test_empty_string(self):
        assert FuzzyMatcher.normalize_text("") == ""
```

### Integration Tests

Test usage in Validation Service (Task 4.2):
1. Create validation service
2. Test answer with exact match
3. Test answer with small typo
4. Test answer with large difference
5. Verify correct validation method returned

## Dependencies

**Blocked By:**
- Task 0.2: Setup Dependencies (python-Levenshtein, rapidfuzz installed)

**Blocks:**
- Task 4.2: Validation Service (uses FuzzyMatcher)

## Acceptance Criteria

- [ ] FuzzyMatcher class created
- [ ] levenshtein_distance() implemented and tested
- [ ] is_typo() implements threshold of 2 characters (UC9 requirement)
- [ ] similarity_ratio() working
- [ ] normalize_text() handles edge cases
- [ ] Unit tests written (покрытие >90%)
- [ ] All tests pass
- [ ] Cyrillic and Unicode support verified
- [ ] Can be imported from src.words.utils

## Implementation Notes

### Design Decisions

1. **Two Libraries:**
   - `python-Levenshtein`: Fast C implementation for distance
   - `rapidfuzz`: Modern library for similarity ratios

2. **Static Methods:** FuzzyMatcher is stateless, so static methods are appropriate

3. **Threshold = 2:** As per requirements.md constraint
   - Can be overridden in is_typo() for flexibility
   - Default matches UC9 specification

### Performance Considerations

- Levenshtein distance is O(n*m) where n, m are string lengths
- For short words (< 20 chars) this is very fast
- python-Levenshtein uses C extension for speed

### Future Enhancements

- Add phonetic matching (Soundex, Metaphone)
- Support for accented characters normalization
- Word-level vs character-level distance
- Custom distance functions for specific languages

## References

- **requirements.md:** UC9 - Обработка ошибок и опечаток (lines 115-136)
- **requirements.md:** Constraint "Проверка опечаток должна допускать расстояние не более 2 символов" (line 327)
- **architecture.md:** Utilities layer

---

**Created:** 2025-11-09
**Author:** Based on implementation plan
