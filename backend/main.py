"""
MEDDY Main Application
FastAPI backend for Clinical Decision Support
"""

import os
import sys
import asyncio
import logging
from contextlib import asynccontextmanager

# Pastikan folder backend/ selalu bisa ditemukan saat import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from telegram import Update

from telegram_bot import get_telegram_bot

# Load environment variables dari .env
load_dotenv()

# Setup logging — force=True agar override konfigurasi uvicorn
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(levelname)s: [MEDDY] %(message)s",
    force=True
)
logger = logging.getLogger(__name__)

APP_VERSION = "0.1.0"

# ============================================
# LIFESPAN — Start/Stop Telegram Bot
# ============================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[MEDDY] Server starting up...", flush=True)

    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    bot = None
    polling_task = None

    if bot_token:
        print(f"[MEDDY] TELEGRAM_BOT_TOKEN ditemukan, memulai bot...", flush=True)
        try:
            bot = get_telegram_bot(bot_token, gemini_api_key)
            await bot.initialize()
            await bot.app.start()
            polling_task = asyncio.create_task(
                bot.app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
            )
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

    if polling_task:
        polling_task.cancel()
    if bot:
        try:
            await bot.stop()
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
# HEALTH CHECK ENDPOINTS
# ============================================

@app.get("/")
async def root():
    """Root endpoint - Server status"""
    return {
        "message": "MEDDY API is running ✓",
        "version": APP_VERSION,
        "environment": os.getenv("ENVIRONMENT", "development")
    }

@app.get("/health")
async def health_check():
    """Health check endpoint (untuk monitoring)"""
    return {
        "status": "healthy",
        "service": "MEDDY",
        "version": APP_VERSION
    }

# ============================================
# TELEGRAM BOT TEST ENDPOINT (Optional)
# ============================================

@app.get("/test/telegram")
async def test_telegram():
    """Test Telegram bot token"""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        return {
            "status": "error",
            "message": "TELEGRAM_BOT_TOKEN not set in .env"
        }

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
        logger.error("Telegram API timeout")
        return {"status": "error", "message": "Telegram API timeout"}
    except Exception as e:
        logger.error(f"Telegram test failed: {e}")
        return {"status": "error", "message": str(e)}

# ============================================
# ERROR HANDLING
# ============================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global error handler"""
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
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info"
    )
