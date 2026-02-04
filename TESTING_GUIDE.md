# 🧪 Testing Guide - Assistant Brain OS

## 📋 Overview

Comprehensive test suite to ensure system robustness and reliability.

---

## 🎯 Test Coverage

### 1. **Agent Tests** (`test_agents.py`)

Tests all three AI agents:

**Archivist Tests:**
- ✅ Successful knowledge saving
- ✅ Successful knowledge searching
- ✅ Error handling
- ✅ Empty text handling

**Researcher Tests:**
- ✅ Successful research execution
- ✅ Topic-based research
- ✅ Error handling

**Writer Tests:**
- ✅ Successful content writing
- ✅ Writing with research data
- ✅ Different format types
- ✅ Error handling

### 2. **Message Handling Tests** (`test_message_handling.py`)

Tests message routing and detection:

**Casual Message Detection:**
- ✅ Greetings detection
- ✅ Thanks detection
- ✅ Goodbye detection
- ✅ "How are you" detection
- ✅ Actionable messages not detected as casual
- ✅ Short unclear messages
- ✅ Messages with keywords

**Intent Routing:**
- ✅ Save/archive intent
- ✅ Research intent
- ✅ Writing intent
- ✅ Default fallback

**User Settings:**
- ✅ Default settings retrieval
- ✅ Existing settings retrieval
- ✅ Settings persistence

**Thinking Messages:**
- ✅ Message existence
- ✅ Uniqueness
- ✅ Non-empty validation

### 3. **Contract Tests** (`test_contracts.py`)

Tests data models and validation:

**Job Model:**
- ✅ Creation with defaults
- ✅ Creation with custom values
- ✅ Status enumeration
- ✅ Validation
- ✅ History management
- ✅ Serialization

**Knowledge Entry:**
- ✅ Entry creation
- ✅ Metadata handling
- ✅ Validation
- ✅ Empty tags

**Agent Response:**
- ✅ Success responses
- ✅ Failure responses
- ✅ Agent chaining
- ✅ Additional data
- ✅ Validation

### 4. **Worker Tests** (`test_worker.py`)

Tests job processing:

**Job Processing:**
- ✅ Successful processing
- ✅ Failed job retry
- ✅ Max retries exceeded
- ✅ Agent chaining

**Dynamic Agent Loading:**
- ✅ Load archivist
- ✅ Load researcher
- ✅ Load writer

### 5. **Integration Tests** (`test_integration.py`)

Tests end-to-end workflows:

**Workflows:**
- ✅ Save and search workflow
- ✅ Research and write workflow

**Error Recovery:**
- ✅ Agent failure recovery
- ✅ Malformed payload handling

**Concurrency:**
- ✅ Multiple agents in parallel

**Data Persistence:**
- ✅ Job serialization/deserialization
- ✅ Response serialization

### 6. **Configuration Tests** (`test_config.py`)

Tests configuration loading:

**Configuration:**
- ✅ Required vars loading
- ✅ Default values
- ✅ Database paths

---

## 🚀 Running Tests

### Quick Start

```bash
# Run all tests
./run_tests.sh
```

### Manual Commands

```bash
# Activate virtual environment
source venv/bin/activate

# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_agents.py -v

# Run specific test class
python -m pytest tests/test_agents.py::TestArchivist -v

# Run specific test
python -m pytest tests/test_agents.py::TestArchivist::test_archivist_save_success -v

# Run with coverage
python -m pytest tests/ --cov=. --cov-report=html

# Run only unit tests (exclude integration)
python -m pytest tests/ -m "not integration"

# Run only integration tests
python -m pytest tests/test_integration.py -v
```

---

## 📊 Test Output

### Successful Run

```
🧪 Running Assistant Brain OS Test Suite
========================================

📝 Running unit tests...
tests/test_agents.py::TestArchivist::test_archivist_save_success PASSED
tests/test_agents.py::TestArchivist::test_archivist_search_success PASSED
tests/test_agents.py::TestArchivist::test_archivist_error_handling PASSED
...

======== 45 passed in 5.23s ========

✅ Test suite complete!
```

### Failed Test

```
tests/test_agents.py::TestArchivist::test_archivist_save_success FAILED

FAILED tests/test_agents.py::TestArchivist::test_archivist_save_success
AssertionError: assert False is True
```

---

## 🛠️ Writing New Tests

### Test Structure

```python
import pytest
from unittest.mock import Mock, patch, AsyncMock

class TestYourFeature:
    """Test your feature"""

    @pytest.mark.asyncio
    async def test_feature_success(self):
        """Test successful feature execution"""
        # Arrange
        input_data = {"key": "value"}

        # Act
        result = await your_function(input_data)

        # Assert
        assert result.success is True
        assert result.output != ""
```

### Mocking Guidelines

