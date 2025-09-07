import asyncio
import logging
import os
import aiohttp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from dotenv import load_dotenv
import datetime
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

load_dotenv()

API_TOKEN = os.getenv("API_TOKEN")
WEATHER_API = os.getenv("WEATHER_API")

logging.basicConfig(level=logging.INFO)

dp = Dispatcher()

# ===================== ФУНКЦІЇ =====================

async def get_geolocation(city: str):
    url = "http://api.openweathermap.org/geo/1.0/direct"
    params = {
        "q": city,
        "appid": WEATHER_API,
        "limit": 1
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            if resp.status != 200:
                return None, None
            data = await resp.json()
            if not data:
                return None, None
            lat = data[0]["lat"]
            lon = data[0]["lon"]
            return lat, lon

async def get_current_weather(city: str, lat, lon) -> str:
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "lat": lat,
        "lon": lon,
        "appid": WEATHER_API,
        "units": "metric",
        "lang": "ua"
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            if resp.status != 200:
                return "❌ Не вдалося отримати дані."
            data = await resp.json()
            temp = data["main"]["temp"]
            feels = data["main"]["feels_like"]
            desc = data["weather"][0]["description"].capitalize()
            return (
                f"🌍 Погода у місті {city}:\n"
                f"🌡 Температура: {temp}°C\n"
                f"🤔 Відчувається як: {feels}°C\n"
                f"☁ {desc}"
            )
        
async def get_hourly_weather(city, lat, lon, hours=1):
    url = f"https://api.openweathermap.org/data/2.5/forecast"
    params = {
        "lat": lat,
        "lon": lon,
        "appid": WEATHER_API,
        "units": "metric",
        "lang": "ua"
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            data = await resp.json()
    
    forecast = data["list"][:hours]  
    report = f"🌤 Погода в {city} по годинах:\n\n"
    
    for f in forecast:
        time = f["dt_txt"][11:16] 
        temp = f["main"]["temp"]
        desc = f["weather"][0]["description"].capitalize()
        report += f"🕑 {time} → {temp}°C, {desc}\n"
    
    return report

async def get_daily_weather(city: str, lat, lon, days=5) -> str:
    url = "https://api.openweathermap.org/data/2.5/forecast"
    params = {
        "lat": lat,
        "lon": lon,
        "appid": WEATHER_API,
        "units": "metric",
        "lang": "ua"
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            if resp.status != 200:
                return "❌ Не вдалося отримати дані."
            data = await resp.json()

            forecast = {}
            for item in data["list"]:
                date = datetime.datetime.fromtimestamp(item["dt"]).date()
                if date not in forecast:
                    forecast[date] = {"temps": [], "descriptions": []}
                forecast[date]["temps"].append(item["main"]["temp"])
                forecast[date]["descriptions"].append(item["weather"][0]["description"])

            result = [f"📅 Прогноз для {city} на {days} днів:\n"]
            for i, (date, info) in enumerate(forecast.items()):
                if i >= days:
                    break
                avg_temp = round(sum(info["temps"]) / len(info["temps"]), 1)
                desc = max(set(info["descriptions"]), key=info["descriptions"].count).capitalize()
                result.append(f"👉 {date}: {avg_temp}°C, {desc}")

            return "\n".join(result)

# ===================== ХЕНДЛЕРИ =====================

@dp.callback_query(F.data.startswith("current:"))
async def process_current(callback: types.CallbackQuery):
    _, city, lat, lon = callback.data.split(":")
    report = await get_current_weather(city, float(lat), float(lon))
    await callback.message.answer(report)
    await callback.answer()

@dp.callback_query(F.data.startswith("daily:"))
async def process_daily(callback: types.CallbackQuery):
    _, city, lat, lon, cnt = callback.data.split(":")
    report = await get_daily_weather(city, float(lat), float(lon), int(cnt))
    await callback.message.answer(report)
    await callback.answer()

@dp.callback_query(F.data.startswith("hourly"))
async def cmd_hourly(message: types.Message):
    args = message.text.split(maxsplit=2)
    if len(args) < 2:
        await message.answer("⚠️ Напиши місто: `/hourly Київ`", parse_mode="Markdown")
        return
    
    city = args[1]
    lat, lon = await get_geolocation(city)
    if lat is None:
        await message.answer("❌ Не знайшов такого міста.")
        return
    
    report = await get_hourly_weather(city, lat, lon)
    await message.answer(report)


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "Привіт 👋\n"
        "Я бот, який показує погоду.\n\n"
        "Введи команду у форматі:\n"
        "`/weather Львів`\n\n"
        "👉 І я скажу температуру, відчуття та опис погоди 🌦",
        parse_mode="Markdown"
    )

@dp.message(Command("weather"))
async def cmd_weather(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("⚠️ Напиши місто: `/weather Київ`", parse_mode="Markdown")
        return

    city = args[1]
    lat, lon = await get_geolocation(city)
    if lat is None:
        await message.answer("❌ Не знайшов такого міста. Спробуй ще раз.")
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌡 Поточна", callback_data=f"current:{city}:{lat}:{lon}")],
        [InlineKeyboardButton(text="📅 Прогноз на день погодинно", callback_data=f"hourly:{city}:{lat}:{lon}:1")]
        [InlineKeyboardButton(text="📅 Прогноз на 5 днів", callback_data=f"daily:{city}:{lat}:{lon}:5")]
    ])

    await message.answer(f"Окей, {city} знайдено! Вибери режим:", reply_markup=keyboard)

# ===================== MAIN =====================

async def main():
    bot = Bot(token=API_TOKEN)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
