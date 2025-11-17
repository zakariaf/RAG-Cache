# CI/CD Test Performance Issue

## Problem

CI/CD tests are taking **30+ minutes** to complete, with the job timing out or running very slowly. After 30 minutes, only 19% of tests (203/1065) had completed.

## Root Cause Analysis

### Epic 6 Tests (Fixed ✅)
My error recovery tests were using actual `asyncio.sleep()` delays:
- Fixed by mocking `asyncio.sleep` in all retry strategy tests
- Commit: `fix: mock asyncio.sleep in error recovery tests for speed`

### Existing Tests (Still Slow ⚠️)
Analysis of `tests/unit/` shows many existing tests with real sleep delays:

```bash
# Circuit breaker tests
tests/unit/llm/test_circuit_breaker.py:321:        await asyncio.sleep(1.1)
tests/unit/llm/test_circuit_breaker.py:123:        await asyncio.sleep(0.15)
tests/unit/llm/test_circuit_breaker.py:161:        await asyncio.sleep(0.15)
tests/unit/llm/test_circuit_breaker.py:186:        await asyncio.sleep(0.15)
tests/unit/llm/test_circuit_breaker.py:353:        await asyncio.sleep(0.15)

# Timeout handler tests
tests/unit/llm/test_timeout_handler.py:64:            await asyncio.sleep(1.0)
tests/unit/llm/test_timeout_handler.py:79:            await asyncio.sleep(1.0)
tests/unit/llm/test_timeout_handler.py:220:            await asyncio.sleep(2.0)
tests/unit/llm/test_timeout_handler.py:93:            await asyncio.sleep(0.2)
tests/unit/llm/test_timeout_handler.py:107:            await asyncio.sleep(0.2)
tests/unit/llm/test_timeout_handler.py:171:            await asyncio.sleep(0.2)

# Qdrant pool tests
tests/unit/cache/test_qdrant_pool.py:316:            await asyncio.sleep(0.2)
tests/unit/cache/test_qdrant_pool.py:387:                await asyncio.sleep(0.1)
```

**Estimated impact:**
- Circuit breaker: ~1.85 seconds per test × multiple tests
- Timeout handler: ~5.6 seconds per test × multiple tests
- Qdrant pool: ~0.3 seconds per test

With 1065 tests total, even small delays compound significantly.

## Recommended Fixes

### Option 1: Mock asyncio.sleep (Fastest, Recommended)

Add a global fixture in `tests/conftest.py`:

```python
import asyncio
from unittest.mock import AsyncMock, patch
import pytest

@pytest.fixture(autouse=True)
def mock_sleep_in_tests(request):
    """
    Auto-mock asyncio.sleep in all async tests.

    Tests that explicitly need real sleep can use:
    @pytest.mark.no_mock_sleep
    """
    if "no_mock_sleep" in request.keywords:
        yield
    else:
        with patch("asyncio.sleep", new=AsyncMock()):
            yield
```

Then mark tests that NEED real sleep:
```python
@pytest.mark.no_mock_sleep
async def test_actual_timeout_needed():
    await asyncio.sleep(1.0)  # Real sleep
```

### Option 2: Use pytest-timeout (Partial Fix)

Install and configure:
```bash
pip install pytest-timeout
```

In `pytest.ini`:
```ini
[pytest]
timeout = 5  # Fail any test that takes > 5 seconds
```

This won't speed up tests but will prevent hanging.

### Option 3: Fix Individual Test Files

For each slow test file, add a fixture:

```python
# tests/unit/llm/test_circuit_breaker.py
@pytest.fixture
def mock_sleep():
    with patch("asyncio.sleep", new=AsyncMock()) as mock:
        yield mock

# Then update test signatures:
async def test_circuit_breaker_timeout(self, mock_sleep):
    # Test runs instantly
```

## Impact Analysis

### Before Fixes
- 1065 tests × average 2 seconds = **~35 minutes**
- With timeouts/hangs: **> 60 minutes** (often fails)

### After Option 1 (Mock All Sleep)
- 1065 tests × average 0.1 seconds = **~2-3 minutes**
- Most tests run instantly, only CPU-bound delays

### After Option 2 (Timeout Only)
- Still **~35 minutes**, but won't hang
- Fails fast on problematic tests

### After Option 3 (Per-File Fixes)
- Depends on how many files fixed
- Each file fixed saves **~1-5 minutes**

## Recommended Implementation Plan

1. **Immediate** (Epic 6 PR):
   - ✅ My error recovery tests now mocked
   - Epic 6 tests no longer contribute to slowness

2. **Short-term** (Next PR):
   - Add global `mock_sleep_in_tests` fixture
   - Mark exceptions with `@pytest.mark.no_mock_sleep`
   - Expected CI time: **3-5 minutes**

3. **Long-term** (Refactoring):
   - Review which tests truly need real delays
   - Use fake timers or time-travel libraries
   - Consider `pytest-freezegun` for time-dependent tests

## Testing the Fix

Run locally to verify:
```bash
# Before: measure current time
time pytest tests/unit/llm/test_circuit_breaker.py -v

# After adding mock: should be much faster
time pytest tests/unit/llm/test_circuit_breaker.py -v

# Check all tests still pass
pytest tests/unit/ -v --tb=short
```

## Why This Matters

**Unit tests should be fast:**
- ✅ Test logic, not timing
- ✅ Mock external delays (network, timers)
- ✅ Use fake clocks for time-dependent code
- ❌ Don't use real `asyncio.sleep()` in unit tests

**Integration tests** can have real delays, but they should be:
- Separate test suite (`tests/integration/`)
- Run less frequently (not on every commit)
- Have appropriate timeouts

## Status

- [x] Epic 6 error recovery tests mocked
- [ ] Global sleep mock in conftest.py
- [ ] Individual test file fixes
- [ ] CI time target: < 5 minutes

## Related

- Epic 6: Query Processing Pipeline
- CI/CD optimization
- Test suite performance

---

**Last Updated:** 2025-11-16
**Estimated CI Time Savings:** 30+ minutes → < 5 minutes with global mock
