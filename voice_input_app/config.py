import os
import json
from vosk import Model
from typing import Dict, Any
from voice_input_app.logger import logger


class ConfigManager:
    """Управление конфигурацией и загрузкой модели"""

    CONFIG_FILE = os.path.expanduser('~/.voice_input_config.json')

    def __init__(self):
        self.config = self._load_config()
        self.model = self._load_model()

    def _load_config(self) -> Dict[str, Any]:
        default_config = {
            'model_path': None,
            'hotkey': 'shift',  # По умолчанию Shift
            'audio_rate': 16000
        }
        try:
            if os.path.exists(self.CONFIG_FILE):
                with open(self.CONFIG_FILE, 'r') as f:
                    loaded_config = json.load(f)
                    return {**default_config, **loaded_config}
            else:
                return default_config
        except Exception as e:
            logger.error(f"Ошибка загрузки конфигурации: {e}", exc_info=True)
            self._save_config(default_config)
            return default_config

    def _load_model(self) -> Model:
        model_path = self.config.get('model_path')
        if not model_path or not self._validate_model_path(model_path):
            model_path = self._prompt_model_path()
        try:
            logger.info(f"Загрузка модели из: {model_path}")
            return Model(model_path)
        except Exception as e:
            logger.critical(f"Ошибка загрузки модели: {e}", exc_info=True)
            raise

    def _validate_model_path(self, path: str) -> bool:
        # Проверяем наличие файла конфигурации модели
        return os.path.exists(os.path.join(path, "conf", "mfcc.conf"))

    def _prompt_model_path(self) -> str:
        while True:
            path = input("Введите путь к модели Vosk: ").strip()
            if self._validate_model_path(path):
                self._save_config({'model_path': path})
                return path
            print("Неверный путь. Попробуйте снова.")

    def _save_config(self, updates: Dict[str, Any]):
        try:
            self.config.update(updates)
            os.makedirs(os.path.dirname(self.CONFIG_FILE), exist_ok=True)
            with open(self.CONFIG_FILE, 'w') as f:
                json.dump(self.config, f, indent=4)
            logger.info("Конфигурация успешно сохранена")
        except Exception as e:
            logger.error(f"Ошибка сохранения конфигурации: {e}", exc_info=True)
