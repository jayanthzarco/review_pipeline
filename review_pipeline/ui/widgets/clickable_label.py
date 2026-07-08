"""Small QLabel subclass that emits a `clicked` signal — used for the
comment image thumbnails in the Activity tab feed, which open the
full-screen viewer on click."""
from __future__ import annotations

from ..qt import QtWidgets, QtCore
from ..utils.placeholder_images import make_placeholder_pixmap


class ClickableImageLabel(QtWidgets.QLabel):
    clicked = QtCore.Signal()

    def __init__(self, label_text: str, width: int = 96, height: int = 64, parent=None):
        super().__init__(parent)
        self.label_text = label_text
        self.setPixmap(make_placeholder_pixmap(label_text, width=width, height=height, seed=label_text))
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setToolTip("Click to view full screen")

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)
