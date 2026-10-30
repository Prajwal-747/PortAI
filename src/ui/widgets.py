
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

