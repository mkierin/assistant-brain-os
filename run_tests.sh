#!/bin/bash
# Test runner script for Assistant Brain OS

echo "🧪 Running Assistant Brain OS Test Suite"
echo "========================================"

# Activate virtual environment
source venv/bin/activate

# Set test environment variables
export OPENAI_API_KEY="test-key"
export DEEPSEEK_API_KEY="test-key"
export TELEGRAM_TOKEN="test-token"
export LLM_PROVIDER="deepseek"
export REDIS_URL="redis://localhost:6379"
export DATABASE_PATH="data/test_brain.db"
export CHROMA_PATH="data/test_chroma"

# Run tests with different verbosity levels

echo ""
echo "📝 Running unit tests..."
python -m pytest tests/ -v -m "not integration"

echo ""
echo "🔗 Running integration tests..."
python -m pytest tests/test_integration.py -v

echo ""
echo "📊 Running all tests with coverage..."
python -m pytest tests/ --cov=. --cov-report=term-missing --cov-report=html

echo ""
echo "✅ Test suite complete!"
echo ""
echo "📁 Coverage report available at: htmlcov/index.html"
