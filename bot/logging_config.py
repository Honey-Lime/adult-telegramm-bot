"""
Конфигурация логирования для бота.
"""
import logging
import logging.handlers
import os
import sys
import json
import time
from typing import Optional, Dict, Any

# Уровень логирования по умолчанию
DEFAULT_LOG_LEVEL = "INFO"

# Формат логов
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
# Расширенный формат с именем функции и строкой
DETAILED_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(funcName)s - %(message)s"


class JsonFormatter(logging.Formatter):
    """
    Форматтер, который преобразует запись лога в JSON строку.
    """
    def format(self, record: logging.LogRecord) -> str:
        log_object: Dict[str, Any] = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", self.converter(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if hasattr(record, "chat_id"):
            log_object["chat_id"] = record.chat_id
        if hasattr(record, "user_id"):
            log_object["user_id"] = record.user_id
        if hasattr(record, "image_id"):
            log_object["image_id"] = record.image_id
        if record.exc_info:
            log_object["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_object, ensure_ascii=False)


def get_log_level() -> str:
    """Возвращает уровень логирования из переменной окружения LOG_LEVEL."""
    return os.getenv("LOG_LEVEL", DEFAULT_LOG_LEVEL).upper()

def setup_logging(
    log_file: str = "bot.log",
    max_bytes: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 5,
    use_json: bool = False,
    detailed: bool = False,
) -> None:
    """
    Настраивает глобальное логирование.

    :param log_file: путь к файлу логов
    :param max_bytes: максимальный размер файла перед ротацией
    :param backup_count: количество резервных копий
    :param use_json: использовать JSON формат
    :param detailed: использовать подробный формат с именем файла и строкой
    """
    level_name = get_log_level()
    level = getattr(logging, level_name, logging.INFO)

    # Очищаем все существующие обработчики корневого логгера
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Выбор форматера
    if use_json:
        formatter = JsonFormatter()
    else:
        formatter = logging.Formatter(
            DETAILED_FORMAT if detailed else LOG_FORMAT,
            datefmt="%Y-%m-%d %H:%M:%S"
        )

    # Обработчик для консоли
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)

    # Обработчик для файла с ротацией
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)

    # Добавляем обработчики
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    root_logger.setLevel(level)

    # Логируем факт настройки
    logging.info(f"Логирование настроено. Уровень: {level_name}, файл: {log_file}, JSON: {use_json}")

def get_logger(name: str) -> logging.Logger:
    """Возвращает логгер с указанным именем."""
    return logging.getLogger(name)