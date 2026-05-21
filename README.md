# Lumen Bot

Telegram-бот для поиска жизненной миссии через глубокий диалог.

Люмен — мудрый тихий проводник. Он задаёт вопросы, идёт глубже в каждый ответ и помогает найти ядро твоей миссии. В конце генерирует превью неоновой вывески с твоей миссией.

## Возможности

- Живой диалог через Grok API (техника laddering)
- Распознавание голосовых сообщений (Whisper)
- Синтез миссии в 2-3 слова
- Генерация превью неоновой вывески
- Уведомления владельцу о новых миссиях

## Установка

### 1. Получить TELEGRAM_BOT_TOKEN

1. Открой Telegram и найди [@BotFather](https://t.me/BotFather)
2. Напиши `/newbot`
3. Введи имя бота (например: "Люмен")
4. Введи username бота (например: `lumen_mission_bot`)
5. BotFather пришлёт токен вида `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`
6. Скопируй этот токен

### 2. Получить GROK_API_KEY

1. Перейди на [console.x.ai](https://console.x.ai)
2. Зарегистрируйся или войди
3. Перейди в раздел API Keys
4. Создай новый ключ (Create API Key)
5. Скопируй ключ (он показывается только один раз!)

### 3. Получить OWNER_CHAT_ID

1. Открой Telegram и найди [@userinfobot](https://t.me/userinfobot)
2. Напиши `/start`
3. Бот пришлёт твой ID (число вида `123456789`)
4. Скопируй этот ID

### 4. Установить ffmpeg

**Windows:**
```powershell
# Через winget
winget install ffmpeg

# Или через Chocolatey
choco install ffmpeg

# Или скачай с https://ffmpeg.org/download.html
# и добавь в PATH
```

**macOS:**
```bash
brew install ffmpeg
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install ffmpeg
```

Проверь установку:
```bash
ffmpeg -version
```

### 5. Установить Python-зависимости

```bash
cd lumen-bot

# Создай виртуальное окружение (рекомендуется)
python -m venv venv

# Активируй его
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Установи зависимости
pip install -r requirements.txt
```

### 6. Настроить переменные окружения

```bash
# Скопируй пример
cp .env.example .env

# Открой .env и заполни значения
```

Содержимое `.env`:
```
TELEGRAM_BOT_TOKEN=твой_токен_от_botfather
GROK_API_KEY=твой_ключ_от_console.x.ai
OWNER_CHAT_ID=твой_chat_id
```

### 7. Запустить бота

```bash
python bot.py
```

## Команды бота

- `/start` — начать диалог с Люменом
- `/restart` — начать заново
- `/mission` — показать свою миссию (если уже проходил)

## Структура проекта

```
lumen-bot/
├── bot.py              # Основной файл бота
├── neon_generator.py   # Генерация превью неона
├── grok_client.py      # Работа с Grok API
├── dialog_manager.py   # Управление диалогом
├── voice_handler.py    # Обработка голоса
├── storage.py          # Сохранение в JSON
├── logs/
│   └── dialogs.json    # История диалогов
├── previews/           # Сгенерированные превью
├── .env                # Переменные окружения
├── .env.example        # Пример переменных
├── requirements.txt    # Зависимости
└── README.md           # Документация
```

## Как это работает

1. Пользователь пишет `/start`
2. Люмен задаёт первый вопрос о моменте "делания того что должен"
3. После каждого ответа Grok анализирует историю и решает:
   - Куда идти глубже
   - Готов ли материал для синтеза миссии
4. После 8-15 обменов Grok синтезирует миссию
5. Бот показывает миссию с драматической подачей
6. Предлагает превью неоновой вывески
7. Уведомляет владельца о новой миссии

## Голосовые сообщения

Бот распознаёт голосовые сообщения через Whisper:
1. Скачивает OGG файл из Telegram
2. Конвертирует в WAV через ffmpeg
3. Транскрибирует через Whisper (модель "small")
4. Показывает транскрипцию и обрабатывает как текст

## Примечания

- Первый запуск Whisper скачает модель (~500 MB)
- Диалоги сохраняются в `logs/dialogs.json`
- Превью сохраняются в `previews/`
- Для production рекомендуется использовать базу данных

## Лицензия

MIT
