# In stock_analyzer/screener.py

import requests
from bs4 import BeautifulSoup
from typing import Dict, Any, List
import pprint
import time

# --- Configuration ---
BASE_URL = "https://www.screener.in/company/{symbol}/"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'
}

def _parse_key_ratios(soup: BeautifulSoup) -> Dict[str, Any]:
    """Parses the main ratios section at the top of the page."""
    ratios = {}
    try:
        data_list = soup.select_one("#top-ratios")
        if not data_list: return ratios
        
        for li in data_list.find_all("li"):
            name_span = li.find("span", class_="name")
            value_span = li.find("span", class_="nowrap value")
            if name_span and value_span:
                name = name_span.text.strip()
                value = value_span.text.strip()
                ratios[name] = value
    except Exception as e:
        print(f"Error parsing key ratios: {e}")
    return ratios

def _parse_pros_and_cons(soup: BeautifulSoup) -> Dict[str, List[str]]:
    """Parses the 'Pros' and 'Cons' section."""
    pros_cons = {"pros": [], "cons": []}
    try:
        # Select all divs that contain pros or cons
        sections = soup.select("div.warning.flex-column")
        for section in sections:
            h3 = section.find("h3")
            if not h3: continue
            
            category_text = h3.text.lower()
            points = [li.text.strip() for li in section.find("ul").find_all("li")]
            
            if "pro" in category_text:
                pros_cons["pros"] = points
            elif "con" in category_text:
                pros_cons["cons"] = points
    except Exception as e:
        print(f"Error parsing pros and cons: {e}")
    return pros_cons

def _parse_quarterly_results(soup: BeautifulSoup) -> Dict[str, Any]:
    """Parses the 'Quarterly Results' table into a structured format."""
    results = {"headers": [], "rows": []}
    try:
        section = soup.select_one("#quarters")
        if not section: return results
        
        table = section.find("table")
        # Get headers (the dates of the quarters)
        headers = [th.text.strip() for th in table.select("thead th")][1:] # Skip first empty header
        results["headers"] = headers
        
        # Get rows (e.g., Sales, Net Profit)
        for row in table.select("tbody tr"):
            row_data = [td.text.strip().replace('\n', '').replace(' ', '') for td in row.find_all("td")]
            if row_data:
                # Format: {'metric': 'Net Profit', 'values': ['1000', '1100', ...]}
                metric_name = row_data[0].replace('+', '').strip()
                values = row_data[1:]
                results["rows"].append({"metric": metric_name, "values": values})
    except Exception as e:
        print(f"Error parsing quarterly results: {e}")
    return results

def _parse_shareholding_pattern(soup: BeautifulSoup) -> Dict[str, Any]:
    """Parses the 'Shareholding Pattern' table."""
    shareholding = {"headers": [], "rows": []}
    try:
        section = soup.select_one("#shareholding")
        if not section: return shareholding
        
        table = section.find("table")
        headers = [th.text.strip() for th in table.select("thead th")][1:]
        shareholding["headers"] = headers
        
        for row in table.select("tbody tr"):
            row_data = [td.text.strip() for td in row.find_all("td")]
            if row_data:
                metric_name = row_data[0]
                values = row_data[1:]
                shareholding["rows"].append({"metric": metric_name, "values": values})
    except Exception as e:
        print(f"Error parsing shareholding pattern: {e}")
    return shareholding

def fetch_screener_data(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fetches comprehensive data for a stock from Screener.in.
    This is a powerful, all-in-one data collector.
    """
    print("---NODE: Fetching Data from Screener.in---")
    
    try:
        stock_symbol = state["stock_ticker"].replace(".NS", "")
    except KeyError as e:
        print(f"Error: Missing 'stock_ticker' in state - {e}")
        return {"screener_data": {}}

    url = BASE_URL.format(symbol=stock_symbol)
    print(f"Scraping URL: {url}")

    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Check if it's a valid page
        if soup.find("h1", class_="text-center"):
            print(f"Error: Company '{stock_symbol}' not found on Screener.in")
            return {"screener_data": {"error": "Company not found"}}

        # Run all our parsers
        key_ratios = _parse_key_ratios(soup)
        pros_cons = _parse_pros_and_cons(soup)
        quarterly_results = _parse_quarterly_results(soup)
        shareholding_pattern = _parse_shareholding_pattern(soup)
        
        # Combine everything into a single structured dictionary
        screener_data = {
            "key_ratios": key_ratios,
            "analysis": pros_cons,
            "quarterly_results": quarterly_results,
            "shareholding_pattern": shareholding_pattern,
            "source_url": url
        }
        
        # We also get the company name, a useful side-effect
        company_name = soup.select_one("h1").text.strip()
        
        return {
            "screener_data": screener_data,
            "company_name": company_name # Update the state with the proper name
        }

    except requests.exceptions.RequestException as e:
        print(f"A network error occurred while fetching from Screener.in: {e}")
        return {"screener_data": {"error": f"Network error: {e}"}}
    except Exception as e:
        print(f"An unexpected error occurred during scraping: {e}")
        return {"screener_data": {"error": f"Scraping failed: {e}"}}

# --- Self-testing block ---
if __name__ == '__main__':
    print("---Testing Screener.in Scraper Module---")
    
    test_state_infy = {"stock_ticker": "INFY.NS"}
    result_infy = fetch_screener_data(test_state_infy)
    pprint.pprint(result_infy)
    
    print("\n" + "="*50 + "\n")
    time.sleep(2)

    test_state_reliance = {"stock_ticker": "RELIANCE.NS"}
    result_reliance = fetch_screener_data(test_state_reliance)
    pprint.pprint(result_reliance)