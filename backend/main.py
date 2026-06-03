"""
MEDDY Main Application
FastAPI backend for Clinical Decision Support
"""

import os
import sys
import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from telegram import Update

# Pastikan folder backend/ selalu bisa ditemukan saat import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from telegram_bot import get_telegram_bot

# Load environment variables dari .env
load_dotenv()

# Setup logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(levelname)s: [MEDDY] %(message)s",
    force=True
)
logger = logging.getLogger(__name__)

APP_VERSION = "0.1.0"

# ============================================
# LIFESPAN — Start/Stop Telegram Bot (Webhook)
# ============================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[MEDDY] Server starting up...", flush=True)

    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    bot = None

    if bot_token:
        print("[MEDDY] TELEGRAM_BOT_TOKEN ditemukan, memulai bot...", flush=True)
        try:
            bot = get_telegram_bot(bot_token)
            await bot.setup_handlers(gemini_api_key)
            await bot.app.initialize()
            await bot.app.start()

            # Set webhook menggunakan domain Railway
            railway_domain = os.getenv("RAILWAY_PUBLIC_DOMAIN")
            if railway_domain:
                webhook_url = f"https://{railway_domain}/webhook"
                await bot.app.bot.set_webhook(webhook_url)
                print(f"[MEDDY] ✓ Webhook aktif: {webhook_url}", flush=True)
            else:
                print("[MEDDY] ⚠ RAILWAY_PUBLIC_DOMAIN tidak ada — webhook tidak diset", flush=True)

            app.state.telegram_bot = bot
            print("[MEDDY] ✓ Telegram bot started", flush=True)
        except Exception as e:
            print(f"[MEDDY] ✗ Failed to start Telegram bot: {e}", flush=True)
            logger.error(f"Failed to start Telegram bot: {e}")
            app.state.telegram_bot = None
    else:
        print("[MEDDY] ✗ TELEGRAM_BOT_TOKEN tidak ditemukan — bot disabled", flush=True)
        app.state.telegram_bot = None

    yield

    # Shutdown
    if bot:
        try:
            await bot.app.bot.delete_webhook()
            await bot.app.stop()
            await bot.app.shutdown()
            print("[MEDDY] Telegram bot stopped", flush=True)
        except Exception as e:
            logger.error(f"Error stopping Telegram bot: {e}")

# ============================================
# APPLICATION INITIALIZATION
# ============================================

app = FastAPI(
    title="MEDDY",
    description="Medical Decision AI Companion",
    version=APP_VERSION,
    lifespan=lifespan
)

# ============================================
# TELEGRAM WEBHOOK ENDPOINT
# ============================================

@app.post("/webhook")
async def telegram_webhook(request: Request):
    """Terima update dari Telegram via webhook"""
    try:
        bot = app.state.telegram_bot
        if bot is None:
            print("[MEDDY] Webhook hit tapi bot is None!", flush=True)
            return {"ok": False}

        data = await request.json()
        print(f"[MEDDY] Webhook received: {list(data.keys())}", flush=True)

        update = Update.de_json(data, bot.app.bot)
        await bot.app.process_update(update)
        print("[MEDDY] Update processed OK", flush=True)
        return {"ok": True}
    except Exception as e:
        print(f"[MEDDY] Webhook error: {e}", flush=True)
        logger.error(f"Webhook error: {e}", exc_info=True)
        return {"ok": False}

# ============================================
# HEALTH CHECK ENDPOINTS
# ============================================

@app.get("/")
async def root():
    return {
        "message": "MEDDY API is running ✓",
        "version": APP_VERSION,
        "environment": os.getenv("ENVIRONMENT", "development")
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "MEDDY",
        "version": APP_VERSION
    }

@app.get("/test/webhook")
async def test_webhook():
    """Cek status webhook dari Telegram"""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        return {"error": "TELEGRAM_BOT_TOKEN not set"}
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"https://api.telegram.org/bot{bot_token}/getWebhookInfo",
                timeout=10.0
            )
        return r.json()
    except Exception as e:
        return {"error": str(e)}

@app.get("/test/telegram")
async def test_telegram():
    """Test Telegram bot token"""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        return {"status": "error", "message": "TELEGRAM_BOT_TOKEN not set in .env"}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.telegram.org/bot{bot_token}/getMe",
                timeout=10.0
            )
        if response.status_code == 200:
            bot_info = response.json()
            return {
                "status": "success",
                "bot_name": bot_info["result"]["first_name"],
                "bot_username": bot_info["result"]["username"]
            }
        return {"status": "error", "message": "Invalid bot token"}
    except httpx.TimeoutException:
        return {"status": "error", "message": "Telegram API timeout"}
    except Exception as e:
        logger.error(f"Telegram test failed: {e}")
        return {"status": "error", "message": str(e)}

# ============================================
# ERROR HANDLING
# ============================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"}
    )

# ============================================
# RUN APPLICATION
# ============================================

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False, log_level="info")
