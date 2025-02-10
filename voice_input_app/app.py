from voice_input_app.logger import logger
from voice_input_app.config import ConfigManager
from voice_input_app.audio_processing import AudioProcessor
from voice_input_app.system_integration import TrayVisualizer


class AppState:
    def __init__(self):
        self.is_recording = False
        self.last_inserted_text = ""


class VoiceRecognitionApp:
    def __init__(self):
        self.state = AppState()
        self._initialize_components()

    def _initialize_components(self):
        try:
            self.config = ConfigManager()
            self.audio_processor = AudioProcessor(self.config.model, self.config.config)
            # Передаём ссылку на приложение в TrayVisualizer
            self.system_integration = TrayVisualizer(self)
            logger.info("Компоненты инициализированы")
        except Exception as e:
            logger.critical(f"Ошибка инициализации: {e}", exc_info=True)
            raise

    def toggle_recording(self):
        if self.state.is_recording:
            self._stop_recording()
        else:
            self._start_recording()

    def _start_recording(self):
        if self.state.is_recording:
            logger.warning("Запись уже запущена")
            return
        try:
            self.audio_processor.start_stream()
            self.state.is_recording = True
            self.system_integration.update_tray_icon()
            logger.info("Запись начата")
        except Exception as e:
            logger.error(f"Ошибка запуска записи: {e}", exc_info=True)

    def _stop_recording(self):
        if not self.state.is_recording:
            logger.warning("Запись не запущена")
            return
        try:
            self.audio_processor.stop_stream()
            self._process_audio_data()
            self.state.is_recording = False
            self.system_integration.update_tray_icon()
            logger.info("Запись остановлена")
        except Exception as e:
            logger.error(f"Ошибка остановки записи: {e}", exc_info=True)

    def _process_audio_data(self):
        try:
            text = self.audio_processor.process_audio()
            if text:
                self._insert_text(text)
        except Exception as e:
            logger.error(f"Ошибка обработки аудио: {e}", exc_info=True)

    def _format_text(self, text):
        # Удаляем лишние пробелы
        text = text.strip()
        if not text:
            return ""
        if self.state.last_inserted_text:
            # Если предыдущий текст не заканчивается пробелом — добавляем пробел
            if not self.state.last_inserted_text.endswith(" "):
                formatted_text = f" {text}"
            else:
                formatted_text = text
        else:
            formatted_text = text
        self.state.last_inserted_text = formatted_text.rstrip(" ")
        return formatted_text

    def _insert_text(self, text):
        try:
            formatted_text = self._format_text(text)
            if formatted_text and hasattr(self.system_integration, 'keyboard_controller'):
                self.system_integration.keyboard_controller.type(formatted_text)
                logger.info(f"Вставлен текст: {formatted_text[:50]}...")
            else:
                logger.warning("Нет контроллера клавиатуры для вставки текста")
        except Exception as e:
            logger.error(f"Ошибка вставки текста: {e}", exc_info=True)

    def run(self):
        try:
            # Запуск системной иконки, которая содержит логику отображения и горячих клавиш
            self.system_integration.run_tray()
            logger.info("Приложение запущено")
        except Exception as e:
            logger.error(f"Ошибка запуска: {e}", exc_info=True)
            self.shutdown()

    def shutdown(self):
        try:
            if self.state.is_recording:
                self._stop_recording()
        except Exception as e:
            logger.error(f"Ошибка остановки записи при завершении: {e}", exc_info=True)
        finally:
            try:
                self.audio_processor.cleanup()
            except Exception as e:
                logger.error(f"Ошибка очистки аудио процессора: {e}", exc_info=True)
            try:
                self.system_integration.shutdown()
            except Exception as e:
                logger.error(f"Ошибка завершения системной интеграции: {e}", exc_info=True)
            logger.info("Приложение завершено")


def main():
    try:
        app = VoiceRecognitionApp()
        app.run()
    except Exception as e:
        logger.critical(f"Критическая ошибка: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
