"""
Semi-transparent loading overlay built around the circular progress ring
(CircularProgress) instead of an indeterminate bar.

Two usage modes:

- Real staged progress: pipeline.fetch's `on_progress(percent, message)`
  callback drives `set_progress()` directly as each real stage
  completes (fetch versions -> fetch representations -> build results).
- No real percentage available (e.g. populating the Projects/Departments
  dropdowns — a single network call with no sub-steps to report):
  `animate_indeterminate()` climbs the ring to ~90% and holds, then
  `complete_and_hide()` snaps it to 100% on completion. It's an
  approximation (CircularProgress is a percentage ring, not a spinner),
  but avoids the ring looking frozen at 0% for the call's whole duration.
"""
from __future__ import annotations

from typing import Optional

from ..qt import QtWidgets, QtCore
from .circular_progress import CircularProgress


class LoadingOverlay(QtWidgets.QWidget):
    def __init__(self, parent: QtWidgets.QWidget):
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self.setStyleSheet("background-color: rgba(20, 20, 20, 160);")

        ring_holder = QtWidgets.QWidget(self)
        ring_holder.setFixedSize(120, 120)
        ring_stack = QtWidgets.QStackedLayout(ring_holder)
        ring_stack.setStackingMode(QtWidgets.QStackedLayout.StackAll)

        self._ring = CircularProgress()
        self._percent_label = QtWidgets.QLabel("0%")
        self._percent_label.setAlignment(QtCore.Qt.AlignCenter)
        self._percent_label.setStyleSheet(
            "color: white; font-size: 15px; font-weight: bold; background: transparent;"
        )
        ring_stack.addWidget(self._ring)
        ring_stack.addWidget(self._percent_label)

        self._message_label = QtWidgets.QLabel("Loading…")
        self._message_label.setAlignment(QtCore.Qt.AlignCenter)
        self._message_label.setStyleSheet("color: white; font-size: 12px; background: transparent;")

        layout = QtWidgets.QVBoxLayout(self)
        layout.addStretch()
        layout.addWidget(ring_holder, alignment=QtCore.Qt.AlignCenter)
        layout.addWidget(self._message_label)
        layout.addStretch()

        parent.installEventFilter(self)
        self.hide()

    def show_overlay(self, message: str = "Loading…") -> None:
        self._message_label.setText(message)
        self._ring.setValue(0)
        self._percent_label.setText("0%")
        self._resize_to_parent()
        self.raise_()
        self.show()

    def set_progress(self, percent: int, message: Optional[str] = None) -> None:
        percent = max(0, min(100, percent))
        if message:
            self._message_label.setText(message)
        self._ring.animateTo(percent)
        self._percent_label.setText(f"{percent}%")

    def animate_indeterminate(self) -> None:
        self._ring.animateTo(90)
        self._percent_label.setText("…")

    def complete_and_hide(self, delay_ms: int = 200) -> None:
        self._ring.animateTo(100)
        self._percent_label.setText("100%")
        QtCore.QTimer.singleShot(delay_ms, self.hide_overlay)

    def hide_overlay(self) -> None:
        self.hide()

    def eventFilter(self, obj, event):
        if event.type() in (QtCore.QEvent.Resize, QtCore.QEvent.Show):
            self._resize_to_parent()
        return super().eventFilter(obj, event)

    def _resize_to_parent(self) -> None:
        if self.parent() is not None:
            self.setGeometry(self.parent().rect())
