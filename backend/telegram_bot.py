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

MEDDY_SYSTEM_PROMPT = """Kamu adalah MEDDY, AI Clinical Decision Companion dari MDKIT untuk dokter dan tenaga medis profesional di Indonesia.

Peranmu:
- Memberikan rekomendasi klinis berbasis evidence (evidence-based medicine)
- Membantu kalkulasi dosis, protokol sepsis, interpretasi lab, persiapan intubasi
- Menjawab dalam Bahasa Indonesia kecuali istilah medis baku (tetap dalam bahasa Inggris/Latin)
- Selalu sertakan disclaimer bahwa rekomendasi ini bersifat pendukung keputusan, bukan pengganti penilaian klinis dokter

Batasan:
- Jangan memberikan diagnosis definitif
- Jangan merekomendasikan pengobatan untuk pasien tanpa supervision dokter
- Jika pertanyaan di luar domain medis, tolak dengan sopan dan redirect ke pertanyaan medis

Format respons:
- Gunakan format terstruktur dengan poin-poin jika relevan
- Sertakan referensi guideline jika applicable (IDSA, WHO, PNPK, dll)
- Maksimal 500 kata per respons kecuali diminta lebih detail
"""


class MeddyTelegramBot:
    """MEDDY Telegram Bot Handler"""

    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.gemini_client = None
        # updater(None) = webhook mode, tidak pakai polling/Updater sama sekali
        self.app = Application.builder().token(self.bot_token).updater(None).build()

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        message = """
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
        ai_status = "✓ Aktif" if self.gemini_client else "✗ Tidak tersedia"
        message = f"✓ MEDDY bot is running normally\n\nAI Engine: {ai_status}\nSiap membantu dokter 24/7"
        await update.message.reply_text(message)

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming text messages"""
        user_message = update.message.text
        user = update.effective_user

        logger.info(f"Message from {user.first_name} ({user.id}): {user_message}")

        if self.gemini_client is None:
            await update.message.reply_text(
                "Maaf, AI assistant sedang tidak tersedia.\n\n"
                "Silakan refer ke:\n"
                "- ICU Helper: https://icuhelper.mdkit.app/\n"
                "- ACLS Helper: https://aclshelper.mdkit.app/\n"
                "- ResNeo Helper: https://resneohelper.mdkit.app/\n"
                "- PICNIC Helper: https://picnichelper.mdkit.app/"
            )
            return

        try:
            await context.bot.send_chat_action(
                chat_id=update.effective_chat.id,
                action="typing"
            )
            from google.genai import types
            response = await self.gemini_client.aio.models.generate_content(
                model="gemini-1.5-flash",
                contents=user_message,
                config=types.GenerateContentConfig(
                    system_instruction=MEDDY_SYSTEM_PROMPT
                )
            )
            await update.message.reply_text(response.text)
        except Exception as e:
            logger.error(f"Gemini error for user {user.id}: {e}")
            await update.message.reply_text(
                "Maaf, terjadi kesalahan saat memproses pertanyaan Anda. "
                "Silakan coba lagi dalam beberapa saat."
            )

    async def setup_handlers(self, gemini_api_key: str | None = None):
        """Setup command handlers dan inisialisasi Gemini AI."""
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(CommandHandler("status", self.status_command))
        self.app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
        )

        if gemini_api_key:
            try:
                from google import genai
                self.gemini_client = genai.Client(api_key=gemini_api_key)
                print("[MEDDY] ✓ Gemini AI initialized", flush=True)
            except Exception as e:
                print(f"[MEDDY] ✗ Gemini init failed: {e}", flush=True)
        else:
            print("[MEDDY] GEMINI_API_KEY tidak diset — AI disabled", flush=True)


def get_telegram_bot(bot_token: str) -> MeddyTelegramBot:
    """Factory function to create telegram bot instance"""
    return MeddyTelegramBot(bot_token)
