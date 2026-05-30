"""Lumen Bot — Telegram-помощник для поиска миссии через диалог.

Стек: aiogram 3.x (polling), aiohttp (health server), Claude через OpenRouter.

Запуск: python bot.py
"""

import asyncio
import logging
import os
import sys
from typing import Any

from aiohttp import web
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from dotenv import load_dotenv

from claude_client import call_claude_chat
import neon_generator


load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("lumen")


TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    print("Ошибка: TELEGRAM_BOT_TOKEN не найден в .env")
    sys.exit(1)

if not os.getenv("OPENROUTER_API_KEY"):
    print("Ошибка: OPENROUTER_API_KEY не найден в .env")
    sys.exit(1)


SYSTEM_PERSONAL = """Ты — Люмен, тихий помощник. Помогаешь человеку найти его личную миссию в 2-3 слова.

Твоя задача — вытащить из него то, что уже есть внутри. Не придумать — а назвать точно.

Задавай вопросы по одному. Медленно. Глубоко. Без спешки.
Слушай ответы. Замечай повторяющиеся слова и образы.
Когда почувствуешь суть — предложи 3 варианта миссии по 2-3 слова.

Стиль: тихий, глубокий, без мотивации и шаблонов. Не подбадривай и не комментируй ответ — сразу следующий вопрос.

Вопросы примерно такие (адаптируй под ответы):
- Что ты делаешь, когда забываешь о времени?
- Что для тебя очевидно, но другим непонятно?
- Если убрать деньги и мнение других — чем бы занимался?
- Что тебя злит в мире? (за этим часто стоит миссия)
- Каким тебя запомнят люди, которые тебя знают?

ЖЁСТКИЕ ПРАВИЛА:
- Только ОДИН вопрос за раз. Никогда не задавай два сразу.
- Минимум 5 вопросов прежде чем предлагать варианты.
- После 5–7 ответов предложи 3 варианта миссии. Каждый с новой строки, без нумерации, по 2-3 слова. Пример:
  Свет с направлением
  Тихая сила
  Глубина в простом
- После вариантов спроси: «Какой резонирует? Или поищем точнее?»
- Если пользователь выбрал — подтверди итоговое слово/фразу и в том же сообщении закончи строкой: «Это можно сделать в неон. Хочешь узнать как?»
- Если хочет докрутить — задай 1–2 уточняющих вопроса и предложи новые 3 варианта.
- Никогда не объясняй, что ты делаешь. Просто веди диалог."""


SYSTEM_BUSINESS = """Ты — Люмен. Помогаешь предпринимателю найти миссию его бизнеса в 2-3 слова.

Не слоган. Не описание услуг. А суть — зачем это дело существует.

Задавай вопросы по одному. Конкретно. По делу.
Слушай, что повторяется. Замечай, где у человека загораются глаза даже в тексте.

Вопросы примерно такие (адаптируй):
- Чем занимается твой бизнес? Коротко.
- Почему ты начал именно это, а не другое?
- Что ты даёшь клиенту кроме продукта/услуги?
- Что было бы потеряно, если бы твоего бизнеса не было?
- Чем твоё дело отличается — не по услуге, а по духу?
- Какой момент в работе даёт тебе больше всего энергии?

ЖЁСТКИЕ ПРАВИЛА:
- Только ОДИН вопрос за раз. Никогда не задавай два сразу.
- Минимум 5 вопросов прежде чем предлагать варианты.
- После 5–7 ответов предложи 3 варианта миссии бизнеса — каждый с новой строки, без нумерации, коротко и точно. Пример:
  Тепло в деталях
  Скорость с душой
  Смысл в каждом шве
- После вариантов спроси: «Какой точнее? Или докрутим?»
- Если пользователь выбрал — подтверди итоговое слово/фразу и в том же сообщении закончи строкой: «Это слово можно поставить на стену офиса в неоне. Хочешь узнать как?»
- Если хочет докрутить — задай 1–2 уточняющих вопроса и предложи новые 3 варианта.
- Никогда не объясняй, что ты делаешь. Просто веди диалог."""


WELCOME = (
    "Привет. Я помогу найти твоё слово.\n\n"
    "Про что работаем сегодня?"
)

NEON_COLOR = "#B040FF"


user_states: dict[int, dict[str, Any]] = {}

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()
router = Router()


def start_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1. Про меня — личная миссия",
                              callback_data="branch:1")],
        [InlineKeyboardButton(text="2. Про моё дело — миссия бизнеса",
                              callback_data="branch:2")],
    ])


def neon_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✨ Сделать неон", callback_data="neon")],
    ])


