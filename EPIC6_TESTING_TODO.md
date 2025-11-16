# Epic 6 Testing Requirements

## Current Status
- **Code Coverage**: 27.13% (below 70% requirement)
- **New Files Added**: 11 modules without tests
- **Test Collection Errors**: 2 (likely import issues in CI)

## Files Requiring Tests

### Embeddings Module (4 files)
- [ ] `app/embeddings/generator.py` - EmbeddingGenerator tests
- [ ] `app/embeddings/model_loader.py` - EmbeddingModelLoader tests  
- [ ] `app/embeddings/cache.py` - EmbeddingCache tests
- [ ] `app/embeddings/batch_processor.py` - EmbeddingBatchProcessor tests

### Processing Module (6 files)
- [ ] `app/processing/normalizer.py` - QueryNormalizer tests
- [ ] `app/processing/validator.py` - QueryValidator tests
- [ ] `app/processing/preprocessor.py` - QueryPreprocessor tests
- [ ] `app/processing/context_manager.py` - RequestContextManager tests
- [ ] `app/processing/pipeline.py` - QueryPipeline tests
- [ ] `app/processing/error_recovery.py` - ErrorRecovery tests

### Services Module (1 file)
- [ ] `app/services/semantic_matcher.py` - SemanticMatcher tests

## Recommendation

These tests correspond to **Epic 6 Task #140: Query Pipeline Integration Tests** which was deferred as non-critical for MVP.

### Suggested Approach:
1. **Unit tests** for each module (test individual components)
2. **Integration tests** for end-to-end pipeline flows
3. **Mock external dependencies** (sentence-transformers, Qdrant)
4. Target **70%+ coverage** for Epic 6 modules

### Priority Order:
1. High: Generator, Normalizer, Validator (core functionality)
2. Medium: Pipeline, Preprocessor, SemanticMatcher (orchestration)
3. Low: Cache, BatchProcessor, ErrorRecovery (optimizations)

## Note
All Epic 6 code passes quality checks (black, flake8, isort, mypy). Only test coverage remains to be addressed.
