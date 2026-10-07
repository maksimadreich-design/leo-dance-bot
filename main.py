import asyncio
import logging
import uvicorn
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from config import settings
from database import init_db
from client_handlers import client_router
from admin_handlers import admin_router
from server import app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

async def start_web_server():
    port = int(os.environ.get("PORT", 8000))
    cfg = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="warning")
    server = uvicorn.Server(cfg)
    await server.serve()

async def start_telegram_bot():
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
    )
    dp = Dispatcher()
    dp.include_router(admin_router)
    dp.include_router(client_router)

    logger.info(f"Starting {settings.STUDIO_NAME} bot polling...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

async def main():
    logger.info("Initializing Database...")
    await init_db()

    # Run both web server (Mini App API) and Telegram polling concurrently
    await asyncio.gather(
        start_web_server(),
        start_telegram_bot()
    )

if __name__ == "__main__":
    asyncio.run(main())
