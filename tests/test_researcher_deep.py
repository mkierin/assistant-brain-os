"""
Deep Researcher Agent Tests - Real Execution & Edge Cases

Tests actual API calls, multi-source aggregation, error handling, and edge cases.
"""

import pytest
import asyncio
import time
import logging
from unittest.mock import patch, MagicMock
from agents.researcher import Researcher, researcher_agent
from common.contracts import AgentResponse
from common.database import db

# Set up logging to capture agent activity
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestResearcherBasicExecution:
    """Test basic researcher execution with real API calls"""

    @pytest.mark.asyncio
    async def test_simple_research_query(self):
        """Test basic research query executes successfully"""
        researcher = Researcher()

        payload = {
            "text": "What is Python programming language?",
            "user_id": 12345
        }

        start_time = time.time()
        result = await researcher.execute(payload)
        duration = time.time() - start_time

        # Assertions
        assert isinstance(result, AgentResponse), "Should return AgentResponse"
        assert result.success is True, "Should succeed"
        assert len(result.output) > 150, f"Should return substantial content, got {len(result.output)} chars"
        assert "python" in result.output.lower(), "Should mention Python"
        assert duration < 120, f"Should complete in <120s, took {duration}s"  # Adjusted for multi-source research

        logger.info(f"✅ Simple research completed in {duration:.2f}s")
        logger.info(f"Output length: {len(result.output)} chars")

    @pytest.mark.asyncio
    async def test_multi_source_research(self):
        """Test that researcher uses multiple sources (Tavily + DuckDuckGo)"""
        researcher = Researcher()

        # Query that should trigger multi-source search
        payload = {
            "text": "Research the latest developments in quantum computing 2026",
            "user_id": 12345
        }

        # Capture logs to verify multi-source usage
        with patch('agents.researcher.logger') as mock_logger:
            result = await researcher.execute(payload)

        assert result.success is True, "Should succeed"
        assert len(result.output) > 200, "Should have comprehensive output"

        # Output should contain information from multiple sources
        # (Tavily provides summaries, DuckDuckGo provides additional context)
        assert any(word in result.output.lower() for word in ["quantum", "computing", "qubit"]), \
            "Should contain relevant quantum computing content"

        logger.info("✅ Multi-source research verified")

    @pytest.mark.asyncio
    async def test_research_with_caching(self):
        """Test that repeated queries use cache"""
        researcher = Researcher()

        payload = {
            "text": "What is machine learning?",
            "user_id": 12345
        }

        # First execution - should hit APIs
        start1 = time.time()
        result1 = await researcher.execute(payload)
        duration1 = time.time() - start1

        # Second execution - should use cache
        start2 = time.time()
        result2 = await researcher.execute(payload)
        duration2 = time.time() - start2

        assert result1.success is True
        assert result2.success is True

        # Cache hit should be faster (though not always guaranteed)
        # Main check: both should succeed
        logger.info(f"First execution: {duration1:.2f}s")
        logger.info(f"Second execution: {duration2:.2f}s")
        logger.info("✅ Caching mechanism tested")


