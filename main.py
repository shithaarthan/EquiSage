# In main.py - Simplified Version

import os
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from telegram import Update
from telegram.ext import Application
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage

# Import our STATELESS LangGraph app
from graph import app as analysis_graph

# --- Configuration ---
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

if not TELEGRAM_BOT_TOKEN or not WEBHOOK_URL:
    raise ValueError("TELEGRAM_BOT_TOKEN and WEBHOOK_URL must be set.")

bot_app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

async def send_long_message(bot, chat_id: int, text: str, max_length: int = 4096):
    """
    Send a long message by splitting it into chunks if necessary.
    """
    if len(text) <= max_length:
        await bot.send_message(chat_id=chat_id, text=text)
        return
    
    # Split the message into chunks
    chunks = []
    current_chunk = ""
    
    # Split by paragraphs first, then by sentences if needed
    paragraphs = text.split('\n\n')
    
    for paragraph in paragraphs:
        if len(current_chunk) + len(paragraph) + 2 <= max_length:
            if current_chunk:
                current_chunk += '\n\n' + paragraph
            else:
                current_chunk = paragraph
        else:
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = paragraph
            else:
                # If single paragraph is too long, split by sentences
                sentences = paragraph.split('. ')
                temp_chunk = ""
                for sentence in sentences:
                    if len(temp_chunk) + len(sentence) + 2 <= max_length:
                        if temp_chunk:
                            temp_chunk += '. ' + sentence
                        else:
                            temp_chunk = sentence
                    else:
                        if temp_chunk:
                            chunks.append(temp_chunk)
                        temp_chunk = sentence
                if temp_chunk:
                    current_chunk = temp_chunk
    
    if current_chunk:
        chunks.append(current_chunk)
    
    # Send each chunk
    for i, chunk in enumerate(chunks):
        if i == 0:
            await bot.send_message(chat_id=chat_id, text=chunk)
        else:
            await bot.send_message(chat_id=chat_id, text=f"({i+1}/{len(chunks)})\n\n{chunk}")
        
        # Small delay between messages to avoid rate limiting
        await asyncio.sleep(0.5)

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Application startup: Setting Telegram webhook...")
    webhook_endpoint = f"{WEBHOOK_URL}"
    await bot_app.bot.set_webhook(url=webhook_endpoint)
    print(f"Webhook has been set to: {webhook_endpoint}")
    yield
    print("Application shutdown: Removing Telegram webhook...")
    await bot_app.bot.delete_webhook()
    print("Webhook has been removed.")

api = FastAPI(lifespan=lifespan, title="EquiSage API", version="3.0.0-stable")

@api.post("/webhook")
async def telegram_webhook(request: Request):
    chat_id = -1
    try:
        data = await request.json()
        update = Update.de_json(data, bot_app.bot)

        if not update.message or not update.message.text:
            return Response(status_code=200)

        user_message = update.message.text
        chat_id = update.message.chat_id

        print(f"--- New Request | Chat ID: {chat_id} | Msg: '{user_message}' ---")

        # Create initial state with the new message
        initial_state = {"messages": [HumanMessage(content=user_message)]}

        # Invoke the stateless graph
        final_state = await asyncio.to_thread(analysis_graph.invoke, initial_state)

        # Send response
        if final_state and final_state.get('messages'):
            ai_response_message = final_state['messages'][-1].content
            
            # Split long messages into chunks (Telegram max is 4096 characters)
            await send_long_message(bot_app.bot, chat_id, ai_response_message)

            # Handle chart if available
            tech_analysis = final_state.get('technical_analysis')
            if isinstance(tech_analysis, dict):
                chart_path = tech_analysis.get('chart_path')
                if chart_path and os.path.exists(chart_path):
                    print(f"Sending chart: {chart_path}")
                    with open(chart_path, 'rb') as photo_file:
                        await bot_app.bot.send_photo(chat_id=chat_id, photo=photo_file)
        else:
            await bot_app.bot.send_message(chat_id=chat_id, text="Sorry, I couldn't process that.")

    except Exception as e:
        print(f"CRITICAL ERROR processing webhook for chat_id {chat_id}: {e}")
        import traceback
        traceback.print_exc()
        if chat_id != -1:
            await bot_app.bot.send_message(chat_id=chat_id, text="Apologies, a critical system error occurred. The team has been notified.")

    return Response(status_code=200)

@api.get("/")
def health_check():
    return {"status": "ok", "bot": "EquiSage", "architecture": "Webhook (Stateless)"}