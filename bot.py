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

OWNER_CHAT_ID = os.getenv("OWNER_CHAT_ID")


SYSTEM_PERSONAL = """Ты — Люмен, тихий помощник. Помогаешь человеку найти его личную миссию в 2-3 слова.

Твоя задача — вытащить из него то, что уже есть внутри. Не придумать — а назвать точно.

Задавай вопросы по одному. Медленно. Глубоко. Без спешки.
Слушай ответы. Запоминай слова и образы, которые повторяются, — миссия соберётся из них.

Стиль: тихий, глубокий, без мотивации и шаблонов. Не подбадривай и не комментируй ответ — сразу следующий вопрос.

Вопросы примерно такие (адаптируй под ответы, иди вглубь за тем, что человек уже сказал):
- Что ты делаешь, когда забываешь о времени?
- Что для тебя очевидно, но другим непонятно?
- Если убрать деньги и мнение других — чем бы занимался?
- Что тебя злит в мире? (за этим часто стоит миссия)
- Каким тебя запомнят люди, которые тебя знают?

ОБЩИЕ ПРАВИЛА:
- Только ОДИН вопрос за раз. Никогда не задавай два сразу.
- Никогда не объясняй, что ты делаешь. Просто веди диалог.
- Вместе с последним сообщением пользователя приходит служебная инструкция с текущей ФАЗОЙ диалога. Следуй ей строго. Пользователю о ней не говори."""


SYSTEM_BUSINESS = """Ты — Люмен. Помогаешь предпринимателю найти предназначение его бизнеса в 2-3 слова.

Не слоган. Не УТП. Не миссию из учебника. А его личное «зачем» — то, ради чего он этим занимается на самом деле. Оно уже есть внутри, но не названо. Твоя задача — вытащить и назвать точно.

Задавай вопросы по одному. Конкретно, но вглубь: от фактов — к ценностям, от ценностей — к смыслу.
Слушай, какие слова и образы повторяются. Замечай, где человек оживает, где отвечает длиннее и теплее.

Стиль: тихий, точный, без мотивации и шаблонов. Не подбадривай и не комментируй ответ — сразу следующий вопрос.

Вопросы примерно такие (адаптируй под ответы):
- Чем занимается твой бизнес? Коротко.
- Зачем ты это начал? Не «заработать» — что зацепило по-настоящему?
- Вспомни момент, когда ты понял: вот ради этого всё. Что тогда произошло?
- Что в своём деле ты не готов делать «как все», даже если так проще и дешевле?
- Что меняется в жизни клиента после тебя — не в продукте, а в жизни?
- Если завтра бизнес исчезнет — чего не станет в мире, кроме твоего дохода?

ОБЩИЕ ПРАВИЛА:
- Только ОДИН вопрос за раз. Никогда не задавай два сразу.
- Никогда не объясняй, что ты делаешь. Просто веди диалог.
- Вместе с последним сообщением пользователя приходит служебная инструкция с текущей ФАЗОЙ диалога. Следуй ей строго. Пользователю о ней не говори."""


NEON_LINE_PERSONAL = "Это можно сделать в неон. Хочешь узнать как?"
NEON_LINE_BUSINESS = "Это слово можно поставить на стену офиса в неоне. Хочешь узнать как?"

# Лимиты фазы исследования: меньше MIN — варианты запрещены,
# больше HARD_CAP — синтез принудительно.
MIN_QUESTIONS_FIRST = 5
MIN_QUESTIONS_REFINE = 3
HARD_CAP_QUESTIONS = 9

READY_MARKER = "ГОТОВ"
DIG_MARKER = "КОПАЕМ"


def exploring_block(state: dict) -> str:
    block = (
        f"ФАЗА: ИССЛЕДОВАНИЕ. Уже задано вопросов: {state['questions']}. "
        "Задай следующий вопрос — один, вглубь того, что человек уже сказал. "
        "Предлагать варианты миссии в этой фазе ЗАПРЕЩЕНО."
    )
    if state["questions"] >= state["min_questions"]:
        block += (
            " Но если материала уже достаточно — слова повторяются, суть проступила — "
            f"не задавай вопрос, а ответь ровно одним словом: {READY_MARKER}"
        )
    return block


def synthesis_block(state: dict) -> str:
    ask = (
        "«Какой резонирует? Или поищем точнее?»"
        if state["branch"] == 1
        else "«Какой точнее? Или докрутим?»"
    )
    return (
        "ФАЗА: СИНТЕЗ. Вопросы закончились — больше НЕ задавай вопросов о деле. "
        "Сейчас единственное место в диалоге, где ты предлагаешь варианты. "
        "Собери 3 варианта миссии по 2-3 слова. Строй их из слов и образов самого "
        "человека — из того, что он повторял и где оживал. Никаких красивых "
        "шаблонных пар слов, которые подошли бы любому. "
        "Каждый вариант с новой строки, без нумерации и пояснений. "
        f"После вариантов спроси: {ask}"
    )


