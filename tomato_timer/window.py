"""枠なしのトマトウィンドウ、設定、右上の通知。"""

from __future__ import annotations

import ctypes
import ctypes.wintypes
import sys
import time
import traceback
from pathlib import Path

from PySide6.QtCore import QPoint, QPointF, QRect, Qt, QSettings, QTimer
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontDatabase,
    QFontMetrics,
    QIcon,
    QPainter,
    QPalette,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from tomato_timer import __version__
from tomato_timer.art import load_tomato_source
from tomato_timer.audio import play_sound
from tomato_timer.logic import Effect, Phase, SoundChoice, TimerEngine

DESIGN_W = 420
DESIGN_H = 430
CREAM = QColor(255, 245, 219)
EDGE = 8


def run() -> None:
    try:
        _run()
    except Exception:
        log = Path(__file__).resolve().parent.parent / "tomato-timer-error.log"
        log.write_text(traceback.format_exc(), encoding="utf-8")
        raise


def _run() -> None:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("com.codex.tomatotimer")
    app = QApplication(sys.argv)
    app.setApplicationName("トマトタイマー")
    app.setOrganizationName("com.codex.tomatotimer")
    app.setApplicationVersion(__version__)
    app.setStyle("Fusion")
    window = MainWindow()
    window.center_on_screen()
    window.show()
    sys.exit(app.exec())


def _settings() -> QSettings:
    return QSettings("com.codex.tomatotimer", "TomatoTimer")


def _ui_font_family() -> str:
    families = set(QFontDatabase.families())
    for name in ("Yu Gothic UI", "Yu Gothic", "Meiryo UI", "Meiryo", "Segoe UI"):
        if name in families:
            return name
    return "Segoe UI"


def _clock_font_family() -> str:
    families = set(QFontDatabase.families())
    if "Segoe UI" in families:
        return "Segoe UI"
    return _ui_font_family()


class ShadowLabel(QLabel):
    def __init__(self, text: str = "", parent: QWidget | None = None, opacity: float = 1.0) -> None:
        super().__init__(text, parent)
        self.opacity = opacity
        self.setAutoFillBackground(False)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setFont(self.font())
        rect = self.rect().adjusted(2, 1, -2, -1)
        flags = self.alignment()
        spread = max(1, round(self.font().pixelSize() / 34))
        painter.setPen(QColor(0, 0, 0, 140))
        for dx, dy in ((0, spread), (spread, spread), (-spread, spread)):
            painter.drawText(rect.translated(dx, dy), flags, self.text())
        painter.setPen(QColor(255, 245, 219, int(255 * self.opacity)))
        painter.drawText(rect, flags, self.text())


class CircleButton(QPushButton):
    def __init__(self, kind: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.kind = kind
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAutoFillBackground(False)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(1, 1, -1, -1)
        if self.kind == "close":
            fill = QColor(255, 97, 89)
            mark = QColor(107, 20, 15)
        else:
            fill = QColor(255, 199, 71)
            mark = QColor(122, 82, 10)
        if self.isDown():
            fill = fill.darker(110)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(fill)
        painter.drawEllipse(rect)
        pen = QPen(mark, max(1.4, self.width() * 0.12))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        center = rect.center()
        arm = rect.width() * 0.22
        cx, cy = float(center.x()), float(center.y())
        if self.kind == "close":
            painter.drawLine(QPointF(cx - arm, cy - arm), QPointF(cx + arm, cy + arm))
            painter.drawLine(QPointF(cx - arm, cy + arm), QPointF(cx + arm, cy - arm))
        else:
            painter.drawLine(QPointF(cx - arm, cy), QPointF(cx + arm, cy))


class GearButton(QPushButton):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAutoFillBackground(False)
        self.setToolTip("設定")

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 90 if self.isDown() else 71))
        painter.drawEllipse(self.rect().adjusted(0, 0, -1, -1))
        pen = QPen(CREAM, max(1.2, self.width() * 0.07))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        center = QPointF(self.width() / 2, self.height() / 2)
        radius = self.width() * 0.18
        painter.drawEllipse(center, radius, radius)
        painter.save()
        painter.translate(center)
        inner = self.width() * 0.26
        outer = self.width() * 0.34
        for _ in range(8):
            painter.drawLine(QPointF(0, inner), QPointF(0, outer))
            painter.rotate(45)
        painter.restore()


