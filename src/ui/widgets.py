from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QPainter, QPen, QBrush
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout

class GlassyPill(QWidget):
    """Apple AI-style floating translucent pill widget."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
    Qt.WindowType.FramelessWindowHint
    | Qt.WindowType.WindowStaysOnTopHint
    | Qt.WindowType.Tool
)       
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(320, 50)
        
        # Layout & Label
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 5, 15, 5)
        self.label = QLabel("PortAI Ready (Ctrl+Alt)", self)
        self.label.setStyleSheet("color: white; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto; font-size: 13px; font-weight: 500;")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label)
        
        # # Drop Shadow for floating depth
        # shadow = QGraphicsDropShadowEffect(self)
        # shadow.setBlurRadius(20)
        # shadow.setColor(QColor(0, 0, 0, 120))
        # shadow.setOffset(0, 4)
        # self.setGraphicsEffect(shadow)
        
        self.current_state = "IDLE" # IDLE, RECORDING, PROCESSING, SPEAKING

    def set_status_text(self, text):
        self.label.setText(text)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Glassmorphism background pill
        path_rect = self.rect().adjusted(2, 2, -2, -2)
        painter.setBrush(QBrush(QColor(30, 30, 35, 180)))
        
        # Dynamic border glow based on state
        if self.current_state == "RECORDING":
            painter.setPen(QPen(QColor(0, 122, 255, 220), 2)) # Apple Blue
        elif self.current_state == "PROCESSING":
            painter.setPen(QPen(QColor(175, 82, 222, 220), 2)) # Purple glow
        else:
            painter.setPen(QPen(QColor(255, 255, 255, 50), 1))
            
        painter.drawRoundedRect(path_rect, 24, 24)


class GeminiOverlay(QWidget):
    """Fullscreen Gemini-style screen illumination border effect."""
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        
        # Cover entire primary screen
        screen = self.screen().geometry()
        self.setGeometry(screen)
        
        self.alpha = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_glow)
        self._glow_direction = 1

    def start_glow(self):
        self.show()
        self.alpha = 20
        self.timer.start(30)

    def stop_glow(self):
        self.timer.stop()
        self.alpha = 0
        self.hide()

    def update_glow(self):
        self.alpha += self._glow_direction * 4
        if self.alpha >= 120 or self.alpha <= 20:
            self._glow_direction *= -1
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw glowing multi-color gradient border around the screen edges
        border_width = 8
        rect = self.rect().adjusted(border_width//2, border_width//2, -border_width//2, -border_width//2)
        
        pen = QPen()
        pen.setWidth(border_width)
        pen.setColor(QColor(66, 133, 244, self.alpha)) # Gemini Blue-Violet Glow
        painter.setPen(pen)
        painter.drawRect(rect)