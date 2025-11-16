# ML Dependencies Strategy

## Overview

This project uses **sentence-transformers** for generating vector embeddings, which depends on PyTorch (~3GB). To keep CI/CD tests fast and avoid 6-hour installation timeouts, we use a **mocking strategy**.

## Strategy

### For Testing (CI/CD)
- **Mock sentence-transformers** in `tests/conftest.py`
- Tests run WITHOUT installing PyTorch
- Fast CI/CD execution (<5 minutes instead of 6+ hours)
- Unit tests verify wrapper logic, not ML model behavior

### For Production
- Install sentence-transformers separately:
  ```bash
  pip install sentence-transformers==2.3.1
  ```
- Or uncomment in `requirements.txt`:
  ```python
  sentence-transformers==2.3.1
  ```

## How It Works

### 1. Test Mocking (`tests/conftest.py`)
```python
import sys
from unittest.mock import MagicMock, Mock

# Mock sentence-transformers before any app imports
mock_sentence_transformer = MagicMock()
mock_sentence_transformer.SentenceTransformer = Mock
sys.modules["sentence_transformers"] = mock_sentence_transformer
```

This allows tests to import `from sentence_transformers import SentenceTransformer` without actually having the package installed.

### 2. Test Fixtures
Tests use mocked models:
```python
@pytest.fixture
def mock_model():
    model = Mock()
    model.encode = Mock(return_value=np.array([0.1, 0.2, 0.3]))
    model.get_sentence_embedding_dimension = Mock(return_value=384)
    return model
```

### 3. Unit Tests Focus
Our unit tests verify:
- ✅ API contracts (correct method calls)
- ✅ Error handling
- ✅ Edge cases
- ✅ Integration between components

NOT testing:
- ❌ Actual ML model behavior (that's SentenceTransformers' job)
- ❌ Embedding quality
- ❌ GPU/CPU performance

## Installation Guide

### Development (with ML models)
```bash
# Install all dependencies including ML
pip install -r requirements-dev.txt
pip install sentence-transformers==2.3.1

# Run with real models
python app/main.py
```

### Testing Only
```bash
# Install test dependencies (no ML)
pip install -r requirements-dev.txt

# Run tests (uses mocks)
pytest tests/unit/ -v --cov=app
```

### Production Deployment

#### Option 1: Docker (Recommended)
```dockerfile
# Add to Dockerfile
RUN pip install sentence-transformers==2.3.1 \
    --index-url https://download.pytorch.org/whl/cpu  # CPU-only
```

#### Option 2: Manual Install
```bash
# Install CPU-only PyTorch (faster, smaller)
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install sentence-transformers==2.3.1

# Or install with CUDA support (for GPU)
pip install sentence-transformers==2.3.1
```

## CI/CD Configuration

### GitHub Actions
```yaml
# .github/workflows/ci.yml
- name: Install dependencies
  run: |
    python -m pip install --upgrade pip
    pip install -r requirements-dev.txt
    # sentence-transformers is mocked, not installed

- name: Run tests
  run: pytest tests/unit/ --cov=app --cov-fail-under=70
```

Benefits:
- ⚡ Fast installation (~2 minutes vs 6+ hours)
- 💾 Small cache size (~100MB vs 3GB)
- ✅ Tests pass without GPU
- 🎯 Focuses on code logic, not ML behavior

## Troubleshooting

### "ModuleNotFoundError: No module named 'sentence_transformers'"
**In tests:** This is normal - tests mock this module.
**In production:** Install sentence-transformers:
```bash
pip install sentence-transformers==2.3.1
```

### "Tests fail with AttributeError on SentenceTransformer"
Check that `tests/conftest.py` mocking is loaded before tests run.
Pytest should automatically load conftest.py first.

### "Production code fails to load models"
Ensure sentence-transformers is installed:
```bash
python -c "import sentence_transformers; print('OK')"
```

If not installed:
```bash
pip install sentence-transformers==2.3.1
```

## Why This Approach?

### Problem
- PyTorch is **~3GB** to download
- Takes **hours** to install in CI
- Not needed for unit testing wrapper code
- Causes CI timeouts (6+ hours)

### Solution
- Mock in tests → Fast CI (< 5 minutes)
- Install separately for production → Works when needed
- Test wrapper logic → Same coverage, no ML dependency

### Trade-offs
- ✅ **Pro:** Fast CI/CD, no timeouts
- ✅ **Pro:** Smaller test environment
- ✅ **Pro:** Tests focus on our code
- ⚠️ **Con:** Requires manual installation for production
- ⚠️ **Con:** Integration tests need real models (run separately)

## Integration Testing

For testing actual embedding generation:
```bash
# Install ML dependencies
pip install sentence-transformers==2.3.1

# Run integration tests (not in CI)
pytest tests/integration/test_embeddings.py -v
```

## References

- [SentenceTransformers Documentation](https://www.sbert.net/)
- [PyTorch Installation Guide](https://pytorch.org/get-started/locally/)
- [Mocking in Python](https://docs.python.org/3/library/unittest.mock.html)
