"""
Миграция: добавление столбца language в таблицу users.
Запускается один раз для обновления существующей базы данных.
"""
import psycopg2
from config_reader import config
import logging

logging.basicConfig(level=logging.INFO)

def add_language_column():
    """Добавляет столбец language в таблицу users, если его нет."""
    try:
        conn = psycopg2.connect(
            database=config.db_name,
            user=config.db_user,
            password=config.db_password.get_secret_value(),
            host=config.db_host,
            port=config.db_port
        )
        cur = conn.cursor()
        
        # Проверяем, существует ли столбец language
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'users' AND column_name = 'language'
        """)
        
        if cur.fetchone():
            logging.info("Столбец language уже существует в таблице users")
        else:
            # Добавляем столбец language со значением по умолчанию 'ru'
            cur.execute("""
                ALTER TABLE users 
                ADD COLUMN language TEXT DEFAULT 'ru'
            """)
            conn.commit()
            logging.info("✓ Столбец language добавлен в таблицу users")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        logging.error(f"Ошибка при добавлении столбца language: {e}")
        raise

if __name__ == "__main__":
    logging.info("Запуск миграции: добавление столбца language...")
    add_language_column()
    logging.info("Миграция завершена успешно")
