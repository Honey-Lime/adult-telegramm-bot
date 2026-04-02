"""
Обработчики жалоб на контент.
"""

import database
from keyboards import get_report_reasons_keyboard
from locales import get_text


async def handle_report_menu(controller, chat_id: int, message_id: int, lang: str):
    """
    Показ меню выбора причины жалобы.
    
    Args:
        controller: Экземпляр BotController
        chat_id: ID чата пользователя
        message_id: ID сообщения для удаления
        lang: Язык пользователя
    """
    await controller.delete_current(chat_id, message_id)
    
    keyboard = get_report_reasons_keyboard(lang)
    text = get_text(lang, 'report_reason_text')
    
    await controller.send_and_track(
        chat_id,
        text=text,
        reply_markup=keyboard
    )


async def handle_report_wrong_type(controller, chat_id: int, lang: str):
    """
    Жалоба на неправильный тип изображения.
    
    Args:
        controller: Экземпляр BotController
        chat_id: ID чата пользователя
        lang: Язык пользователя
    """
    user = database.get_user(chat_id)
    
    if not user:
        await controller.send_picture(chat_id)
        return
    
    image_id = user.get('last_watched')
    
    if image_id is None:
        await controller.send_picture(chat_id)
        return
    
    # Проверка: админ или обычный пользователь
    if chat_id in controller.admin_ids:
        # Админ: сразу меняем тип
        database.toggle_type(chat_id)
        database.add_coins(chat_id, 1)  # начисляем монету
        await controller.send_picture(chat_id)
    else:
        # Обычный пользователь: проверяем not_real_type
        not_real = database.get_not_real_type(image_id)
        
        if not_real is None:
            await controller.send_picture(chat_id)
            return
        
        if not_real:
            # Уже была жалоба – меняем тип
            database.toggle_type(chat_id)
            database.add_coins(chat_id, 1)
            await controller.send_picture(chat_id)
        else:
            # Первая жалоба – ставим флаг
            database.set_not_real_type(image_id, True)
            database.add_coins(chat_id, 1)
            await controller.send_picture(chat_id)


async def handle_report_inappropriate(controller, chat_id: int, lang: str):
    """
    Жалоба на неприемлемый контент.
    
    Args:
        controller: Экземпляр BotController
        chat_id: ID чата пользователя
        lang: Язык пользователя
    """
    user = database.get_user(chat_id)
    
    if user and user.get('last_watched'):
        database.set_need_moderate(user['last_watched'])
        database.add_coins(chat_id, 1)  # начисляем монету
    
    await controller.send_picture(chat_id)


async def handle_report_cancel(controller, chat_id: int, lang: str):
    """
    Отмена жалобы.
    
    Args:
        controller: Экземпляр BotController
        chat_id: ID чата пользователя
        lang: Язык пользователя
    """
    await controller.send_picture(chat_id)
