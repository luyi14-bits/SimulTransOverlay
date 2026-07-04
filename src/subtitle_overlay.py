"""Subtitle overlay window using PyQt6.

Creates a transparent, always-on-top, click-through overlay window
for displaying real-time translation subtitles.
"""

import logging
from typing import List, Optional, Dict, Any

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QPainter, QBrush, QPen, QAction, QIcon
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel,
    QSystemTrayIcon, QMenu, QHBoxLayout,
)

logger = logging.getLogger(__name__)

# Available color themes
# Each theme: {"bg": background color, "fg": text color, "opacity": window opacity}
THEMES: Dict[str, Dict[str, Any]] = {
    "dark":       {"bg": "#000000", "fg": "#FFFFFF", "opacity": 0.5},
    "light":      {"bg": "#FFFFFF", "fg": "#000000", "opacity": 0.4},
    "glass":      {"bg": "rgba(255, 255, 255, 0.15)", "fg": "#FFFFFF", "opacity": 0.3},
    "blue":       {"bg": "#1a1a2e", "fg": "#00d2ff", "opacity": 0.5},
    "green":      {"bg": "#0a1a0a", "fg": "#00ff88", "opacity": 0.5},
    "purple":     {"bg": "#1a0a2e", "fg": "#c084fc", "opacity": 0.5},
    "red":        {"bg": "#2e0a0a", "fg": "#ff4444", "opacity": 0.5},
    "orange":     {"bg": "#2e1a0a", "fg": "#ff8800", "opacity": 0.5},
    "pink":       {"bg": "#2e0a1a", "fg": "#ff69b4", "opacity": 0.5},
    "cyber":      {"bg": "#000000", "fg": "#00ff00", "opacity": 0.4},
    "sunset":     {"bg": "#1a0a00", "fg": "#ffaa66", "opacity": 0.5},
    "ocean":      {"bg": "#001a2e", "fg": "#66ddff", "opacity": 0.5},
}


