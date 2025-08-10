from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from services.stats_service import get_user_stats, get_global_stats
from utils.logger import logger
from utils.helpers import escape_markdown_v2 as _esc, get_separator as _sep


def _format_user_stats(stats: dict) -> str:
    if not stats.get("exists"):
        return "❌ User not found\\."
    username = _esc(str(stats.get('username', '')))
    active = "Yes" if stats.get('is_active') else "No"
    total_recv = str(stats.get('total_messages_received', 0))
    unread = str(stats.get('unread_count', 0))
    total_sent = str(stats.get('total_messages_sent', 0))
    last = _esc(str(stats.get('last_activity', '—')))
    return (
        "*📊 Your Stats*\n"
        f"{_sep()}\n"
        f"👤 *Username*\\: {username}\n"
        f"✅ *Active*\\: {active}\n"
        f"📥 *Messages received*\\: {total_recv} \\(unread\\: {unread}\\)\n"
        f"📤 *Messages sent*\\: {total_sent}\n"
        f"🕓 *Last activity*\\: {last}\n"
    )


def _format_global_stats(stats: dict) -> str:
    total_users = str(stats.get('total_users', 0))
    active_30d = str(stats.get('active_users', 0))
    sent_today = str(stats.get('messages_sent_today', 0))
    new_regs = str(stats.get('new_registrations', 0))
    return (
        "*🌍 Global Stats* \\(today\\)\n"
        f"{_sep()}\n"
        f"👥 *Total users*\\: {total_users}\n"
        f"🔥 *Active users* \\(30d\\)\\: {active_30d}\n"
        f"✉️ *Messages sent today*\\: {sent_today}\n"
        f"🆕 *New registrations*\\: {new_regs}\n"
    )


async def handle_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        tg_user = update.effective_user
        user_stats = get_user_stats(tg_user.id)
        global_stats = get_global_stats()
        text = _format_user_stats(user_stats) + "\n" + _format_global_stats(global_stats)
        await update.message.reply_markdown_v2(text)
    except Exception as e:
        logger.error(f"[StatsHandler] Error in /stats: {e}")
        await update.message.reply_markdown_v2("❌ Failed to load stats\\. Please try again later\\.")


