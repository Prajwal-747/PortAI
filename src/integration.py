import sys
import os

# Add parent directories to path to allow clean cross-folder imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(current_dir, "..")))

import keyboard
from PyQt6.QtCore import QObject, QThread, pyqtSignal, pyqtSlot, QTimer, Qt
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
    result_signal = pyqtSignal(str, str) # answer, type

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
    hotkey_triggered = pyqtSignal()

    def __init__(self):
        super().__init__()

        self.app = QApplication.instance()

        self.hotkey_triggered.connect(self.trigger_assistant)

        self.app = QApplication(sys.argv)
        
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
        # Bind Ctrl + Alt to trigger voice recording
        keyboard.hook(self.global_key_event)

    def global_key_event(self, event):
        if event.event_type == keyboard.KEY_DOWN:
            if keyboard.is_pressed("ctrl") and keyboard.is_pressed("alt"):
                if not self.worker or not self.worker.isRunning():
                    self.hotkey_triggered.emit()

    def trigger_assistant(self):
        self.pill.current_state = "RECORDING"
        self.pill.update()
        self.pill.set_status_text("Listening (Ctrl+Alt)...")
        self.overlay.start_glow()

        self.worker = AssistantWorker(self.whisper_model)
        self.worker.status_signal.connect(self.update_status)
        self.worker.result_signal.connect(self.handle_result)
        self.worker.start()

    def update_status(self, text):
        self.pill.set_status_text(text)
        if "Thinking" in text:
            self.pill.current_state = "PROCESSING"

    def handle_result(self, prompt, answer):
        print(f"\n[User]: {prompt}\n[AI]: {answer}\n")
        self.overlay.stop_glow()
        self.pill.current_state = "IDLE"
        self.pill.set_status_text("Ready")

    def run(self):
        sys.exit(self.app.exec())

if __name__ == "__main__":
    app = QApplication(sys.argv)
    controller = PortAIController()
    controller.run()