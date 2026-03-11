from config_reader import config
import database

import logging
import asyncio
from aiogram import Bot, Dispatcher, Router, types
from aiogram.filters.command import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, FSInputFile, BotCommand

logging.basicConfig(level=logging.INFO)

bot = Bot(token=config.bot_token.get_secret_value())
dp = Dispatcher()
router = Router()

ADMIN_IDS = [7413924512, 5186349076]  # ID администраторов

message_history = {}		  	# chat_id -> list of message_id (макс. 10)
last_image_path = {}		 	# chat_id -> путь к последней отправленной картинке
last_image_data = {}		  	# chat_id -> словарь с данными последней картинки (id, type, ...)
last_image_message_id = {}  	# chat_id -> message_id последней картинки
user_processing = {}  			# chat_id -> bool (True если обрабатывается)


async def set_bot_commands():
	commands = [
		BotCommand(command="start", description="Запустить бота / сменить тип"),
	]
	await bot.set_my_commands(commands)


async def send_and_track(chat_id: int, text: str = None, photo=None, reply_markup=None, track=True):
	history = message_history.get(chat_id, [])
	if track and len(history) >= 10:
		oldest_id = history.pop(0)
		try:
			await bot.delete_message(chat_id, oldest_id)
		except Exception as e:
			print(f"Не удалось удалить самое старое сообщение {oldest_id}: {e}")
	if photo:
		sent = await bot.send_photo(
			chat_id,
			photo=photo,
			caption=text,
			reply_markup=reply_markup,
			protect_content=True
		)
	else:
		sent = await bot.send_message(chat_id, text=text, reply_markup=reply_markup)
	if track:
		history.append(sent.message_id)
		message_history[chat_id] = history
	return sent


def remove_from_history(chat_id: int, message_id: int):
	if chat_id in message_history and message_id in message_history[chat_id]:
		message_history[chat_id].remove(message_id)


async def edit_message_to_save_button(chat_id: int, message_id: int, image_id: int):
	"""Редактирует существующее сообщение с картинкой: убирает старые кнопки и добавляет одну кнопку 'Сохранить' с ID."""
	keyboard = InlineKeyboardMarkup(inline_keyboard=[
		[InlineKeyboardButton(text="Сохранить 5🪙", callback_data=f"save_{image_id}")]
	])
	try:
		# Явно передаём business_connection_id=None, чтобы избежать ошибки валидации
		await bot.edit_message_reply_markup(
			chat_id=chat_id,
			message_id=message_id,
			reply_markup=keyboard,
			business_connection_id=None  # <-- добавляем эту строку
		)
		print(f"[OK] Сообщение {message_id} отредактировано, добавлена кнопка save_{image_id}")
	except Exception as e:
		print(f"[ОШИБКА] Не удалось отредактировать сообщение {message_id}: {type(e).__name__}: {e}")


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
	chat_id = message.chat.id
	# Удаляем последнюю отправленную картинку, если она есть
	if chat_id in last_image_message_id:
		try:
			await bot.delete_message(chat_id, last_image_message_id[chat_id])
			# Удаляем из истории, чтобы не накапливать
			remove_from_history(chat_id, last_image_message_id[chat_id])
		except Exception as e:
			print(f"Не удалось удалить последнюю картинку: {e}")
		finally:
			del last_image_message_id[chat_id]

	# Показываем меню выбора стиля
	await send_menu(chat_id)


