import asyncio
from aiogram import Bot, Dispatcher
from aiogram.types import Message, reply_keyboard_markup
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import CallbackQuery
import sqlite3
import os
from aiohttp import web
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application


db = sqlite3.connect("movie_reviews.db")
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user TEXT,
    movie TEXT,
    rating INTEGER,
    review TEXT
)
""")

db.commit()

cursor.execute("DELETE FROM reviews")
db.commit()




bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher()

class Reviews(StatesGroup):
    movie = State()
    rating = State()
    review = State()

movie_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text = "Odyssey", callback_data = "Odyssey"),
            InlineKeyboardButton(text = "Forest Gump", callback_data = "Forest Gump"),
        ]
    ]
)

rating_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text = "1", callback_data = "1"),
            InlineKeyboardButton(text = "2", callback_data = "2"),
        ],
        [
            InlineKeyboardButton(text = "3", callback_data = "3"),
            InlineKeyboardButton(text = "4", callback_data = "4"),
        ],
        [
            InlineKeyboardButton(text = "5", callback_data = "5"),
            InlineKeyboardButton(text = "6", callback_data = "6"),
        ],
        [
            InlineKeyboardButton(text = "7", callback_data = "7"),
            InlineKeyboardButton(text = "8", callback_data = "8"),
        ],
        [
            InlineKeyboardButton(text = "9", callback_data = "9"),
            InlineKeyboardButton(text = "10", callback_data = "10"),
        ]
    ]
)
reviews_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text = "Odyssey", callback_data = "reviews_Odyssey"),
            InlineKeyboardButton(text = "Forest Gump", callback_data = "reviews_Forest Gump"),
        ]
    ]
)

async def main():
    await dp.start_polling(bot)


@dp.message(Command('start'))
async def message_handler(message: Message, state: FSMContext):
    name = message.from_user.first_name

    await state.set_state(Reviews.movie)

    await message.answer(f"Hello! {name}! \n"
                         "Welcome to Movie Reviews Bot!\n"
                         "What movie did you watch today?",
                         reply_markup=movie_keyboard)

@dp.callback_query(Reviews.movie)
async def movie_selected(callback: CallbackQuery, state: FSMContext):
    await state.update_data(movie=callback.data)
    await callback.answer()

    await state.set_state(Reviews.rating)

    await callback.message.answer("Awesome, so how would you rate it?",
                                  reply_markup=rating_keyboard)

@dp.callback_query(Reviews.rating)
async def rating_selected(callback: CallbackQuery, state: FSMContext):
    await state.update_data(rating=callback.data)
    await callback.answer()
    await state.set_state(Reviews.review)

    await callback.message.answer("What is your review?\n"
                                  "Write 20 words at least")

@dp.message(Reviews.review)
async def review_selected(message: Message, state: FSMContext):
    if len(message.text.split()) < 20:
        await message.answer("Your review isn't enough words!\n"
                             "Please write 50 words at least")
        return

    await state.update_data(review=message.text)
    data = await state.get_data()

    user = message.from_user.first_name
    movie = data['movie']
    rating = data['rating']
    review = data['review']

    cursor.execute(
        "INSERT INTO reviews (user, movie, rating, review) VALUES (?, ?, ?, ?)",
        (user, movie, rating, review)
    )
    db.commit()

    await message.answer(f"Movie: {movie}\n"
                         f"Rating: {rating}\n"
                         f"Review: {review}\n"
                         "Thanks for your review!\n"
                         "See you in the next movie session"
                         )
    await state.clear()

@dp.message(Command('reviews'))
async def review_list(message: Message):
    await message.answer("Which movies review do you want see",
                         reply_markup = reviews_keyboard)

@dp.callback_query()
async def review_selected(callback: CallbackQuery):
    movie = callback.data.replace("reviews_", "")
    cursor.execute(
        "SELECT * FROM reviews WHERE movie = ?",
        (movie,)
    )

    reviews = cursor.fetchall()
    await callback.answer()

    if not reviews:
        await callback.message.answer(
            f"There are no reviews for {movie} yet! 🎬"
        )
        return

    reviews_text = ""
    for review in reviews:
        reviews_text +=(
            f"User: {review[1]}\n"
            f"Movie: {review[2]}\n"
            f"Rating: {review[3]}\n"
            f"Review: {review[4]}\n"
        )
    await callback.message.answer(
        f"Reviews for {movie}\n"
        + reviews_text
    )




async def on_startup(app):
    render_url = os.getenv("RENDER_EXTERNAL_URL")
    print("RENDER URL:", render_url)

    if render_url:
        webhook_url = render_url + "/webhook"
        print("SETTING WEBHOOK:", webhook_url)
        await bot.set_webhook(webhook_url)
        print("WEBHOOK SET!")
    else:
        print("RENDER_EXTERNAL_URL IS MISSING!")

async def on_shutdown(app):
    await bot.delete_webhook()


app = web.Application()

webhook_handler = SimpleRequestHandler(
    dispatcher=dp,
    bot=bot
)

webhook_handler.register(
    app,
    path="/webhook"
)

setup_application(app, dp, bot=bot)

app.on_startup.append(on_startup)
app.on_shutdown.append(on_shutdown)


if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))

    web.run_app(
        app,
        host="0.0.0.0",
        port=port
    )

