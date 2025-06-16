# In telegram_bot.py

import os
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

# Assume your graph is built in a file called `graph.py`
# from graph import compiled_graph, get_funny_reply, HELP_MESSAGE, GREETING_MESSAGE

# --- Placeholder functions for what the graph would do ---
# You will replace these with the actual graph invocation
def get_funny_reply(): return "My circuits are buzzing, but not about that! Try asking about a stock."
def get_help_message(): return "I am EquiSage! Ask me to analyze any Indian stock by name (e.g., 'analyze Reliance') and I will provide a full report."
def get_greeting_message(): return "Hello! I am EquiSage, your AI stock research assistant. Which stock can I analyze for you today?"

async def run_analysis_graph(user_message: str) -> Dict[str, Any]:
    """
    This function will be the entry point to your LangGraph.
    For now, it simulates the graph's logic based on the new intent classifier.
    """
    # 1. Simulate the intent classifier
    print(f"Simulating graph for message: '{user_message}'")
    from stock_analyzer.intent_classifier import classify_intent # For testing
    state = classify_intent({"user_message": user_message})
    
    intent = state.get("intent")
    
    # 2. Simulate the conditional routing
    if intent == "stock_analysis":
        # In a real scenario, you'd run the full data collection and reporting chain
        ticker = state.get('stock_ticker')
        return {"final_report": f"This is a placeholder analysis for {ticker}.", "chart_path": None}
    elif intent == "help":
        return {"final_report": get_help_message()}
    elif intent == "greeting":
        return {"final_report": get_greeting_message()}
    else: # off_topic or error
        return {"final_report": get_funny_reply()}


# --- The Single Message Handler ---
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """The single entry point for all user text messages."""
    user_message = update.message.text
    chat_id = update.message.chat_id
    
    print(f"Received message from user {chat_id}: '{user_message}'")
    
    # Let the user know we're working on it
    await context.bot.send_message(chat_id, text="Analyzing... Please wait.")
    
    # --- Invoke the Main Analysis Graph ---
    # This is where you call your LangGraph application
    # result = compiled_graph.invoke({"user_message": user_message})
    result = await run_analysis_graph(user_message) # Using the placeholder for now
    
    final_report = result.get("final_report", "Sorry, an error occurred.")
    chart_path = result.get("chart_path")
    
    # Send the text report
    await update.message.reply_text(final_report)
    
    # If a chart was generated, send it
    if chart_path and os.path.exists(chart_path):
        await update.message.reply_photo(photo=open(chart_path, 'rb'))

def main() -> None:
    """Start the conversational bot."""
    load_dotenv()
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("Error: TELEGRAM_BOT_TOKEN not found in .env file.")
        return

    application = Application.builder().token(token).build()

    # Register the single, powerful message handler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    print("Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()