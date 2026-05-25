"""
Lumen Bot - Telegram bot for discovering life mission through deep dialogue.
Polling + health check server for Render deployment.
"""

import asyncio
import os
import logging
from dotenv import load_dotenv

from aiohttp import web
from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    FSInputFile,
)
from aiogram.enums import ChatAction

import dialog_manager
from dialog_manager import DialogState
import groq_client
import neon_generator
import storage

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OWNER_CHAT_ID = os.getenv("OWNER_CHAT_ID")
PORT = int(os.getenv("PORT", 10000))

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN not set in .env file")

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()
router = Router()


async def send_typing(chat_id: int, duration: float = 2.0):
    """Send typing action for specified duration."""
    await bot.send_chat_action(chat_id, ChatAction.TYPING)
    await asyncio.sleep(duration)


async def send_with_typing(chat_id: int, text: str, delay: float = 2.0, **kwargs):
    """Send message with typing indicator beforehand."""
    await send_typing(chat_id, delay)
    return await bot.send_message(chat_id, text, **kwargs)


@router.message(Command("start"))
async def cmd_start(message: Message):
    """Handle /start command."""
    user_id = message.from_user.id
    username = message.from_user.username
    name = message.from_user.full_name

    if dialog_manager.has_completed_dialog(user_id):
        mission_data = dialog_manager.get_user_mission(user_id)
        if mission_data:
            await message.answer(
                f"С возвращением.\n\n"
                f"Твоя найденная миссия: *{mission_data['mission']}*\n\n"
                f"Если хочешь пройти путь заново — напиши /restart",
                parse_mode="Markdown"
            )
            return

    dialog_manager.start_dialog(user_id, username, name)

    await send_typing(message.chat.id, 3.0)

    first_message = await groq_client.get_first_message()
    dialog_manager.add_bot_message(user_id, first_message)

    await message.answer(
        f"Привет. Я Люмен.\n\n{first_message}"
    )


@router.message(Command("restart"))
async def cmd_restart(message: Message):
    """Handle /restart command."""
    user_id = message.from_user.id
    username = message.from_user.username
    name = message.from_user.full_name

    dialog_manager.restart_dialog(user_id, username, name)

    await send_typing(message.chat.id, 3.0)

    first_message = await groq_client.get_first_message()
    dialog_manager.add_bot_message(user_id, first_message)

    await message.answer(
        f"Начнём сначала.\n\n{first_message}"
    )


@router.message(Command("mission"))
async def cmd_mission(message: Message):
    """Handle /mission command - show saved mission."""
    user_id = message.from_user.id

    mission_data = dialog_manager.get_user_mission(user_id)

    if mission_data:
        await message.answer(
            f"Твоя миссия: *{mission_data['mission']}*\n\n"
            f"{mission_data['explanation']}",
            parse_mode="Markdown"
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Показать в неоне", callback_data="show_neon")]
        ])
        await message.answer(
            "Хочешь увидеть её в неоне?",
            reply_markup=keyboard
        )
    else:
        await message.answer(
            "У тебя пока нет найденной миссии.\n"
            "Напиши /start чтобы начать путь."
        )


@router.message(F.text)
async def handle_text(message: Message):
    """Handle text messages."""
    user_id = message.from_user.id
    state = dialog_manager.get_state(user_id)

    if state != DialogState.IN_PROGRESS:
        await message.answer("Напиши /start чтобы начать диалог.")
        return

    await process_user_message(message, message.text)


async def process_user_message(message: Message, text: str):
    """Process user message and get Lumen's response."""
    user_id = message.from_user.id
    chat_id = message.chat.id

    dialog_manager.add_user_message(user_id, text, voice=False)

    history = dialog_manager.get_history(user_id)

    await send_typing(chat_id, 2.5)

    try:
        response = await groq_client.get_lumen_response(history)
    except Exception as e:
        logger.error(f"Groq API error: {e}")
        await message.answer(
            "Прости, мне нужно немного времени. Попробуй написать снова."
        )
        return

    if response.get("ready"):
        await begin_synthesis(message)
    else:
        lumen_message = response.get("message", "Расскажи мне больше.")
        dialog_manager.add_bot_message(user_id, lumen_message)
        await message.answer(lumen_message)


