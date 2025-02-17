from duckduckgo_search import DDGS
from duckduckgo_search.exceptions import (
    DuckDuckGoSearchException,
    RatelimitException,
    TimeoutException,
    ConversationLimitException
)
import time

def test_search_functionality():
    print("Starting DuckDuckGo Search Tests...")
    
    try:
        # Initialize DDGS
        ddgs = DDGS()
        
        # Test 1: Text Search
        print("\n1. Testing text search...")
        text_results = ddgs.text(
            keywords="Python programming",
            region="wt-wt",
            safesearch="moderate",
            timelimit="m",
            max_results=5
        )
        print(f"Text search results: {len(text_results)} items found")
        for result in text_results:
            print(f"- {result['title']}")

        # Test 2: Image Search
        print("\n2. Testing image search...")
        image_results = ddgs.images(
            keywords="python logo",
            region="wt-wt",
            safesearch="moderate",
            size="Medium",
            color=None,
            type_image="photo",
            max_results=3
        )
        print(f"Image search results: {len(image_results)} items found")
        for result in image_results:
            print(f"- {result['title']}: {result['image']}")

        # Test 3: News Search
        print("\n3. Testing news search...")
        news_results = ddgs.news(
            keywords="technology",
            region="wt-wt",
            safesearch="moderate",
            timelimit="d",
            max_results=3
        )
        print(f"News search results: {len(news_results)} items found")
        for result in news_results:
            print(f"- {result['title']} ({result['date']})")

        # Test 4: Video Search
        print("\n4. Testing video search...")
        video_results = ddgs.videos(
            keywords="python tutorial",
            region="wt-wt",
            safesearch="moderate",
            resolution="high",
            duration="medium",
            max_results=3
        )
        print(f"Video search results: {len(video_results)} items found")
        for result in video_results:
            print(f"- {result['title']}")

        # Test 5: AI Chat
        print("\n5. Testing AI chat...")
        chat_response = ddgs.chat(
            keywords="What is Python programming?",
            model="o3-mini"
        )
        print(f"Chat response received: {chat_response[:100]}...")

    except RatelimitException as e:
        print(f"Rate limit exceeded: {e}")
    except TimeoutException as e:
        print(f"Request timed out: {e}")
    except ConversationLimitException as e:
        print(f"Conversation limit reached: {e}")
    except DuckDuckGoSearchException as e:
        print(f"DuckDuckGo search error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

def main():
    print("DuckDuckGo Search Package Test Suite")
    print("====================================")
    
    try:
        test_search_functionality()
        print("\nAll tests completed!")
    except Exception as e:
        print(f"\nTest suite failed: {e}")

if __name__ == "__main__":
    main()