class TranslucentWidget(QWidget):
    """Custom widget with translucent background."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._bg_color = QColor(0, 0, 0, 128)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def set_bg_color(self, color: QColor):
        self._bg_color = color
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QBrush(self._bg_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(self.rect(), 8, 8)


class _CloseButtonOverlay(QWidget):
    """Tiny floating close button that sits over the overlay window.

    This is a SEPARATE window (not transparent to input), so users
    can click the ✕ to quit even when the main overlay is click-through.
    """

    def __init__(self, parent_overlay: QMainWindow):
        super().__init__()
        self._parent_overlay = parent_overlay
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(32, 32)

        self._hovered = False

    def show(self):
        """Position above the parent overlay\'s top-right corner."""
        super().show()
        self._reposition()

    def _reposition(self):
        """Move to top-right corner of parent overlay."""
        if self._parent_overlay:
            parent_pos = self._parent_overlay.pos()
            parent_w = self._parent_overlay.width()
            btn_x = parent_pos.x() + parent_w - self.width() - 4
            btn_y = parent_pos.y() + 2
            self.move(btn_x, btn_y)

    def mousePressEvent(self, event):
        """Click = quit the application."""
        if event.button() == Qt.MouseButton.LeftButton:
            QApplication.quit()
        super().mousePressEvent(event)

    def enterEvent(self, event):
        self._hovered = True
        self.update()

    def leaveEvent(self, event):
        self._hovered = False
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Background circle
        if self._hovered:
            color = QColor(220, 40, 40, 200)
        else:
            color = QColor(180, 30, 30, 120)
        painter.setBrush(QBrush(color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(4, 4, 24, 24)

        # ✕ symbol
        painter.setPen(QPen(QColor(255, 255, 255, 220), 2))
        painter.drawLine(12, 12, 20, 20)
        painter.drawLine(20, 12, 12, 20)


class SubtitleOverlay(QMainWindow):
    """Transparent overlay window for displaying subtitles."""

    def __init__(self):
        super().__init__()

        self.window_width = 600
        self.window_height = 100
        self.opacity = 0.5
        self.always_on_top = True
        self.click_through = True
        self.is_visible = True
        self.theme = "dark"
        self.history_lines = 2
        self.font_size = 24
        self.history: List[str] = []

        self._setup_window()
        self._setup_ui()
        self.set_theme("dark")

    def _setup_window(self):
        """Configure window properties."""
        self.setWindowTitle("SimulTransOverlay")
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.resize(self.window_width, self.window_height)

        # Center on screen
        screen = QApplication.primaryScreen()
        if screen:
            geometry = screen.availableGeometry()
            x = (geometry.width() - self.window_width) // 2
            y = int(geometry.height() * 0.85)  # 85% from top
            self.move(x, y)

        # Enable click-through (mouse transparent), except for the close button
        if self.click_through:
            self.setWindowFlags(
                self.windowFlags() | Qt.WindowType.WindowTransparentForInput
            )

    def _setup_ui(self):
        """Setup the UI elements."""
        central = TranslucentWidget()
        self.setCentralWidget(central)

        # Main layout
        layout = QVBoxLayout(central)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(2)

        # Close button (sits in a tiny frameless window on top of overlay)
        self._close_btn = _CloseButtonOverlay(self)
        self._close_btn.show()

        # Current subtitle (main line)
        self.current_label = QLabel()
        self.current_label.setWordWrap(True)
        self.current_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.current_label)

        # History container
        self.history_layout = QVBoxLayout()
        self.history_layout.setSpacing(0)
        layout.addLayout(self.history_layout)

    def set_theme(self, theme_name: str) -> None:
        """Apply a color theme.

        Args:
            theme_name: Key from THEMES dict
        """
        if theme_name not in THEMES:
            logger.warning(f"Unknown theme: {theme_name}, using dark")
            theme_name = "dark"

        self.theme = theme_name
        colors = THEMES[theme_name]
        self.opacity = colors["opacity"]

        bg = QColor(colors["bg"])
        fg = QColor(colors["fg"])

        # Set window opacity
        self.setWindowOpacity(self.opacity)

        # Set widget background
        central = self.centralWidget()
        if isinstance(central, TranslucentWidget):
            bg.setAlpha(int(255 * min(1.0, self.opacity + 0.3)))
            central.set_bg_color(bg)

        # Set text color
        style = f"color: {colors['fg']}; font-size: {self.font_size}px;"
        self.current_label.setStyleSheet(style)

        for i in range(self.history_layout.count()):
            label = self.history_layout.itemAt(i).widget()
            if label:
                alpha = max(40, 100 - i * 30)
                label.setStyleSheet(
                    f"color: {colors['fg']}; font-size: {self.font_size - 4}px; "
                    f"background: transparent; opacity: 0.{alpha};"
                )

    def show_text(self, text: str) -> None:
        """Display translated text in the overlay.

        Args:
            text: Translation text to display
        """
        if not text:
            return

        # Push current to history
        current = self.current_label.text()
        if current:
            self.history.append(current)
            if len(self.history) > self.history_lines:
                self.history.pop(0)

        # Update current text
        self.current_label.setText(text)

        # Update history display
        self._update_history()

    def _update_history(self) -> None:
        """Update the history subtitle display."""
        # Clear existing history labels
        while self.history_layout.count():
            item = self.history_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Add history items (most recent last)
        colors = THEMES.get(self.theme, THEMES["dark"])
        for i, text in enumerate(self.history):
            label = QLabel(text)
            alpha = max(40, 100 - (len(self.history) - 1 - i) * 30)
            label.setStyleSheet(
                f"color: {colors['fg']}; font-size: {self.font_size - 4}px; "
                f"background: transparent;"
            )
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.history_layout.addWidget(label)

    def toggle_visibility(self) -> None:
        """Toggle overlay visibility."""
        if self.is_visible:
            self.hide()
        else:
            self.show()
        self.is_visible = not self.is_visible

    def set_opacity_value(self, value: float) -> None:
        """Set window opacity.

        Args:
            value: Opacity between 0.0 and 1.0
        """
        self.opacity = max(0.1, min(1.0, value))
        self.setWindowOpacity(self.opacity)


class OverlayApp:
    """Application controller for the overlay window."""

    def __init__(self):
        self.app = QApplication.instance() or QApplication([])
        self.overlay = SubtitleOverlay()
        self._setup_tray()

    def _setup_tray(self):
        """Setup system tray icon."""
        self.tray = QSystemTrayIcon()
        self.tray.setToolTip("SimulTransOverlay")

        menu = QMenu()
        show_action = QAction("显示/隐藏", menu)
        show_action.triggered.connect(self.overlay.toggle_visibility)
        menu.addAction(show_action)

        settings_action = QAction("设置", menu)
        settings_action.triggered.connect(self._open_settings)
        menu.addAction(settings_action)

        menu.addSeparator()

        quit_action = QAction("退出", menu)
        quit_action.triggered.connect(self.quit)
        menu.addAction(quit_action)

        self.tray.setContextMenu(menu)
        self.tray.show()

    def _open_settings(self):
        """Open settings panel (placeholder)."""
        logger.info("Settings panel requested")

    def show(self):
        """Show the overlay window."""
        self.overlay.show()
        return self.app.exec()

    def quit(self):
        """Quit the application."""
        self.app.quit()
