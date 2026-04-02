"""
Обработчики выбора типа контента (аниме/фото).
"""

import database
from locales import get_text


async def handle_content_type(controller, callback_data: str, chat_id: int, lang: str):
    """
    Обработка выбора типа контента: аниме или фото.
    
    Args:
        controller: Экземпляр BotController
        callback_data: Данные callback (anime/real)
        chat_id: ID чата пользователя
        lang: Язык пользователя
    """
    if callback_data == "anime":
        database.user_set_type(chat_id, database.ImageType.ANIME.value)
    elif callback_data == "real":
        database.user_set_type(chat_id, database.ImageType.REAL.value)
    
    await controller.send_picture(chat_id)


async def handle_menu(controller, chat_id: int):
    """
    Показ главного меню.
    
    Args:
        controller: Экземпляр BotController
        chat_id: ID чата пользователя
    """
    await controller.send_menu(chat_id)
