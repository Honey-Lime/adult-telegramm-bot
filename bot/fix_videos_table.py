# fix_videos_table.py
"""
Скрипт для пересоздания таблицы videos с правильным SERIAL.
ВНИМАНИЕ: Все существующие данные в таблице videos будут удалены!
"""
import psycopg2
import logging
from config_reader import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def fix_videos_table():
    """Пересоздаёт таблицу videos с правильным SERIAL PRIMARY KEY."""
    
    conn = None
    try:
        conn = psycopg2.connect(
            database=config.db_name,
            user=config.db_user,
            password=config.db_password.get_secret_value(),
            host=config.db_host,
            port=config.db_port
        )
        conn.autocommit = False
        
        with conn.cursor() as cur:
            logger.info("Dropping existing videos table...")
            cur.execute("DROP TABLE IF EXISTS videos CASCADE;")
            
            logger.info("Creating videos table with SERIAL PRIMARY KEY...")
            cur.execute("""
                CREATE TABLE videos (
                    id SERIAL PRIMARY KEY,
                    post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
                    path TEXT NOT NULL,
                    likes INTEGER DEFAULT 0,
                    dislikes INTEGER DEFAULT 0,
                    total INTEGER DEFAULT 0,
                    value INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            logger.info("Creating index on videos(post_id)...")
            cur.execute("CREATE INDEX idx_videos_post_id ON videos(post_id);")
            
            conn.commit()
            logger.info("✓ Таблица videos успешно пересоздана!")
            return True
            
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"✗ Ошибка при пересоздании таблицы: {e}")
        return False
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    print("ВНИМАНИЕ: Все данные в таблице videos будут удалены!")
    response = input("Продолжить? (yes/no): ")
    if response.lower() == "yes":
        success = fix_videos_table()
        if success:
            print("\n✓ Готово! Таблица videos пересоздана.")
        else:
            print("\n✗ Ошибка при пересоздании таблицы.")
    else:
        print("Отменено.")
