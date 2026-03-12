#!/usr/bin/env python3
"""
Скрипт для проверки соответствия изображений в базе данных и файловой системе.
Запускается на сервере для диагностики проблемы "Нет доступных изображений".
"""
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

import database

def check_real_images():
    conn = database.get_connection()
    if not conn:
        print("Не удалось подключиться к базе данных")
        return
    cur = conn.cursor()
    try:
        cur.execute("SELECT COUNT(*) FROM pictures WHERE type = %s", (database.ImageType.REAL.value,))
        total = cur.fetchone()[0]
        print(f"Всего REAL изображений в БД: {total}")
        
        cur.execute("SELECT id, path FROM pictures WHERE type = %s LIMIT 20", (database.ImageType.REAL.value,))
        rows = cur.fetchall()
        print(f"Первые {len(rows)} записей:")
        missing = 0
        for img_id, path in rows:
            full_path = os.path.join(database.IMAGE_DIR_REAL, path)
            exists = os.path.isfile(full_path)
            status = "OK" if exists else "MISSING"
            if not exists:
                missing += 1
            print(f"  {img_id}: {path} -> {full_path} [{status}]")
        print(f"Из них отсутствует на диске: {missing}")
        
        # Проверим также количество изображений в директории
        if os.path.isdir(database.IMAGE_DIR_REAL):
            files = [f for f in os.listdir(database.IMAGE_DIR_REAL) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'))]
            print(f"Файлов в директории {database.IMAGE_DIR_REAL}: {len(files)}")
        else:
            print(f"Директория {database.IMAGE_DIR_REAL} не существует!")
            
    except Exception as e:
        print(f"Ошибка при проверке: {e}")
    finally:
        database.return_connection(conn)

if __name__ == "__main__":
    check_real_images()