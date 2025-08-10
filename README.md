# WhisperBot

Telegram bot to receive and send anonymous messages via unique links.

## Quick Start

1. Create `.env` from `.env.example` and set values:

```
TELEGRAM_BOT_TOKEN=your_bot_token
BOT_USERNAME=WhisperBot
DATABASE_URL=postgresql://user:pass@localhost/whisperbot_db
REDIS_URL=redis://localhost:6379/0
DEBUG=false
LOG_LEVEL=INFO
```

2. Install deps and run:

```
pip install -r requirements.txt
python main.py
```

## Commands

- /start [code]
- /play
- /inbox
- /stats
- /delete

## Jobs

The app starts background schedulers for session cleanup and daily stats.


