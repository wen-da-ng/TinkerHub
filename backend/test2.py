from duckduckgo_search import DDGS
from duckduckgo_search.exceptions import DuckDuckGoSearchException
import time

def search_and_summarize(topic, max_news=5):
    print(f"\nSearching and summarizing news about: {topic}")
    print("=" * 50)
    
    try:
        ddgs = DDGS()
        
        # Search for news
        print("\nFetching news articles...")
        news_results = ddgs.news(
            keywords=topic,
            region="wt-wt",
            safesearch="moderate",
            timelimit="d",  # Last 24 hours
            max_results=max_news
        )
        
        if not news_results:
            print("No news articles found.")
            return
        
        # Prepare news content for summarization
        articles_text = "Please summarize these news articles:\n\n"
        
        for i, article in enumerate(news_results, 1):
            print(f"\nArticle {i}:")
            print(f"Title: {article['title']}")
            print(f"Date: {article['date']}")
            print(f"Source: {article['source']}")
            
            articles_text += f"Article {i}:\n"
            articles_text += f"Title: {article['title']}\n"
            articles_text += f"Content: {article['body']}\n\n"
        
        # Get AI summary
        print("\nGenerating summary...")
        summary = ddgs.chat(
            keywords=articles_text,
            model="o3-mini"
        )
        
        print("\nSummary of Recent News:")
        print("-" * 30)
        print(summary)
        
    except DuckDuckGoSearchException as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

def main():
    # Test with different topics
    topics = [
        "artificial intelligence developments",
        "space exploration",
        "climate change"
    ]
    
    for topic in topics:
        search_and_summarize(topic, max_news=3)
        time.sleep(2)  # Pause between topics to avoid rate limiting

if __name__ == "__main__":
    main()