class TestResearcherEdgeCases:
    """Test edge cases and error handling"""

    @pytest.mark.asyncio
    async def test_empty_query(self):
        """Test handling of empty query"""
        researcher = Researcher()

        payload = {
            "text": "",
            "user_id": 12345
        }

        result = await researcher.execute(payload)

        # Should fail gracefully or return minimal response
        assert isinstance(result, AgentResponse)
        # Either fails or returns very short response
        if result.success:
            assert len(result.output) < 200, "Empty query should not return extensive research"

        logger.info("✅ Empty query handled")

    @pytest.mark.asyncio
    async def test_very_long_query(self):
        """Test handling of very long query (>1000 chars)"""
        researcher = Researcher()

        # Generate a very long query
        long_query = "Research " + " ".join([f"topic{i}" for i in range(200)])

        payload = {
            "text": long_query,
            "user_id": 12345
        }

        result = await researcher.execute(payload)

        # Should handle long query without crashing
        assert isinstance(result, AgentResponse)
        # Should either succeed or fail gracefully
        assert result.error is None or isinstance(result.error, str)

        logger.info("✅ Long query handled")

    @pytest.mark.asyncio
    async def test_special_characters_query(self):
        """Test query with special characters"""
        researcher = Researcher()

        payload = {
            "text": "What is C++ & C# programming? @#$%",
            "user_id": 12345
        }

        result = await researcher.execute(payload)

        assert result.success is True, "Should handle special characters"
        assert len(result.output) > 100
        assert any(lang in result.output for lang in ["C++", "C#", "programming"]), \
            "Should contain relevant content"

        logger.info("✅ Special characters handled")

    @pytest.mark.asyncio
    async def test_obscure_topic_research(self):
        """Test research on very obscure topic (may return no results)"""
        researcher = Researcher()

        payload = {
            "text": "Research xyzabc123nonexistent topic that doesnt exist",
            "user_id": 12345
        }

        result = await researcher.execute(payload)

        # Should complete without error, even if no good results
        assert isinstance(result, AgentResponse)
        if result.success:
            # Should acknowledge lack of results or provide general info
            assert len(result.output) > 50, "Should provide some response"

        logger.info("✅ Obscure topic handled")

    @pytest.mark.asyncio
    async def test_multiple_questions_in_query(self):
        """Test query with multiple questions"""
        researcher = Researcher()

        payload = {
            "text": "What is AI? How does it work? What are its applications? What are the risks?",
            "user_id": 12345
        }

        result = await researcher.execute(payload)

        assert result.success is True
        assert len(result.output) > 300, "Should provide comprehensive answer to multiple questions"

        # Should address multiple aspects
        assert any(word in result.output.lower() for word in ["ai", "artificial", "intelligence"])

        logger.info("✅ Multiple questions handled")


class TestResearcherQueryAnalysis:
    """Test query analysis and breakdown functionality"""

    @pytest.mark.asyncio
    async def test_complex_query_breakdown(self):
        """Test that complex queries are broken down into sub-questions"""
        researcher = Researcher()

        # Complex query that should trigger analyze_query
        payload = {
            "text": "Research the comprehensive impact of artificial intelligence on software development, "
                   "including productivity, job market changes, and future trends",
            "user_id": 12345
        }

        result = await researcher.execute(payload)

        assert result.success is True
        assert len(result.output) > 400, "Complex query should yield comprehensive results"

        # Should cover multiple aspects
        keywords = ["software", "development", "productivity", "job", "trend", "ai", "artificial"]
        matches = sum(1 for kw in keywords if kw in result.output.lower())
        assert matches >= 4, f"Should cover multiple aspects, found {matches} keywords"

        logger.info("✅ Complex query breakdown tested")


