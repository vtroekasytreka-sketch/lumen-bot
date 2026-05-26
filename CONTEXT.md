# Lumen Bot

Telegram-бот для поиска жизненной миссии через глубокий диалог. Использует технику лестницы (laddering) — берёт конкретные слова из ответов и идёт глубже. После 8-15 обменов синтезирует миссию в 2-3 слова и генерирует неоновое превью.

## Стек

- Python 3.11
- aiogram 3.4+ (polling)
- aiohttp (health server)
- Groq API (llama-3.3-70b-versatile)
- Pillow — генерация неоновых превью
- httpx — HTTP клиент для API

## Структура

- `bot.py` — основной бот, хендлеры, health server
- `groq_client.py` — работа с Groq API, промпты для диалога и синтеза
- `dialog_manager.py` — управление состоянием диалога
- `storage.py` — хранение данных пользователей
- `neon_generator.py` — генерация неоновых картинок
- `voice_handler.py` — обработка голосовых (если есть)

## Запуск

```bash
python bot.py
```

Запускает параллельно:
- Telegram polling (`dp.start_polling(bot)`)
- aiohttp health server на порту из `PORT` (по умолчанию 10000)

## Деплой

- Платформа: Render
- Runtime: Docker
- URL: задеплоен на Render (см. dashboard)
- Репозиторий: https://github.com/vtroekasytreka-sketch/lumen-bot

## Переменные окружения

| Переменная | Описание |
|------------|----------|
| `TELEGRAM_BOT_TOKEN` | Токен бота от @BotFather |
| `GROQ_API_KEY` | API ключ Groq |
| `OWNER_CHAT_ID` | ID чата владельца для уведомлений о новых миссиях |
| `PORT` | Порт для health server (по умолчанию 10000) |

## Как работает

1. `/start` — бот задаёт первый вопрос про момент когда человек чувствовал себя на своём месте
2. Диалог 8-15 сообщений — Люмен берёт слова из ответов и идёт глубже (laddering)
3. Когда готов — синтезирует миссию в 2-3 слова + объяснение + цвет неона
4. Предлагает показать неоновое превью
5. Уведомляет владельца о новой найденной миссии

## Команды

- `/start` — начать диалог
- `/restart` — начать заново
- `/mission` — показать сохранённую миссию

## Решённые проблемы

**Webhook → Polling (май 2026)**
Render требует HTTP endpoint для health check. Решение:
- Polling для Telegram через aiogram
- aiohttp сервер для `/health` на том же event loop
- В render.yaml: `type: web` + `healthCheckPath: /health` + Docker runtime