**Mock external APIs:**
```python
with patch('agents.archivist.archivist_agent.run') as mock_run:
    mock_run.return_value = AsyncMock(output="Success")
    result = await archivist.execute(payload)
```

**Mock Redis:**
```python
with patch('worker.r') as mock_redis:
    mock_redis.lpush.return_value = True
    # Test code
```

**Mock Telegram bot:**
```python
with patch('worker.bot.send_message', new_callable=AsyncMock) as mock_send:
    await process_job(job_data)
    mock_send.assert_called_once()
```

### Test Best Practices

1. **Use descriptive names**
   - ✅ `test_archivist_save_success`
   - ❌ `test_1`

2. **Test one thing per test**
   - Each test should verify one specific behavior

3. **Use AAA pattern**
   - **Arrange:** Set up test data
   - **Act:** Execute the function
   - **Assert:** Verify results

4. **Mock external dependencies**
   - Don't make real API calls
   - Don't access real databases
   - Don't send real Telegram messages

5. **Test edge cases**
   - Empty inputs
   - Invalid inputs
   - Network errors
   - Timeouts

---

## 🎯 Test Markers

Use markers to categorize tests:

```python
@pytest.mark.asyncio  # Async test
@pytest.mark.slow     # Slow running test
@pytest.mark.integration  # Integration test
@pytest.mark.unit     # Unit test
```

Run specific markers:
```bash
# Run only slow tests
pytest -m slow

# Run all except slow tests
pytest -m "not slow"

# Run unit tests only
pytest -m unit
```

---

## 📈 Coverage Report

After running tests with coverage:

```bash
# View in terminal
pytest tests/ --cov=. --cov-report=term-missing

# Generate HTML report
pytest tests/ --cov=. --cov-report=html

# Open HTML report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

**Coverage targets:**
- ✅ Aim for >80% overall coverage
- ✅ 100% coverage for critical paths
- ✅ All agents fully tested
- ✅ Error handling tested

---

## 🐛 Debugging Failed Tests

### Verbose Output

```bash
# Show detailed output
pytest tests/ -vv

# Show print statements
pytest tests/ -s

# Show full traceback
pytest tests/ --tb=long
```

### Run Failed Tests Only

```bash
# Run tests that failed last time
pytest --lf

# Run failed tests first, then others
pytest --ff
```

### Debug Mode

```python
# Add breakpoint in test
def test_something():
    import pdb; pdb.set_trace()
    # Test code
```

Run with:
```bash
pytest tests/ -s  # -s allows pdb interaction
```

---

## ✅ Continuous Integration

### Pre-commit Hook

Create `.git/hooks/pre-commit`:

```bash
#!/bin/bash
echo "Running tests before commit..."
./run_tests.sh
if [ $? -ne 0 ]; then
    echo "Tests failed! Commit aborted."
    exit 1
fi
```

Make executable:
```bash
chmod +x .git/hooks/pre-commit
```

### GitHub Actions (Example)

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.12
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-cov
      - name: Run tests
        run: ./run_tests.sh
```

---

## 📚 Additional Test Files Needed

### Future Test Additions

1. **`test_database.py`** - Database operations
   - ChromaDB interactions
   - SQLite operations
   - Vector search

2. **`test_telegram.py`** - Telegram bot handlers
   - Command handlers
   - Message handlers
   - Callback queries

3. **`test_redis.py`** - Redis queue operations
   - Queue push/pop
   - Job serialization
   - Queue management

4. **`test_performance.py`** - Performance tests
   - Response time
   - Concurrent users
   - Memory usage

---

## 🎓 Test Maintenance

### Regular Tasks

- ✅ Run tests before commits
- ✅ Update tests when code changes
- ✅ Add tests for new features
- ✅ Fix broken tests immediately
- ✅ Review coverage reports weekly
- ✅ Remove obsolete tests

### Test Health Metrics

Monitor:
- Test count (should grow with features)
- Coverage percentage (aim for >80%)
- Test execution time (keep fast)
- Flaky tests (fix immediately)
- Test failures (investigate all)

---

## 📝 Test Checklist

Before deployment:

- [ ] All tests passing
- [ ] Coverage >80%
- [ ] Integration tests passing
- [ ] Error handling tested
- [ ] Edge cases covered
- [ ] Performance acceptable
- [ ] No flaky tests
- [ ] Documentation updated

---

## 🚀 Quick Commands Reference

```bash
# Run all tests
./run_tests.sh

# Run specific file
pytest tests/test_agents.py -v

# Run with coverage
pytest tests/ --cov=. --cov-report=html

# Run only fast tests
pytest tests/ -m "not slow"

# Debug mode
pytest tests/ -s --pdb

# Watch mode (rerun on changes)
pytest-watch tests/
```

---

**🎉 Happy Testing! Ensure your brain is robust!**
