import sys
import os

os.environ["QT_LOGGING_RULES"] = "qt.qpa.window=false"

import keyboard
from PyQt6.QtCore import QObject, QThread, pyqtSignal, Qt
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtGui import QAction

from backend import (
    load_whisper_model,
    check_internet,
    record_audio_until_released,
    transcribe_audio,
    classify_query_type,
    generate_text_response,
    generate_vision_response,
    conversation_history
)
from ui import GlassyPill, GeminiOverlay, SideDrawer, create_tray_icon


class AssistantWorker(QThread):
    status_signal = pyqtSignal(str)
    result_signal = pyqtSignal(str, str, bytes) # prompt, answer, screenshot_bytes

    def __init__(self, whisper_model):
        super().__init__()
        self.whisper_model = whisper_model

    def run(self):
        if not check_internet():
            self.status_signal.emit("No internet connection")
            return

        self.status_signal.emit("Listening...")
        audio_chunks = record_audio_until_released()
        
        self.status_signal.emit("Transcribing...")
        prompt = transcribe_audio(self.whisper_model, audio_chunks)
        if not prompt:
            self.status_signal.emit("Ready (No speech detected)")
            return

        self.status_signal.emit("Routing query...")
        query_type = classify_query_type(prompt, conversation_history)

        if query_type == "CLEARCONTEXT":
            conversation_history.clear()
            self.status_signal.emit("Context Cleared")
            self.result_signal.emit(prompt, "Conversation context cleared.", b"")
            return

        self.status_signal.emit(f"Thinking ({query_type})...")
        if query_type == "VISION":
            answer, screenshot_bytes = generate_vision_response(prompt)
            self.result_signal.emit(prompt, answer, screenshot_bytes)
        else:
            answer = generate_text_response(prompt)
            self.result_signal.emit(prompt, answer, b"")

        self.status_signal.emit("Ready")


class PortAIController(QObject):
    hotkey_signal = pyqtSignal()

    def __init__(self):
        super().__init__()

        self.app = QApplication.instance()
        self.app.setQuitOnLastWindowClosed(False)
        self.hotkey_signal.connect(self.trigger_assistant)

        # Load UI Elements
        self.pill = GlassyPill()
        self.overlay = GeminiOverlay()
        self.drawer = SideDrawer()

        # Position pill centered at the top of the main screen
        screen_geo = self.app.primaryScreen().geometry()
        self.pill.move((screen_geo.width() - self.pill.width()) // 2, 15)
        self.pill.show()

        # System Tray Integration
        self.tray_icon = QSystemTrayIcon(create_tray_icon(), self.app)
        tray_menu = QMenu()

        toggle_drawer_action = QAction("Toggle Side Drawer", self.app)
        toggle_drawer_action.triggered.connect(
            lambda: self.drawer.slide_out()
            if self.drawer.x() < screen_geo.width()
            else self.drawer.slide_in("Manual Toggle", "PortAI is active.")
        )
        tray_menu.addAction(toggle_drawer_action)

        clear_context_action = QAction("Clear Context", self.app)
        clear_context_action.triggered.connect(lambda: conversation_history.clear())
        tray_menu.addAction(clear_context_action)

        tray_menu.addSeparator()

        exit_action = QAction("Exit PortAI", self.app)
        exit_action.triggered.connect(self.app.quit)
        tray_menu.addAction(exit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.setToolTip("PortAI Assistant (Ctrl + Alt)")
        self.tray_icon.show()

        # Load AI backend
        print("Loading Whisper Model...")
        self.whisper_model = load_whisper_model()
        print("Whisper model loaded successfully!")

        self.worker = None
        self.setup_hotkeys()

    def setup_hotkeys(self):
        keyboard.add_hotkey(
            "ctrl+alt",
            lambda: self.hotkey_signal.emit(),
            trigger_on_release=False,
        )

    def trigger_assistant(self):
        if self.worker and self.worker.isRunning():
            return # Don't trigger if busy

        self.pill.current_state = "RECORDING"
        self.pill.set_status_text("Listening (Ctrl+Alt)...")
        self.overlay.start_glow()

        self.worker = AssistantWorker(self.whisper_model)

        self.worker.status_signal.connect(
            self.update_status,
            Qt.ConnectionType.QueuedConnection,
        )
        self.worker.result_signal.connect(
            self.handle_result,
            Qt.ConnectionType.QueuedConnection,
        )

        self.worker.start()

    def update_status(self, text):
        print(f"[UI STATUS] {text}")
        self.pill.set_status_text(text)

        if "Listening" in text:
            self.pill.current_state = "RECORDING"
        elif any(word in text for word in ("Transcribing", "Routing", "Thinking")):
            self.pill.current_state = "PROCESSING"
        elif any(word in text for word in ("Ready", "Context Cleared", "No internet")):
            self.pill.current_state = "IDLE"
            self.overlay.stop_glow()

        self.pill.update()

    def handle_result(self, prompt, answer, screenshot_bytes):
        print(f"\n[User]: {prompt}\n[AI]: {answer}\n")

        self.overlay.stop_glow()
        self.pill.current_state = "IDLE"
        self.pill.set_status_text("Ready")
        self.pill.update()

        # Show the side drawer with response & optional screenshot preview
        self.drawer.slide_in(prompt, answer, screenshot_bytes)

    def run(self):
        sys.exit(self.app.exec())


if __name__ == "__main__":
    app = QApplication(sys.argv)
    controller = PortAIController()
    controller.run()