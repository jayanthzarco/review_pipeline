"""
Version card widgets, matching the sketch's "Version Card" / "Master
Version" / "Previous Versions" boxes.

Two pieces:
- VersionListItemWidget: compact row used in the Versions tab's left
  rail (the small "Version card" boxes in the sketch's Version Tab).
- VersionDetailPanel: the wide detail strip (thumbnail + two side-by-side
  field columns) used for the selected version in the Versions tab, and
  for the Master Version / Previous Versions cards in the Activity tab.
  Layout fixed per feedback: originally this stacked all six fields in
  one vertical QFormLayout next to the thumbnail; the sketch instead
  wants ONE WIDE horizontal strip — thumbnail, then a
  Project/Artist/Date column, then a Status/Task_name/Task_type column,
  side by side across the card's width.
"""
from __future__ import annotations

from typing import Optional

from ..qt import QtWidgets, QtCore
from ..utils.placeholder_images import make_placeholder_pixmap
from ...core import models

STATUS_OPTIONS = [
    "Ready to Start", "In Progress", "Ready for Review",
    "Lead Review", "Approved", "artist published",
]


class VersionListItemWidget(QtWidgets.QWidget):
    """One row in a version list: thumbnail + name + status pill."""

    def __init__(self, version: models.Version, parent=None):
        super().__init__(parent)
        self.version = version

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        thumb = QtWidgets.QLabel()
        thumb.setPixmap(make_placeholder_pixmap(version.name, width=64, height=36, seed=version.id))
        layout.addWidget(thumb)

        text_col = QtWidgets.QVBoxLayout()
        name_label = QtWidgets.QLabel(version.display_name)
        name_label.setStyleSheet("font-weight: bold;")
        meta_label = QtWidgets.QLabel(f"{version.artist or ''}  ·  {version.status or ''}")
        meta_label.setStyleSheet("color: #888; font-size: 11px;")
        text_col.addWidget(name_label)
        text_col.addWidget(meta_label)
        layout.addLayout(text_col)
        layout.addStretch()


class VersionDetailPanel(QtWidgets.QFrame):
    """Wide detail strip: thumbnail | Project/Artist/Date | Status/Task
    name/Task type — one horizontal row spanning the card's width, per
    the sketch (Image 1 / Image 2's Master Version & Previous Version
    boxes), rather than a single stacked vertical field list."""

    status_changed = QtCore.Signal(object, str, str)  # version, old_status, new_status

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self._version: Optional[models.Version] = None
        self._suppress_status_signal = False

        root = QtWidgets.QHBoxLayout(self)

        # Thumbnail
        self.thumb_label = QtWidgets.QLabel()
        self.thumb_label.setFixedSize(150, 90)
        self.thumb_label.setScaledContents(True)
        root.addWidget(self.thumb_label)

        # Title, above the two field columns
        title_and_columns = QtWidgets.QVBoxLayout()
        self.title_label = QtWidgets.QLabel()
        self.title_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        title_and_columns.addWidget(self.title_label)

        columns_row = QtWidgets.QHBoxLayout()

        # Column 1: Project / Artist / Date
        col1 = QtWidgets.QFormLayout()
        self.project_label = QtWidgets.QLabel()
        self.artist_label = QtWidgets.QLabel()
        self.date_label = QtWidgets.QLabel()
        col1.addRow("Project:", self.project_label)
        col1.addRow("Artist:", self.artist_label)
        col1.addRow("Date:", self.date_label)
        columns_row.addLayout(col1)

        columns_row.addSpacing(24)

        # Column 2: Status / Task name / Task type
        col2 = QtWidgets.QFormLayout()
        self.status_combo = QtWidgets.QComboBox()
        self.status_combo.addItems(STATUS_OPTIONS)
        self.status_combo.currentTextChanged.connect(self._on_status_changed)
        self.task_name_label = QtWidgets.QLabel()
        self.task_type_label = QtWidgets.QLabel()
        col2.addRow("Status:", self.status_combo)
        col2.addRow("Task name:", self.task_name_label)
        col2.addRow("Task type:", self.task_type_label)
        columns_row.addLayout(col2)

        columns_row.addStretch()
        title_and_columns.addLayout(columns_row)

        root.addLayout(title_and_columns)
        root.addStretch()

    @property
    def version(self) -> Optional[models.Version]:
        return self._version

    def set_version(self, version: models.Version, task_name: str = "", task_type: str = "") -> None:
        self._version = version
        self._suppress_status_signal = True

        self.thumb_label.setPixmap(make_placeholder_pixmap(version.display_name, width=150, height=90, seed=version.id))
        self.title_label.setText(version.display_name)
        self.project_label.setText(version.project or "")
        self.artist_label.setText(version.artist or "")
        self.date_label.setText(version.updated_at or "")
        if version.status and version.status not in STATUS_OPTIONS:
            self.status_combo.addItem(version.status)
        self.status_combo.setCurrentText(version.status or "")
        self.task_name_label.setText(task_name)
        self.task_type_label.setText(task_type)

        self._suppress_status_signal = False

    def _on_status_changed(self, new_status: str) -> None:
        if self._suppress_status_signal or self._version is None:
            return
        old_status = self._version.status
        self._version.status = new_status
        self.status_changed.emit(self._version, old_status, new_status)
