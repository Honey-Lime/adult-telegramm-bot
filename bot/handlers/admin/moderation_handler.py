"""
Обработчик модерации изображений.
"""

import database
from keyboards import get_moderation_keyboard
from locales import get_text


async def handle_moderation_change_type(controller, callback_data: str, chat_id: int, lang: str):
    """
    Смена типа изображения на модерации (Фото <-> Аниме).
    
    Args:
        controller: Экземпляр BotController
        callback_data: Данные callback (mod_change_type_{image_id})
        chat_id: ID чата пользователя
        lang: Язык пользователя
    """
    if chat_id not in controller.admin_ids:
        await controller.send_and_track(chat_id, text="⛔ Доступ запрещён", track=False)
        return
    
    # Извлечение ID изображения
    try:
        image_id = int(callback_data.split('_')[3])
    except (IndexError, ValueError):
        await controller.send_and_track(chat_id, text=get_text(lang, 'callback_error'), track=False)
        return
    
    new_type = database.change_image_type(image_id)
    
    if new_type is not None:
        type_name = 'Аниме' if new_type == database.ImageType.ANIME.value else 'Фото'
        await controller.send_and_track(chat_id, text=get_text(lang, 'type_changed_moderation'), track=False)
        # Обновляем сообщение модерации с новым типом
        await controller.send_next_moderation_image(chat_id)
    else:
        await controller.send_and_track(chat_id, text=get_text(lang, 'type_change_error'), track=False)


async def handle_admin_moderation(controller, chat_id: int, message_id: int, lang: str):
    """
    Показ изображения на модерации.
    
    Args:
        controller: Экземпляр BotController
        chat_id: ID чата пользователя
        message_id: ID сообщения для удаления
        lang: Язык пользователя
    """
    if chat_id not in controller.admin_ids:
        await controller.send_and_track(chat_id, text="⛔ Доступ запрещён", track=False)
        await controller.delete_current(chat_id, message_id)
        return
    
    await controller.show_moderation_image(chat_id, message_id)


async def handle_moderation_delete(controller, callback_data: str, chat_id: int, lang: str):
    """
    Удаление изображения на модерации.
    
    Args:
        controller: Экземпляр BotController
        callback_data: Данные callback (mod_delete_{image_id})
        chat_id: ID чата пользователя
        lang: Язык пользователя
    """
    if chat_id not in controller.admin_ids:
        await controller.send_and_track(chat_id, text="⛔ Доступ запрещён", track=False)
        return
    
    # Извлечение ID изображения
    try:
        image_id = int(callback_data.split('_')[2])
    except (IndexError, ValueError):
        await controller.send_and_track(chat_id, text=get_text(lang, 'callback_error'), track=False)
        return
    
    success = database.delete_image(image_id)
    
    if success:
        await controller.send_and_track(chat_id, text=get_text(lang, 'image_deleted'), track=False)
    else:
        await controller.send_and_track(chat_id, text=get_text(lang, 'image_restore_error'), track=False)
    
    # Обновление очереди модерации
    if chat_id in controller.moderation_queues and controller.moderation_queues[chat_id]:
        controller.moderation_queues[chat_id].pop(0)
    
    await controller.send_next_moderation_image(chat_id)


async def handle_moderation_restore(controller, callback_data: str, chat_id: int, lang: str):
    """
    Восстановление изображения (снятие флага модерации).
    
    Args:
        controller: Экземпляр BotController
        callback_data: Данные callback (mod_restore_{image_id})
        chat_id: ID чата пользователя
        lang: Язык пользователя
    """
    if chat_id not in controller.admin_ids:
        await controller.send_and_track(chat_id, text="⛔ Доступ запрещён", track=False)
        return
    
    # Извлечение ID изображения
    try:
        image_id = int(callback_data.split('_')[2])
    except (IndexError, ValueError):
        await controller.send_and_track(chat_id, text=get_text(lang, 'callback_error'), track=False)
        return
    
    success = database.clear_moderation(image_id)
    
    if success:
        await controller.send_and_track(chat_id, text=get_text(lang, 'image_restored'), track=False)
    else:
        await controller.send_and_track(chat_id, text=get_text(lang, 'restore_error'), track=False)
    
    # Обновление очереди модерации
    if chat_id in controller.moderation_queues and controller.moderation_queues[chat_id]:
        controller.moderation_queues[chat_id].pop(0)
    
    await controller.send_next_moderation_image(chat_id)