class CapsuleButton(QPushButton):
    def __init__(self, text: str, primary: bool, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.primary = primary
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAutoFillBackground(False)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRect(self.rect()).adjusted(1, 1, -2, -2)
        if self.isDown():
            shrink = max(1, int(rect.width() * 0.02))
            rect = rect.adjusted(shrink, shrink, -shrink, -shrink)
        if self.primary:
            fill = QColor(255, 245, 219)
            text = QColor(184, 31, 26)
            border = None
        else:
            fill = QColor(255, 255, 255, 70 if self.isDown() else 46)
            text = QColor(255, 255, 255)
            border = QColor(255, 255, 255, 128)
        painter.setPen(Qt.PenStyle.NoPen if border is None else QPen(border, 1))
        painter.setBrush(fill)
        radius = rect.height() / 2
        painter.drawRoundedRect(rect, radius, radius)
        painter.setPen(text)
        painter.setFont(self.font())
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.text())


class PhaseButton(QPushButton):
    def __init__(self, phase: Phase, parent: QWidget | None = None) -> None:
        super().__init__(phase.value, parent)
        self.phase = phase
        self.selected = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAutoFillBackground(False)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setFont(self.font())
        alpha = 255 if self.selected else int(255 * 0.65)
        rect = self.rect().adjusted(0, 0, 0, -max(3, int(self.height() * 0.16)))
        painter.setPen(QColor(0, 0, 0, 120 if self.selected else 80))
        painter.drawText(rect.translated(0, 1), Qt.AlignmentFlag.AlignCenter, self.text())
        painter.setPen(QColor(255, 245, 219, alpha))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.text())
        if self.selected:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(255, 245, 219))
            bar_h = max(2, int(self.height() * 0.08))
            bar_w = max(16, int(self.fontMetrics().horizontalAdvance(self.text())))
            x = (self.width() - bar_w) // 2
            y = self.height() - bar_h - 1
            painter.drawRoundedRect(x, y, bar_w, bar_h, bar_h / 2, bar_h / 2)


