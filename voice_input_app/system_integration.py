from PIL import Image, ImageDraw
import random
import time
import threading
import pystray
from pynput import keyboard
from voice_input_app.logger import logger
import math

# Константы цветов и базовые частоты для анимации
REST_COLOR = (200, 0, 0, 255)         # Ярко-красный
ACTIVE_COLOR = (0, 255, 180, 255)       # Неоновый бирюзовый
SELECT_COLOR = (255, 255, 255, 255)     # Белый для выбора горячей клавиши
BASE_FREQUENCIES = [0.8, 1.2, 1.5, 2.0, 2.3, 1.7, 1.1, 0.9]


def generate_visualizer_frame(size=128, transition=0.0, select_mode=False):
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    num_bars = 8
    bar_width = size // num_bars
    center = size // 2
    # Определение цвета
    if select_mode:
        current_color = SELECT_COLOR
    else:
        current_color = (
            int(REST_COLOR[0] * (1 - transition) + ACTIVE_COLOR[0] * transition),
            int(REST_COLOR[1] * (1 - transition) + ACTIVE_COLOR[1] * transition),
            int(REST_COLOR[2] * (1 - transition) + ACTIVE_COLOR[2] * transition),
            255
        )
    time_factor = time.time() * 3
    for i in range(num_bars):
        wave = abs(math.sin(time_factor * BASE_FREQUENCIES[i]))
        height = max(16, int((wave * 0.9 + 0.3) * center * transition))
        height += int(math.sin(time_factor * 0.5 + i) * 10)
        x1 = i * bar_width + 2
        x2 = (i + 1) * bar_width - 2
        y_base = center + int((1 - transition) * 40 * math.sin(time_factor + i))
        shadow_offset = int(8 * transition)
        y0_shadow = y_base - height // 2 + shadow_offset
        y1_shadow = y_base + height // 2 + shadow_offset
        if y1_shadow < y0_shadow:
            y0_shadow, y1_shadow = y1_shadow, y0_shadow
        draw.rectangle(
            [x1 + shadow_offset, y0_shadow, x2 + shadow_offset, y1_shadow],
            fill=(0, 0, 0, 80)
        )
        y0_main = y_base - height // 2
        y1_main = y_base + height // 2
        if y1_main < y0_main:
            y0_main, y1_main = y1_main, y0_main
        draw.rounded_rectangle(
            [x1, y0_main, x2, y1_main],
            radius=5,
            fill=current_color
        )
    return image


class TrayVisualizer:
    def __init__(self, app):
        self.app = app
        self.keyboard_controller = keyboard.Controller()
        self.tray_icon = None
        self.animation_thread = None
        self.running = True
        self.size = 128
        self.transition = 0.0
        self.select_mode = False  # Режим выбора горячей клавиши
        self._init_hotkeys()
        self._init_tray()
        self._start_animation()

    def _init_hotkeys(self):
        self.listener = keyboard.Listener(
            on_press=self._on_key_press,
            on_release=self._on_key_release,
            daemon=True
        )
        self.listener.start()

    def _get_hotkey(self):
        # Приводим горячую клавишу к нужному типу: если она содержится в keyboard.Key, то используем его
        hotkey_name = self.get_hotkey_name().lower()
        if hasattr(keyboard.Key, hotkey_name):
            return getattr(keyboard.Key, hotkey_name)
        return hotkey_name

    def _on_key_press(self, key):
        try:
            expected_hotkey = self._get_hotkey()
            if self._key_matches(key, expected_hotkey) and not self.app.state.is_recording:
                self.app.toggle_recording()
        except Exception as e:
            logger.error(f"Ошибка обработки нажатия клавиши: {e}", exc_info=True)

    def _on_key_release(self, key):
        try:
            expected_hotkey = self._get_hotkey()
            if self._key_matches(key, expected_hotkey) and self.app.state.is_recording:
                self.app.toggle_recording()
        except Exception as e:
            logger.error(f"Ошибка обработки отпускания клавиши: {e}", exc_info=True)

    def _key_matches(self, key, expected):
        try:
            if isinstance(expected, keyboard.Key):
                return key == expected
            elif hasattr(key, 'char') and key.char:
                return key.char.lower() == expected
            elif hasattr(key, 'name'):
                return key.name.lower() == expected
        except Exception:
            return False
        return False

    def _init_tray(self):
        menu = pystray.Menu(
            pystray.MenuItem(f"Hot key [{self.get_hotkey_name()}]", self._change_hotkey),
            pystray.MenuItem("Exit", lambda icon, item: self.app.shutdown())
        )
        initial_frame = generate_visualizer_frame(size=self.size, transition=0.0)
        self.tray_icon = pystray.Icon("voice_input", initial_frame, "Voice Input", menu)

    def get_hotkey_name(self):
        return self.app.config.config.get('hotkey', 'shift')

    def _change_hotkey(self, icon, item):
        try:
            if hasattr(self, "listener") and self.listener.is_alive():
                self.listener.stop()
            self.select_mode = True
            self.update_tray_icon()
            with keyboard.Listener(on_press=self._on_key_assign) as assign_listener:
                logger.info("Ожидание нажатия новой клавиши для горячей клавиши...")
                assign_listener.join()
            self.select_mode = False
            self.update_tray_icon()
            self._init_hotkeys()
        except Exception as e:
            logger.error(f"Ошибка при изменении горячей клавиши: {e}", exc_info=True)

    def _on_key_assign(self, key):
        try:
            new_hotkey = getattr(key, 'name', None) or str(key)
            new_hotkey = new_hotkey.lower()
            logger.info(f"Новая горячая клавиша назначена: {new_hotkey}")
            self.app.config.config['hotkey'] = new_hotkey
            self.app.config._save_config({'hotkey': new_hotkey})
            self.tray_icon.menu = pystray.Menu(
                pystray.MenuItem(f"Горячая клавиша [{self.get_hotkey_name()}]", self._change_hotkey),
                pystray.MenuItem("Выход", lambda icon, item: self.app.shutdown())
            )
            return False  # Останавливаем Listener после первого нажатия
        except Exception as e:
            logger.error(f"Ошибка при назначении клавиши: {e}", exc_info=True)
            return False

    def _animate(self):
        last_time = time.time()
        while self.running:
            current_time = time.time()
            delta = current_time - last_time
            last_time = current_time
            target = 1.0 if self.app.state.is_recording else 0.0
            self.transition += (target - self.transition) * delta * 0.8
            frame = generate_visualizer_frame(
                size=self.size,
                transition=self.transition,
                select_mode=self.select_mode
            )
            if self.tray_icon is not None:
                self.tray_icon.icon = frame
            time.sleep(0.03)

    def _start_animation(self):
        if self.tray_icon and (self.animation_thread is None or not self.animation_thread.is_alive()):
            self.animation_thread = threading.Thread(target=self._animate, daemon=True)
            self.animation_thread.start()

    def update_tray_icon(self):
        self._start_animation()

    def run_tray(self):
        if self.tray_icon:
            self.tray_icon.run()

    def shutdown(self):
        self.running = False
        if self.tray_icon:
            self.tray_icon.stop()
        if hasattr(self, "listener"):
            try:
                self.listener.stop()
            except Exception as e:
                logger.error(f"Ошибка остановки слушателя горячих клавиш: {e}", exc_info=True)
        if self.animation_thread and self.animation_thread.is_alive():
            self.animation_thread.join(timeout=1)
