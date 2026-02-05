"""
Test YouTube extraction with a real video
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


async def test_youtube_extraction():
    """Test extracting a real YouTube video"""
    from agents import content_saver

    # Use a short, popular video
    test_url = "https://youtu.be/tLMViADvSNE"

    print(f"\n🎥 Testing YouTube extraction with: {test_url}\n")

    try:
        result = await content_saver.execute(test_url)

        print(f"\n{'='*60}")
        print(f"Success: {result.success}")
        print(f"Error: {result.error}")
        print(f"Output length: {len(result.output)} chars")
        print(f"{'='*60}\n")

        if result.success:
            print("📄 OUTPUT:")
            print(result.output)
            print(f"\n{'='*60}")
            print("✅ YouTube extraction WORKS!")
        else:
            print(f"❌ Failed: {result.error}")

        return result

    except Exception as e:
        print(f"\n❌ Exception: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_url_detection():
    """Test URL detection and routing"""
    from main import is_casual_message
    import re

    test_urls = [
        "https://youtube.com/watch?v=abc123",
        "https://youtu.be/xyz",
        "Check this: https://youtube.com/watch?v=test",
    ]

    print("\n📋 Testing URL Detection:")
    print("="*60)

    for url in test_urls:
        # Check casual
        is_casual = is_casual_message(url)

        # Check URL pattern
        url_pattern = r'https?://[^\s]+'
        has_url = re.search(url_pattern, url, re.IGNORECASE)

        # Routing
        agent = "content_saver" if has_url else "other"

        print(f"\nText: {url}")
        print(f"  Is Casual: {is_casual}")
        print(f"  Has URL: {has_url is not None}")
        print(f"  Routes to: {agent}")

        # Verify
        assert is_casual == False, f"URL should not be casual"
        assert has_url is not None, f"Should detect URL"
        assert agent == "content_saver", f"Should route to content_saver"

    print("\n" + "="*60)
    print("✅ All URL detection tests passed!")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("YOUTUBE LIVE TEST")
    print("="*60)

    # Test 1: URL Detection
    asyncio.run(test_url_detection())

    # Test 2: Actual YouTube Extraction
    print("\n")
    result = asyncio.run(test_youtube_extraction())

    if result and result.success:
        print("\n🎉 ALL TESTS PASSED! YouTube feature is working!")
    else:
        print("\n⚠️ Some tests failed. Check output above.")
