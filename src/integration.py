import sys
import os

# Add parent directories to path to allow clean cross-folder imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(current_dir, "..")))

import keyboard
from PyQt6.QtCore import QObject, QThread, pyqtSignal, pyqtSlot, Qt
from PyQt6.QtWidgets import QApplication

from backend.ai_core import (
    load_whisper_model,
    check_internet,
    record_audio_until_released,
    transcribe_audio,
    classify_query_type,
    generate_text_response,
    generate_vision_response,
    conversation_history
)
from ui.widgets import GlassyPill, GeminiOverlay

class AssistantWorker(QThread):
    status_signal = pyqtSignal(str)
    result_signal = pyqtSignal(str, str) # prompt, answer

    def __init__(self, whisper_model):
        super().__init__()
        self.whisper_model = whisper_model

    def run(self):
        if not check_internet():
            self.status_signal.emit("No internet connection")
            return

        self.status_signal.emit("Listening...")
        audio_chunks = record_audio_until_released(keyboard)
        
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
            return

        self.status_signal.emit(f"Thinking ({query_type})...")
        if query_type == "VISION":
            answer, _ = generate_vision_response(prompt)
        else:
            answer = generate_text_response(prompt)

        self.result_signal.emit(prompt, answer)
        self.status_signal.emit("Ready")


class PortAIController(QObject):
    hotkey_signal = pyqtSignal()

    def __init__(self):
        super().__init__()

        self.app = QApplication.instance()
        self.hotkey_signal.connect(self.trigger_assistant)

        # Load UI
        self.pill = GlassyPill()
        self.overlay = GeminiOverlay()
        
        # Position pill centered at the top of the main screen
        screen_geo = self.app.primaryScreen().geometry()
        self.pill.move((screen_geo.width() - self.pill.width()) // 2, 15)
        self.pill.show()

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
            return # Don't trigger if it's already busy

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

        elif any(word in text for word in (
            "Transcribing", "Routing", "Thinking"
        )):
            self.pill.current_state = "PROCESSING"

        elif any(word in text for word in (
            "Ready", "Context Cleared", "No internet"
        )):
            self.pill.current_state = "IDLE"
            self.overlay.stop_glow()

        self.pill.update()

    def handle_result(self, prompt, answer):
        print(f"\n[User]: {prompt}\n[AI]: {answer}\n")

        self.overlay.stop_glow()
        self.pill.current_state = "IDLE"
        self.pill.set_status_text("Ready")
        self.pill.update()

    def run(self):
        sys.exit(self.app.exec())

if __name__ == "__main__":
    app = QApplication(sys.argv)
    controller = PortAIController()
    controller.run()