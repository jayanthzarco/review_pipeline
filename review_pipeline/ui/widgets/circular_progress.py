"""
Circular progress ring.

This is the widget provided directly for this project (originally
written against `PySide6` imports); adapted here to import through
`ui.qt` so it works under either PySide2 (Nuke) or PySide6 without
modification, and used by LoadingOverlay instead of an indeterminate bar.
Logic/behavior is otherwise unchanged from the original.
"""
from __future__ import annotations

from ..qt import QtCore, QtGui, QtWidgets


class CircularProgress(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._value = 0

        self.setFixedSize(120, 120)

        self.animation = QtCore.QPropertyAnimation(self, b"value")
        self.animation.setDuration(400)
        self.animation.setEasingCurve(QtCore.QEasingCurve.InOutCubic)

    def getValue(self):
        return self._value

    def setValue(self, value):
        self._value = value
        self.update()

    value = QtCore.Property(int, getValue, setValue)

    def animateTo(self, value):
        self.animation.stop()
        self.animation.setStartValue(self._value)
        self.animation.setEndValue(value)
        self.animation.start()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        rect = self.rect().adjusted(8, 8, -8, -8)

        # Background
        pen = QtGui.QPen(QtGui.QColor(80, 80, 80), 2)
        painter.setPen(pen)
        painter.drawEllipse(rect)

        # Progress
        pen = QtGui.QPen(QtGui.QColor(230, 230, 230), 6)
        pen.setCapStyle(QtCore.Qt.RoundCap)
        painter.setPen(pen)

        span = int(360 * self._value / 100)
        painter.drawArc(rect, 90 * 16, -span * 16)
