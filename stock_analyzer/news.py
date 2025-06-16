# In stock_analyzer/news.py

import os
from datetime import datetime, timedelta
from gnews import GNews
from typing import List, Dict, Any

# --- Configuration ---
# Your brainstorming mentioned a 2-week window
NEWS_TIME_WINDOW = "14d"  # e.g., '14d' for 14 days, '1h' for 1 hour
MAX_NEWS_RESULTS = 7     # Limit results to not overwhelm the LLM and to stay concise
# More specific search for Indian market context
SEARCH_QUERY_TEMPLATE = '"{company_name}" OR "{stock_ticker}" stock news India'


def fetch_stock_news(state: Dict[str, Any]) -> Dict[str, List[Dict[str, str]]]:
    """
    Fetches recent news articles for a given stock ticker using Google News.

    This function is designed to be a node in a LangGraph.
    - It reads the 'stock_ticker' and 'company_name' from the state.
    - It fetches relevant news within a predefined time window.
    - It returns a dictionary with a 'news_articles' key, containing
      structured data for the next node (e.g., an LLM analyzer).

    Args:
        state (Dict[str, Any]): The current state of the LangGraph,
                                expected to contain 'stock_ticker' and 'company_name'.

    Returns:
        Dict[str, List[Dict[str, str]]]: A dictionary containing a list of
                                         formatted news articles.
                                         Returns an empty list on failure.
    """
    print("---NODE: Fetching Stock News---")
    
    # 1. Get required data from the state
    try:
        stock_ticker = state["stock_ticker"]
        company_name = state["company_name"] # Using company name yields better search results
    except KeyError as e:
        print(f"Error: Missing required key in state - {e}")
        return {"news_articles": []}

    # 2. Initialize the news client and construct the query
    google_news = GNews(
        period=NEWS_TIME_WINDOW,
        max_results=MAX_NEWS_RESULTS,
        country='IN',  # Focus on India
        language='en'  # English language news
    )
    
    search_query = SEARCH_QUERY_TEMPLATE.format(company_name=company_name, stock_ticker=stock_ticker)
    print(f"Searching news with query: {search_query}")

    # 3. Fetch and process the news articles
    try:
        articles = google_news.get_news(search_query)
        
        if not articles:
            print("No relevant news articles found.")
            return {"news_articles": []}

        # 4. Format the articles into a clean, structured list for the LLM
        formatted_articles = []
        for article in articles:
            formatted_articles.append({
                "title": article["title"],
                "url": article["url"],
                "published_date": article.get("published date", "N/A"),
                "source": article["publisher"]["title"],
                "summary": article.get("description", "No summary available.")
            })
        
        print(f"Successfully fetched {len(formatted_articles)} articles.")
        return {"news_articles": formatted_articles}

    except Exception as e:
        print(f"An error occurred while fetching news: {e}")
        # Return an empty list to allow the graph to continue gracefully
        return {"news_articles": []}


# --- Self-testing block ---
# This allows you to run this file directly to test its functionality
if __name__ == '__main__':
    import pprint

    print("---Testing News Fetching Module---")

    # Mock LangGraph state for a known Indian stock
    mock_state = {
        "stock_ticker": "RELIANCE.NS",
        "company_name": "Reliance Industries"
    }
    
    news_data = fetch_stock_news(mock_state)

    print("\n--- Results ---")
    if news_data['news_articles']:
        pprint.pprint(news_data['news_articles'])
    else:
        print("Could not fetch any news data.")

    print("\n--- Testing with another stock ---")
    mock_state_tcs = {
        "stock_ticker": "TCS.NS",
        "company_name": "Tata Consultancy Services"
    }

    news_data_tcs = fetch_stock_news(mock_state_tcs)

    print("\n--- Results ---")
    if news_data_tcs['news_articles']:
        pprint.pprint(news_data_tcs['news_articles'])
    else:
        print("Could not fetch any news data for TCS.")