@dp.callback_query()
async def process_callback(callback: types.CallbackQuery):
	chat_id = callback.message.chat.id
	message_id = callback.message.message_id

	# Защита от повторных нажатий
	if user_processing.get(chat_id):
		await callback.answer("Подождите, предыдущее действие ещё выполняется")
		return
	user_processing[chat_id] = True

	try:
		await callback.answer()

		async def delete_current():
			try:
				await bot.delete_message(chat_id, message_id)
				remove_from_history(chat_id, message_id)
				if chat_id in last_image_message_id and last_image_message_id[chat_id] == message_id:
					del last_image_message_id[chat_id]
			except Exception as e:
				print(f"Не удалось удалить сообщение {message_id}: {e}")

		if callback.data in ["anime", "real"]:
			await delete_current()

		if callback.data == "anime":
			database.user_set_type(chat_id, 0)
			await send_picture(chat_id)
		elif callback.data == "real":
			database.user_set_type(chat_id, 1)
			await send_picture(chat_id)

		elif callback.data == "menu":
			await delete_current()
			await send_menu(chat_id)

		elif callback.data == "dislike":
			user = database.get_user(chat_id)
			if user and user.get('last_watched'):
				image_id = user['last_watched']
				await edit_message_to_save_button(chat_id, message_id, image_id)
			else:
				await delete_current()
			database.dislike(chat_id)
			await send_picture(chat_id)

		elif callback.data == "like":
			user = database.get_user(chat_id)
			if user and user.get('last_watched'):
				image_id = user['last_watched']
				await edit_message_to_save_button(chat_id, message_id, image_id)
			else:
				await delete_current()
			database.like(chat_id)
			await send_picture(chat_id)

		elif callback.data.startswith("save_"):
			try:
				image_id = int(callback.data.split('_')[1])
			except (IndexError, ValueError):
				await callback.answer("Ошибка идентификатора")
				await delete_current()
				return

			await delete_current()
			success = database.save_and_like(chat_id, image_id)
			if success:
				await send_and_track(chat_id, text="✅ Изображение сохранено! 🪙-5", track=False)
			else:
				await send_and_track(chat_id, text="❌ Недостаточно монет", track=False)

		elif callback.data == "save":
			await delete_current()
			user = database.get_user(chat_id)
			if not user:
				await send_picture(chat_id)
				return
			image_id = user.get('last_watched')
			if image_id is None:
				await send_picture(chat_id)
				return
			success = database.save_and_like(chat_id, image_id)
			if success:
				await send_and_track(chat_id, text="✅ Изображение сохранено! 🪙-5", track=False)
			else:
				await send_and_track(chat_id, text="❌ Недочитаточно монет", track=False)
			await send_picture(chat_id)

		elif callback.data == "report":
			await delete_current()
			keyboard = InlineKeyboardMarkup(inline_keyboard=[
				[InlineKeyboardButton(text="У изображения не тот тип", callback_data="report_wrong_type")],
				[InlineKeyboardButton(text="Контент неприемлем", callback_data="report_inappropriate")],
				[InlineKeyboardButton(text="Отмена", callback_data="report_cancel")]
			])
			await send_and_track(chat_id, text="Выберите причину жалобы:", reply_markup=keyboard)

		elif callback.data == "report_wrong_type":
			await delete_current()
			database.toggle_type(chat_id)
			await send_picture(chat_id)

		elif callback.data == "report_inappropriate":
			await delete_current()
			user = database.get_user(chat_id)
			if user and user.get('last_watched'):
				database.set_need_moderate(user['last_watched'])
			await send_picture(chat_id)

		elif callback.data == "report_cancel":
			await delete_current()
			await send_picture(chat_id)

	finally:
		# Снимаем блокировку после завершения обработки
		user_processing.pop(chat_id, None)


async def send_menu(chat_id: int):
	keyboard = InlineKeyboardMarkup(inline_keyboard=[
		[InlineKeyboardButton(text="Anime", callback_data="anime"),
		 InlineKeyboardButton(text="Real", callback_data="real")]
	])
	await send_and_track(chat_id, text="Выбери стиль картинок", reply_markup=keyboard)


async def send_picture(chat_id: int):
	result = database.get_image(chat_id)
	if result is None or result[0] is None:
		await send_and_track(chat_id, text="Нет доступных изображений")
		return
	image_path, image_data = result
	last_image_path[chat_id] = image_path
	last_image_data[chat_id] = image_data

	user = database.get_user(chat_id)
	coins = user.get('coins', 0) if user else 0

	current_type = "Аниме" if image_data['type'] == 0 else "Фото"
	caption_text = f"{current_type} | {coins}🪙"

	buttons = [
		InlineKeyboardButton(text="😐", callback_data="dislike"),
		InlineKeyboardButton(text="Menu", callback_data="menu"),
		InlineKeyboardButton(text="❤️", callback_data="like"),
		InlineKeyboardButton(text="Сохранить 5🪙", callback_data="save"),
		InlineKeyboardButton(text="⚠️ Ошибка/Жалоба", callback_data="report")
	]
	keyboard_rows = [buttons[:3], buttons[3:]]
	keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_rows)

	image = FSInputFile(image_path)
	sent = await send_and_track(chat_id, photo=image, text=caption_text, reply_markup=keyboard)
	# Запоминаем message_id последней отправленной картинки
	last_image_message_id[chat_id] = sent.message_id


async def main():
	await set_bot_commands()
	dp.include_router(router)
	await dp.start_polling(bot)


if __name__ == "__main__":
	asyncio.run(main())