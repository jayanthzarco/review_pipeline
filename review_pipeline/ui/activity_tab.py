"""
Activity Tab — flattened per feedback into ONE single scrollable column,
no left rail / right main-area split. Top to bottom:

    1. Master Version  — VersionDetailPanel, same widget as the Versions
       tab (thumbnail + Project/Artist/Date + Status/Task name/Task type).
    2. Previous Version(s) — PreviousVersionCard, smaller, only 4 fields
       (title/Artist/Status/Date) since Project/Task info is already on
       Master. Click-to-select (highlighted border) instead of a
       checkbox, so multiple can still be selected for "Compare vXXX |
       vYYY" on right-click.
    3. Activity feed — status-change lines + full comment entries
       (author, clickable [version tag], text, click-to-enlarge images).
       This is now the ONLY comment list — the earlier compact rail
       comment-index is gone, not duplicated.
    4. Text Field + Submit — one composer, at the bottom of this column.

There is now only one Status control (Master's own dropdown) — the
earlier separate rail "Status Change" combo was a duplicate of it and
has been removed; changing Master's status still logs a feed entry.
Changing a Previous Version's own status combo also logs a feed entry,
attributed to that version by name so it isn't ambiguous with Master's.

`ayon_service` needs `get_previous_versions(project, version)` and
`get_activity_feed(project, version)` beyond the base AyonService — only
DummyAyonService implements them for now; wiring real AYON activity/
comment queries is still deferred.
"""
from __future__ import annotations

from typing import Optional

from .qt import QtWidgets, QtCore
from .widgets.version_card import VersionDetailPanel
from .widgets.previous_version_card import PreviousVersionCard
from .widgets.clickable_label import ClickableImageLabel
from .widgets.image_viewer import FullScreenImageViewer
from .widgets.loading_overlay import LoadingOverlay
from ..core import models
from ..workers.query_worker import Worker


