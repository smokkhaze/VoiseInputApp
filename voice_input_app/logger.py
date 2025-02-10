import logging
import os
from logging.handlers import RotatingFileHandler


def setup_logger() -> logging.Logger:
    """Настройка системы логирования"""
    logger = logging.getLogger('voice_input_app')
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Добавляем обработчики, если их ещё нет
    if not logger.handlers:
        log_file = os.path.expanduser('~/.voice_input_app.log')
        file_handler = RotatingFileHandler(
            log_file, maxBytes=5 * 1024 * 1024, backupCount=3
        )
        file_handler.setFormatter(formatter)
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger


logger = setup_logger()