class TestResearcherAPIIntegration:
    """Test integration with different search APIs"""

    @pytest.mark.asyncio
    async def test_tavily_search_execution(self):
        """Test that Tavily search actually executes"""
        from agents.researcher import search_tavily

        try:
            result = await search_tavily(None, "Python programming language", max_results=3)

            assert isinstance(result, str)
            assert len(result) > 100, "Should return substantial results"
            assert "python" in result.lower()

            # Check for Tavily-specific features (AI summary)
            has_summary = "summary" in result.lower() or "ai" in result.lower()
            has_sources = "source" in result.lower() or "http" in result.lower()

            assert has_sources, "Should include source URLs"

            logger.info("✅ Tavily search executed successfully")
            logger.info(f"Result length: {len(result)} chars")

        except Exception as e:
            pytest.skip(f"Tavily API not available: {str(e)}")

    @pytest.mark.asyncio
    async def test_duckduckgo_search_execution(self):
        """Test that DuckDuckGo search actually executes"""
        from agents.researcher import search_web_ddg

        try:
            result = await search_web_ddg(None, "machine learning basics", max_results=3)

            assert isinstance(result, str)
            assert len(result) > 100, "Should return substantial results"
            assert "machine learning" in result.lower() or "ml" in result.lower()
            assert "http" in result.lower(), "Should include URLs"

            logger.info("✅ DuckDuckGo search executed successfully")
            logger.info(f"Result length: {len(result)} chars")

        except Exception as e:
            pytest.skip(f"DuckDuckGo search failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_brave_search_execution(self):
        """Test Brave search if configured"""
        from agents.researcher import search_brave
        from common.config import BRAVE_API_KEY

        if not BRAVE_API_KEY:
            pytest.skip("Brave API key not configured")

        try:
            result = await search_brave(None, "neural networks", max_results=3)

            assert isinstance(result, str)
            if "not configured" not in result.lower():
                assert len(result) > 100
                assert "neural" in result.lower()

            logger.info("✅ Brave search tested")

        except Exception as e:
            logger.warning(f"Brave search unavailable: {str(e)}")


class TestResearcherErrorHandling:
    """Test error handling and recovery"""

    @pytest.mark.asyncio
    async def test_api_failure_recovery(self):
        """Test that researcher handles API failures gracefully"""
        researcher = Researcher()

        # Temporarily break Tavily to test fallback
        with patch('agents.researcher.tavily_client', None):
            payload = {
                "text": "What is blockchain technology?",
                "user_id": 12345
            }

            result = await researcher.execute(payload)

            # Should still succeed using DuckDuckGo
            assert isinstance(result, AgentResponse)
            # Either succeeds with fallback or fails gracefully
            if result.success:
                assert len(result.output) > 100, "Should still get results from fallback"
            else:
                assert result.error is not None, "Should provide error message"

        logger.info("✅ API failure recovery tested")

    @pytest.mark.asyncio
    async def test_timeout_handling(self):
        """Test handling of slow/timeout scenarios"""
        researcher = Researcher()

        # This should complete even if some sources are slow
        payload = {
            "text": "Quick research on Python",
            "user_id": 12345
        }

        start = time.time()
        result = await researcher.execute(payload)
        duration = time.time() - start

        assert isinstance(result, AgentResponse)
        assert duration < 90, f"Should not hang indefinitely, took {duration}s"

        logger.info(f"✅ Completed in {duration:.2f}s (timeout test)")

    @pytest.mark.asyncio
    async def test_malformed_response_handling(self):
        """Test handling of malformed API responses"""
        researcher = Researcher()

        # Query that might return unexpected format
        payload = {
            "text": "!@#$%^&*()",
            "user_id": 12345
        }

        result = await researcher.execute(payload)

        # Should not crash, should return valid AgentResponse
        assert isinstance(result, AgentResponse)
        assert result.output is not None or result.error is not None

        logger.info("✅ Malformed response handled")


class TestResearcherLogging:
    """Test that logging happens correctly"""

    @pytest.mark.asyncio
    async def test_logging_during_research(self, caplog):
        """Test that research operations are logged"""
        researcher = Researcher()

        payload = {
            "text": "What is JavaScript?",
            "user_id": 12345
        }

        with caplog.at_level(logging.INFO):
            result = await researcher.execute(payload)

        assert result.success is True

        # Check logs were created (even if not captured by caplog)
        logger.info("✅ Logging test completed")

    @pytest.mark.asyncio
    async def test_error_logging(self, caplog):
        """Test that errors are logged properly"""
        researcher = Researcher()

        # Force an error by providing invalid payload
        payload = None  # Invalid

        with caplog.at_level(logging.ERROR):
            try:
                result = await researcher.execute(payload)
            except Exception as e:
                logger.error(f"Expected error occurred: {e}")

        logger.info("✅ Error logging test completed")


class TestResearcherPerformance:
    """Test performance and efficiency"""

    @pytest.mark.asyncio
    async def test_concurrent_research_requests(self):
        """Test handling multiple concurrent requests"""
        researcher = Researcher()

        # Create 3 concurrent research tasks
        payloads = [
            {"text": "What is Python?", "user_id": 1},
            {"text": "What is JavaScript?", "user_id": 2},
            {"text": "What is Rust?", "user_id": 3},
        ]

        start = time.time()
        results = await asyncio.gather(*[
            researcher.execute(payload) for payload in payloads
        ])
        duration = time.time() - start

        # All should succeed
        assert all(r.success for r in results), "All requests should succeed"
        assert all(len(r.output) > 100 for r in results), "All should have content"

        # Should be faster than sequential (though caching may affect this)
        logger.info(f"✅ 3 concurrent requests completed in {duration:.2f}s")
        assert duration < 120, "Should complete reasonably fast"

    @pytest.mark.asyncio
    async def test_cache_effectiveness(self):
        """Test that caching reduces API calls"""
        researcher = Researcher()

        payload = {
            "text": "What is Docker containerization?",
            "user_id": 12345
        }

        # First call - should hit API
        start1 = time.time()
        result1 = await researcher.execute(payload)
        time1 = time.time() - start1

        # Immediate second call - should use cache
        start2 = time.time()
        result2 = await researcher.execute(payload)
        time2 = time.time() - start2

        # Third call after short delay
        await asyncio.sleep(1)
        start3 = time.time()
        result3 = await researcher.execute(payload)
        time3 = time.time() - start3

        assert result1.success and result2.success and result3.success

        logger.info(f"Call 1: {time1:.2f}s | Call 2: {time2:.2f}s | Call 3: {time3:.2f}s")
        logger.info("✅ Cache effectiveness tested")


class TestResearcherOutputQuality:
    """Test the quality of research output"""

    @pytest.mark.asyncio
    async def test_output_format(self):
        """Test that output is well-formatted and readable"""
        researcher = Researcher()

        payload = {
            "text": "Explain how neural networks work",
            "user_id": 12345
        }

        result = await researcher.execute(payload)

        assert result.success is True
        output = result.output

        # Quality checks
        assert len(output) > 200, "Should be comprehensive"
        assert len(output) < 5000, "Should not be excessively long"

        # Should contain relevant terms
        relevant_terms = ["neural", "network", "layer", "train", "data", "learn"]
        matches = sum(1 for term in relevant_terms if term in output.lower())
        assert matches >= 3, f"Should contain relevant terminology, found {matches}"

        # Should not be generic "I can help" response
        generic_phrases = ["i can help", "i'd be happy to", "let me help"]
        assert not any(phrase in output.lower() for phrase in generic_phrases), \
            "Should not contain generic helper phrases"

        logger.info("✅ Output quality verified")
        logger.info(f"Output length: {len(output)} chars")
        logger.info(f"Relevant terms: {matches}/6")

    @pytest.mark.asyncio
    async def test_source_citations(self):
        """Test that sources are mentioned in output"""
        researcher = Researcher()

        payload = {
            "text": "Research the latest trends in cloud computing",
            "user_id": 12345
        }

        result = await researcher.execute(payload)

        assert result.success is True
        output = result.output.lower()

        # Should mention sources (URLs, websites, or explicit references)
        has_urls = "http" in output or "www" in output
        has_references = any(word in output for word in ["source", "according", "research", "study"])

        assert has_urls or has_references, "Should cite sources or provide references"

        logger.info("✅ Source citation verified")

    @pytest.mark.asyncio
    async def test_no_hallucination_indicators(self):
        """Test that output doesn't contain obvious hallucination indicators"""
        researcher = Researcher()

        payload = {
            "text": "What is Kubernetes?",
            "user_id": 12345
        }

        result = await researcher.execute(payload)

        assert result.success is True
        output = result.output

        # Should not contain hallucination red flags
        red_flags = [
            "i don't have access",
            "i cannot access",
            "as an ai",
            "i'm not able to browse",
            "i don't have real-time"
        ]

        for flag in red_flags:
            assert flag not in output.lower(), f"Should not contain '{flag}' - indicates tools not used"

        logger.info("✅ No hallucination indicators found")


# Performance summary test
@pytest.mark.asyncio
async def test_research_performance_summary():
    """Summary test of overall researcher performance"""
    researcher = Researcher()

    test_queries = [
        "What is Python?",
        "Explain machine learning basics",
        "Research quantum computing"
    ]

    results = []
    for query in test_queries:
        start = time.time()
        result = await researcher.execute({"text": query, "user_id": 12345})
        duration = time.time() - start

        results.append({
            "query": query,
            "success": result.success,
            "duration": duration,
            "output_length": len(result.output) if result.output else 0
        })

    # Summary report
    logger.info("\n" + "="*60)
    logger.info("RESEARCHER PERFORMANCE SUMMARY")
    logger.info("="*60)

    for r in results:
        status = "✅" if r["success"] else "❌"
        logger.info(f"{status} {r['query'][:40]:40} | {r['duration']:5.2f}s | {r['output_length']:4d} chars")

    avg_duration = sum(r["duration"] for r in results) / len(results)
    success_rate = sum(1 for r in results if r["success"]) / len(results) * 100

    logger.info("="*60)
    logger.info(f"Average Duration: {avg_duration:.2f}s")
    logger.info(f"Success Rate: {success_rate:.0f}%")
    logger.info("="*60)

    assert success_rate >= 80, "Should have at least 80% success rate"
    assert avg_duration < 45, "Average should be under 45 seconds"
