"""
Versions Tab — matches the sketch's "Version Tab" section.

Updated per feedback: the earlier design (a compact list rail on the
left + a single shared detail panel on the right, switching per
selection) is replaced with ONE COLUMN of full-width VersionDetailPanel
cards, stacked top to bottom — each card always shows its own version's
data, no left/right split. Same visual language as the Activity tab's
Previous Versions.

Nuke Studio integration (the actual "load to timeline" / "compare" file
loading) is still deferred — see the HostAdapter discussion. Those
actions surface via `timeline_action_requested` so a host adapter can be
wired in later without touching this file.
"""
from __future__ import annotations

from typing import Optional

from .qt import QtWidgets, QtCore
from .widgets.version_card import VersionDetailPanel
from .widgets.loading_overlay import LoadingOverlay
from ..core import models


class VersionsTab(QtWidgets.QWidget):
    activity_requested = QtCore.Signal(object)            # models.Version
    timeline_action_requested = QtCore.Signal(str, list)   # action name, list[models.Version]
    status_changed = QtCore.Signal(object, str, str)       # version, old_status, new_status

    def __init__(self, parent=None):
        super().__init__(parent)
        self._versions: list[models.Version] = []
        self._cards: list[VersionDetailPanel] = []
        self._build_ui()
        self._overlay = LoadingOverlay(self)

    def _build_ui(self) -> None:
        root = QtWidgets.QVBoxLayout(self)

        self.empty_label = QtWidgets.QLabel("Load versions from the Options tab to see them here.")
        self.empty_label.setStyleSheet("color: #888;")
        root.addWidget(self.empty_label)

        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.hide()

        self.container = QtWidgets.QWidget()
        self.container_layout = QtWidgets.QVBoxLayout(self.container)
        self.container_layout.addStretch()
        self.scroll.setWidget(self.container)

        root.addWidget(self.scroll)

    # ── Loading visual (driven by OptionsTab.load_progress via
    #    MainWindow — see the architecture explanation) ──────────────

    def show_loading(self, message: str = "Loading…") -> None:
        self._overlay.show_overlay(message)

    def set_loading_progress(self, percent: int, message: Optional[str] = None) -> None:
        self._overlay.set_progress(percent, message)

    def hide_loading(self) -> None:
        self._overlay.complete_and_hide()

    # ── Population ───────────────────────────────────────────────

    def set_versions(self, versions: list[models.Version]) -> None:
        self.hide_loading()
        self._versions = list(versions)

        while self.container_layout.count() > 1:  # keep the trailing stretch
            item = self.container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._cards = []

        for version in self._versions:
            card = VersionDetailPanel()
            card.set_version(version, task_name=version.task_id or "", task_type="")
            card.status_changed.connect(self.status_changed)
            card.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
            card.customContextMenuRequested.connect(lambda pos, c=card: self._on_context_menu(c, pos))
            self.container_layout.insertWidget(self.container_layout.count() - 1, card)
            self._cards.append(card)

        self.empty_label.setVisible(not self._versions)
        self.scroll.setVisible(bool(self._versions))

    def clear_version(self, version: models.Version) -> None:
        """Removes one card — the sketch's right-click 'Clear' action."""
        for card in list(self._cards):
            if card.version is not None and card.version.id == version.id:
                self.container_layout.removeWidget(card)
                card.deleteLater()
                self._cards.remove(card)
        self._versions = [v for v in self._versions if v.id != version.id]
        if not self._versions:
            self.scroll.hide()
            self.empty_label.show()

    # ── Right-click menu (per card, no multi-select in this tab) ────

    def _on_context_menu(self, card: VersionDetailPanel, pos: QtCore.QPoint) -> None:
        version = card.version
        if version is None:
            return

        menu = QtWidgets.QMenu(self)
        load_menu = menu.addMenu("Load To TimeLine")
        load_menu.addAction("Frames", lambda: self.timeline_action_requested.emit("load_frames", [version]))
        load_menu.addAction("Mov", lambda: self.timeline_action_requested.emit("load_mov", [version]))
        load_menu.addAction("Both", lambda: self.timeline_action_requested.emit("load_both", [version]))

        menu.addAction("Compare with Input", lambda: self.timeline_action_requested.emit("compare_with_input", [version]))
        menu.addAction("Load Activity", lambda: self.activity_requested.emit(version))
        menu.addSeparator()
        menu.addAction("Clear", lambda: self.clear_version(version))

        menu.exec(card.mapToGlobal(pos))
