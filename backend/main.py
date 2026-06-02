"""
MEDDY Main Application
FastAPI backend for Clinical Decision Support
"""

import os
import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

# Load environment variables dari .env
load_dotenv()

# Setup logging
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

# ============================================
# APPLICATION INITIALIZATION
# ============================================

app = FastAPI(
    title="MEDDY",
    description="Medical Decision AI Companion",
    version="0.1.0"
)

# ============================================
# HEALTH CHECK ENDPOINTS
# ============================================

@app.get("/")
async def root():
    """Root endpoint - Server status"""
    return {
        "message": "MEDDY API is running ✓",
        "version": os.getenv("APP_VERSION"),
        "environment": os.getenv("ENVIRONMENT")
    }

@app.get("/health")
async def health_check():
    """Health check endpoint (untuk monitoring)"""
    return {
        "status": "healthy",
        "service": "MEDDY",
        "version": os.getenv("APP_VERSION"),
        "timestamp": str(os.uname().nodename) if hasattr(os, 'uname') else 'windows'
    }

# ============================================
# GEMINI API TEST
# ============================================

# @app.get("/test/gemini")
# async def test_gemini():
#     """Test Google Gemini API connection"""
#     try:
#         import google.generativeai as genai
        
#         api_key = os.getenv("GOOGLE_API_KEY")
#         if not api_key:
#             return {
#                 "status": "error",
#                 "message": "GOOGLE_API_KEY not set in .env"
#             }
        
#         genai.configure(api_key=api_key)
#         model = genai.GenerativeModel('gemini-2.0-flash')
        
#         response = model.generate_content(
#             "Respond briefly: Are you ready to help doctors?"
#         )
        
#         return {
#             "status": "success",
#             "gemini_response": response.text,
#             "model": "gemini-pro"
#         }
#     except Exception as e:
#         logger.error(f"Gemini test failed: {e}")
#         return {
#             "status": "error",
#             "message": str(e)
#         }

# ============================================
# TELEGRAM BOT TEST
# ============================================

@app.get("/test/telegram")
async def test_telegram():
    """Test Telegram bot token"""
    try:
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not bot_token:
            return {
                "status": "error",
                "message": "TELEGRAM_BOT_TOKEN not set in .env"
            }
        
        import requests
        response = requests.get(
            f"https://api.telegram.org/bot{bot_token}/getMe"
        )
        
        if response.status_code == 200:
            bot_info = response.json()
            return {
                "status": "success",
                "bot_name": bot_info['result']['first_name'],
                "bot_username": bot_info['result']['username']
            }
        else:
            return {
                "status": "error",
                "message": "Invalid bot token"
            }
    except Exception as e:
        logger.error(f"Telegram test failed: {e}")
        return {
            "status": "error",
            "message": str(e)
        }

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
    
    # Run server
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Auto-reload saat edit file
        log_level="info"
    )