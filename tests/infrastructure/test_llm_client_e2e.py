"""
End-to-end tests for LLM Client using real OpenAI API.

These tests make actual API calls to OpenAI and verify the LLM client
works correctly with the real service. They verify response structure
and basic functionality with real-world data.

IMPORTANT:
- These tests use real API calls which cost money
- Run only when necessary: pytest -m e2e
- Tests skip automatically if LLM_API_KEY is not set to a real API key
- Keep tests minimal and focused to avoid unnecessary API costs

Running E2E Tests:
    # Run only e2e tests
    pytest -m e2e

    # Run e2e tests for a specific file
    pytest tests/infrastructure/test_llm_client_e2e.py

    # Skip e2e tests (run everything else)
    pytest -m "not e2e"

Setting up API Key:
    export LLM_API_KEY="sk-..."
"""

import os
import pytest
from src.words.config.settings import settings
from src.words.infrastructure.llm_client import LLMClient


# Check if API key is available from environment (not test key)
def _has_api_key() -> bool:
    """
    Check if a real OpenAI API key is available for e2e testing.

    Checks the LLM_API_KEY environment variable and validates that it's
    a real OpenAI API key (starts with 'sk-') rather than the test key
    set by conftest.py.
    """
    env_key = os.getenv("LLM_API_KEY")
    # Exclude the test key set by conftest.py
    return bool(env_key and env_key.strip() and
                env_key.startswith("sk-") and
                env_key != "test_api_key_12345")


def _get_api_key() -> str:
    """Get the real API key for e2e testing."""
    env_key = os.getenv("LLM_API_KEY")
    # Exclude the test key set by conftest.py
    if (env_key and env_key.strip() and
        env_key.startswith("sk-") and
        env_key != "test_api_key_12345"):
        return env_key

    raise ValueError(
        "No valid OpenAI API key available for e2e tests. "
        "Set LLM_API_KEY environment variable to a real API key (sk-...) to run e2e tests."
    )


# Skip all tests in this module if no API key is available
pytestmark = pytest.mark.skipif(
    not _has_api_key(),
    reason="Real OpenAI API key not available for e2e tests. Set LLM_API_KEY to a real API key (sk-...)."
)


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_translate_word_english_to_russian_real_api():
    """
    E2E test: Verify translate_word works with real OpenAI API for English to Russian.

    This test validates:
    - Real API connection works
    - Response structure matches expected schema
    - Translation returns proper data types
    - All required fields are present
    """
    # Use real API key and client
    api_key = _get_api_key()
    client = LLMClient(api_key=api_key, model="gpt-4o-mini")

    # Translate a simple, common word
    result = await client.translate_word(
        word="hello",
        source_lang="English",
        target_lang="Russian"
    )

    # Verify response structure
    assert isinstance(result, dict), "Result should be a dictionary"

    # Verify all required fields are present
    assert "word" in result, "Response must contain 'word' field"
    assert "translations" in result, "Response must contain 'translations' field"
    assert "examples" in result, "Response must contain 'examples' field"
    assert "word_forms" in result, "Response must contain 'word_forms' field"

    # Verify field types
    assert isinstance(result["word"], str), "'word' must be a string"
    assert isinstance(result["translations"], list), "'translations' must be a list"
    assert isinstance(result["examples"], list), "'examples' must be a list"
    assert isinstance(result["word_forms"], dict), "'word_forms' must be a dict"

    # Verify data quality
    assert result["word"] == "hello", "Word should match input"
    assert len(result["translations"]) > 0, "Should have at least one translation"
    assert "привет" in result["translations"] or "здравствуй" in result["translations"], \
        "Should contain common Russian translation for 'hello'"

    # Verify examples structure if present
    if result["examples"]:
        example = result["examples"][0]
        assert isinstance(example, dict), "Example must be a dict"
        assert "source" in example, "Example must have 'source' field"
        assert "target" in example, "Example must have 'target' field"
        assert isinstance(example["source"], str), "Example source must be string"
        assert isinstance(example["target"], str), "Example target must be string"
        assert len(example["source"]) > 0, "Example source must not be empty"
        assert len(example["target"]) > 0, "Example target must not be empty"

    print(f"\n✓ E2E Test passed: translate_word(hello, EN→RU)")
    print(f"  Translations: {result['translations'][:3]}")  # Show first 3 translations
    print(f"  Examples: {len(result['examples'])} provided")
    print(f"  Word forms: {len(result['word_forms'])} forms")


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_translate_word_russian_to_english_real_api():
    """
    E2E test: Verify translate_word works with real OpenAI API for Russian to English.

    This test validates:
    - Bidirectional translation works
    - Cyrillic characters are handled correctly
    - Response structure is consistent across language pairs
    """
    api_key = _get_api_key()
    client = LLMClient(api_key=api_key, model="gpt-4o-mini")

    # Translate a simple Russian word
    result = await client.translate_word(
        word="дом",
        source_lang="Russian",
        target_lang="English"
    )

    # Verify response structure (same as English→Russian)
    assert isinstance(result, dict)
    assert "word" in result
    assert "translations" in result
    assert "examples" in result
    assert "word_forms" in result

    # Verify field types
    assert isinstance(result["word"], str)
    assert isinstance(result["translations"], list)
    assert isinstance(result["examples"], list)
    assert isinstance(result["word_forms"], dict)

    # Verify data quality
    assert result["word"] == "дом", "Word should match input (Cyrillic)"
    assert len(result["translations"]) > 0, "Should have at least one translation"
    assert "house" in result["translations"] or "home" in result["translations"], \
        "Should contain common English translation for 'дом'"

    print(f"\n✓ E2E Test passed: translate_word(дом, RU→EN)")
    print(f"  Translations: {result['translations'][:3]}")
    print(f"  Examples: {len(result['examples'])} provided")


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_translate_word_retry_logic_works():
    """
    E2E test: Verify that retry logic works with real API.

    This test validates that the client can successfully complete
    a request even if configured with retry capabilities. We can't
    easily trigger a real retry without intentionally causing errors,
    but we can verify the retry-enabled code path works.
    """
    api_key = _get_api_key()
    client = LLMClient(api_key=api_key, model="gpt-4o-mini")

    # Make a call that should succeed on first try
    # The retry logic is in place but won't be triggered
    result = await client.translate_word(
        word="cat",
        source_lang="English",
        target_lang="Russian"
    )

    # Verify basic structure
    assert isinstance(result, dict)
    assert result["word"] == "cat"
    assert len(result["translations"]) > 0

    # Verify at least one common translation is present
    translations_lower = [t.lower() for t in result["translations"]]
    assert any("кот" in t or "кошка" in t for t in translations_lower), \
        "Should contain common Russian translation for 'cat'"

    print(f"\n✓ E2E Test passed: translate_word with retry logic (cat, EN→RU)")
    print(f"  Translations: {result['translations'][:3]}")


# NOTE: We intentionally DO NOT test validate_answer with real API
# The validation logic is simple and well-covered by unit tests with mocks.
# Testing it with real API would be expensive and not provide meaningful
# additional validation beyond what translate_word already provides.
