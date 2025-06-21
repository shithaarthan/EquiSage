import os
import random
import json
from typing import TypedDict, List, Any, Optional, Dict

from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage
import google.generativeai as genai

# Import your existing nodes and db functions
from stock_analyzer.intent_classifier import classify_intent
from stock_analyzer.screener import fetch_screener_data
from stock_analyzer.technicals import fetch_technical_analysis
from stock_analyzer.news import fetch_stock_news
from stock_analyzer.market_news import fetch_market_context_news
from stock_analyzer.reporter import generate_report
from stock_analyzer.reporter_pdf import generate_pdf_report
from db_manager import load_session

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
llm = genai.GenerativeModel('gemini-2.0-flash')

# --- AgentState Definition ---
class AgentState(TypedDict):
    messages: List[BaseMessage]
    intent: Optional[str]
    stock_ticker: Optional[str]
    company_name: Optional[str]
    screener_data: Optional[Dict[str, Any]]
    technical_analysis: Optional[Dict[str, Any]]
    news_articles: Optional[List[Dict[str, str]]]
    market_context_articles: Optional[List[Dict[str, str]]]
    pdf_report_path: Optional[str]
    pdf_filename: Optional[str]
    chat_id: Optional[int]
    session_data: Optional[Dict[str, Any]]
    next_node: Optional[str]


# --- Node Functions ---

def generate_greeting_response(state: AgentState) -> Dict[str, Any]:
    return {"messages": state['messages'] + [AIMessage(content="Hello! I am EquiSage, your AI stock research assistant. Which stock can I analyze for you today?")]}

def generate_help_response(state: AgentState) -> Dict[str, Any]:
    return {"messages": state['messages'] + [AIMessage(content="I am EquiSage! Ask me to analyze any Indian stock by name (e.g., 'tell me about Reliance Industries') to get a full report.")]}

def generate_off_topic_response(state: AgentState) -> Dict[str, Any]:
    fallback_replies = ["My circuits are 100% focused on candlestick charts. Try asking me about a stock!", "That question is currently trading outside my knowledge-circuit. Let's talk about the Indian market."]
    return {"messages": state['messages'] + [AIMessage(content=random.choice(fallback_replies))]}

def run_report_generation(state: AgentState) -> Dict[str, Any]:
    print("---NODE: Preparing to generate final AI message---")
    report_text = generate_report(state).get("final_report", "An error occurred while generating the report.")
    return {"messages": state['messages'] + [AIMessage(content=report_text)]}

def run_pdf_report_generation(state: AgentState) -> Dict[str, Any]:
    print("---NODE: Generating PDF report---")
    if state.get("screener_data") and not state["screener_data"].get("error"):
        pdf_result = generate_pdf_report(state)
        return {"pdf_report_path": pdf_result.get("pdf_report_path"), "pdf_filename": pdf_result.get("pdf_filename")}
    return {}

def answer_follow_up_question(state: AgentState) -> Dict[str, Any]:
    print("---NODE: Answering Follow-up Question---")
    messages = state['messages']
    user_question = messages[-1].content
    
    session_data = state.get("session_data")
    if not session_data:
        return {"messages": messages + [AIMessage(content="I seem to have lost our previous conversation context. Please ask for a new analysis.")]}

    company_name = session_data.get("company_name", "the previously discussed company")

    prompt = f"""You are EquiSage, a helpful AI stock analyst. The user is asking a follow-up question about **{company_name}**.
    Your task is to answer the user's question based *only* on the provided data from the previous analysis.
    If the data does not contain the answer, state that clearly and politely. Be concise.

    **User's Question:** "{user_question}"
    **Data Context from Previous Analysis:**
    {json.dumps(session_data, indent=2)}"""
    
    response = llm.generate_content(prompt)
    return {"messages": messages + [AIMessage(content=response.text)]}

