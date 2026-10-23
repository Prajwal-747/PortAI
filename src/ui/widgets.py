import os
os.environ["QT_LOGGING_RULES"] = "qt.qpa.window=false"

from PyQt6.QtCore import (
    QEasingCurve, QPropertyAnimation, QRect, Qt, QTimer
)
from PyQt6.QtGui import (
    QAction, QColor, QFont, QIcon, QImage, QPainter,
    QPixmap, QPen, QBrush
)
from PyQt6.QtWidgets import (
    QApplication, QGraphicsDropShadowEffect,
    QHBoxLayout, QLabel, QMenu, QScrollArea,
    QSystemTrayIcon, QVBoxLayout, QWidget
)


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
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 5, 15, 5)
        self.label = QLabel("PortAI Ready (Ctrl+Alt)", self)
        self.label.setStyleSheet("color: white; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto; font-size: 13px; font-weight: 500;")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label)
        
        self.current_state = "IDLE" # IDLE, RECORDING, PROCESSING, SPEAKING

    def set_status_text(self, text):
        self.label.setText(text)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        path_rect = self.rect().adjusted(2, 2, -2, -2)
        painter.setBrush(QBrush(QColor(30, 30, 35, 180)))
        
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
        
        border_width = 8
        rect = self.rect().adjusted(border_width//2, border_width//2, -border_width//2, -border_width//2)
        
        pen = QPen()
        pen.setWidth(border_width)
        pen.setColor(QColor(66, 133, 244, self.alpha))
        painter.setPen(pen)
        painter.drawRect(rect)


class SideDrawer(QWidget):
    """Side drawer sliding in from screen right to display AI responses & screenshots."""

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.drawer_width = 380
        self.drawer_height = 500

        self.init_ui()
        self.reposition_hidden()

    def init_ui(self):
        self.container = QWidget(self)
        self.container.setStyleSheet("""
            QWidget {
                background-color: #1E1E2E;
                border: 1px solid #313244;
                border-radius: 16px;
            }
            QLabel#header {
                color: #89B4FA;
                font-family: 'Segoe UI', sans-serif;
                font-size: 15px;
                font-weight: bold;
            }
            QLabel#prompt {
                color: #A6E3A1;
                font-size: 13px;
                font-weight: 600;
            }
        """)

        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(16, 16, 16, 16)

        header = QLabel("PortAI Assistant", self)
        header.setObjectName("header")
        layout.addWidget(header)

        self.prompt_label = QLabel("", self)
        self.prompt_label.setObjectName("prompt")
        self.prompt_label.setWordWrap(True)
        layout.addWidget(self.prompt_label)

        self.image_label = QLabel(self)
        self.image_label.hide()
        layout.addWidget(self.image_label)

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("border: none; background: transparent;")

        self.content_label = QLabel("", self)
        self.content_label.setWordWrap(True)
        self.content_label.setStyleSheet("color: #CDD6F4; font-size: 13px;")
        self.scroll_area.setWidget(self.content_label)

        layout.addWidget(self.scroll_area)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(25)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setXOffset(-4)
        shadow.setYOffset(4)
        self.container.setGraphicsEffect(shadow)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.container)

        self.anim = QPropertyAnimation(self, b"geometry")
        self.anim.setDuration(350)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def reposition_hidden(self):
        screen = QApplication.primaryScreen().geometry()
        x = screen.width()
        y = (screen.height() - self.drawer_height) // 2
        self.setGeometry(x, y, self.drawer_width, self.drawer_height)

    def slide_in(self, prompt, response, screenshot_bytes=b""):
        screen = QApplication.primaryScreen().geometry()

        self.prompt_label.setText(f"You: {prompt}")
        self.content_label.setText(response)

        if screenshot_bytes:
            image = QImage.fromData(screenshot_bytes)
            pixmap = QPixmap.fromImage(image).scaledToWidth(
                340, Qt.TransformationMode.SmoothTransformation
            )
            self.image_label.setPixmap(pixmap)
            self.image_label.show()
        else:
            self.image_label.hide()

        start_x = screen.width()
        end_x = screen.width() - self.drawer_width - 20
        y = (screen.height() - self.drawer_height) // 2

        self.show()
        self.anim.setStartValue(QRect(start_x, y, self.drawer_width, self.drawer_height))
        self.anim.setEndValue(QRect(end_x, y, self.drawer_width, self.drawer_height))
        self.anim.start()

    def slide_out(self):
        screen = QApplication.primaryScreen().geometry()
        start_x = self.x()
        end_x = screen.width()
        y = self.y()

        self.anim.setStartValue(QRect(start_x, y, self.drawer_width, self.drawer_height))
        self.anim.setEndValue(QRect(end_x, y, self.drawer_width, self.drawer_height))
        self.anim.start()


def create_tray_icon():
    pixmap = QPixmap(32, 32)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setBrush(QColor("#89B4FA"))
    painter.drawEllipse(2, 2, 28, 28)
    painter.end()
    return QIcon(pixmap)