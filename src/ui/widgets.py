
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


# ---------------------------------------------------------
# Response drawer
# ---------------------------------------------------------

class SideDrawer(QWidget):
    """Animated response drawer with Markdown rendering."""

    def __init__(self):
        super().__init__()

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        # Keep the animated drawer opaque. Layered/translucent top-level
        # windows can fail to repaint reliably on Windows after repeated
        # geometry animations, especially with display scaling enabled.
        self.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground,
            False,
        )
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(self.backgroundRole(), QColor(BG_COLOR))
        self.setPalette(palette)
        self.setStyleSheet(
            f"""
            SideDrawer {{
                background-color: {BG_COLOR};
                border: 1px solid {BORDER_COLOR};
                border-radius: 22px;
            }}
            """
        )

        self.drawer_width = 400
        self.drawer_height = 560
        self._hide_after_animation = False

        self.init_ui()
        self.reposition_hidden()

    def init_ui(self):
        self.container = QWidget(self)
        self.container.setObjectName("drawerContainer")
        self.container.setStyleSheet(
            f"""
            QWidget#drawerContainer {{
                background-color: {BG_COLOR};
                border: 1px solid {BORDER_COLOR};
                border-radius: 22px;
            }}
            QLabel#header {{
                color: {ACCENT_COLOR};
                font-family: {FONT_FAMILY};
                font-size: 16px;
                font-weight: 700;
                background: transparent;
                border: none;
            }}
            QLabel#prompt {{
                color: {SUCCESS_COLOR};
                font-family: {FONT_FAMILY};
                font-size: 13px;
                font-weight: 600;
                background: transparent;
                border: none;
            }}
            QLabel#screenshot {{
                background: {SURFACE_COLOR};
                border: 1px solid {BORDER_COLOR};
                border-radius: 12px;
                padding: 4px;
            }}
            QScrollArea {{
                background: transparent;
                border: none;
            }}
            """
        )

        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        # Header
        header_row = QHBoxLayout()
        header_row.setSpacing(8)

        icon_label = QLabel("✦", self.container)
        icon_label.setStyleSheet(
            f"""
            color: {ACCENT_COLOR};
            font-family: {FONT_FAMILY};
            font-size: 23px;
            background: transparent;
            border: none;
            """
        )

        header = QLabel("PortAI Assistant", self.container)
        header.setObjectName("header")

        header_row.addWidget(icon_label)
        header_row.addWidget(header)
        header_row.addStretch()

        self.close_button = QToolButton(self.container)
        self.close_button.setText("×")
        self.close_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_button.setFixedSize(30, 30)
        self.close_button.setStyleSheet(
            f"""
            QToolButton {{
                color: {MUTED_COLOR};
                background: transparent;
                border: none;
                border-radius: 15px;
                font-size: 22px;
            }}
            QToolButton:hover {{
                color: {TEXT_COLOR};
                background: {BORDER_COLOR};
            }}
            """
        )
        self.close_button.clicked.connect(self.slide_out)

        header_row.addWidget(self.close_button)
        layout.addLayout(header_row)

        # User prompt
        self.prompt_label = QLabel("", self.container)
        self.prompt_label.setObjectName("prompt")
        self.prompt_label.setWordWrap(True)
        layout.addWidget(self.prompt_label)

        # Optional screenshot
        self.image_label = QLabel(self.container)
        self.image_label.setObjectName("screenshot")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMaximumHeight(180)
        self.image_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Maximum,
        )
        self.image_label.hide()
        layout.addWidget(self.image_label)

        # Markdown-aware response area
        self.scroll_area = QScrollArea(self.container)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)

        self.content_label = QTextBrowser(self.scroll_area)
        self.content_label.setOpenExternalLinks(True)
        self.content_label.setReadOnly(True)
        self.content_label.setFrameShape(QTextBrowser.Shape.NoFrame)
        self.content_label.setStyleSheet(
            f"""
            QTextBrowser {{
                background: transparent;
                color: {TEXT_COLOR};
                border: none;
                padding: 4px;
                font-family: {FONT_FAMILY};
                font-size: 14px;
                selection-background-color: {BORDER_COLOR};
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 8px;
                margin: 2px;
            }}
            QScrollBar::handle:vertical {{
                background: {BORDER_COLOR};
                min-height: 28px;
                border-radius: 4px;
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{
                height: 0;
            }}
            """
        )
        self.content_label.setPlaceholderText("Your response will appear here.")
        self.scroll_area.setWidget(self.content_label)
        layout.addWidget(self.scroll_area, 1)

        # Avoid QGraphicsDropShadowEffect on this animated window.
        # It can force expensive repaints of layered windows on Windows.
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.container)

        self.anim = QPropertyAnimation(self, b"geometry", self)
        self.anim.setDuration(320)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim.finished.connect(self._on_animation_finished)

    def _screen_geometry(self):
        return get_primary_screen_geometry()

    def reposition_hidden(self):
        screen = self._screen_geometry()
        x = screen.x() + screen.width()
        y = screen.y() + (screen.height() - self.drawer_height) // 2
        self.setGeometry(x, y, self.drawer_width, self.drawer_height)

    def _on_animation_finished(self):
        if self._hide_after_animation:
            self.hide()
            self._hide_after_animation = False

    def slide_in(self, prompt, response, screenshot_bytes=b""):
        self.anim.stop()
        self._hide_after_animation = False

        screen = self._screen_geometry()

        self.prompt_label.setText(f"You asked: {prompt}")
        self.content_label.setMarkdown(response or "")

        if screenshot_bytes:
            image = QImage.fromData(screenshot_bytes)

            if not image.isNull():
                pixmap = QPixmap.fromImage(image).scaled(
                    350,
                    170,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self.image_label.setPixmap(pixmap)
                self.image_label.show()
            else:
                self.image_label.clear()
                self.image_label.hide()
        else:
            self.image_label.clear()
            self.image_label.hide()

        start_x = screen.x() + screen.width()
        end_x = start_x - self.drawer_width - 20
        y = screen.y() + (screen.height() - self.drawer_height) // 2

        # If already visible, animate from its current position.
        if self.isVisible():
            start_x = self.x()
        else:
            self.setGeometry(
                start_x,
                y,
                self.drawer_width,
                self.drawer_height,
            )

        self.show()
        self.raise_()

        self.anim.setStartValue(
            QRect(start_x, y, self.drawer_width, self.drawer_height)
        )
        self.anim.setEndValue(
            QRect(end_x, y, self.drawer_width, self.drawer_height)
        )
        self.anim.start()

    def slide_out(self):
        if not self.isVisible():
            return

        self.anim.stop()

        screen = self._screen_geometry()
        start_x = self.x()
        end_x = screen.x() + screen.width()
        y = self.y()

        self._hide_after_animation = True

        self.anim.setStartValue(
            QRect(start_x, y, self.drawer_width, self.drawer_height)
        )
        self.anim.setEndValue(
            QRect(end_x, y, self.drawer_width, self.drawer_height)
        )
        self.anim.start()


# ---------------------------------------------------------
# System tray icon
# ---------------------------------------------------------

def create_tray_icon():
    pixmap = QPixmap(32, 32)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(137, 180, 250))
    painter.drawEllipse(2, 2, 28, 28)

    painter.setBrush(QColor(30, 30, 46))
    painter.drawEllipse(11, 11, 10, 10)
    painter.end()

    return QIcon(pixmap)
