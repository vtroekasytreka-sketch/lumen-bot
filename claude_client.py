"""Claude через OpenRouter (anthropic/claude-sonnet-4-5)."""

import os

import requests

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "anthropic/claude-sonnet-4-5"


def call_claude_chat(messages: list[dict], system: str,
                     max_tokens: int = 500) -> str:
    """Многоходовой запрос. messages — alternating user/assistant, последний — user."""

    full = [{"role": "system", "content": system}] + messages

    response = requests.post(
        OPENROUTER_URL,
        headers={
            "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
            "Content-Type": "application/json",
        },
        json={
            "model": MODEL,
            "messages": full,
            "max_tokens": max_tokens,
        },
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def call_claude(prompt: str, system: str, max_tokens: int = 500) -> str:
    """Одноходовой запрос — обёртка над call_claude_chat."""

    return call_claude_chat(
        [{"role": "user", "content": prompt}], system, max_tokens
    )
