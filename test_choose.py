# -*- coding: utf-8 -*-
"""Проверка фазы ВЫБОР: пользователь берёт вариант — должна прийти строка про неон."""

import asyncio
import sys

sys.stdout.reconfigure(encoding="utf-8")

import bot  # noqa: E402


async def main() -> None:
    state = {
        "branch": 2,
        "system": bot.SYSTEM_BUSINESS,
        "history": [
            {"role": "user", "content": "Начнём."},
            {"role": "assistant", "content": "Чем занимается твой бизнес? Коротко."},
            {"role": "user", "content": "Обучающие видео по покеру и телеграм-канал."},
            {"role": "assistant",
             "content": "Честный покер\nДумать, не сливать\nУважение к деньгам\n\nКакой точнее? Или докрутим?"},
            {"role": "user", "content": "Беру «Честный покер», это прям оно."},
        ],
        "final_mission": None,
        "phase": "choosing",
        "questions": 6,
        "min_questions": 5,
    }

    reply = await bot.next_reply(state)
    print(f"[фаза={state['phase']}] ЛЮМЕН: {reply}")
    print(f"\nneon_offered: {bot.neon_offered(reply)}")


if __name__ == "__main__":
    asyncio.run(main())
