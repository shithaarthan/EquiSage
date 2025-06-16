# In graph.py

import os
import random
from typing import TypedDict, List, Any, Optional, Dict

from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, AIMessage

# --- Import all our tool functions ---
from stock_analyzer.intent_classifier import classify_intent
from stock_analyzer.screener import fetch_screener_data
from stock_analyzer.technicals import fetch_technical_analysis
from stock_analyzer.news import fetch_stock_news
from stock_analyzer.market_news import fetch_market_context_news
from stock_analyzer.reporter import generate_report

# --- Load Environment Variables ---
load_dotenv()

# --- Define Helper Replies ---
FUNNY_FALLBACK_REPLIES = [
    "My circuits are 100% focused on candlestick charts. Try asking me about a stock!",
    "That question is currently trading outside my knowledge-circuit. Let's talk about the Indian market.",
]
HELP_MESSAGE = "I am EquiSage! Ask me to analyze any Indian stock by name (e.g., 'tell me about Reliance Industries') and I will provide a full report."
GREETING_MESSAGE = "Hello! I am EquiSage, your AI stock research assistant. Which stock can I analyze for you today?"

# --- Define the Graph's State ---
class AgentState(TypedDict):
    messages: List[BaseMessage]
    intent: Optional[str]
    stock_ticker: Optional[str]
    company_name: Optional[str]
    screener_data: Optional[Dict[str, Any]]
    technical_analysis: Optional[Dict[str, Any]]
    news_articles: Optional[List[Dict[str, str]]]
    market_context_articles: Optional[List[Dict[str, str]]]

# --- Define Node Functions ---
def generate_greeting_response(state: AgentState) -> Dict[str, Any]:
    return {"messages": state['messages'] + [AIMessage(content=GREETING_MESSAGE)]}

def generate_help_response(state: AgentState) -> Dict[str, Any]:
    return {"messages": state['messages'] + [AIMessage(content=HELP_MESSAGE)]}

def generate_funny_fallback(state: AgentState) -> Dict[str, Any]:
    return {"messages": state['messages'] + [AIMessage(content=random.choice(FUNNY_FALLBACK_REPLIES))]}

def run_report_generation(state: AgentState) -> Dict[str, Any]:
    print("---NODE: Preparing to generate final AI message---")
    report_text = generate_report(state).get("final_report", "An error occurred while generating the report.")
    return {"messages": state['messages'] + [AIMessage(content=report_text)]}

# --- Define the Router ---
# Updated router function for graph.py

def route_after_intent_classification(state: AgentState) -> str:
    intent = state.get("intent")
    stock_ticker = state.get("stock_ticker")
    
    print(f"---ROUTER 1: Intent is '{intent}', Ticker is '{stock_ticker}'---")
    
    if intent == "stock_analysis" and stock_ticker:
        return "fetch_screener"
    elif intent == "stock_analysis" and not stock_ticker:
        # Stock analysis requested but no valid ticker found
        return "generate_fallback"
    elif intent == "greeting":
        return "generate_greeting"
    elif intent == "help":
        return "generate_help"
    else:
        return "generate_fallback"

def route_after_screener(state: AgentState) -> str:
    if state.get("screener_data") and not state["screener_data"].get("error"):
        print("---ROUTER 2: Screener data found. Fetching secondary data in parallel.---")
        return ["fetch_technicals", "fetch_stock_news", "fetch_market_news"]
    else:
        print("---ROUTER 2: Screener data failed. Generating fallback.---")
        return "generate_fallback"

# --- Build the Graph ---
workflow = StateGraph(AgentState)

workflow.add_node("classify_intent", classify_intent)
workflow.add_node("fetch_screener", fetch_screener_data)
workflow.add_node("fetch_technicals", fetch_technical_analysis)
workflow.add_node("fetch_stock_news", fetch_stock_news)
workflow.add_node("fetch_market_news", fetch_market_context_news)
workflow.add_node("generate_report", run_report_generation)
workflow.add_node("generate_greeting", generate_greeting_response)
workflow.add_node("generate_help", generate_help_response)
workflow.add_node("generate_fallback", generate_funny_fallback)

workflow.set_entry_point("classify_intent")
workflow.add_conditional_edges("classify_intent", route_after_intent_classification)
workflow.add_conditional_edges("fetch_screener", route_after_screener)
workflow.add_edge("fetch_technicals", "generate_report")
workflow.add_edge("fetch_stock_news", "generate_report")
workflow.add_edge("fetch_market_news", "generate_report")
workflow.add_edge("generate_report", END)
workflow.add_edge("generate_greeting", END)
workflow.add_edge("generate_help", END)
workflow.add_edge("generate_fallback", END)

# --- THE FIX: Compile the graph WITHOUT a checkpointer. It is now a pure, stateless function. ---
app = workflow.compile()
print("Stateless LangGraph workflow compiled successfully.")