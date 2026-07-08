"""
Compact card for the Activity tab's Previous Versions.

Smaller than VersionDetailPanel and shows only 4 fields — title, Artist,
Status, Date — since Project/Task name/Task type are already visible on
the Master Version card above it; showing them again on every previous
version would just repeat the same three values.

Selection is click-to-toggle (highlighted border) rather than a
checkbox, per feedback — clicking the card body selects/deselects it;
clicking the Status combo still works normally since it's a child
widget and gets the mouse event first. Multiple cards can be selected
this way so the right-click menu's "Compare vXXX | vYYY" option (see
ActivityTab) still works without a visible checkbox.
"""
from __future__ import annotations

from ..qt import QtWidgets, QtCore
from ..utils.placeholder_images import make_placeholder_pixmap
from .version_card import STATUS_OPTIONS
from ...core import models


class PreviousVersionCard(QtWidgets.QFrame):
    context_menu_requested = QtCore.Signal(QtCore.QPoint)
    selection_changed = QtCore.Signal()
    status_changed = QtCore.Signal(object, str, str)  # version, old_status, new_status

    def __init__(self, version: models.Version, parent=None):
        super().__init__(parent)
        self.version = version
        self._selected = False

        self.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.context_menu_requested)
        self.setCursor(QtCore.Qt.PointingHandCursor)

        layout = QtWidgets.QHBoxLayout(self)

        self.thumb_label = QtWidgets.QLabel()
        self.thumb_label.setFixedSize(90, 54)
        self.thumb_label.setScaledContents(True)
        self.thumb_label.setPixmap(make_placeholder_pixmap(version.name, width=90, height=54, seed=version.id))
        layout.addWidget(self.thumb_label)

        text_col = QtWidgets.QVBoxLayout()
        title = QtWidgets.QLabel(f"Version ({version.name})")
        title.setStyleSheet("font-weight: bold;")
        text_col.addWidget(title)

        columns_row = QtWidgets.QHBoxLayout()

        col1 = QtWidgets.QFormLayout()
        self.artist_label = QtWidgets.QLabel(version.artist or "")
        col1.addRow("Artist:", self.artist_label)
        columns_row.addLayout(col1)
        columns_row.addSpacing(24)

        col2 = QtWidgets.QFormLayout()
        self.status_combo = QtWidgets.QComboBox()
        self.status_combo.addItems(STATUS_OPTIONS)
        if version.status and version.status not in STATUS_OPTIONS:
            self.status_combo.addItem(version.status)
        self.status_combo.setCurrentText(version.status or "")
        self.status_combo.currentTextChanged.connect(self._on_status_changed)
        self.date_label = QtWidgets.QLabel(version.updated_at or "")
        col2.addRow("Status:", self.status_combo)
        col2.addRow("Date:", self.date_label)
        columns_row.addLayout(col2)
        columns_row.addStretch()

        text_col.addLayout(columns_row)

        layout.addLayout(text_col)
        layout.addStretch()

    def is_selected(self) -> bool:
        return self._selected

    def set_selected(self, selected: bool) -> None:
        self._selected = selected
        self.setStyleSheet(
            "PreviousVersionCard { border: 2px solid #4098e8; border-radius: 4px; }" if selected else ""
        )

    def set_highlighted(self, on: bool) -> None:
        """Temporary flash used by version-tag click-to-highlight,
        distinct from the persistent selection border above."""
        if not self._selected:
            self.setStyleSheet(
                "PreviousVersionCard { border: 2px solid #e8a040; border-radius: 4px; }" if on else ""
            )

    def mousePressEvent(self, event) -> None:
        if event.button() == QtCore.Qt.LeftButton:
            self.set_selected(not self._selected)
            self.selection_changed.emit()
        super().mousePressEvent(event)

    def _on_status_changed(self, new_status: str) -> None:
        old_status = self.version.status
        if old_status == new_status:
            return
        self.version.status = new_status
        self.status_changed.emit(self.version, old_status, new_status)
