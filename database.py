# database.py
import psycopg2
from psycopg2 import pool
from config_reader import config
import os
import time  # <-- добавлен импорт

# Базовая директория проекта (там, где лежит database.py)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGE_DIR_ANIME = os.path.join(BASE_DIR, 'images', 'anime')
IMAGE_DIR_REAL = os.path.join(BASE_DIR, 'images', 'real')

# Создаём пул соединений (это эффективнее, чем открывать/закрывать соединение на каждый запрос)
try:
	connection_pool = psycopg2.pool.SimpleConnectionPool(
		1,  # минимальное количество соединений в пуле
		10, # максимальное
		database=config.db_name,
		user=config.db_user,
		password=config.db_password.get_secret_value(),
		host=config.db_host,
		port=config.db_port
	)
	if connection_pool:
		print("Connection pool created successfully")
except Exception as e:
	print(f"Error creating connection pool: {e}")
	connection_pool = None

def get_connection():
	"""Получить соединение из пула"""
	if connection_pool:
		return connection_pool.getconn()
	return None

def return_connection(conn):
	"""Вернуть соединение обратно в пул"""
	if connection_pool and conn:
		connection_pool.putconn(conn)

def close_all_connections():
	"""Закрыть все соединения (при остановке бота)"""
	if connection_pool:
		connection_pool.closeall()




def add_post_record(pic_type, date):
	start = time.perf_counter()
	conn = get_connection()
	if not conn:
		return False
	try:
		with conn.cursor() as cur:
			cur.execute("""
				INSERT INTO posts (type, date)
				VALUES (%s, %s)
				RETURNING id
			""", (pic_type, date))
			post_id = cur.fetchone()[0]
			conn.commit()
			elapsed = time.perf_counter() - start
			print(f"[TIMING] add_post_record: {elapsed:.3f}s")
			return post_id
	except Exception as e:
		print(f"Error adding post record {date}: {e}")
		conn.rollback()
		return False
	finally:
		return_connection(conn)

def add_picture_record(pic_type, post_id, filename):
	start = time.perf_counter()
	conn = get_connection()
	if not conn:
		return False
	try:
		with conn.cursor() as cur:
			cur.execute("""
				INSERT INTO pictures (type, post_id, path)
				VALUES (%s, %s, %s)
			""", (pic_type, post_id, filename))
			conn.commit()
			elapsed = time.perf_counter() - start
			print(f"[TIMING] add_picture_record: {elapsed:.3f}s")
		return True
	except Exception as e:
		print(f"Error adding picture record {filename}: {e}")
		conn.rollback()
		return False
	finally:
		return_connection(conn)

def get_user(user_id):
	start = time.perf_counter()
	conn = get_connection()
	if not conn:
		return None
	try:
		with conn.cursor() as cur:
			cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
			row = cur.fetchone()
			if row:
				columns = [desc[0] for desc in cur.description]
				elapsed = time.perf_counter() - start
				print(f"[TIMING] get_user (existing): {elapsed:.3f}s")
				return dict(zip(columns, row))

			cur.execute("INSERT INTO users (id) VALUES (%s) ON CONFLICT (id) DO NOTHING", (user_id,))
			conn.commit()
			cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
			row = cur.fetchone()
			if row:
				columns = [desc[0] for desc in cur.description]
				elapsed = time.perf_counter() - start
				print(f"[TIMING] get_user (new): {elapsed:.3f}s")
				return dict(zip(columns, row))
			else:
				elapsed = time.perf_counter() - start
				print(f"[TIMING] get_user (failed): {elapsed:.3f}s")
				return None
	except Exception as e:
		print(f"Error getting user {user_id}: {e}")
		conn.rollback()
		return None
	finally:
		return_connection(conn)

def user_set_type(user_id, type):
	start = time.perf_counter()
	conn = get_connection()
	if not conn:
		return False
	try:
		with conn.cursor() as cur:
			cur.execute("""
				UPDATE users
				SET type = %s
				WHERE id = %s
			""", (type, user_id))
			conn.commit()
			elapsed = time.perf_counter() - start
			print(f"[TIMING] user_set_type: {elapsed:.3f}s")
		return True
	except Exception as e:
		print(f"Error set type for user: {user_id}: {e}")
		conn.rollback()
		return False
	finally:
		return_connection(conn)

def user_set_cycle(user_id, cycle):
	start = time.perf_counter()
	if cycle == 0:
		new_cycle = 1
	else:
		new_cycle = 0
	conn = get_connection()
	if not conn:
		return False
	try:
		with conn.cursor() as cur:
			cur.execute("""
				UPDATE users
				SET cycle = %s
				WHERE id = %s
			""", (new_cycle, user_id))
			conn.commit()
			elapsed = time.perf_counter() - start
			print(f"[TIMING] user_set_cycle: {elapsed:.3f}s")
		return True
	except Exception as e:
		print(f"Error set type for user: {user_id}: {e}")
		conn.rollback()
		return False
	finally:
		return_connection(conn)

