import pyaudio
import json
from vosk import KaldiRecognizer
from typing import Optional
from voice_input_app.logger import logger


class AudioProcessor:
    """Обработка аудио и распознавание речи"""

    def __init__(self, model, config):
        self.model = model
        self.config = config
        self.audio_interface = pyaudio.PyAudio()
        self.audio_stream: Optional[pyaudio.Stream] = None
        self.recognizer = KaldiRecognizer(model, config.get('audio_rate', 16000))

    def start_stream(self):
        if self.audio_stream is not None:
            logger.warning("Аудиопоток уже запущен")
            return
        try:
            self.audio_stream = self.audio_interface.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.config.get('audio_rate', 16000),
                input=True,
                frames_per_buffer=4096,
                stream_callback=self._audio_callback
            )
            self.audio_stream.start_stream()
            logger.info("Аудиопоток успешно запущен")
        except OSError as e:
            logger.exception("Ошибка доступа к микрофону")
            raise
        except Exception as e:
            logger.exception("Ошибка инициализации аудиопотока")
            raise

    def _audio_callback(self, in_data, frame_count, time_info, status):
        try:
            self.recognizer.AcceptWaveform(in_data)
        except Exception as e:
            logger.error(f"Ошибка обработки аудио в колбэке: {e}", exc_info=True)
        return (in_data, pyaudio.paContinue)

    def stop_stream(self):
        if self.audio_stream:
            try:
                self.audio_stream.stop_stream()
                self.audio_stream.close()
                logger.info("Аудиопоток успешно остановлен")
            except Exception as e:
                logger.error(f"Ошибка остановки аудиопотока: {e}", exc_info=True)
            finally:
                self.audio_stream = None
        else:
            logger.warning("Аудиопоток не был запущен")

    def process_audio(self) -> Optional[str]:
        try:
            result = self.recognizer.FinalResult()
            parsed = json.loads(result)
            text = parsed.get('text', '').strip()
            return text if text else None
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка декодирования JSON результата: {e}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"Ошибка обработки аудио: {e}", exc_info=True)
            return None

    def cleanup(self):
        try:
            self.audio_interface.terminate()
            logger.info("Аудиоинтерфейс успешно завершён")
        except Exception as e:
            logger.error(f"Ошибка завершения аудио интерфейса: {e}", exc_info=True)
