# -*- coding: utf-8 -*-
"""Смоук-тест фазовой логики без Telegram: гоняем next_reply по сценарию."""

import asyncio
import sys

sys.stdout.reconfigure(encoding="utf-8")

import bot  # noqa: E402


ANSWERS = [
    "Нарезаю обучающие видео по покеру и веду телеграм-канал для игроков",
    "Меня бесит, что новички сливают депозиты из-за мифов и кривых советов",
    "Когда подписчик написал, что впервые вышел в плюс за месяц по моим разборам",
    "Не готов продавать волшебные кнопки и курсы-пустышки, как все инфоцыгане",
    "Человек перестаёт играть на эмоциях, начинает думать и уважать свои деньги",
    "Не станет места, где про покер говорят честно, без обещаний лёгких денег",
    "Хм, наверное про честность и трезвый взгляд",
    "Второй вариант откликается",
]


async def main() -> None:
    state = {
        "branch": 2,
        "system": bot.SYSTEM_BUSINESS,
        "history": [{"role": "user", "content": "Начнём."}],
        "final_mission": None,
        "phase": "exploring",
        "questions": 0,
        "min_questions": bot.MIN_QUESTIONS_FIRST,
    }

    reply = await bot.ask_claude(
        bot.SYSTEM_BUSINESS, state["history"], bot.exploring_block(state)
    )
    state["questions"] = 1
    state["history"].append({"role": "assistant", "content": reply})
    print(f"[фаза={state['phase']} q={state['questions']}] ЛЮМЕН: {reply}\n")

    for answer in ANSWERS:
        state["history"].append({"role": "user", "content": answer})
        print(f"ЮЗЕР: {answer}")
        reply = await bot.next_reply(state)
        state["history"].append({"role": "assistant", "content": reply})
        print(f"[фаза={state['phase']} q={state['questions']}] ЛЮМЕН: {reply}\n")
        if bot.neon_offered(reply):
            print(">>> предложен неон, диалог завершён")
            break


if __name__ == "__main__":
    asyncio.run(main())
