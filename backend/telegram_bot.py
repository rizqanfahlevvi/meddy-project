"""
Telegram Bot Handler for MEDDY
Handles incoming messages and commands
"""

import logging
import os
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

logger = logging.getLogger(__name__)

class MeddyTelegramBot:
    """MEDDY Telegram Bot Handler"""
    
    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.app = None
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        message = f"""
👋 Selamat datang di MEDDY!

Saya adalah AI Clinical Decision Companion dari MDKIT.

Apa yang bisa saya bantu?
- 🔍 Intubasi prep
- 📊 Analisa hasil lab
- 🦠 Sepsis protocol
- ⚗️ Asam-basa interpretation
- 💊 Antibiotik selection

Ketik /help untuk lebih lanjut.
        """
        await update.message.reply_text(message)
        logger.info(f"User started bot: {user.first_name} ({user.id})")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        message = """
📖 MEDDY Commands:

/start - Start bot
/help - Show this help
/status - Check bot status

Atau langsung kirim pertanyaan medis:
- "Intubasi prep untuk 50kg anak, GCS 8"
- "Analisis hasil lab: Na 120, K 6.5, Cl 90"
- "Protocol sepsis untuk neonatal"

Saya akan bantu dengan evidence-based recommendations.
        """
        await update.message.reply_text(message)
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        message = "✓ MEDDY bot is running normally\n\nSiap membantu dokter 24/7"
        await update.message.reply_text(message)
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming text messages"""
        user_message = update.message.text
        user = update.effective_user
        
        logger.info(f"Message from {user.first_name} ({user.id}): {user_message}")
        
        # For MVP, simple echo response
        # Later: integrate with Gemini AI
        response = f"""Saya terima pertanyaan Anda:
"{user_message}"

Full AI integration coming soon! 
Untuk saat ini, silakan refer ke:
- ICU Helper: https://icuhelper.mdkit.app/
- ACLS Helper: https://aclshelper.mdkit.app/
- ResNeo Helper: https://resneohelper.mdkit.app/
- PICNIC Helper: https://picnichelper.mdkit.app/
        """
        await update.message.reply_text(response)
    
    async def initialize(self):
        """Initialize bot application"""
        self.app = Application.builder().token(self.bot_token).build()
        
        # Add handlers
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(CommandHandler("status", self.status_command))
        self.app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
        )
        
        await self.app.initialize()
        logger.info("Telegram bot initialized")
    
    async def start_polling(self):
        """Start bot with polling (for development)"""
        if not self.app:
            await self.initialize()
        
        await self.app.start()
        await self.app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        logger.info("Telegram bot polling started")
    
    async def stop(self):
        """Stop bot"""
        if self.app:
            await self.app.updater.stop()
            await self.app.stop()
            await self.app.shutdown()
            logger.info("Telegram bot stopped")

def get_telegram_bot(bot_token: str) -> MeddyTelegramBot:
    """Factory function to create telegram bot instance"""
    return MeddyTelegramBot(bot_token)