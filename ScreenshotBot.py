import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
import os
from dotenv import load_dotenv

load_dotenv()  

API_TOKEN  = os.getenv("API_TOKEN", "dev_secret")

async def main():
    logging.basicConfig(level=logging.INFO)
    bot = Bot(token=API_TOKEN)
    dp = Dispatcher()

    @dp.message(Command("start"))
    async def cmd_start(message: types.Message):
        await message.answer("Хай!")

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
