import os
import json
from typing import Dict, Any
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

try:
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    MODEL = genai.GenerativeModel('gemini-1.5-flash-latest')
    print("Gemini API configured successfully.")
except Exception as e:
    MODEL = None
    print(f"CRITICAL WARNING: Gemini API key not found or invalid. Reporter will fail. {e}")

def _format_data_for_prompt(data: Any, indent=2) -> str:
    if not data:
        return "Not available."
    return json.dumps(data, indent=indent)

def generate_report(state: Dict[str, Any]) -> Dict[str, str]:
    print("---NODE: Generating Final Report (with real Gemini API call)---")

    if not MODEL:
        return {"final_report": "Report generation failed: The Gemini API is not configured."}

    company_name = state.get("company_name", "the company")
    stock_ticker = state.get("stock_ticker", "N/A")
    screener_data = state.get("screener_data")
    technical_analysis = state.get("technical_analysis")
    news_articles = state.get("news_articles")
    market_context_articles = state.get("market_context_articles")
    
    if not screener_data or screener_data.get("error"):
        return {"final_report": f"Could not generate a report for {company_name} due to missing fundamental data."}

    prompt = f"""
    You are EquiSage, an expert AI stock market analyst for the Indian market.
    Your task is to generate a well-structured report for **{company_name} ({stock_ticker})**.

    **CRITICAL FORMATTING RULES:**
    - **MUST** use Telegram-compatible HTML tags for all formatting.
    - **DO NOT USE MARKDOWN.** No `**`, `*`, `#`, or `-`.
    - Use `<b>...</b>` for all titles and bolding.
    - Use `<i>...</i>` for subtitles or disclaimers.
    - Use bullet points with an emoji, like `📈 <b>Metric:</b> ...` or `✅ <b>Pro:</b> ...`.
    - Start the entire report with a main title and a separating line.

    **DATA FOR ANALYSIS:**
    - Fundamental Data: {_format_data_for_prompt(screener_data)}
    - Technical Summary: {_format_data_for_prompt(technical_analysis.get('summary'))}
    - Company News: {_format_data_for_prompt(news_articles)}
    - Market Context: {_format_data_for_prompt(market_context_articles)}

    ---
    **REQUIRED OUTPUT STRUCTURE (FOLLOW THIS TEMPLATE EXACTLY):**

    <b>📊 EquiSage Analysis: {company_name}</b>
    --------------------------------------

    <b>Fundamental Analysis</b>
    [Your detailed analysis of financial health, valuation, pros & cons, and quarterly results. Use bullet points.]
    
    <b>Technical Outlook</b>
    [Your analysis of the technical summary. Interpret the trend, RSI, and moving averages. A chart will be sent separately.]

    <b>Shareholding Pattern</b>
    [Your analysis of Promoter, FII, and DII holding trends and what they suggest about institutional confidence.]

    <b>News & Market Sentiment</b>
    [Synthesize the company-specific news and the broader market context. Identify tailwinds or headwinds.]

    <b>EquiSage Verdict</b>
    [Your final, balanced summary. Synthesize all points into a cohesive final verdict on the stock's current standing, mentioning risks and opportunities.]

    --------------------------------------
    <i>Disclaimer: AI-generated analysis. Not financial advice. DYOR.</i>
    """

    try:
        print("Sending strict HTML-formatted request to Gemini API...")
        response = MODEL.generate_content(prompt)
        final_report = response.text
        print("Successfully received report from Gemini.")
        
    except Exception as e:
        print(f"An error occurred while calling the Gemini API: {e}")
        final_report = f"Failed to generate the AI-powered analysis for {company_name}. An API error occurred."

    return {"final_report": final_report}