class ActivityTab(QtWidgets.QWidget):
    timeline_action_requested = QtCore.Signal(str, list)  # action, list[models.Version]

    def __init__(self, ayon_service, parent=None):
        super().__init__(parent)
        self.ayon = ayon_service
        self._master_version: Optional[models.Version] = None
        self._previous_cards: list[PreviousVersionCard] = []
        self._thread_pool = QtCore.QThreadPool.globalInstance()
        self._active_workers: list[Worker] = []
        self._build_ui()
        self._overlay = LoadingOverlay(self)

    # ── UI construction ──────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QtWidgets.QVBoxLayout(self)

        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.container = QtWidgets.QWidget()
        self.container_layout = QtWidgets.QVBoxLayout(self.container)

        master_label = QtWidgets.QLabel("Master Version")
        master_label.setStyleSheet("font-weight: bold;")
        self.master_panel = VersionDetailPanel()
        self.master_panel.status_changed.connect(self._on_master_status_changed)
        self.container_layout.addWidget(master_label)
        self.container_layout.addWidget(self.master_panel)

        feed_label = QtWidgets.QLabel("Activity")
        feed_label.setStyleSheet("font-weight: bold; margin-top: 8px;")
        self.container_layout.addWidget(feed_label)
        self.feed_container = QtWidgets.QWidget()
        self.feed_layout = QtWidgets.QVBoxLayout(self.feed_container)
        self.feed_layout.addStretch()
        self.container_layout.addWidget(self.feed_container)

        self.container_layout.addStretch()
        self.scroll.setWidget(self.container)
        root.addWidget(self.scroll, 1)

        composer_row = QtWidgets.QHBoxLayout()
        self.comment_input = QtWidgets.QLineEdit()
        self.comment_input.setPlaceholderText("Submit new annotation for this version…")
        self.submit_btn = QtWidgets.QPushButton("Submit")
        self.submit_btn.clicked.connect(self._on_submit_comment)
        composer_row.addWidget(self.comment_input)
        composer_row.addWidget(self.submit_btn)
        root.addLayout(composer_row)

    # ── Loading a version's activity (background — see Worker below) ──

    def load_for_version(self, version: models.Version) -> None:
        self._master_version = version
        self.master_panel.set_version(version, task_name=version.task_id or "", task_type="")

        self._overlay.show_overlay("Loading activity…")

        worker = Worker(self.ayon.get_activity_feed, version.project, version)
        self._active_workers.append(worker)

        def _cleanup():
            if worker in self._active_workers:
                self._active_workers.remove(worker)
            self._overlay.complete_and_hide()

        worker.signals.result.connect(self._render_feed)
        worker.signals.error.connect(lambda msg: self._overlay.hide_overlay())
        worker.signals.finished.connect(_cleanup)
        self._thread_pool.start(worker)

    # ── Feed rendering — version publishes, status changes, and
    #    comments all interleaved in one chronological list ─────────

    def _render_feed(self, feed_items: list[models.ActivityItem]) -> None:
        while self.feed_layout.count() > 1:  # keep the trailing stretch
            item = self.feed_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self._previous_cards = []

        for entry in sorted(feed_items, key=lambda e: e.order):
            self.feed_layout.insertWidget(self.feed_layout.count() - 1, self._build_feed_widget(entry))

    def _build_feed_widget(self, entry: models.ActivityItem) -> QtWidgets.QWidget:
        if entry.kind == "version":
            card = PreviousVersionCard(entry.payload["version"])
            card.context_menu_requested.connect(lambda pos, c=card: self._on_previous_context_menu(c, pos))
            card.status_changed.connect(self._on_previous_status_changed)
            self._previous_cards.append(card)
            return card

        if entry.kind == "status":
            p = entry.payload
            subject = f" ({p['subject']})" if p.get("subject") else ""
            label = QtWidgets.QLabel(f"{p['author']} changed status{subject} from {p['from_status']} ---> {p['to_status']}")
            label.setStyleSheet("color: #888; font-size: 11px; padding: 4px 2px;")
            return label

        p = entry.payload
        box = QtWidgets.QFrame()
        box.setFrameShape(QtWidgets.QFrame.StyledPanel)
        layout = QtWidgets.QVBoxLayout(box)

        header_row = QtWidgets.QHBoxLayout()
        header = QtWidgets.QLabel(f"<b>{p['author']}</b>")
        header_row.addWidget(header)
        header_row.addWidget(self._make_version_tag_button(p.get("version_tag")))
        header_row.addStretch()
        layout.addLayout(header_row)

        text_label = QtWidgets.QLabel(p["text"])
        text_label.setWordWrap(True)
        layout.addWidget(text_label)

        if p.get("images"):
            img_row = QtWidgets.QHBoxLayout()
            images = p["images"]
            for idx, img_label in enumerate(images):
                thumb = ClickableImageLabel(img_label)
                thumb.clicked.connect(lambda i=idx, imgs=images: self._open_image_viewer(imgs, i))
                img_row.addWidget(thumb)
            img_row.addStretch()
            layout.addLayout(img_row)

        return box

    def _make_version_tag_button(self, version_tag: Optional[str]) -> QtWidgets.QPushButton:
        btn = QtWidgets.QPushButton(f"[{version_tag}]" if version_tag else "[None]")
        btn.setFlat(True)
        btn.setCursor(QtCore.Qt.PointingHandCursor)
        btn.setStyleSheet(
            "QPushButton { color: #2a6fbb; border: none; font-weight: bold; text-align: left; padding: 0; }"
            "QPushButton:hover { text-decoration: underline; }"
        )
        if version_tag:
            btn.clicked.connect(lambda: self._highlight_version(version_tag))
        else:
            btn.setEnabled(False)
        return btn

    def _open_image_viewer(self, images: list[str], index: int = 0) -> None:
        viewer = FullScreenImageViewer(images, index, parent=self)
        viewer.exec()

    # ── Highlighting: clicking a version tag scrolls to / flashes the
    #    corresponding card in this same column ──────────────────────

    def _highlight_version(self, version_ref: str) -> None:
        if self._master_version and version_ref in (self._master_version.name, self._master_version.id):
            self.scroll.ensureWidgetVisible(self.master_panel)
            self.master_panel.setStyleSheet("VersionDetailPanel { border: 2px solid #4098e8; border-radius: 4px; }")
            QtCore.QTimer.singleShot(1200, lambda: self.master_panel.setStyleSheet(""))
            return
        for card in self._previous_cards:
            if version_ref in (card.version.name, card.version.id):
                self.scroll.ensureWidgetVisible(card)
                card.set_highlighted(True)
                QtCore.QTimer.singleShot(1200, lambda c=card: c.set_highlighted(False))
                return

    # ── Comment submission ───────────────────────────────────────

    def _on_submit_comment(self) -> None:
        text = self.comment_input.text().strip()
        if not text or self._master_version is None:
            return
        entry = models.ActivityItem(
            kind="comment",
            order=10_000_000,
            payload={
                "author": "You",
                "version_tag": self._master_version.name,
                "text": text,
                "images": ["Annotation 1"],
            },
        )
        self.feed_layout.insertWidget(self.feed_layout.count() - 1, self._build_feed_widget(entry))
        self.comment_input.clear()

    # ── Status changes (Master's own combo; Previous cards' own combo) ─

    def _on_master_status_changed(self, version: models.Version, old_status: str, new_status: str) -> None:
        self._log_status_change(version, "You", old_status, new_status)

    def _on_previous_status_changed(self, version: models.Version, old_status: str, new_status: str) -> None:
        self._log_status_change(version, "You", old_status, new_status)

    def _log_status_change(self, version: models.Version, author: str, old_status: str, new_status: str) -> None:
        entry = models.ActivityItem(
            kind="status",
            order=10_000_001,
            payload={
                "author": author,
                "from_status": old_status,
                "to_status": new_status,
                "subject": None if version is self._master_version else version.display_name,
            },
        )
        self.feed_layout.insertWidget(self.feed_layout.count() - 1, self._build_feed_widget(entry))

    # ── Previous versions right-click menu ───────────────────────

    def _on_previous_context_menu(self, card: PreviousVersionCard, pos: QtCore.QPoint) -> None:
        selected = [c.version for c in self._previous_cards if c.is_selected()] or [card.version]

        menu = QtWidgets.QMenu(self)
        load_menu = menu.addMenu("Load To TimeLine")
        load_menu.addAction("Frames", lambda: self.timeline_action_requested.emit("load_frames", selected))
        load_menu.addAction("Mov", lambda: self.timeline_action_requested.emit("load_mov", selected))
        load_menu.addAction("Both", lambda: self.timeline_action_requested.emit("load_both", selected))
        menu.addAction("Compare with Input", lambda: self.timeline_action_requested.emit("compare_with_input", selected))

        if len(selected) > 1:
            label = "Compare " + " | ".join(v.name for v in selected)
            compare_menu = menu.addMenu(label)
            compare_menu.addAction("Frames", lambda: self.timeline_action_requested.emit("compare_versions_frames", selected))
            compare_menu.addAction("Mov", lambda: self.timeline_action_requested.emit("compare_versions_mov", selected))

        menu.exec(card.mapToGlobal(pos))
