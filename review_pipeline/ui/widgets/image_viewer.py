"""
Full-screen image viewer — opened by clicking a comment image in the
Activity tab feed, per the sketch's "On image click -> Full Screen Image
View" box. Now takes the whole set of images from that comment plus
which one was clicked, and shows < / > controls (and Left/Right arrow
keys) to step through the rest without closing and re-opening the viewer.
"""
from __future__ import annotations

from ..qt import QtWidgets, QtCore, QtGui
from ..utils.placeholder_images import make_placeholder_pixmap


class FullScreenImageViewer(QtWidgets.QDialog):
    def __init__(self, image_labels: list[str], current_index: int = 0, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Image Viewer")
        self.setModal(True)
        self.resize(900, 700)

        self._labels = image_labels
        self._index = max(0, min(current_index, len(image_labels) - 1))

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        image_row = QtWidgets.QHBoxLayout()

        self.prev_btn = QtWidgets.QPushButton("<")
        self.prev_btn.setFixedWidth(48)
        self.prev_btn.clicked.connect(self._go_prev)
        image_row.addWidget(self.prev_btn)

        self._image_label = QtWidgets.QLabel()
        self._image_label.setAlignment(QtCore.Qt.AlignCenter)
        self._image_label.setStyleSheet("background-color: black;")
        image_row.addWidget(self._image_label, 1)

        self.next_btn = QtWidgets.QPushButton(">")
        self.next_btn.setFixedWidth(48)
        self.next_btn.clicked.connect(self._go_next)
        image_row.addWidget(self.next_btn)

        layout.addLayout(image_row, 1)

        self._counter_label = QtWidgets.QLabel()
        self._counter_label.setAlignment(QtCore.Qt.AlignCenter)
        self._counter_label.setStyleSheet("color: #aaa; padding: 6px; background: black;")
        layout.addWidget(self._counter_label)

        self._refresh()

    def _refresh(self) -> None:
        label_text = self._labels[self._index]
        pixmap = make_placeholder_pixmap(label_text, width=900, height=700, seed=label_text)
        self._image_label.setPixmap(pixmap.scaled(
            self._image_label.size(), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation
        ))
        self._counter_label.setText(f"{label_text}   ({self._index + 1} / {len(self._labels)})")
        self.prev_btn.setEnabled(self._index > 0)
        self.next_btn.setEnabled(self._index < len(self._labels) - 1)

    def _go_prev(self) -> None:
        if self._index > 0:
            self._index -= 1
            self._refresh()

    def _go_next(self) -> None:
        if self._index < len(self._labels) - 1:
            self._index += 1
            self._refresh()

    def resizeEvent(self, event):
        self._refresh()
        super().resizeEvent(event)

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            self.close()
        elif event.key() == QtCore.Qt.Key_Left:
            self._go_prev()
        elif event.key() == QtCore.Qt.Key_Right:
            self._go_next()
        else:
            super().keyPressEvent(event)
