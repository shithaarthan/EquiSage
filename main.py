import os
import asyncio
import json
import traceback
import random
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from telegram import Update
from telegram.ext import Application
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage

from graph import app as analysis_graph
from db_manager import setup_database, save_session, load_session, check_and_register_user
from sanitize import sanitize_for_telegram
from logs.logger_config import user_logger # <-- IMPORT THE NEW LOGGER

# Run the database setup once on startup
setup_database()

load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

if not TELEGRAM_BOT_TOKEN or not WEBHOOK_URL:
    raise ValueError("TELEGRAM_BOT_TOKEN and WEBHOOK_URL must be set.")

bot_app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()


async def send_long_message(bot, chat_id: int, text: str, max_length: int = 4096):
    sanitized_text = sanitize_for_telegram(text)
    if len(sanitized_text) <= max_length:
        await bot.send_message(chat_id=chat_id, text=sanitized_text, parse_mode='HTML')
        return
    # Chunking logic remains the same
    chunks = []
    current_chunk = ""
    paragraphs = sanitized_text.split('\n\n')
    for paragraph in paragraphs:
        if len(current_chunk) + len(paragraph) + 2 > max_length:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = paragraph
        else:
            current_chunk = (current_chunk + '\n\n' + paragraph) if current_chunk else paragraph
    if current_chunk:
        chunks.append(current_chunk)
    for i, chunk in enumerate(chunks):
        await bot.send_message(chat_id=chat_id, text=chunk, parse_mode='HTML')
        await asyncio.sleep(0.5)


async def process_analysis_and_reply(chat_id: int, user_message: str):
    """Runs the full analysis and saves the result to the DB."""
    try:
        print(f"--- Background Task Started for Chat ID: {chat_id} ---")
        initial_state = {
            "messages": [HumanMessage(content=user_message)],
            "chat_id": chat_id
        }
        final_state = await asyncio.to_thread(analysis_graph.invoke, initial_state)

        if final_state.get('intent') == 'stock_analysis' and not final_state.get('screener_data', {}).get('error'):
            tech_analysis_to_save = final_state.get("technical_analysis", {}).copy()
            if isinstance(tech_analysis_to_save, dict):
                tech_analysis_to_save.pop("chart_path", None)

            session_data = {
                "company_name": final_state.get("company_name"),
                "stock_ticker": final_state.get("stock_ticker"),
                "screener_data": final_state.get("screener_data"),
                "technical_analysis": tech_analysis_to_save,
                "news_articles": final_state.get("news_articles"),
                "market_context_articles": final_state.get("market_context_articles"),
            }
            save_session(chat_id, session_data)
            print(f"Saved session for chat_id {chat_id} to database (without file paths).")

        if final_state and final_state.get('messages'):
            ai_response_message = final_state['messages'][-1].content
            await send_long_message(bot_app.bot, chat_id, ai_response_message)
            
            if final_state.get('intent') == 'stock_analysis' and not final_state.get('screener_data', {}).get('error'):
                tech_analysis = final_state.get('technical_analysis')
                if isinstance(tech_analysis, dict) and (chart_path := tech_analysis.get("chart_path")) and os.path.exists(chart_path):
                    with open(chart_path, 'rb') as photo_file:
                        await bot_app.bot.send_photo(chat_id=chat_id, photo=photo_file)
                    try:
                        os.remove(chart_path)
                        print(f"Cleaned up chart file: {chart_path}")
                    except Exception as e:
                        print(f"Error cleaning up chart file {chart_path}: {e}")

                if (pdf_path := final_state.get("pdf_report_path")) and os.path.exists(pdf_path):
                    with open(pdf_path, "rb") as pdf_file:
                        await bot_app.bot.send_document(chat_id=chat_id, document=pdf_file, filename=final_state.get("pdf_filename"), caption="Here is your professional PDF research report.")
                    try:
                        os.remove(pdf_path)
                        print(f"Cleaned up PDF file: {pdf_path}")
                    except Exception as e:
                        print(f"Error cleaning up PDF file {pdf_path}: {e}")
        else:
            await bot_app.bot.send_message(chat_id=chat_id, text="Sorry, I couldn't process your request.")
    except Exception as e:
        print(f"CRITICAL ERROR in background task for chat_id {chat_id}: {e}")
        traceback.print_exc()
        await bot_app.bot.send_message(chat_id=chat_id, text="Apologies, an error occurred while processing your report.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Application startup: Setting Telegram webhook...")
    await bot_app.bot.set_webhook(url=f"{WEBHOOK_URL}")
    print(f"Webhook has been set to: {WEBHOOK_URL}")
    yield
    print("Application shutdown: Removing Telegram webhook...")
    await bot_app.bot.delete_webhook()
    print("Webhook has been removed.")


api = FastAPI(lifespan=lifespan, title="EquiSage API", version="5.3.0-logging")

@api.post("/webhook")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()
        update = Update.de_json(data, bot_app.bot)

        if not update.message or not update.message.text:
            return Response(status_code=200)

        user_message = update.message.text.strip()
        chat_id = update.message.chat_id
        user_details = update.message.from_user

        if user_message == "/start":
            if check_and_register_user(chat_id):
                # --- THIS IS THE NEW LOGGING LOGIC ---
                log_message = (
                    f"New user registered: ID={chat_id}, "
                    f"Username={user_details.username or 'N/A'}, "
                    f"Name='{user_details.first_name}'"
                )
                user_logger.info(log_message)
                # --- END OF LOGGING LOGIC ---
                
                welcome_text = (
                    "🎉 <b>Welcome to EquiSage!</b> 🎉\n\n"
                    "I am your personal AI stock research assistant for the Indian market.\n\n"
                    "Just ask me to analyze any stock by name to get a full report, chart, and PDF.\n\n"
                    "<b>For example:</b>\n"
                    "<i>'analyze Tata Motors'</i>\n"
                    "<i>'tell me about INFY'</i>"
                )
                await bot_app.bot.send_message(chat_id, welcome_text, parse_mode='HTML')
            else:
                await bot_app.bot.send_message(chat_id, "Welcome back! Which stock can I analyze for you today?")
            return Response(status_code=200)

        if user_message.lower() in ["pdf", "send pdf", "download pdf"]:
            await bot_app.bot.send_message(chat_id, "PDF reports are generated with new analyses. Please ask me to analyze a stock to receive a fresh report.")
            return Response(status_code=200)

        acknowledgment_messages = [
            "Got it! 🤖 Running a full analysis on your request. This may take a moment...",
            "Acknowledged! Crunching the numbers and gathering market data for you now. Please wait a moment. 📈",
            "Request received! My circuits are spinning up to create your detailed stock report. This might take a minute. ⚙️",
            "Alright, I'm on it! Preparing your comprehensive analysis now. This can take up to 30 seconds. 📊"
        ]
        
        await bot_app.bot.send_message(chat_id=chat_id, text=random.choice(acknowledgment_messages))
        
        asyncio.create_task(process_analysis_and_reply(chat_id, user_message))

    except Exception as e:
        print(f"Error in main webhook handler: {e}")
        traceback.print_exc()

    return Response(status_code=200)


@api.get("/")
def health_check():
    return {"status": "ok", "bot": "EquiSage", "architecture": "Stateful (SQLite) with auto-cleanup & dynamic replies"}