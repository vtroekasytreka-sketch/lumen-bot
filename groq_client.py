"""Groq API client for dialog and mission synthesis."""

import os
import json
import httpx
from typing import Optional

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.3-70b-versatile"

LUMEN_SYSTEM_PROMPT = """Ты — Люмен. Мудрый тихий проводник который помогает человеку найти свою жизненную миссию.

Твой метод: техника лестницы (laddering). Каждый ответ человека — дверь. Ты заходишь именно в неё и идёшь глубже.

Правила:
— Говори коротко. 1-2 предложения максимум.
— Сначала одно предложение отражения ("Я слышу что для тебя важно...")
— Потом один точный вопрос. Только один.
— Вопрос должен идти глубже в то что человек сказал — не в сторону.
— Не используй слова: миссия, цель, призвание, предназначение. Говори про жизнь, ощущения, людей, моменты.
— После 8-15 обменов когда чувствуешь ядро — верни JSON: {"ready": true}
— Если ещё не готово — верни JSON: {"ready": false, "message": "твой ответ Люмена"}

Первый вопрос всегда:
"Расскажи мне о моменте когда ты чувствовал что делаешь именно то что должен. Неважно насколько он маленький."

ВАЖНО: Всегда отвечай ТОЛЬКО валидным JSON. Никакого текста до или после JSON."""

SYNTHESIS_PROMPT_TEMPLATE = """Вот полный диалог с человеком:
{history}

Найди то что стоит ЗА всеми словами. Не то что он говорил напрямую. А паттерн. Ядро. То что повторялось в разных формах.

Сформулируй миссию в 2-3 слова на русском. Слова должны:
— звучать как открытие, не как вывод
— быть поэтичными и точными
— не повторять слова из диалога напрямую
— рождаться из паттерна, не из прямых слов

Примеры хороших: Свет с направлением, Голос тишины, Мост между мирами, Хранитель огня, Тихая сила.

Также выбери цвет неона исходя из характера миссии:
— #B040FF фиолетовый — духовный, глубокий
— #4080FF синий — ясность, путь
— #FF40B0 розовый — тепло, связь
— #FFFFFF белый — чистота, свет
— #FFB040 золотой — мудрость, сила

Верни строго JSON:
{
  "mission": "Слова миссии",
  "explanation": "Объяснение 2-3 предложения почему именно эти слова",
  "neon_color": "#B040FF"
}

ВАЖНО: Отвечай ТОЛЬКО валидным JSON. Никакого текста до или после."""


def get_api_key() -> str:
    """Get Groq API key from environment."""
    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise ValueError("GROQ_API_KEY not set in environment")
    return key


def format_history_for_groq(history: list) -> list:
    """Convert dialog history to Groq message format."""
    messages = [{"role": "system", "content": LUMEN_SYSTEM_PROMPT}]

    for msg in history:
        role = "assistant" if msg["role"] == "bot" else "user"
        messages.append({"role": role, "content": msg["text"]})

    return messages


def format_history_for_synthesis(history: list) -> str:
    """Format history as readable text for synthesis."""
    lines = []
    for msg in history:
        prefix = "Люмен:" if msg["role"] == "bot" else "Человек:"
        lines.append(f"{prefix} {msg['text']}")
    return "\n".join(lines)


async def get_lumen_response(history: list) -> dict:
    """
    Get Lumen's response from Groq API.

    Returns dict with either:
        {"ready": True} - dialog complete
        {"ready": False, "message": "response text"} - continue dialog
    """
    api_key = get_api_key()
    messages = format_history_for_groq(history)

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            GROQ_API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": MODEL,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 500
            }
        )
        response.raise_for_status()
        data = response.json()

    content = data["choices"][0]["message"]["content"].strip()

    try:
        start = content.find("{")
        end = content.rfind("}") + 1
        if start != -1 and end > start:
            json_str = content[start:end]
            return json.loads(json_str)
    except json.JSONDecodeError:
        pass

    return {"ready": False, "message": content}


async def synthesize_mission(history: list) -> dict:
    """
    Synthesize mission from complete dialog history.

    Returns dict with:
        {"mission": "...", "explanation": "...", "neon_color": "#..."}
    """
    api_key = get_api_key()
    history_text = format_history_for_synthesis(history)
    prompt = SYNTHESIS_PROMPT_TEMPLATE.format(history=history_text)

    async with httpx.AsyncClient(timeout=90.0) as client:
        response = await client.post(
            GROQ_API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": MODEL,
                "messages": [
                    {"role": "system", "content": "Ты аналитик. Отвечай только валидным JSON."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.8,
                "max_tokens": 500
            }
        )
        response.raise_for_status()
        data = response.json()

    content = data["choices"][0]["message"]["content"].strip()

    try:
        start = content.find("{")
        end = content.rfind("}") + 1
        if start != -1 and end > start:
            json_str = content[start:end]
            return json.loads(json_str)
    except json.JSONDecodeError:
        pass

    return {
        "mission": "Путь света",
        "explanation": "Твои слова говорили о стремлении нести что-то важное другим.",
        "neon_color": "#B040FF"
    }


def get_first_message() -> str:
    """Get Lumen's opening message."""
    return "Расскажи мне о моменте когда ты чувствовал что делаешь именно то что должен. Неважно насколько он маленький."
