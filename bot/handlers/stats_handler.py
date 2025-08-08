from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from services.stats_service import get_user_stats, get_global_stats
from utils.logger import logger


def _format_user_stats(stats: dict) -> str:
    if not stats.get("exists"):
        return "❌ User not found."
    return (
        "📊 Your Stats\n\n"
        f"Username: {stats['username']}\n"
        f"Active: {'Yes' if stats['is_active'] else 'No'}\n"
        f"Messages received: {stats['total_messages_received']} (unread: {stats['unread_count']})\n"
        f"Messages sent: {stats['total_messages_sent']}\n"
        f"Last activity: {stats['last_activity']}\n"
    )


def _format_global_stats(stats: dict) -> str:
    return (
        "🌍 Global Stats (today)\n\n"
        f"Total users: {stats.get('total_users', 0)}\n"
        f"Active users (30d): {stats.get('active_users', 0)}\n"
        f"Messages sent today: {stats.get('messages_sent_today', 0)}\n"
        f"New registrations: {stats.get('new_registrations', 0)}\n"
    )


async def handle_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        tg_user = update.effective_user
        user_stats = get_user_stats(tg_user.id)
        global_stats = get_global_stats()
        text = _format_user_stats(user_stats) + "\n" + _format_global_stats(global_stats)
        await update.message.reply_text(text)
    except Exception as e:
        logger.error(f"[StatsHandler] Error in /stats: {e}")
        await update.message.reply_text("❌ Failed to load stats. Please try again later.")