async def begin_synthesis(message: Message):
    """Begin mission synthesis process."""
    user_id = message.from_user.id
    chat_id = message.chat.id

    dialog_manager.set_state(user_id, DialogState.AWAITING_SYNTHESIS)

    await send_with_typing(chat_id, "Позволь мне побыть с тем что ты сказал...", 5.0)

    history = dialog_manager.get_history(user_id)

    try:
        mission_data = await groq_client.synthesize_mission(history)
    except Exception as e:
        logger.error(f"Mission synthesis error: {e}")
        await message.answer(
            "Что-то пошло не так. Попробуй /restart и начнём заново."
        )
        return

    mission = mission_data.get("mission", "Путь света")
    explanation = mission_data.get("explanation", "")
    neon_color = mission_data.get("neon_color", "#B040FF")

    dialog_manager.save_mission(user_id, mission, explanation, neon_color)

    await send_with_typing(chat_id, "Я вижу кое-что в твоих словах.", 3.0)

    await send_with_typing(chat_id, f"Твой путь звучит как: *{mission}*", 2.0, parse_mode="Markdown")

    await asyncio.sleep(1.5)
    await message.answer(explanation)

    await asyncio.sleep(2.0)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Да, покажи", callback_data="show_neon"),
            InlineKeyboardButton(text="Нет, спасибо", callback_data="skip_neon")
        ]
    ])

    dialog_manager.set_state(user_id, DialogState.AWAITING_NEON_CHOICE)

    await message.answer(
        "Хочешь увидеть как это выглядит в неоне?",
        reply_markup=keyboard
    )


@router.callback_query(F.data == "show_neon")
async def callback_show_neon(callback: CallbackQuery):
    """Handle 'show neon' button press."""
    user_id = callback.from_user.id
    chat_id = callback.message.chat.id

    await callback.answer()

    mission_data = dialog_manager.get_user_mission(user_id)
    if not mission_data:
        await callback.message.answer("Сначала пройди диалог: /start")
        return

    await bot.send_chat_action(chat_id, ChatAction.UPLOAD_PHOTO)

    try:
        image_path = neon_generator.generate_neon_for_user(
            user_id,
            mission_data["mission"],
            mission_data["neon_color"]
        )
    except Exception as e:
        logger.error(f"Neon generation error: {e}")
        await callback.message.answer("Не удалось создать превью. Попробуй позже.")
        return

    photo = FSInputFile(image_path)
    await bot.send_photo(chat_id, photo)

    dialog_manager.mark_neon_sent(user_id)
    dialog_manager.mark_completed(user_id)

    await callback.message.answer(
        "Вот как может выглядеть твой путь в неоне.\n\n"
        "Это только превью.\n"
        "Настоящая вывеска — живая, светящаяся, на стене твоего дома.\n\n"
        "Если хочешь сделать её реальной — напиши @neonphrase_studio\n"
        "Обсудим размер, цвет и детали."
    )

    await notify_owner(user_id, mission_data, image_path)


@router.callback_query(F.data == "skip_neon")
async def callback_skip_neon(callback: CallbackQuery):
    """Handle 'skip neon' button press."""
    user_id = callback.from_user.id

    await callback.answer()

    dialog_manager.mark_completed(user_id)

    await callback.message.answer(
        "Хорошо. Твоя миссия сохранена.\n"
        "Если передумаешь — напиши /mission"
    )

    mission_data = dialog_manager.get_user_mission(user_id)
    if mission_data:
        await notify_owner(user_id, mission_data, None)


async def notify_owner(user_id: int, mission_data: dict, image_path: str = None):
    """Send notification to bot owner about completed dialog."""
    if not OWNER_CHAT_ID:
        return

    dialog = storage.get_user_dialog(user_id)
    if not dialog:
        return

    username = dialog.get("username", "")
    name = dialog.get("name", "")
    message_count = len([m for m in dialog.get("history", []) if m["role"] == "user"])

    user_display = f"@{username}" if username else "(без username)"

    notification_text = (
        f"🌟 Новая миссия найдена!\n\n"
        f"👤 {user_display} ({name})\n"
        f"✨ {mission_data['mission']}\n"
        f"📝 {mission_data['explanation']}\n"
        f"🎨 Цвет: {mission_data['neon_color']}\n"
        f"💬 Диалог: {message_count} сообщений"
    )

    try:
        await bot.send_message(int(OWNER_CHAT_ID), notification_text)

        if image_path:
            photo = FSInputFile(image_path)
            await bot.send_photo(int(OWNER_CHAT_ID), photo)
    except Exception as e:
        logger.error(f"Failed to notify owner: {e}")


async def health_check(request):
    """Health check endpoint for Render."""
    return web.Response(text="OK")


async def run_health_server():
    """Run simple HTTP server for health checks."""
    app = web.Application()
    app.router.add_get("/", health_check)
    app.router.add_get("/health", health_check)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logger.info(f"Health check server running on port {PORT}")


async def main():
    """Start the bot with polling and health check server."""
    dp.include_router(router)

    await run_health_server()

    logger.info("Starting bot with polling...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
