import asyncio
import logging

from aiogram import Bot, Dispatcher
from config import config

from bot.handlers import profile, place, timepick


# Bot polling function
async def bot_main():
    # Logging level
    logging.basicConfig(
        level=logging.getLevelName(level=logging.INFO),
        format="[%(asctime)s] - [%(levelname)s] - %(name)s - %(message)s"
    )
    # Инициализируем бот и диспетчер
    bot = Bot(token=config.TELEGRAM_TOKEN)
    dp = Dispatcher()

    # Registering routers
    dp.include_router(profile.router)
    dp.include_router(place.router)
    dp.include_router(timepick.router)

    # Skipping updates and running polling
    await bot.delete_webhook(drop_pending_updates=True)
    logging.info("Webhook deleted")

    await dp.start_polling(bot)
    logging.info("Bot started")

if __name__ == '__main__':
    asyncio.run(bot_main())





# import asyncio
# import logging
#
# from config import config
# from database.database import init_models
# from bot.handlers import profile, place, timepick
# from google.schedule_parser import load_and_parse, temp_data
# from google.API_connection import table
# import copy
# from bot.bot import bot, dp
# from aiogram import Bot
#
# # include routers
# dp.include_router(profile.router)
# dp.include_router(place.router)
# dp.include_router(timepick.router)
#
# logging.basicConfig(level=logging.INFO)
#
#
# from shared_data import SCHEDULE_SHARED, LOCK
#
#
#
# def create_dispatcher_and_bot():
#     global bot
#
#     return dp
#
# async def run_polling():
#     global bot
#     dp = create_dispatcher_and_bot()
#     try:
#         await bot.delete_webhook(drop_pending_updates=False)
#     except Exception as e:
#         logging.warning(f"Не удалось удалить webhook: {e}")
#
#     try:
#         me = await bot.get_me()
#         logging.info(f"Logged in as @{me.username} (id={me.id})")
#     except Exception:
#         logging.exception("Bot token check failed")
#         raise
#
#     allowed = dp.resolve_used_update_types()
#     await dp.start_polling(bot, allowed_updates=allowed)
#
# async def bot_main():
#     await init_models()
#     global bot
#     backoff = 5
#     while True:
#         try:
#             await run_polling()
#             break
#         except asyncio.CancelledError:
#             raise
#         except Exception as e:
#             logging.exception("Polling crashed: %s", e)
#             try:
#                 await bot.session.close()
#             except Exception:
#                 pass
#             bot = Bot(config.TELEGRAM_TOKEN)
#             await asyncio.sleep(backoff)