class SettingsDialog(QDialog):
    def __init__(self, engine: TimerEngine, ui_font: str, on_changed, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.engine = engine
        self.on_changed = on_changed
        self.setWindowTitle("タイマーの設定")
        self.setModal(True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)
        layout.setSizeConstraint(QVBoxLayout.SizeConstraint.SetFixedSize)

        title = QLabel("タイマーの設定")
        title_font = QFont(ui_font, 16)
        title_font.setWeight(QFont.Weight.Bold)
        title.setFont(title_font)
        layout.addWidget(title)

        self._add_minutes(layout, "作業", Phase.FOCUS)
        self._add_minutes(layout, "短い休憩", Phase.SHORT_BREAK)
        self._add_minutes(layout, "長い休憩", Phase.LONG_BREAK)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)

        self._add_sound(layout, "作業開始の音", "focusStart", engine.focus_start_sound)
        self._add_sound(layout, "休憩開始の音", "breakStart", engine.break_start_sound)
        self._add_sound(layout, "休憩終了の音", "breakEnd", engine.break_end_sound)

        caption = QLabel("変更中のタイマーはリセットされます。")
        caption.setFont(QFont(ui_font, 9))
        caption.setStyleSheet("color: #666666;")
        layout.addWidget(caption)

        version = QLabel(f"バージョン {__version__}")
        version.setFont(QFont(ui_font, 8))
        version.setStyleSheet("color: #888888;")
        layout.addWidget(version)

        done_row = QHBoxLayout()
        done_row.addStretch(1)
        done = QPushButton("完了")
        done.setDefault(True)
        done.clicked.connect(self.accept)
        done_row.addWidget(done)
        layout.addLayout(done_row)
        self.setMinimumWidth(480)

    def _add_minutes(self, layout: QVBoxLayout, title: str, phase: Phase) -> None:
        row = QHBoxLayout()
        row.addWidget(QLabel(title))
        row.addStretch(1)
        low, high = phase.minute_bounds
        spin = QSpinBox()
        spin.setRange(low, high)
        spin.setSuffix("分")
        spin.setKeyboardTracking(False)
        spin.setMinimumWidth(96)
        spin.blockSignals(True)
        spin.setValue(self.engine.minutes_for(phase))
        spin.blockSignals(False)
        spin.valueChanged.connect(lambda value, item=phase: self._change_minutes(item, value))
        row.addWidget(spin)
        layout.addLayout(row)

    def _add_sound(self, layout: QVBoxLayout, title: str, event: str, current: SoundChoice) -> None:
        row = QHBoxLayout()
        row.addWidget(QLabel(title))
        combo = QComboBox()
        combo.setMinimumWidth(220)
        for choice in SoundChoice:
            combo.addItem(choice.title, choice)
        index = combo.findData(current)
        combo.blockSignals(True)
        if index >= 0:
            combo.setCurrentIndex(index)
        combo.blockSignals(False)
        combo.currentIndexChanged.connect(lambda _index, name=event, box=combo: self._change_sound(name, box))
        row.addWidget(combo, 1)
        preview = QPushButton("試聴")
        preview.clicked.connect(lambda _checked=False, box=combo: self._preview(box))
        row.addWidget(preview)
        layout.addLayout(row)

    def _change_minutes(self, phase: Phase, value: int) -> None:
        self.engine.set_minutes(value, phase)
        self.on_changed()

    def _change_sound(self, event: str, combo: QComboBox) -> None:
        choice = combo.currentData()
        if isinstance(choice, SoundChoice):
            self.engine.set_sound(choice, event)
            self.on_changed()

    def _preview(self, combo: QComboBox) -> None:
        choice = combo.currentData()
        if isinstance(choice, SoundChoice):
            play_sound(choice)


class Notification(QWidget):
    def __init__(self, title: str, message: str, icon: QPixmap, ui_font: str, anchor: QWidget) -> None:
        super().__init__(None)
        self._anchor = anchor
        self.closed_callback = None
        self.setWindowTitle(title)
        self.setFixedSize(350, 92)
        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_QuitOnClose, False)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 14, 16, 14)
        layout.setSpacing(12)
        image = QLabel()
        image.setFixedSize(62, 62)
        image.setPixmap(_scaled(icon, 62, self.devicePixelRatioF()))
        layout.addWidget(image)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        heading = QLabel(title)
        heading_font = QFont(ui_font, 12)
        heading_font.setWeight(QFont.Weight.Bold)
        heading.setFont(heading_font)
        detail = QLabel(message)
        detail.setFont(QFont(ui_font, 10))
        detail.setWordWrap(True)
        text = self.palette().color(QPalette.ColorRole.WindowText)
        heading.setStyleSheet(f"background: transparent; color: {text.name()};")
        detail.setStyleSheet(
            f"background: transparent; color: rgba({text.red()}, {text.green()}, {text.blue()}, 0.72);"
        )
        image.setStyleSheet("background: transparent;")
        text_col.addStretch(1)
        text_col.addWidget(heading)
        text_col.addWidget(detail)
        text_col.addStretch(1)
        layout.addLayout(text_col, 1)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.close)
        self._timer.start(6000)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        fill = self.palette().color(QPalette.ColorRole.Window)
        fill.setAlpha(247)
        painter.setPen(QPen(QColor(0, 0, 0, 35), 1))
        painter.setBrush(fill)
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -2, -2), 18, 18)

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self._place()
        _make_topmost_no_activate(int(self.winId()))

    def closeEvent(self, event) -> None:  # noqa: N802
        callback = self.closed_callback
        self.closed_callback = None
        if callback is not None:
            callback()
        super().closeEvent(event)

    def _place(self) -> None:
        screen = self._anchor.screen() or QApplication.primaryScreen()
        if screen is None:
            return
        area = screen.availableGeometry()
        self.move(area.x() + area.width() - self.width() - 18, area.y() + 18)


class MainWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("トマトタイマー")
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowMinimizeButtonHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setMouseTracking(True)
        self.setMinimumSize(300, 310)

        self._ui_font = _ui_font_family()
        self._clock_font = _clock_font_family()
        app = QApplication.instance()
        if app is not None:
            app.setFont(QFont(self._ui_font, 10))

        self.engine = TimerEngine()
        self._load_settings()
        self._source = load_tomato_source()
        self._hit_image = self._source.toImage()
        self._notice: Notification | None = None
        self._scale = 1.0
        self._origin_x = 0
        self._origin_y = 0
        self._dragging = False
        self._drag_active = False
        self._resizing = False
        self._captured = False
        self._edges = (False, False, False, False)
        self._press_global = QPointF()
        self._press_window_pos = QPoint()
        self._press_geo = QRect()
        self._minimize_ready = False

        self.tomato = QLabel(self)
        self.tomato.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tomato.setAutoFillBackground(False)
        self.tomato.setStyleSheet("background: transparent; border: none;")
        self.tomato.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._shadow = QGraphicsDropShadowEffect(self.tomato)
        self._shadow.setColor(QColor(0, 0, 0, 48))
        self._shadow.setOffset(0, 7)
        self._shadow.setBlurRadius(18)
        self.tomato.setGraphicsEffect(self._shadow)

        self.phase_label = ShadowLabel(parent=self)
        self.clock = ShadowLabel(parent=self)
        self.completed = ShadowLabel(parent=self, opacity=0.85)
        for label in (self.phase_label, self.clock, self.completed):
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.progress = QProgressBar(self)
        self.progress.setRange(0, 10000)
        self.progress.setTextVisible(False)
        self.progress.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.progress.setStyleSheet(
            """
            QProgressBar { background: rgba(255, 255, 255, 0.28); border: none; border-radius: 4px; }
            QProgressBar::chunk { background: #FFF5DB; border-radius: 4px; }
            """
        )

        self.close_button = CircleButton("close", self)
        self.close_button.setToolTip("アプリを終了")
        self.close_button.setAccessibleName("アプリを終了")
        self.close_button.clicked.connect(self.close)
        self.min_button = CircleButton("min", self)
        self.min_button.setToolTip("ウィンドウをタスクバーにしまう")
        self.min_button.setAccessibleName("ウィンドウをタスクバーにしまう")
        self.min_button.clicked.connect(self.showMinimized)
        self.gear = GearButton(self)
        self.gear.clicked.connect(self._open_settings)
        self.start_button = CapsuleButton("開始", True, self)
        self.start_button.clicked.connect(self._on_toggle)
        self.reset_button = CapsuleButton("リセット", False, self)
        self.reset_button.clicked.connect(self._on_reset)

        self.phase_buttons: list[PhaseButton] = []
        for phase in (Phase.FOCUS, Phase.SHORT_BREAK, Phase.LONG_BREAK):
            button = PhaseButton(phase, self)
            button.clicked.connect(lambda _checked=False, item=phase: self._on_select(item))
            self.phase_buttons.append(button)

        self._front = [
            self.phase_label,
            self.clock,
            self.progress,
            self.completed,
            self.start_button,
            self.reset_button,
            self.close_button,
            self.min_button,
            self.gear,
            *self.phase_buttons,
        ]

        self.ticker = QTimer(self)
        self.ticker.setInterval(250)
        self.ticker.timeout.connect(self._on_tick)

        self.setWindowIcon(self._build_icon())
        self.resize(DESIGN_W, DESIGN_H)
        self._layout()

    def center_on_screen(self) -> None:
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        frame = self.frameGeometry()
        frame.moveCenter(screen.availableGeometry().center())
        self.move(frame.topLeft())

    def paintEvent(self, event) -> None:  # noqa: N802
        return

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._layout()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        if not self._minimize_ready:
            self._minimize_ready = True
            _enable_taskbar_minimize(int(self.winId()))

    def closeEvent(self, event) -> None:  # noqa: N802
        self._dismiss_notice()
        self._release_capture()
        event.accept()
        app = QApplication.instance()
        if app is not None:
            app.quit()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() != Qt.MouseButton.LeftButton:
            return
        pos = event.position().toPoint()
        self._press_global = event.globalPosition()
        edges = _hit_edges(pos, self.width(), self.height())
        if any(edges):
            self._resizing = True
            self._edges = edges
            self._press_geo = self.geometry()
            self._capture()
            event.accept()
            return
        if self._hit_tomato(pos):
            self._dragging = True
            self._drag_active = False
            self._press_window_pos = self.pos()
            self._capture()
            event.accept()

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._resizing:
            self._apply_resize(event.globalPosition())
            return
        if self._dragging:
            if not self._drag_active:
                if (event.globalPosition() - self._press_global).manhattanLength() < 4:
                    return
                self._drag_active = True
            shift = (event.globalPosition() - self._press_global).toPoint()
            self.move(self._press_window_pos + shift)
            return
        self.setCursor(_edge_cursor(_hit_edges(event.position().toPoint(), self.width(), self.height())))

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        self._dragging = False
        self._drag_active = False
        self._resizing = False
        self._release_capture()

    def leaveEvent(self, event) -> None:  # noqa: N802
        if not self._resizing and not self._dragging:
            self.unsetCursor()
        super().leaveEvent(event)

    def _layout(self) -> None:
        if self.width() <= 0 or self.height() <= 0:
            return
        self._scale = min(self.width() / DESIGN_W, self.height() / DESIGN_H)
        self._origin_x = int(round((self.width() - DESIGN_W * self._scale) / 2))
        self._origin_y = int(round((self.height() - DESIGN_H * self._scale) / 2))
        scale = self._scale
        side = max(1, int(round(400 * scale)))
        pad = int(round(28 * scale))
        self._place(self.tomato, 10, 15, 400, 400)
        tomato_rect = self.tomato.geometry().adjusted(-pad, -pad, pad, pad)
        self.tomato.setGeometry(tomato_rect)
        self.tomato.setPixmap(_scaled(self._source, side, self.devicePixelRatioF()))
        self._shadow.setBlurRadius(max(1, 12 * scale))
        self._shadow.setOffset(0, 7 * scale)

        self._place(self.phase_label, 50, 132, 320, 30)
        self._place(self.clock, 20, 160, 380, 86)
        self._place(self.progress, 107, 250, 205, 8)
        self._place(self.start_button, 91, 274, 112, 39)
        self._place(self.reset_button, 217, 274, 112, 39)
        self._place(self.completed, 40, 360, 340, 24)
        self._place(self.min_button, 351, 32, 20, 20)
        self._place(self.close_button, 379, 32, 20, 20)
        self._place(self.gear, 312, 123, 36, 36)

        phase_font = QFont(self._ui_font)
        phase_font.setPixelSize(max(1, int(round(17 * scale))))
        phase_font.setWeight(QFont.Weight.Bold)
        self.phase_label.setFont(phase_font)

        clock_font = QFont(self._clock_font)
        clock_font.setPixelSize(max(1, int(round(68 * scale))))
        clock_font.setWeight(QFont.Weight.Bold)
        self.clock.setFont(clock_font)

        done_font = QFont(self._ui_font)
        done_font.setPixelSize(max(1, int(round(12 * scale))))
        done_font.setWeight(QFont.Weight.Medium)
        self.completed.setFont(done_font)

        button_font = QFont(self._ui_font)
        button_font.setPixelSize(max(1, int(round(15 * scale))))
        button_font.setWeight(QFont.Weight.Bold)
        self.start_button.setFont(button_font)
        self.reset_button.setFont(button_font)

        radius = max(2, int(round(4 * scale)))
        self.progress.setStyleSheet(
            f"""
            QProgressBar {{
                background: rgba(255, 255, 255, 0.28);
                border: none;
                border-radius: {radius}px;
            }}
            QProgressBar::chunk {{
                background: #FFF5DB;
                border-radius: {radius}px;
            }}
            """
        )
        self.tomato.lower()
        for widget in self._front:
            widget.raise_()
        self._refresh()

    def _refresh(self) -> None:
        self.phase_label.setText(self.engine.phase.value)
        self.clock.setText(self.engine.clock_text)
        self.completed.setText(f"完了した作業  {self.engine.completed_focus} / 4")
        self.progress.setValue(int(self.engine.progress * 10000))
        self.start_button.setText("一時停止" if self.engine.running else "開始")
        self._layout_phase_buttons()

    def _layout_phase_buttons(self) -> None:
        scale = self._scale
        pixel = max(8, int(round(12 * scale)))
        widths: list[int] = []
        for button in self.phase_buttons:
            selected = self.engine.phase is button.phase
            font = QFont(self._ui_font)
            font.setPixelSize(pixel)
            font.setWeight(QFont.Weight.Bold if selected else QFont.Weight.Medium)
            button.setFont(font)
            button.selected = selected
            widths.append(QFontMetrics(font).horizontalAdvance(button.text()) + int(round(8 * scale)))
        spacing = int(round(13 * scale))
        total = sum(widths) + spacing * (len(widths) - 1)
        x = self._origin_x + int(round(210 * scale)) - total // 2
        y = self._origin_y + int(round(326 * scale))
        height = max(1, int(round(32 * scale)))
        for button, width in zip(self.phase_buttons, widths):
            button.setGeometry(x, y, max(1, width), height)
            button.raise_()
            button.update()
            x += width + spacing

    def _place(self, widget: QWidget, x: float, y: float, w: float, h: float) -> None:
        scale = self._scale
        widget.setGeometry(
            self._origin_x + int(round(x * scale)),
            self._origin_y + int(round(y * scale)),
            max(1, int(round(w * scale))),
            max(1, int(round(h * scale))),
        )

    def _hit_tomato(self, pos: QPoint) -> bool:
        if self._scale <= 0:
            return False
        local_x = (pos.x() - self._origin_x) / self._scale - 10
        local_y = (pos.y() - self._origin_y) / self._scale - 15
        if not (0 <= local_x < 400 and 0 <= local_y < 400):
            return False
        image = self._hit_image
        ix = min(image.width() - 1, int(local_x / 400 * image.width()))
        iy = min(image.height() - 1, int(local_y / 400 * image.height()))
        return image.pixelColor(ix, iy).alpha() > 24

    def _apply_resize(self, global_pos: QPointF) -> None:
        delta = (global_pos - self._press_global).toPoint()
        geo = self._press_geo
        left, right, top, bottom = self._edges
        x, y, w, h = geo.x(), geo.y(), geo.width(), geo.height()
        if left:
            w = max(self.minimumWidth(), geo.width() - delta.x())
            x = geo.x() + geo.width() - w
        elif right:
            w = max(self.minimumWidth(), geo.width() + delta.x())
        if top:
            h = max(self.minimumHeight(), geo.height() - delta.y())
            y = geo.y() + geo.height() - h
        elif bottom:
            h = max(self.minimumHeight(), geo.height() + delta.y())
        self.setGeometry(x, y, w, h)

    def _on_toggle(self) -> None:
        self._apply_effect(self.engine.toggle(time.time()))
        self._sync_ticker()
        self._refresh()

    def _on_reset(self) -> None:
        self.engine.reset()
        self._sync_ticker()
        self._refresh()

    def _on_select(self, phase: Phase) -> None:
        self.engine.select(phase)
        self._sync_ticker()
        self._refresh()

    def _on_tick(self) -> None:
        self._apply_effect(self.engine.tick(time.time()))
        self._refresh()

    def _on_settings_changed(self) -> None:
        self._save_settings()
        self._sync_ticker()
        self._refresh()

    def _open_settings(self) -> None:
        SettingsDialog(self.engine, self._ui_font, self._on_settings_changed, self).exec()

    def _apply_effect(self, effect: Effect | None) -> None:
        if effect is None:
            return
        if effect.play is not None:
            play_sound(effect.play)
        if effect.title:
            self._notify(effect.title, effect.message)

    def _notify(self, title: str, message: str) -> None:
        self._dismiss_notice()
        notice = Notification(title, message, self._source, self._ui_font, self)
        notice.closed_callback = lambda: self._forget_notice(notice)
        self._notice = notice
        notice.show()

    def _dismiss_notice(self) -> None:
        notice = self._notice
        self._notice = None
        if notice is not None:
            notice.closed_callback = None
            notice.close()
            notice.deleteLater()

    def _forget_notice(self, notice: Notification) -> None:
        if self._notice is notice:
            self._notice = None

    def _sync_ticker(self) -> None:
        if self.engine.running:
            if not self.ticker.isActive():
                self.ticker.start()
        else:
            self.ticker.stop()

    def _load_settings(self) -> None:
        stored = _settings()
        self.engine.apply_settings(
            {
                "focusMinutes": stored.value("focusMinutes", 25),
                "shortBreakMinutes": stored.value("shortBreakMinutes", 5),
                "longBreakMinutes": stored.value("longBreakMinutes", 15),
                "focusStartSound": stored.value("focusStartSound", "chime"),
                "breakStartSound": stored.value("breakStartSound", "chime"),
                "breakEndSound": stored.value("breakEndSound", "chime"),
            }
        )

    def _save_settings(self) -> None:
        stored = _settings()
        for key, value in self.engine.snapshot().items():
            stored.setValue(key, value)

    def _build_icon(self) -> QIcon:
        icon = QIcon()
        for size in (16, 24, 32, 48, 64, 128, 256):
            icon.addPixmap(
                self._source.scaled(
                    size,
                    size,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        return icon

    def _capture(self) -> None:
        if not self._captured:
            self.grabMouse()
            self._captured = True

    def _release_capture(self) -> None:
        if self._captured:
            self.releaseMouse()
            self._captured = False


def _scaled(source: QPixmap, side: int, dpr: float) -> QPixmap:
    pixels = max(1, int(round(side * max(dpr, 1.0))))
    scaled = source.scaled(
        pixels,
        pixels,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    scaled.setDevicePixelRatio(max(dpr, 1.0))
    return scaled


def _hit_edges(pos: QPoint, width: int, height: int) -> tuple[bool, bool, bool, bool]:
    return (
        pos.x() <= EDGE,
        pos.x() >= width - EDGE,
        pos.y() <= EDGE,
        pos.y() >= height - EDGE,
    )


def _edge_cursor(edges: tuple[bool, bool, bool, bool]):
    left, right, top, bottom = edges
    if (left and top) or (right and bottom):
        return Qt.CursorShape.SizeFDiagCursor
    if (right and top) or (left and bottom):
        return Qt.CursorShape.SizeBDiagCursor
    if left or right:
        return Qt.CursorShape.SizeHorCursor
    if top or bottom:
        return Qt.CursorShape.SizeVerCursor
    return Qt.CursorShape.ArrowCursor


def _enable_taskbar_minimize(hwnd: int) -> None:
    try:
        user32 = ctypes.windll.user32
        get_long = user32.GetWindowLongPtrW
        set_long = user32.SetWindowLongPtrW
        get_long.argtypes = [ctypes.wintypes.HWND, ctypes.c_int]
        get_long.restype = ctypes.c_ssize_t
        set_long.argtypes = [ctypes.wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]
        set_long.restype = ctypes.c_ssize_t
        style = get_long(hwnd, -16)
        set_long(hwnd, -16, style | 0x00020000 | 0x00080000)
        user32.SetWindowPos(hwnd, None, 0, 0, 0, 0, 0x0002 | 0x0001 | 0x0004 | 0x0020)
    except (AttributeError, OSError, OverflowError):
        return


def _make_topmost_no_activate(hwnd: int) -> None:
    try:
        user32 = ctypes.windll.user32
        user32.SetWindowPos.argtypes = [
            ctypes.wintypes.HWND,
            ctypes.wintypes.HWND,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_uint,
        ]
        user32.SetWindowPos.restype = ctypes.wintypes.BOOL
        user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0010 | 0x0040)
    except (AttributeError, OSError, OverflowError):
        return
