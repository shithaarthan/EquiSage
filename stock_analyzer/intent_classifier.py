# In stock_analyzer/intent_classifier.py

import os
import json
import re
from typing import Dict, Any, Optional
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def classify_intent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Classify user intent and extract stock ticker if applicable.
    """
    print("---NODE: Classifying Intent (Conversational V4)---")
    
    try:
        # Extract the user message from the state
        messages = state.get("messages", [])
        if not messages:
            return {**state, "intent": "off_topic", "stock_ticker": None}
        
        # Get the last user message (convert from LangChain message to string)
        last_message = messages[-1]
        if hasattr(last_message, 'content'):
            user_message = last_message.content
        else:
            user_message = str(last_message)
        
        print(f"Processing user message: '{user_message}'")
        
        # First, try simple pattern matching for common cases
        intent, ticker = simple_intent_classification(user_message)
        
        if intent != "unknown":
            print(f"Simple classification result: intent='{intent}', ticker='{ticker}'")
            return {**state, "intent": intent, "stock_ticker": ticker}
        
        # If simple classification fails, use Gemini
        print("Using Gemini for intent classification...")
        
        # Create the prompt as a simple string (not LangChain message)
        prompt = f"""
You are an expert intent classifier for EquiSage, an AI Indian stock market analyst.
Analyze the user's message and classify their intent.
Respond ONLY with a single, clean JSON object with two keys: "intent" and "stock_ticker".

1. **"intent"**: Classify the user's intent. Possible values are:
   * "stock_analysis": The user wants to analyze a specific Indian stock.
   * "greeting": The user is greeting or starting a conversation.
   * "help": The user is asking for help or instructions.
   * "off_topic": The user is asking about something unrelated to the Indian stock market.

2. **"stock_ticker"**: If the intent is "stock_analysis", provide the official NSE stock ticker for the company mentioned, ending with ".NS". If you cannot determine a valid Indian stock, this MUST be null.

**Crucial Rules:**
* Map common names to tickers (e.g., "reliance" -> "RELIANCE.NS", "sbi" -> "SBIN.NS", "tata chemicals" -> "TATACHEM.NS")
* If the request is ambiguous or not a known major Indian company, the intent is "off_topic".

**User Message:**
{user_message}

**JSON Response:**
"""
        
        # Use Gemini API correctly
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(prompt)
        
        # Parse the response
        response_text = response.text.strip()
        print(f"Gemini response: {response_text}")
        
        # Extract JSON from response
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group()
            result = json.loads(json_str)
            
            intent = result.get("intent", "off_topic")
            ticker = result.get("stock_ticker")
            
            print(f"Parsed result: intent='{intent}', ticker='{ticker}'")
            return {**state, "intent": intent, "stock_ticker": ticker}
        else:
            raise ValueError("Could not parse JSON from Gemini response")
            
    except Exception as e:
        print(f"Error during Gemini intent resolution: {e}")
        # Fallback to simple classification
        intent, ticker = simple_intent_classification(user_message if 'user_message' in locals() else "")
        return {**state, "intent": intent, "stock_ticker": ticker}

def simple_intent_classification(user_message: str) -> tuple[str, Optional[str]]:
    """
    Simple rule-based intent classification as fallback.
    """
    message_lower = user_message.lower().strip()
    
    # Greeting patterns
    greetings = ['hi', 'hello', 'hey', 'good morning', 'good afternoon', 'good evening']
    if any(greeting in message_lower for greeting in greetings):
        return "greeting", None
    
    # Help patterns
    help_patterns = ['help', 'how to', 'what can you do', 'instructions']
    if any(pattern in message_lower for pattern in help_patterns):
        return "help", None
    
    # Stock analysis patterns
    analysis_patterns = ['analyse', 'analyze', 'tell me about', 'research', 'study', 'look at']
    
    # Common Indian stock mappings
    stock_mappings = {
        'reliance': 'RELIANCE.NS',
        'reliance industries': 'RELIANCE.NS',
        'tata consultancy': 'TCS.NS',
        'tcs': 'TCS.NS',
        'infosys': 'INFY.NS',
        'hdfc bank': 'HDFCBANK.NS',
        'hdfc': 'HDFCBANK.NS',
        'icici bank': 'ICICIBANK.NS',
        'icici': 'ICICIBANK.NS',
        'sbi': 'SBIN.NS',
        'state bank': 'SBIN.NS',
        'wipro': 'WIPRO.NS',
        'bharti airtel': 'BHARTIARTL.NS',
        'airtel': 'BHARTIARTL.NS',
        'itc': 'ITC.NS',
        'tata chemicals': 'TATACHEM.NS',
        'tatachem': 'TATACHEM.NS',
        'tata motors': 'TATAMOTORS.NS',
        'bajaj finance': 'BAJFINANCE.NS',
        'bajaj finserv': 'BAJAJFINSV.NS',
        'asian paints': 'ASIANPAINT.NS',
        'nestle': 'NESTLEIND.NS',
        'hindustan unilever': 'HINDUNILVR.NS',
        'hul': 'HINDUNILVR.NS',
        'maruti suzuki': 'MARUTI.NS',
        'maruti': 'MARUTI.NS'
    }
    
    # Check if it's a stock analysis request
    for pattern in analysis_patterns:
        if pattern in message_lower:
            # Look for stock name
            for stock_name, ticker in stock_mappings.items():
                if stock_name in message_lower:
                    return "stock_analysis", ticker
            # If analysis pattern found but no known stock, return stock_analysis with None ticker
            return "stock_analysis", None
    
    # Check if message contains any known stock names without analysis patterns
    for stock_name, ticker in stock_mappings.items():
        if stock_name in message_lower:
            return "stock_analysis", ticker
    
    return "off_topic", None