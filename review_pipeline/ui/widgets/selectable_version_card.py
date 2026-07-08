"""
Wraps VersionDetailPanel with a selection checkbox — used for the
Activity tab's Previous Versions, where the sketch's right-click menu
shows "Compare vXXX | vYYY" only once more than one card is selected.
QListWidget's built-in selection no longer applies here since each
previous version is now its own wide detail card (matching the sketch)
rather than a compact list row.
"""
from __future__ import annotations

from ..qt import QtWidgets, QtCore
from .version_card import VersionDetailPanel
from ...core import models


class SelectableVersionCard(QtWidgets.QFrame):
    context_menu_requested = QtCore.Signal(QtCore.QPoint)
    selection_changed = QtCore.Signal()

    def __init__(self, version: models.Version, parent=None):
        super().__init__(parent)
        self.version = version
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.context_menu_requested)

        self.checkbox = QtWidgets.QCheckBox()
        self.checkbox.setToolTip("Select for compare")
        self.checkbox.toggled.connect(lambda _checked: self.selection_changed.emit())

        self.detail = VersionDetailPanel()
        self.detail.set_version(version, task_name=version.task_id or "", task_type="")

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.addWidget(self.checkbox, 0, QtCore.Qt.AlignTop)
        layout.addWidget(self.detail, 1)

    def is_selected(self) -> bool:
        return self.checkbox.isChecked()

    def set_highlighted(self, on: bool) -> None:
        self.setStyleSheet(
            "SelectableVersionCard { border: 2px solid #4098e8; border-radius: 4px; }" if on else ""
        )