def conversational_router(state: AgentState) -> Dict[str, Any]:
    """
    This node prioritizes checking for a follow-up before classifying intent.
    """
    print("---NODE: Conversational Router (v2)---")
    user_message = state['messages'][-1].content
    chat_id = state.get('chat_id')

    # 1. Prioritize checking for a follow-up conversation from the database.
    session_data = load_session(chat_id)
    if session_data:
        print("Previous session found. Asking LLM to determine if this is a follow-up.")
        company_name = session_data.get("company_name", "a stock")

        prompt = f"""You are a conversation router for a stock analysis bot. The user's previous analysis was about **{company_name}**. Now, the user has sent a new message.
        Decide if the new message is a follow-up question about the previous analysis, a request for a completely new analysis, or something else.

        Previous Topic: Analysis of {company_name}
        User's New Message: "{user_message}"

        Respond with a single word: **FOLLOWUP**, **NEW**, or **OTHER**.
        - **FOLLOWUP**: If the message asks a question about the previous topic (e.g., "what was its PE ratio?", "tell me more about the fundamentals").
        - **NEW**: If the message clearly asks for a different stock (e.g., "now analyze Reliance", "what about TCS?").
        - **OTHER**: If it's a greeting, a thank you, or something unrelated.
        """
        response = llm.generate_content(prompt)
        decision = response.text.strip().upper()
        print(f"Router Decision: {decision}")

        if decision == "FOLLOWUP":
            return {"session_data": session_data, "next_node": "answer_follow_up"}
            
    # 2. If it's not a follow-up, THEN classify the intent of the message.
    print("No follow-up context, or router decided it's a new request. Classifying intent...")
    classification_state = classify_intent(state)
    intent = classification_state.get("intent")
    
    if intent == "stock_analysis" and classification_state.get("stock_ticker"):
        updates = classification_state
        updates["next_node"] = "fetch_screener"
        return updates
    elif intent in ["greeting", "help"]:
        return {"next_node": f"generate_{intent}"}
    else:
        return {"next_node": "generate_off_topic"}


# --- Conditional Edge Functions ---

def decide_next_node(state: AgentState) -> str:
    """This function reads the decision from the state and tells the graph where to go."""
    return state.get("next_node")

def route_after_screener(state: AgentState) -> str:
    """Checks if screener data was fetched successfully."""
    if state.get("screener_data") and not state["screener_data"].get("error"):
        return "fetch_data_parallel"
    else:
        return "generate_off_topic"


# --- Build the Graph ---

workflow = StateGraph(AgentState)

# 1. Add all nodes
workflow.add_node("router", conversational_router)
workflow.add_node("answer_follow_up", answer_follow_up_question)
workflow.add_node("fetch_screener", fetch_screener_data)
workflow.add_node("fetch_data_parallel", lambda state: {}) # Pseudo-node for parallelism
workflow.add_node("fetch_technicals", fetch_technical_analysis)
workflow.add_node("fetch_stock_news", fetch_stock_news)
workflow.add_node("fetch_market_news", fetch_market_context_news)
workflow.add_node("generate_report", run_report_generation)
workflow.add_node("generate_pdf", run_pdf_report_generation)
workflow.add_node("generate_greeting", generate_greeting_response)
workflow.add_node("generate_help", generate_help_response)
workflow.add_node("generate_off_topic", generate_off_topic_response)

# 2. Set the entry point
workflow.set_entry_point("router")

# 3. Define the routing logic from the main router
workflow.add_conditional_edges(
    "router",
    decide_next_node,
    {
        "fetch_screener": "fetch_screener",
        "answer_follow_up": "answer_follow_up",
        "generate_greeting": "generate_greeting",
        "generate_help": "generate_help",
        "generate_off_topic": "generate_off_topic",
    }
)

# 4. Define the rest of the graph edges
workflow.add_conditional_edges("fetch_screener", route_after_screener)

workflow.add_edge("fetch_data_parallel", "fetch_technicals")
workflow.add_edge("fetch_data_parallel", "fetch_stock_news")
workflow.add_edge("fetch_data_parallel", "fetch_market_news")

workflow.add_edge("fetch_technicals", "generate_report")
workflow.add_edge("fetch_stock_news", "generate_report")
workflow.add_edge("fetch_market_news", "generate_report")

workflow.add_edge("generate_report", "generate_pdf")

# 5. Define end points for all branches
workflow.add_edge("generate_pdf", END)
workflow.add_edge("answer_follow_up", END)
workflow.add_edge("generate_greeting", END)
workflow.add_edge("generate_help", END)
workflow.add_edge("generate_off_topic", END)

# 6. Compile the graph
app = workflow.compile()
print("Stateful LangGraph with corrected router v2 compiled successfully.")