"""
Placeholder pixmap generation.

Real thumbnails come from AYON (`get_thumbnail`), which needs a live
server. For dummy-data mode — and as a visible fallback for real mode
when a thumbnail genuinely fails to load — we draw a simple colored
rectangle with a label instead of shipping binary image assets.
"""
from __future__ import annotations

import hashlib

from ..qt import QtGui, QtCore

_PALETTE = [
    "#3B6E8F", "#8F5A3B", "#4E8F5A", "#8F3B6E", "#6E8F3B",
    "#3B4E8F", "#8F6E3B", "#5A3B8F", "#8F3B3B", "#3B8F8F",
]


def _color_for(seed: str) -> str:
    digest = hashlib.md5(seed.encode("utf-8")).hexdigest()
    return _PALETTE[int(digest, 16) % len(_PALETTE)]


def make_placeholder_pixmap(label: str, width: int = 160, height: int = 90, seed: str | None = None) -> QtGui.QPixmap:
    pixmap = QtGui.QPixmap(width, height)
    color = QtGui.QColor(_color_for(seed or label))
    pixmap.fill(color)

    painter = QtGui.QPainter(pixmap)
    painter.setRenderHint(QtGui.QPainter.Antialiasing)
    painter.setPen(QtGui.QColor("#FFFFFF"))
    font = painter.font()
    font.setPointSize(max(8, height // 10))
    painter.setFont(font)
    painter.drawText(QtCore.QRect(0, 0, width, height), QtCore.Qt.AlignCenter | QtCore.Qt.TextWordWrap, label)
    painter.end()

    return pixmap
