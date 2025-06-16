# In stock_analyzer/reporter.py

import os
import json
from typing import Dict, Any
from dotenv import load_dotenv
import google.generativeai as genai

# --- Configuration ---
load_dotenv()

try:
    # Configure the Gemini API client
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    # Use a fast and cost-effective model for this task
    MODEL = genai.GenerativeModel('gemini-1.5-flash-latest')
    print("Gemini API configured successfully.")
except Exception as e:
    MODEL = None
    print(f"CRITICAL WARNING: Gemini API key not found or invalid. Reporter will fail. {e}")


def _format_data_for_prompt(data: Any, indent=2) -> str:
    """Helper function to cleanly format Python dicts/lists into a string for the prompt."""
    if data is None:
        return "Not available."
    # Use json.dumps for a clean, universally readable format.
    return json.dumps(data, indent=indent)

def generate_report(state: Dict[str, Any]) -> Dict[str, str]:
    """
    Takes the final state with all collected data, synthesizes it using the Gemini LLM,
    and generates a comprehensive final report.
    """
    print("---NODE: Generating Final Report (with real Gemini API call)---")

    if not MODEL:
        return {"final_report": "Report generation failed: The Gemini API is not configured."}

    # 1. Extract all the data from the state
    company_name = state.get("company_name", "the company")
    screener_data = state.get("screener_data")
    technical_analysis = state.get("technical_analysis")
    news_articles = state.get("news_articles")
    market_context_articles = state.get("market_context_articles")
    
    if not screener_data or screener_data.get("error"):
        return {"final_report": f"Could not generate a report for {company_name} due to missing fundamental data."}

    # 2. Build the Comprehensive Prompt using the helper for clean formatting
    prompt = f"""
    You are EquiSage, an expert AI stock market analyst for the Indian market. Your tone is professional, insightful, and data-driven.
    Generate a comprehensive, unbiased, and well-structured report for **{company_name}**.
    Analyze the provided data section by section. Do not just repeat the data; provide insights and connect the dots.

    **1. Fundamental Analysis**
    *Source: Screener.in*
    Analyze the company's financial health, valuation, and performance based on this data. Comment on the pros and cons in context.
    - Key Ratios:
    {_format_data_for_prompt(screener_data.get('key_ratios'))}
    - Pros & Cons:
    {_format_data_for_prompt(screener_data.get('analysis'))}
    - Quarterly Results:
    Analyze the trend from the latest quarterly results. Is there growth in sales and profit?
    {_format_data_for_prompt(screener_data.get('quarterly_results'))}
    
    **2. Technical Outlook**
    Based on the technical indicators, what is the current short-to-medium term sentiment?
    - Indicator Summary:
    {_format_data_for_prompt(technical_analysis.get('summary'))}
    - Briefly interpret the price action relative to the key moving averages mentioned. A chart has been generated separately for the user.

    **3. Shareholding Pattern**
    Analyze the shareholding data. What do the recent changes in Promoter, FII, and DII holdings suggest about institutional confidence?
    - Shareholding Pattern & QoQ Changes:
    {_format_data_for_prompt(screener_data.get('shareholding_pattern'))}
    
    **4. News & Market Sentiment**
    Synthesize the recent news. Are there any significant company-specific or market-wide events creating tailwinds or headwinds for the stock?
    - Company-Specific News:
    {_format_data_for_prompt(news_articles)}
    - General Market Context:
    {_format_data_for_prompt(market_context_articles)}

    **5. EquiSage Verdict**
    Conclude with a final, balanced summary. Synthesize all the points above (fundamentals, technicals, shareholding, news) into a cohesive final verdict on the stock's current standing.

    ---
    **Disclaimer:** This is an AI-generated analysis based on publicly available data and is not financial advice. Please conduct your own research before making any investment decisions.
    """

    # 3. Call the Gemini API
    try:
        print("Sending request to Gemini API...")
        response = MODEL.generate_content(prompt)
        final_report = response.text
        print("Successfully received report from Gemini.")
        
    except Exception as e:
        print(f"An error occurred while calling the Gemini API: {e}")
        final_report = f"Failed to generate the AI-powered analysis for {company_name}. An API error occurred."

    return {"final_report": final_report}