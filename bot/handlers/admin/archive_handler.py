"""
Обработчик раздела "Архив" в админ-панели.
Показывает статистику по картинкам и видео в базе данных.
"""

import database
from locales import get_text


async def handle_admin_archive(controller, chat_id: int, message_id: int, lang: str):
    """
    Показывает статистику архива: количество картинок/видео,
    сколько не проходят фильтр, и статистику по уровням total.
    """
    if chat_id not in controller.admin_ids:
        await controller.send_and_track(chat_id, text="⛔ Доступ запрещён", track=False)
        await controller.delete_current(chat_id, message_id)
        return

    stats = database.get_archive_stats()

    text = (
        f"📦 <b>Архив контента</b>\n\n"
        f"🖼 <b>Картинки:</b>\n"
        f"  Всего: {stats['images']['total']}\n"
        f"  • Фото: {stats['images']['real']}\n"
        f"  • Аниме: {stats['images']['anime']}\n"
        f"  Не проходят фильтр: {stats['images']['need_more_ratings']}\n\n"
        f"🎞 <b>Видео:</b>\n"
        f"  Всего: {stats['videos']['total']}\n"
        f"  Не проходят фильтр: {stats['videos']['need_more_ratings']}\n\n"
        f"📊 <b>Уровни total (картинки):</b>\n"
        f"  total ≥ 1: {stats['images']['total_gte_1']}\n"
        f"  total ≥ 2: {stats['images']['total_gte_2']}\n"
        f"  total ≥ 4: {stats['images']['total_gte_4']}\n"
        f"  total ≥ 10: {stats['images']['total_gte_10']}\n"
        f"  total ≥ 20: {stats['images']['total_gte_20']}\n\n"
        f"📊 <b>Уровни total (видео):</b>\n"
        f"  total ≥ 1: {stats['videos']['total_gte_1']}\n"
        f"  total ≥ 2: {stats['videos']['total_gte_2']}\n"
        f"  total ≥ 4: {stats['videos']['total_gte_4']}\n"
        f"  total ≥ 10: {stats['videos']['total_gte_10']}\n"
        f"  total ≥ 20: {stats['videos']['total_gte_20']}"
    )

    await controller.send_and_track(chat_id, text=text, track=False)
