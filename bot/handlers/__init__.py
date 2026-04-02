"""
Обработчики команд и callback бота.
Каждый модуль отвечает за свою группу функций.
"""

from . import content_handlers
from . import video_handlers
from . import user_handlers
from . import report_handlers
from .admin import users_handler
from .admin import moderation_handler
from .admin import notifications_handler
from .admin import promo_handler

__all__ = [
    'content_handlers',
    'video_handlers',
    'user_handlers',
    'report_handlers',
    'users_handler',
    'moderation_handler',
    'notifications_handler',
    'promo_handler',
]
