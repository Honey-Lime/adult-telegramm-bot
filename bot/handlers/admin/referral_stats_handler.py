"""
Обработчик статистики рефералов для админ-панели.
Показывает статистику по рекламным ссылкам и по пользователям, которые привлекли рефералов.
"""
import logging
from database import (
    get_all_promo_links_registration_stats,
    get_all_promo_links,
    get_promo_link_by_code,
    get_referral_stats_by_users,
)
from locales import get_text
from keyboards import get_admin_panel_keyboard


async def handle_admin_referral_stats(controller, chat_id: int, message_id: int, lang: str) -> None:
    """Показывает статистику по рекламным ссылкам и рефералам пользователей."""
    await controller.delete_current(chat_id, message_id)

    # Статистика по рекламным ссылкам
    promo_stats = get_all_promo_links_registration_stats()
    promo_links = get_all_promo_links()

    # Статистика по пользователям-реферерам
    user_referral_stats = get_referral_stats_by_users()

    lines = []

    # --- Блок 1: Рекламные ссылки ---
    lines.append("📊 Статистика рекламных ссылок:\n")
    if not promo_stats:
        lines.append("❌ Пока нет регистраций по рекламным ссылкам.\n")
    else:
        name_map = {p['code']: p['name'] for p in promo_links}
        for i, stat in enumerate(promo_stats, 1):
            code = stat['promo_code']
            name = name_map.get(code, code)
            lines.append(
                f"{i}. 📛 {name} (`{code}`)\n"
                f"   👥 Всего: {stat['total_users']} | 📅 Сегодня: {stat['today_users']}\n"
            )
        lines.append("")

    # --- Блок 2: Рефералы пользователей ---
    lines.append("👥 Топ рефереров:\n")
    if not user_referral_stats:
        lines.append("❌ Пока нет рефералов от пользователей.")
    else:
        for i, stat in enumerate(user_referral_stats, 1):
            display_name = _format_user_name(stat)
            lines.append(
                f"{i}. {display_name}\n"
                f"   👥 Всего рефералов: {stat['referrals_count']} | 📅 Сегодня: {stat['today_referrals']}\n"
                f"   💰 Монет заработано: {stat['total_coins_earned']}\n"
            )

    text = "\n".join(lines)

    await controller.send_and_track(chat_id, text=text, track=False)

    # Возвращаем в админ-меню
    keyboard = get_admin_panel_keyboard(lang)
    await controller.send_and_track(
        chat_id,
        text="Админ-панель. Выберите действие:",
        reply_markup=keyboard,
        track=False
    )


def _format_user_name(stat: dict) -> str:
    """Форматирует имя пользователя для отображения."""
    parts = []
    if stat.get('first_name'):
        parts.append(stat['first_name'])
    if stat.get('last_name'):
        parts.append(stat['last_name'])
    
    name = " ".join(parts) if parts else f"ID {stat['referrer_id']}"
    
    if stat.get('username'):
        return f"👤 {name} (@{stat['username']})"
    return f"👤 {name}"
