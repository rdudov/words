"""
Tests for ValidationService behavior.

These tests verify the full validation pipeline:
exact match, fuzzy typo match, and LLM fallback.
"""

import pytest
from unittest.mock import AsyncMock

from src.words.services.validation import ValidationService


@pytest.mark.asyncio
async def test_validation_exact_match_short_circuits_llm():
    translation_service = AsyncMock()
    service = ValidationService(translation_service)

    result = await service.validate_answer(
        user_answer="house",
        expected_answer="house",
        alternative_answers=["home"],
        word_id=1,
        direction="native_to_foreign",
        question="дом",
        source_lang="ru",
        target_lang="en"
    )

    assert result.is_correct is True
    assert result.method == "exact"
    translation_service.validate_answer_with_llm.assert_not_called()


@pytest.mark.asyncio
async def test_validation_accepts_small_typos():
    translation_service = AsyncMock()
    service = ValidationService(translation_service)

    result = await service.validate_answer(
        user_answer="prviat",
        expected_answer="privat",
        alternative_answers=None
    )

    assert result.is_correct is True
    assert result.method == "fuzzy"
    assert "typo" in (result.feedback or "").lower()
    translation_service.validate_answer_with_llm.assert_not_called()


@pytest.mark.asyncio
async def test_validation_uses_llm_when_no_match():
    translation_service = AsyncMock()
    translation_service.validate_answer_with_llm.return_value = (True, "synonym accepted")
    service = ValidationService(translation_service)

    result = await service.validate_answer(
        user_answer="car",
        expected_answer="automobile",
        alternative_answers=[],
        word_id=7,
        direction="native_to_foreign",
        question="машина",
        source_lang="ru",
        target_lang="en"
    )

    assert result.is_correct is True
    assert result.method == "llm"
    assert result.feedback == "synonym accepted"
    translation_service.validate_answer_with_llm.assert_called_once()
