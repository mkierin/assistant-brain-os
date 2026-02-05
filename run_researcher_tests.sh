#!/bin/bash

echo "=================================================="
echo "   DEEP RESEARCHER TEST SUITE"
echo "   Testing with REAL API calls (not mocked)"
echo "=================================================="
echo ""

# Activate virtual environment
source venv/bin/activate

# Set Python path
export PYTHONPATH=/root/assistant-brain-os:$PYTHONPATH

# Run tests with verbose output and logging
pytest tests/test_researcher_deep.py \
    -v \
    --tb=short \
    --log-cli-level=INFO \
    --capture=no \
    -s

echo ""
echo "=================================================="
echo "   TEST RUN COMPLETE"
echo "=================================================="
