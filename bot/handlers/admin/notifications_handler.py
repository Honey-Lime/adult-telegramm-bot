"""
Обработчик уведомлений и рассылок.
"""

import asyncio
import logging
import database
from keyboards import get_notifications_menu_keyboard, get_notification_confirm_keyboard, get_admin_messages_menu_keyboard
from locales import get_text


async def handle_admin_notifications(controller, chat_id: int, message_id: int, lang: str):
    """
    Показ меню выбора оповещения для рассылки.
    
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
    
    await controller.delete_current(chat_id, message_id)
    
    keyboard = get_notifications_menu_keyboard(lang)
    await controller.send_and_track(
        chat_id,
        text="📢 Выберите оповещение для рассылки:",
        reply_markup=keyboard,
        track=False
    )


async def handle_notification_restored(controller, chat_id: int, message_id: int, lang: str):
    """
    Подготовка рассылки о восстановлении работы бота.
    
    Args:
        controller: Экземпляр BotController
        chat_id: ID чата пользователя
        message_id: ID сообщения для удаления
        lang: Язык пользователя
    """
    if chat_id not in controller.admin_ids:
        await controller.send_and_track(chat_id, text="⛔ Доступ запрещён", track=False)
        return
    
    await controller.delete_current(chat_id, message_id)
    
    message_text = "Работа бота восстановлена, ждем вас снова"
    keyboard = get_notification_confirm_keyboard("restored", lang)
    
    await controller.send_and_track(
        chat_id,
        text=f"📢 Отправить оповещение:\n\n{message_text}",
        reply_markup=keyboard,
        track=False
    )


async def handle_notification_custom(controller, chat_id: int, message_id: int, lang: str):
    """
    Подготовка рассылки пользовательского сообщения.
    
    Args:
        controller: Экземпляр BotController
        chat_id: ID чата пользователя
        message_id: ID сообщения для удаления
        lang: Язык пользователя
    """
    if chat_id not in controller.admin_ids:
        await controller.send_and_track(chat_id, text="⛔ Доступ запрещён", track=False)
        return
    
    await controller.delete_current(chat_id, message_id)
    
    await controller.send_and_track(
        chat_id,
        text="Следующее сообщение будет отправлено всем пользователям. Напишите текст сообщения:",
        track=False
    )
    
    controller.waiting_for_custom_message[chat_id] = True
    controller.pending_custom_message[chat_id] = ""


async def handle_notification_confirm(controller, callback_data: str, chat_id: int, lang: str):
    """
    Подтверждение рассылки.
    
    Args:
        controller: Экземпляр BotController
        callback_data: Данные callback (notification_confirm_{type})
        chat_id: ID чата пользователя
        lang: Язык пользователя
    """
    if chat_id not in controller.admin_ids:
        await controller.send_and_track(chat_id, text="⛔ Доступ запрещён", track=False)
        return
    
    await controller.delete_current(chat_id, controller.last_moderation_message_id.get(chat_id))
    
    await controller.send_and_track(
        chat_id,
        text="📢 Рассылка сообщения всем пользователям...",
        track=False
    )
    
    user_ids = database.get_all_user_ids()
    
    if not user_ids:
        await controller.send_and_track(chat_id, text="❌ Нет пользователей для рассылки.", track=False)
        keyboard = get_admin_messages_menu_keyboard(lang)
        await controller.send_and_track(
            chat_id,
            text=get_text(lang, 'admin_messages_menu'),
            reply_markup=keyboard,
            track=False
        )
        return
    
    # Определение типа рассылки и текста
    if "restored" in callback_data:
        message_text = "Работа бота восстановлена, ждем вас снова"
    else:
        message_text = controller.pending_custom_message.get(chat_id)
        if not message_text:
            await controller.send_and_track(
                chat_id,
                text="❌ Не найден текст сообщения. Начните заново.",
                track=False
            )
            keyboard = get_admin_messages_menu_keyboard(lang)
            await controller.send_and_track(
                chat_id,
                text=get_text(lang, 'admin_messages_menu'),
                reply_markup=keyboard,
                track=False
            )
            return
    
    # Рассылка
    success_count = 0
    fail_count = 0
    
    for user_id in user_ids:
        try:
            await controller.bot.send_message(user_id, message_text)
            success_count += 1
            await asyncio.sleep(0.05)  # Задержка для соблюдения лимитов
        except Exception as e:
            logging.warning(f"Не удалось отправить сообщение пользователю {user_id}: {e}")
            fail_count += 1
    
    report = f"✅ Рассылка завершена.\nУспешно: {success_count}\nНе удалось: {fail_count}"
    await controller.send_and_track(chat_id, text=report, track=False)
    
    # Очистка и возврат в меню
    if "custom" in callback_data:
        controller.pending_custom_message.pop(chat_id, None)
    
    keyboard = get_admin_messages_menu_keyboard(lang)
    await controller.send_and_track(
        chat_id,
        text=get_text(lang, 'admin_messages_menu'),
        reply_markup=keyboard,
        track=False
    )


async def handle_notification_cancel(controller, chat_id: int, message_id: int, lang: str):
    """
    Отмена рассылки.
    
    Args:
        controller: Экземпляр BotController
        chat_id: ID чата пользователя
        message_id: ID сообщения для удаления
        lang: Язык пользователя
    """
    if chat_id not in controller.admin_ids:
        await controller.send_and_track(chat_id, text="⛔ Доступ запрещён", track=False)
        return
    
    await controller.delete_current(chat_id, message_id)
    
    keyboard = get_admin_messages_menu_keyboard(lang)
    await controller.send_and_track(
        chat_id,
        text=get_text(lang, 'admin_messages_menu'),
        reply_markup=keyboard,
        track=False
    )


async def handle_notification_callbacks(controller, callback_data: str, chat_id: int, message_id: int, lang: str):
    """
    Общий обработчик callback уведомлений.
    
    Args:
        controller: Экземпляр BotController
        callback_data: Данные callback
        chat_id: ID чата пользователя
        message_id: ID сообщения
        lang: Язык пользователя
    """
    if callback_data == "notification_restored":
        await handle_notification_restored(controller, chat_id, message_id, lang)
    elif callback_data == "notification_custom":
        await handle_notification_custom(controller, chat_id, message_id, lang)
    elif callback_data.startswith("notification_confirm_"):
        await handle_notification_confirm(controller, callback_data, chat_id, lang)
    elif callback_data == "notification_cancel":
        await handle_notification_cancel(controller, chat_id, message_id, lang)
