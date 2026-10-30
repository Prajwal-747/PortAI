
import os

os.environ["QT_LOGGING_RULES"] = "qt.qpa.window=false"

from PyQt6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    QRect,
    Qt,
    QTimer,
)
from PyQt6.QtGui import (
    QColor,
    QIcon,
    QImage,
    QPainter,
    QPixmap,
    QPen,
    QBrush,
)
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QToolButton,
    QTextBrowser,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)


# ---------------------------------------------------------
# Shared styling
# ---------------------------------------------------------

BG_COLOR = "#1E1E2E"
SURFACE_COLOR = "#181825"
BORDER_COLOR = "#45475A"
TEXT_COLOR = "#CDD6F4"
MUTED_COLOR = "#A6ADC8"
ACCENT_COLOR = "#89B4FA"
SUCCESS_COLOR = "#A6E3A1"
PURPLE_COLOR = "#CBA6F7"

FONT_FAMILY = "'Segoe UI', sans-serif"


def get_primary_screen_geometry():
    """Return the available primary screen geometry."""
    screen = QApplication.primaryScreen()
    if screen is None:
        return QRect(0, 0, 1280, 800)
    return screen.availableGeometry()


# ---------------------------------------------------------
# Floating pill
# ---------------------------------------------------------

class GlassyPill(QWidget):
    """Floating translucent status pill for PortAI."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(320, 54)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 6, 16, 6)

        self.label = QLabel("PortAI Ready (Ctrl+Alt)", self)
        self.label.setStyleSheet(
            f"""
            color: {TEXT_COLOR};
            font-family: {FONT_FAMILY};
            font-size: 13px;
            font-weight: 600;
            background: transparent;
            """
        )
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setWordWrap(False)
        layout.addWidget(self.label)

        self.current_state = "IDLE"

    def set_status_text(self, text: str):
        self.label.setText(text)
        self.update()

    def set_state(self, state: str):
        """Set the visual state and repaint."""
        allowed_states = {"IDLE", "RECORDING", "PROCESSING", "SPEAKING"}
        self.current_state = state if state in allowed_states else "IDLE"
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect().adjusted(2, 2, -2, -2)
        painter.setBrush(QBrush(QColor(30, 30, 35, 220)))

        if self.current_state == "RECORDING":
            painter.setPen(QPen(QColor(0, 122, 255, 230), 2))
        elif self.current_state == "PROCESSING":
            painter.setPen(QPen(QColor(203, 166, 247, 230), 2))
        elif self.current_state == "SPEAKING":
            painter.setPen(QPen(QColor(166, 227, 161, 230), 2))
        else:
            painter.setPen(QPen(QColor(255, 255, 255, 65), 1))

        painter.drawRoundedRect(rect, 27, 27)
    


# ---------------------------------------------------------
# Screen glow overlay
# ---------------------------------------------------------

class GeminiOverlay(QWidget):
    """Animated screen-edge illumination effect."""

    def __init__(self):
        super().__init__()

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        self.alpha = 20
        self._glow_direction = 1

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_glow)

        screen = QApplication.primaryScreen()
        if screen is not None:
            self.setGeometry(screen.geometry())

    def start_glow(self):
        screen = QApplication.primaryScreen()
        if screen is not None:
            self.setGeometry(screen.geometry())

        self.alpha = 20
        self._glow_direction = 1
        self.show()
        self.raise_()
        self.timer.start(30)

    def stop_glow(self):
        self.timer.stop()
        self.alpha = 0
        self.hide()

    def update_glow(self):
        self.alpha += self._glow_direction * 4

        if self.alpha >= 120:
            self.alpha = 120
            self._glow_direction = -1
        elif self.alpha <= 20:
            self.alpha = 20
            self._glow_direction = 1

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        border_width = 8
        rect = self.rect().adjusted(
            border_width // 2,
            border_width // 2,
            -(border_width // 2),
            -(border_width // 2),
        )

        pen = QPen(QColor(137, 180, 250, self.alpha))
        pen.setWidth(border_width)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect, 18, 18)
