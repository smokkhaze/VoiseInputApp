from typing import Any, Optional
from .logger import logger


def validate_text(text: Any) -> bool:
    """Валидация текстовых данных"""
    if not isinstance(text, str):
        logger.warning(f"Неверный тип текста: {type(text)}")
        return False
    return len(text.strip()) > 0


def format_error_message(error: Exception) -> str:
    """Форматирование сообщений об ошибках"""
    return f"{type(error).__name__}: {str(error)}"


def safe_execute(func, *args, **kwargs) -> Optional[Any]:
    """Безопасное выполнение функций с обработкой исключений"""
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logger.error(format_error_message(e), exc_info=True)
        return None
