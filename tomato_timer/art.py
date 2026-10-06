"""トマトの描画。画像があればそれを使い、なければ図形で描きます。"""

from __future__ import annotations

import math
import os
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QLinearGradient, QPainter, QPainterPath, QPixmap

ROOT = Path(__file__).resolve().parent.parent
_SOURCE_SIDE = 640
_cache: QPixmap | None = None


def find_image_path() -> Path | None:
    env = os.environ.get("TOMATO_IMAGE")
    if env:
        candidate = Path(env)
        if candidate.is_file():
            return candidate
    candidates = (
        ROOT / "tomato-cutout.png",
        ROOT.parent / "tomato-timer" / "tomato-cutout.png",
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def load_tomato_source() -> QPixmap:
    global _cache
    if _cache is None:
        path = find_image_path()
        loaded = _pixmap_from_file(path) if path is not None else None
        _cache = loaded if loaded is not None else _draw_tomato(_SOURCE_SIDE)
    return _cache


def _pixmap_from_file(path: Path) -> QPixmap | None:
    image = QImage(str(path))
    if image.isNull():
        return None
    side = min(image.width(), image.height())
    x = (image.width() - side) // 2
    y = (image.height() - side) // 2
    square = image.copy(x, y, side, side)
    if side > 1254:
        square = square.scaled(
            1254,
            1254,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
    return QPixmap.fromImage(square)


def _draw_tomato(side: int) -> QPixmap:
    image = QImage(side, side, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    rect = QRectF(0, 0, side, side)
    _paint_fruit(painter, rect)
    _paint_leaves(painter, rect)
    painter.end()
    return QPixmap.fromImage(image)


def _paint_fruit(painter: QPainter, rect: QRectF) -> None:
    gradient = QLinearGradient(rect.topLeft(), rect.bottomLeft())
    gradient.setColorAt(0, QColor.fromRgbF(0.96, 0.33, 0.26))
    gradient.setColorAt(1, QColor.fromRgbF(0.78, 0.12, 0.10))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(gradient)
    painter.drawPath(_tomato_path(rect))


def _paint_leaves(painter: QPainter, tomato: QRectF) -> None:
    width = tomato.width() * 0.425
    height = tomato.height() * 0.275
    center_x = tomato.x() + tomato.width() / 2
    center_y = tomato.y() + tomato.height() / 2 - tomato.height() * 0.355
    leaf = QRectF(center_x - width / 2, center_y - height / 2, width, height)
    gradient = QLinearGradient(leaf.topLeft(), leaf.bottomLeft())
    gradient.setColorAt(0, QColor.fromRgbF(0.35, 0.62, 0.30))
    gradient.setColorAt(1, QColor.fromRgbF(0.20, 0.45, 0.20))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(gradient)
    painter.drawPath(_leaf_path(leaf))


def _tomato_path(rect: QRectF) -> QPainterPath:
    width = rect.width()
    height = rect.height()
    origin_x = rect.x()
    origin_y = rect.y()

    def point(px: float, py: float) -> QPointF:
        return QPointF(origin_x + width * px, origin_y + height * py)

    path = QPainterPath()
    path.moveTo(point(0.50, 0.14))
    path.cubicTo(point(0.42, 0.11), point(0.24, 0.15), point(0.18, 0.32))
    path.cubicTo(point(0.07, 0.45), point(0.12, 0.69), point(0.28, 0.78))
    path.cubicTo(point(0.38, 0.91), point(0.62, 0.91), point(0.72, 0.78))
    path.cubicTo(point(0.88, 0.69), point(0.93, 0.45), point(0.82, 0.32))
    path.cubicTo(point(0.76, 0.15), point(0.58, 0.11), point(0.50, 0.14))
    path.closeSubpath()
    return path


def _leaf_path(rect: QRectF) -> QPainterPath:
    origin_x = rect.x() + rect.width() / 2
    origin_y = rect.y() + rect.height() * 0.55
    path = QPainterPath()
    for index in range(5):
        angle = index * math.pi * 2 / 5 - math.pi / 2
        left = angle - 0.36
        right = angle + 0.36
        tip = QPointF(
            origin_x + math.cos(angle) * rect.width() * 0.42,
            origin_y + math.sin(angle) * rect.height() * 0.47,
        )
        control_left = QPointF(
            origin_x + math.cos(left) * rect.width() * 0.25,
            origin_y + math.sin(left) * rect.height() * 0.26,
        )
        control_right = QPointF(
            origin_x + math.cos(right) * rect.width() * 0.25,
            origin_y + math.sin(right) * rect.height() * 0.26,
        )
        path.moveTo(origin_x, origin_y)
        path.quadTo(control_left, tip)
        path.quadTo(control_right, QPointF(origin_x, origin_y))
    return path
