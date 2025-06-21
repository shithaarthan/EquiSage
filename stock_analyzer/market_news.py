# In stock_analyzer/market_news.py

from gnews import GNews
from typing import List, Dict, Any, Set
import pprint

# --- Configuration ---
# These are the broad topics we'll search for. This list is the "secret sauce"
# and can be refined over time to improve relevance for the Indian market.
MACRO_SEARCH_TOPICS = [
    "RBI interest rate decision",
    "India inflation CPI data",
    "India GDP growth forecast",
    "SEBI new regulations",
    "FII DII net investment India",
    "War tension increases"
    # Specific topics for current geopolitical context
    "Crude oil prices Middle East tension", # More targeted than "global"
    "OPEC+ production cuts",
    "USD INR exchange rate forecast" # Foreign/Domestic Institutional Investor flows
]

# We want only the most impactful, recent news for each topic.
ARTICLES_PER_TOPIC = 1
NEWS_TIME_WINDOW = "7d"  # 7-day window for macro news is usually sufficient
MAX_TOTAL_ARTICLES = 9   # A hard cap to keep the context for the LLM concise

def fetch_market_context_news(state: Dict[str, Any]) -> Dict[str, List[Dict[str, str]]]:
    """
    Fetches broad, market-moving news relevant to the Indian economy.

    This function is designed to be a node in a LangGraph. It does not require
    any specific input from the state but provides crucial context for the overall analysis.
    It fetches the top news for a curated list of macroeconomic topics.

    Args:
        state (Dict[str, Any]): The current state of the LangGraph (not used in this node).

    Returns:
        Dict[str, List[Dict[str, str]]]: A dictionary containing a list of
                                         market context news articles.
                                         The key is 'market_context_articles'.
    """
    print("---NODE: Fetching General Market Context News---")

    google_news = GNews(
        period=NEWS_TIME_WINDOW,
        max_results=ARTICLES_PER_TOPIC,
        country='IN',
        language='en'
    )

    all_articles: List[Dict[str, str]] = []
    seen_urls: Set[str] = set() # To avoid duplicate articles from different search terms

    try:
        for topic in MACRO_SEARCH_TOPICS:
            if len(all_articles) >= MAX_TOTAL_ARTICLES:
                print(f"Reached max article limit of {MAX_TOTAL_ARTICLES}. Stopping search.")
                break

            print(f"Searching for macro topic: '{topic}'...")
            articles = google_news.get_news(topic)

            for article in articles:
                url = article.get("url")
                # Check if we have already added this article from another search
                if url and url not in seen_urls:
                    formatted_article = {
                        "topic": topic, # Add the topic to know why this news was pulled
                        "title": article["title"],
                        "url": url,
                        "published_date": article.get("published date", "N/A"),
                        "source": article["publisher"]["title"],
                        "summary": article.get("description", "No summary available.")
                    }
                    all_articles.append(formatted_article)
                    seen_urls.add(url)
        
        if not all_articles:
            print("No significant market context news found.")
            return {"market_context_articles": []}
        
        print(f"Successfully fetched {len(all_articles)} macro-economic/market articles.")
        return {"market_context_articles": all_articles}

    except Exception as e:
        print(f"An error occurred while fetching market context news: {e}")
        return {"market_context_articles": []}

# --- Self-testing block ---
# This allows you to run this file directly to test its functionality
if __name__ == '__main__':
    print("---Testing Market Context News Fetching Module---")

    # This function doesn't need any input state, so we pass an empty dict
    market_data = fetch_market_context_news({})

    print("\n--- Results ---")
    if market_data['market_context_articles']:
        pprint.pprint(market_data['market_context_articles'])
    else:
        print("Could not fetch any market context news data.")