def neon_offered(reply: str) -> bool:
    """Claude закончил сообщение предложением неона."""

    low = reply.lower()
    return "можно сделать в неон" in low or "поставить на стену офиса в неоне" in low


async def ask_claude(system: str, history: list[dict],
                     max_tokens: int = 500) -> str:
    """Запрос к Claude в отдельном потоке — requests блокирующий."""

    return await asyncio.to_thread(call_claude_chat, history, system, max_tokens)


@router.message(Command("start"))
async def cmd_start(message: Message):
    user_states.pop(message.chat.id, None)
    await message.answer(WELCOME, reply_markup=start_keyboard())


@router.message(Command("restart"))
async def cmd_restart(message: Message):
    user_states.pop(message.chat.id, None)
    await message.answer(WELCOME, reply_markup=start_keyboard())


@router.message(Command("mission"))
async def cmd_mission(message: Message):
    state = user_states.get(message.chat.id)
    mission = (state or {}).get("final_mission")
    if mission:
        await message.answer(f"Твоя миссия: {mission}", reply_markup=neon_keyboard())
    else:
        await message.answer("Миссии пока нет. /start — чтобы начать.")


@router.callback_query(F.data.startswith("branch:"))
async def cb_branch(cb: CallbackQuery):
    branch = int(cb.data.split(":")[1])
    chat_id = cb.message.chat.id
    system = SYSTEM_PERSONAL if branch == 1 else SYSTEM_BUSINESS

    state = {
        "branch": branch,
        "system": system,
        "history": [{"role": "user", "content": "Начнём."}],
        "final_mission": None,
    }
    user_states[chat_id] = state

    await cb.answer()
    await bot.send_chat_action(chat_id, "typing")
    try:
        reply = await ask_claude(system, state["history"])
    except Exception:
        logger.exception("Claude error on branch select")
        await cb.message.answer("Не удалось связаться с Claude. Попробуй /start ещё раз.")
        return

    state["history"].append({"role": "assistant", "content": reply})
    await cb.message.answer(reply)


@router.callback_query(F.data == "neon")
async def cb_neon(cb: CallbackQuery):
    chat_id = cb.message.chat.id
    state = user_states.get(chat_id)
    if not state:
        await cb.answer("Сначала /start", show_alert=True)
        return

    await cb.answer()
    await bot.send_chat_action(chat_id, "upload_photo")

    extract_prompt = (
        "Из нашего диалога выведи итоговую миссию пользователя в 2-3 слова. "
        "Только эту фразу, без кавычек, без пояснений, одной строкой."
    )
    extract_history = list(state["history"]) + [
        {"role": "user", "content": extract_prompt}
    ]

    try:
        raw = await ask_claude(state["system"], extract_history, max_tokens=30)
    except Exception:
        logger.exception("Claude error on mission extract")
        await cb.message.answer("Не получилось достать миссию. /restart")
        return

    mission = raw.strip().strip('"').strip().splitlines()[0].strip()
    state["final_mission"] = mission

    try:
        path = await asyncio.to_thread(
            neon_generator.generate_neon,
            mission,
            NEON_COLOR,
            f"previews/neon_{chat_id}.png",
        )
        await cb.message.answer_photo(
            photo=FSInputFile(path),
            caption=mission,
        )
    except Exception:
        logger.exception("Neon generation failed")
        await cb.message.answer(f"{mission}\n\n(не удалось собрать превью)")


@router.message(F.text)
async def handle_text(message: Message):
    chat_id = message.chat.id
    state = user_states.get(chat_id)
    if not state:
        await message.answer("Нажми /start, чтобы начать.")
        return

    history = state["history"]
    history.append({"role": "user", "content": message.text.strip()})

    await bot.send_chat_action(chat_id, "typing")
    try:
        reply = await ask_claude(state["system"], history)
    except Exception:
        logger.exception("Claude error on user message")
        history.pop()
        await message.answer("Не получилось ответить. Попробуй ещё раз.")
        return

    history.append({"role": "assistant", "content": reply})

    kb = neon_keyboard() if neon_offered(reply) else None
    await message.answer(reply, reply_markup=kb)


async def health(_request):
    return web.Response(text="ok")


async def start_health_server():
    app = web.Application()
    app.router.add_get("/health", health)
    app.router.add_get("/", health)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", "10000"))
    site = web.TCPSite(runner, host="0.0.0.0", port=port)
    await site.start()
    logger.info("Health server on :%d", port)


async def main():
    dp.include_router(router)
    await start_health_server()
    logger.info("Lumen bot polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