def user_watched_image(user_id, image):
	start = time.perf_counter()
	if image['type'] == 0:
		viewed_name = 'viewed_anime'
	else:
		viewed_name = 'viewed_real'
	conn = get_connection()
	if not conn:
		return False
	try:
		with conn.cursor() as cur:
			query = f"""
				UPDATE users
				SET {viewed_name} = array_append(coalesce({viewed_name}, ARRAY[]::integer[]), %s),
					last_watched = %s
				WHERE id = %s
			"""
			cur.execute(query, (image['id'], image['id'], user_id))
			conn.commit()
			elapsed = time.perf_counter() - start
			print(f"[TIMING] user_watched_image: {elapsed:.3f}s")
		return True
	except Exception as e:
		print(f"Error updating watched for user {user_id}: {e}")
		conn.rollback()
		return False
	finally:
		return_connection(conn)

def get_good_images(type):
	start = time.perf_counter()
	conn = get_connection()
	if not conn:
		return []
	try:
		with conn.cursor() as cur:
			cur.execute(f"SELECT * FROM pictures WHERE type = {type} ORDER BY value DESC OFFSET 100")
			columns = [desc[0] for desc in cur.description]
			rows = cur.fetchall()
			result = [dict(zip(columns, row)) for row in rows]
			elapsed = time.perf_counter() - start
			print(f"[TIMING] get_good_images: {elapsed:.3f}s (rows={len(result)})")
			return result
	except Exception as e:
		print(f"Error getting all images: {e}")
		return []
	finally:
		return_connection(conn)

def get_noname_images(type):
	start = time.perf_counter()
	conn = get_connection()
	if not conn:
		return []
	try:
		with conn.cursor() as cur:
			cur.execute(f"SELECT * FROM pictures WHERE value > -10 and type = {type} ORDER BY total ASC")
			columns = [desc[0] for desc in cur.description]
			rows = cur.fetchall()
			result = [dict(zip(columns, row)) for row in rows]
			elapsed = time.perf_counter() - start
			print(f"[TIMING] get_noname_images: {elapsed:.3f}s (rows={len(result)})")
			return result
	except Exception as e:
		print(f"Error getting all images: {e}")
		return []
	finally:
		return_connection(conn)

def toggle_type(user_id):
	start = time.perf_counter()
	user = get_user(user_id)
	if not user:
		return "Пользователь не найден"
	image_id = user.get('last_watched')
	if not image_id:
		return "Нет текущего изображения"
	conn = get_connection()
	if not conn:
		return "Ошибка подключения"
	try:
		with conn.cursor() as cur:
			cur.execute("UPDATE pictures SET type = 1 - type WHERE id = %s", (image_id,))
			conn.commit()
			if cur.rowcount == 0:
				elapsed = time.perf_counter() - start
				print(f"[TIMING] toggle_type (not found): {elapsed:.3f}s")
				return "Изображение не найдено"
			elapsed = time.perf_counter() - start
			print(f"[TIMING] toggle_type: {elapsed:.3f}s")
			return "Тип успешно изменён"
	except Exception as e:
		print(f"Error toggling type: {e}")
		conn.rollback()
		return "Ошибка при изменении типа"
	finally:
		return_connection(conn)


def set_need_moderate(image_id):
	"""Устанавливает need_moderate = true для указанного изображения."""
	conn = get_connection()
	if not conn:
		return False
	try:
		with conn.cursor() as cur:
			cur.execute("UPDATE pictures SET need_moderate = TRUE WHERE id = %s", (image_id,))
			conn.commit()
		return True
	except Exception as e:
		print(f"Error setting need_moderate for image {image_id}: {e}")
		conn.rollback()
		return False
	finally:
		return_connection(conn)


def add_saved_image(user_id, image_id):
	"""
	Добавляет image_id в массив saved_images пользователя и списывает 5 монет.
	Возвращает True при успехе, False если недостаточно монет или ошибка.
	"""
	conn = get_connection()
	if not conn:
		return False
	try:
		with conn.cursor() as cur:
			cur.execute("""
				UPDATE users
				SET saved_images = array_append(coalesce(saved_images, ARRAY[]::integer[]), %s),
					coins = coins - 5
				WHERE id = %s AND coins >= 5
				RETURNING coins
			""", (image_id, user_id))
			if cur.rowcount == 0:
				return False
			conn.commit()
			return True
	except Exception as e:
		print(f"Error adding saved image: {e}")
		conn.rollback()
		return False
	finally:
		return_connection(conn)


def save_and_like(user_id, image_id):
	"""Сохраняет изображение: добавляет в saved_images, списывает монеты, добавляет в просмотренные, ставит двойной лайк."""
	conn = get_connection()
	if not conn:
		return False
	try:
		with conn.cursor() as cur:
			# Определяем тип изображения
			cur.execute("SELECT type FROM pictures WHERE id = %s", (image_id,))
			pic = cur.fetchone()
			if not pic:
				return False
			pic_type = pic[0]
			viewed_field = 'viewed_anime' if pic_type == 0 else 'viewed_real'

			cur.execute(f"""
				UPDATE users
				SET saved_images = array_append(coalesce(saved_images, ARRAY[]::integer[]), %s),
					coins = coins - 5,
					{viewed_field} = CASE
						WHEN NOT (%s = ANY(coalesce({viewed_field}, ARRAY[]::integer[])))
						THEN array_append(coalesce({viewed_field}, ARRAY[]::integer[]), %s)
						ELSE {viewed_field}
					END
				WHERE id = %s AND coins >= 5
				RETURNING coins
			""", (image_id, image_id, image_id, user_id))
			if cur.rowcount == 0:
				return False

			cur.execute("""
				UPDATE pictures
				SET likes = likes + 2,
					total = total + 1,
					value = value + 2
				WHERE id = %s
			""", (image_id,))
			conn.commit()
			return True
	except Exception as e:
		print(f"Error in save_and_like: {e}")
		conn.rollback()
		return False
	finally:
		return_connection(conn)


