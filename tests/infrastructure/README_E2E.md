# End-to-End Testing for LLM Client

This directory contains end-to-end (e2e) tests that use the **real OpenAI API** to verify the LLM client functionality.

## Important Notes

⚠️ **E2E tests make real API calls to OpenAI and cost money!**

- Run e2e tests **only when necessary** (e.g., before major releases, after infrastructure changes)
- E2E tests are **automatically skipped** if no real API key is provided
- Unit tests with mocks provide comprehensive coverage - e2e tests are for integration validation only

## Running E2E Tests

### Prerequisites

Set your OpenAI API key as an environment variable:

```bash
export LLM_API_KEY="sk-..."
```

**Note:** The API key must start with `sk-` and must not be the test key (`test_api_key_12345`) to be recognized as a real key.

### Run E2E Tests

```bash
# Run only e2e tests
pytest -m e2e

# Run e2e tests with verbose output
pytest -m e2e -v

# Run e2e tests for LLM client specifically
pytest tests/infrastructure/test_llm_client_e2e.py -v
```

### Skip E2E Tests

```bash
# Run all tests EXCEPT e2e tests (default behavior)
pytest -m "not e2e"

# Run all tests (including e2e if API key available)
pytest
```

### Without API Key

If you don't set `LLM_API_KEY` to a real API key, the tests will be skipped automatically:

```bash
$ pytest tests/infrastructure/test_llm_client_e2e.py -v
...
test_translate_word_english_to_russian_real_api SKIPPED
test_translate_word_russian_to_english_real_api SKIPPED
test_translate_word_retry_logic_works SKIPPED
...
====== 3 skipped in 0.12s ======
```

## What E2E Tests Cover

### Currently Tested (✅)

- `translate_word()` - English to Russian translation
- `translate_word()` - Russian to English translation (Cyrillic support)
- Response structure validation (all fields present and correct types)
- Retry logic functionality

### Intentionally NOT Tested (❌)

- `validate_answer()` - Covered by unit tests, not cost-effective to test with real API
- Rate limiting - Covered by unit tests with mocks
- Circuit breaker - Covered by unit tests with mocks
- Error handling edge cases - Covered by unit tests with mocks

## Test Philosophy

E2E tests should be:

1. **Minimal** - Only 2-3 focused tests
2. **High-value** - Test critical integration points that mocks can't verify
3. **Cost-conscious** - Each API call costs money
4. **Reliable** - Use common words that are unlikely to change

## API Cost Estimation

Each e2e test makes one API call:

- Model: `gpt-4o-mini`
- Approximate cost per test: $0.0001 - $0.001 (depending on response length)
- Total cost for all 3 tests: ~$0.0003 - $0.003

## Troubleshooting

### Tests are skipped even with API key set

Make sure your API key:
- Is set as `LLM_API_KEY` environment variable
- Starts with `sk-` (real key, not the test key "test_api_key_12345")
- Is exported in your current shell session

```bash
echo $LLM_API_KEY  # Should print your key
```

### Tests fail with "Access denied"

Your API key might be:
- Invalid or expired
- Not properly exported
- Missing required permissions

### Tests timeout

- OpenAI API can be slow sometimes
- Tests have 60-second timeout by default
- Check your internet connection
- Verify OpenAI service status

## Adding New E2E Tests

Before adding a new e2e test, ask:

1. ❓ Can this be tested with mocks? (If yes, add unit test instead)
2. ❓ Does this test a critical integration point? (If no, skip it)
3. ❓ Is the cost justified? (If no, skip it)

If you answer yes to all questions, then add the e2e test following this pattern:

```python
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_new_feature_real_api():
    """
    E2E test: Brief description of what's being validated.

    This test validates:
    - Specific behavior 1
    - Specific behavior 2
    """
    api_key = _get_api_key()
    client = LLMClient(api_key=api_key, model="gpt-4o-mini")

    # Make real API call
    result = await client.some_method(...)

    # Verify response structure
    assert isinstance(result, dict)
    assert "required_field" in result

    # Print summary for manual verification
    print(f"\n✓ E2E Test passed: some_method(...)")
```

## CI/CD Integration

In CI/CD pipelines:

- E2E tests should be **skipped by default** (no API key set)
- Use `pytest -m "not e2e"` to explicitly skip e2e tests
- Only run e2e tests in dedicated jobs with API key secrets configured
- Consider running e2e tests on schedule (nightly) instead of every commit

```yaml
# Example GitHub Actions
test-unit:
  run: pytest -m "not e2e"

test-e2e:
  # Run only on main branch or schedule
  if: github.ref == 'refs/heads/main'
  env:
    LLM_API_KEY: ${{ secrets.LLM_API_KEY }}
  run: pytest -m e2e
```