def choosing_block(state: dict) -> str:
    neon_line = NEON_LINE_PERSONAL if state["branch"] == 1 else NEON_LINE_BUSINESS
    return (
        "ФАЗА: ВЫБОР. Варианты уже предложены. Новые варианты предлагать НЕЛЬЗЯ, "
        "новые вопросы задавать НЕЛЬЗЯ. У тебя ровно два хода: "
        "1) если пользователь выбрал вариант или сформулировал свою фразу — подтверди "
        f"её и в том же сообщении закончи строкой: «{neon_line}» "
        "2) если он сомневается, хочет точнее или ни один вариант не отозвался — "
        f"ответь ровно одним словом: {DIG_MARKER}"
    )


def chosen_block(state: dict) -> str:
    return (
        "ФАЗА: ФИНАЛ. Миссия уже выбрана. Отвечай коротко и тихо. "
        "Если пользователь хочет пересмотреть миссию — "
        f"ответь ровно одним словом: {DIG_MARKER}"
    )


def is_marker(reply: str, marker: str) -> bool:
    text = reply.strip().upper()
    return text.startswith(marker) and len(text) <= len(marker) + 10


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


async def notify_owner(text: str) -> None:
    """Отправить уведомление владельцу. Молча игнорирует ошибки."""

    if not OWNER_CHAT_ID:
        return
    try:
        await bot.send_message(OWNER_CHAT_ID, text)
    except Exception:
        logger.exception("Не удалось уведомить владельца")


async def ask_claude(system: str, history: list[dict], note: str = "",
                     max_tokens: int = 500) -> str:
    """Запрос к Claude в отдельном потоке — requests блокирующий.

    note — служебная фазовая инструкция: подклеивается к последнему сообщению
    пользователя только на время вызова, в history не сохраняется.
    """

    messages = [dict(m) for m in history]
    if note:
        messages[-1]["content"] = (
            f"{messages[-1]['content']}\n\n"
            f"[Служебная инструкция ведущему, пользователь её не видит. {note}]"
        )
    return await asyncio.to_thread(call_claude_chat, messages, system, max_tokens)


@router.message(Command("start"))
async def cmd_start(message: Message):
    user_states.pop(message.chat.id, None)
    user = message.from_user
    name = (user.full_name if user else None) or "—"
    username = f"@{user.username}" if user and user.username else "—"
    await notify_owner(
        f"Новый пользователь в боте.\nИмя: {name}\nUsername: {username}"
    )
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
        "phase": "exploring",
        "questions": 0,
        "min_questions": MIN_QUESTIONS_FIRST,
    }
    user_states[chat_id] = state

    branch_label = "личная миссия" if branch == 1 else "миссия бизнеса"
    await notify_owner(f"Ветка: {branch_label}")

    await cb.answer()
    await bot.send_chat_action(chat_id, "typing")
    try:
        reply = await ask_claude(system, state["history"], exploring_block(state))
    except Exception:
        logger.exception("Claude error on branch select")
        await cb.message.answer("Не удалось связаться с Claude. Попробуй /start ещё раз.")
        return

    state["questions"] = 1
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


async def next_reply(state: dict) -> str:
    """Сделать ход диалога с учётом фазы. Меняет state, возвращает текст для пользователя.

    Маркерные ответы Claude (ГОТОВ/КОПАЕМ) перехватываются здесь, в историю
    не попадают — вместо них сразу делается следующий вызов в новой фазе.
    """

    system = state["system"]
    history = state["history"]

    if state["phase"] == "exploring":
        if state["questions"] < HARD_CAP_QUESTIONS:
            reply = await ask_claude(system, history, exploring_block(state))
            if not is_marker(reply, READY_MARKER):
                state["questions"] += 1
                return reply
        # Claude решил, что материала достаточно, либо упёрлись в потолок —
        # синтез: единственное место, где предлагаются варианты.
        reply = await ask_claude(system, history, synthesis_block(state))
        state["phase"] = "choosing"
        return reply

    block = choosing_block(state) if state["phase"] == "choosing" else chosen_block(state)
    reply = await ask_claude(system, history, block)

    if is_marker(reply, DIG_MARKER):
        state["phase"] = "exploring"
        state["questions"] = 0
        state["min_questions"] = MIN_QUESTIONS_REFINE
        reply = await ask_claude(system, history, exploring_block(state))
        state["questions"] = 1
        return reply

    if neon_offered(reply):
        state["phase"] = "chosen"
    return reply


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
        reply = await next_reply(state)
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