def like(user_id):
	start = time.perf_counter()
	user = get_user(user_id)
	if not user:
		return False
	image_id = user.get('last_watched')
	if image_id is None:
		return False

	viewed_field = 'viewed_anime' if user['type'] == 0 else 'viewed_real'
	liked_field = 'liked_anime' if user['type'] == 0 else 'liked_real'

	conn = get_connection()
	if not conn:
		return False
	try:
		with conn.cursor() as cur:
			cur.execute(f"""
				UPDATE users
				SET {viewed_field} = array_append(coalesce({viewed_field}, ARRAY[]::integer[]), %s)
				WHERE id = %s
			""", (image_id, user_id))
			cur.execute(f"""
				UPDATE users
				SET {liked_field} = array_append(coalesce({liked_field}, ARRAY[]::integer[]), %s)
				WHERE id = %s
			""", (image_id, user_id))
			cur.execute("""
				UPDATE pictures
				SET likes = likes + 1, total = total + 1, value = value + 1
				WHERE id = %s
			""", (image_id,))
			if cur.rowcount == 0:
				conn.rollback()
				return False
			# Начисляем монету
			cur.execute("UPDATE users SET coins = coins + 1 WHERE id = %s", (user_id,))
			cur.execute("UPDATE users SET last_watched = NULL WHERE id = %s", (user_id,))
			conn.commit()
			elapsed = time.perf_counter() - start
			print(f"[TIMING] like: {elapsed:.3f}s")
		return True
	except Exception as e:
		print(f"Error liking: {e}")
		conn.rollback()
		return False
	finally:
		return_connection(conn)


def dislike(user_id):
	start = time.perf_counter()
	user = get_user(user_id)
	if not user:
		return False
	image_id = user.get('last_watched')
	if image_id is None:
		return False

	viewed_field = 'viewed_anime' if user['type'] == 0 else 'viewed_real'

	conn = get_connection()
	if not conn:
		return False
	try:
		with conn.cursor() as cur:
			cur.execute(f"""
				UPDATE users
				SET {viewed_field} = array_append(coalesce({viewed_field}, ARRAY[]::integer[]), %s)
				WHERE id = %s
			""", (image_id, user_id))
			cur.execute("""
				UPDATE pictures
				SET dislikes = dislikes + 1, total = total + 1, value = value - 1
				WHERE id = %s
			""", (image_id,))
			if cur.rowcount == 0:
				conn.rollback()
				return False
			# Начисляем монету
			cur.execute("UPDATE users SET coins = coins + 1 WHERE id = %s", (user_id,))
			cur.execute("UPDATE users SET last_watched = NULL WHERE id = %s", (user_id,))
			conn.commit()
			elapsed = time.perf_counter() - start
			print(f"[TIMING] dislike: {elapsed:.3f}s")
		return True
	except Exception as e:
		print(f"Error disliking: {e}")
		conn.rollback()
		return False
	finally:
		return_connection(conn)


def get_image(user_id):
	start = time.perf_counter()
	user = get_user(user_id)
	if not user:
		elapsed = time.perf_counter() - start
		print(f"[TIMING] get_image (no user): {elapsed:.3f}s")
		return None, None

	if user['type'] == 0:
		exclude = set(user['viewed_anime'])
		base_path = IMAGE_DIR_ANIME
	else:
		exclude = set(user['viewed_real'])
		base_path = IMAGE_DIR_REAL

	if user['cycle'] == 0:
		database_images = get_good_images(user['type'])
	else:
		database_images = get_noname_images(user['type'])

	for img in database_images:
		if img['id'] not in exclude:
			full_path = os.path.join(base_path, img['path'])
			if os.path.isfile(full_path):
				# Обновляем last_watched
				conn = get_connection()
				if conn:
					try:
						with conn.cursor() as cur:
							cur.execute("UPDATE users SET last_watched = %s WHERE id = %s", (img['id'], user_id))
							conn.commit()
					except Exception as e:
						print(f"Error updating last_watched: {e}")
						conn.rollback()
					finally:
						return_connection(conn)
				user_set_cycle(user_id, user['cycle'])
				elapsed = time.perf_counter() - start
				print(f"[TIMING] get_image (found): {elapsed:.3f}s")
				return full_path, img

	elapsed = time.perf_counter() - start
	print(f"[TIMING] get_image (none): {elapsed:.3f}s")
	return None, None