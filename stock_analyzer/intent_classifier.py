# In stock_analyzer/intent_classifier.py

import os
import json
import re
from typing import Dict, Any, Optional
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
MODEL = genai.GenerativeModel('gemini-2.0-flash')

def classify_intent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Classifies user intent using a fully AI-powered approach for all messages.
    """
    print("---NODE: Classifying Intent (Full AI V6)---")
    
    messages = state.get("messages", [])
    if not messages:
        # This case is for safety, should rarely be hit.
        return {**state, "intent": "off_topic", "stock_ticker": None}
    
    user_message = messages[-1].content
    print(f"Processing user message: '{user_message}'")

    # Every message now goes to Gemini for classification.
    print("Using Gemini for universal intent classification...")
    
    prompt = f"""
    You are an expert intent classifier for EquiSage, an AI Indian stock market analyst.
    Your task is to analyze the user's message and determine their primary intent.
    Respond ONLY with a single, clean JSON object with two keys: "intent" and "stock_ticker".

    1. **"intent"**: Classify the user's intent into one of these four categories:
       * "stock_analysis": The user is asking about or mentioning a specific Indian company.
       * "greeting": The user is saying hello or making a social pleasantry (e.g., "hi", "good morning", "how are you?").
       * "help": The user is asking for instructions or help (e.g., "what can you do?", "help me", "instructions").
       * "off_topic": The user is asking about anything else.

    2. **"stock_ticker"**:
       - If the intent is "stock_analysis", you MUST provide the official NSE latest stock ticker ending in ".NS".
         Use your knowledge to map company names, common abbreviations, or even misspelled names to the correct ticker.
         Examples: "reliance" -> "RELIANCE.NS", "sbi bank" -> "SBIN.NS", "infy" -> "INFY.NS".
       - For ANY OTHER intent ("greeting", "help", "off_topic"), this key MUST be null.

    **User Message:** "{user_message}"

    **JSON Response:**
    """
    
    try:
        response = MODEL.generate_content(prompt)
        response_text = response.text.strip()
        print(f"Gemini response: {response_text}")
        
        # Robustly find the JSON blob in the response
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            intent = result.get("intent", "off_topic")
            ticker = result.get("stock_ticker")
            
            # Final validation: if intent is analysis, ticker must not be null.
            if intent == "stock_analysis" and not ticker:
                print("Gemini suggested 'stock_analysis' but found no ticker. Reclassifying as off_topic.")
                intent = "off_topic"
            
            print(f"Parsed result: intent='{intent}', ticker='{ticker}'")
            return {**state, "intent": intent, "stock_ticker": ticker}
        else:
            # If Gemini fails to return JSON, it's an off-topic query.
            raise ValueError("Could not parse JSON from Gemini response")
            
    except Exception as e:
        print(f"Error during Gemini intent resolution: {e}. Defaulting to off_topic.")
        return {**state, "intent": "off_topic", "stock_ticker": None}