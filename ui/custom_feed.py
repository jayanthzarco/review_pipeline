try:
    from PySide2 import QtWidgets, QtCore, QtGui
except ImportError:
    from PySide6 import QtWidgets, QtCore, QtGui

STATUSES = ["In Review", "Lead Review", "Approved", "Retake"]


# ─────────────────────────────────────────────
#  Version Card Widget
# ─────────────────────────────────────────────

class VersionCardWidget(QtWidgets.QWidget):
    """
    compact=False      full card (Versions tab + Activity header)
    compact=True       smaller card (Activity feed previous versions)
    status_editable    status field is a QComboBox
    """

    status_changed = QtCore.Signal(str, str)  # (version_name, new_status)

    THUMB_FULL = QtCore.QSize(120, 100)
    THUMB_COMPACT = QtCore.QSize(72, 60)

    def __init__(self, data: dict, parent=None,
                 compact=False, status_editable=False):
        super().__init__(parent)
        self.data = data
        self.compact = compact
        self.status_editable = status_editable
        self._build_ui()

    def _build_ui(self):
        root = QtWidgets.QHBoxLayout(self)
        m = 4 if self.compact else 8
        root.setContentsMargins(m, m, m, m)
        root.setSpacing(8)

        thumb_size = self.THUMB_COMPACT if self.compact else self.THUMB_FULL
        self.thumbnail_label = QtWidgets.QLabel()
        self.thumbnail_label.setFixedWidth(thumb_size.width())
        self.thumbnail_label.setMinimumHeight(thumb_size.height())
        self.thumbnail_label.setAlignment(QtCore.Qt.AlignCenter)
        self._set_thumbnail(self.data.get("thumbnail_path"), thumb_size)
        root.addWidget(self.thumbnail_label)

        right = QtWidgets.QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(2)

        name_lbl = QtWidgets.QLabel(self.data.get("version_name", ""))
        f = name_lbl.font()
        f.setBold(True)
        if self.compact:
            f.setPointSize(f.pointSize() - 1)
        name_lbl.setFont(f)
        right.addWidget(name_lbl)

        form = QtWidgets.QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(2)
        form.setLabelAlignment(QtCore.Qt.AlignRight)

        for key, label in [("project", "Project"),
                           ("artist", "Artist"),
                           ("date", "Date")]:
            val = QtWidgets.QLabel(str(self.data.get(key, "")))
            if self.compact:
                vf = val.font()
                vf.setPointSize(vf.pointSize() - 1)
                val.setFont(vf)
            form.addRow(label + ":", val)

        if self.status_editable:
            self.status_combo = QtWidgets.QComboBox()
            self.status_combo.addItems(STATUSES)
            cur = self.data.get("status", STATUSES[0])
            idx = self.status_combo.findText(cur)
            if idx >= 0:
                self.status_combo.setCurrentIndex(idx)
            self.status_combo.currentTextChanged.connect(
                lambda t: self.status_changed.emit(
                    self.data.get("version_name", ""), t))
            form.addRow("Status:", self.status_combo)
        else:
            form.addRow("Status:", QtWidgets.QLabel(
                self.data.get("status", "")))

        right.addLayout(form)
        right.addStretch()
        root.addLayout(right)

    def _set_thumbnail(self, src, size):
        pixmap = QtGui.QPixmap()
        loaded = False
        if isinstance(src, (bytes, bytearray)):
            loaded = pixmap.loadFromData(src)
        elif isinstance(src, str) and src:
            loaded = pixmap.load(src)

        if loaded and not pixmap.isNull():
            self.thumbnail_label.setPixmap(
                pixmap.scaled(size, QtCore.Qt.KeepAspectRatio,
                              QtCore.Qt.SmoothTransformation))
            return

        ph = QtGui.QPixmap(size)
        ph.fill(QtGui.QColor(80, 80, 80))
        painter = QtGui.QPainter(ph)
        painter.setPen(QtGui.QColor(180, 180, 180))
        painter.setFont(QtGui.QFont("Arial", 12 if self.compact else 20))
        painter.drawText(ph.rect(), QtCore.Qt.AlignCenter, "?")
        painter.end()
        self.thumbnail_label.setPixmap(ph)


# ─────────────────────────────────────────────
#  Image Viewer Dialog
# ─────────────────────────────────────────────

class ImageViewerDialog(QtWidgets.QDialog):
    """
    Full-size image viewer with prev/next navigation.
    Keyboard: Left/Right to navigate, Esc to close.
    """

    def __init__(self, pixmaps: list, start_index: int = 0, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Image Viewer")
        self.setWindowFlags(
            self.windowFlags() | QtCore.Qt.WindowMaximizeButtonHint)
        self._pixmaps = pixmaps
        self._index = start_index
        self._build_ui()
        self._show_current()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        self._counter = QtWidgets.QLabel()
        self._counter.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(self._counter)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(False)
        scroll.setAlignment(QtCore.Qt.AlignCenter)
        self._img_lbl = QtWidgets.QLabel()
        self._img_lbl.setAlignment(QtCore.Qt.AlignCenter)
        scroll.setWidget(self._img_lbl)
        layout.addWidget(scroll, 1)

        btn_row = QtWidgets.QHBoxLayout()

        self._prev_btn = QtWidgets.QPushButton("← Prev")
        self._prev_btn.setFixedWidth(80)
        self._prev_btn.clicked.connect(self._go_prev)
        btn_row.addWidget(self._prev_btn)

        btn_row.addStretch()

        close_btn = QtWidgets.QPushButton("Close")
        close_btn.setFixedWidth(80)
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)

        btn_row.addStretch()

        self._next_btn = QtWidgets.QPushButton("Next →")
        self._next_btn.setFixedWidth(80)
        self._next_btn.clicked.connect(self._go_next)
        btn_row.addWidget(self._next_btn)

        layout.addLayout(btn_row)

        screen = QtWidgets.QApplication.primaryScreen().availableGeometry()
        self._max_w = int(screen.width() * 0.80)
        self._max_h = int(screen.height() * 0.80)
        self.resize(self._max_w, self._max_h)

    def _show_current(self):
        total = len(self._pixmaps)
        pixmap = self._pixmaps[self._index]
        self._counter.setText(f"{self._index + 1} / {total}")
        scaled = pixmap.scaled(
            self._max_w - 40, self._max_h - 120,
            QtCore.Qt.KeepAspectRatio,
            QtCore.Qt.SmoothTransformation)
        self._img_lbl.setPixmap(scaled)
        self._img_lbl.resize(scaled.size())
        self._prev_btn.setEnabled(self._index > 0)
        self._next_btn.setEnabled(self._index < total - 1)

    def _go_prev(self):
        if self._index > 0:
            self._index -= 1
            self._show_current()

    def _go_next(self):
        if self._index < len(self._pixmaps) - 1:
            self._index += 1
            self._show_current()

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            self.accept()
        elif event.key() == QtCore.Qt.Key_Left:
            self._go_prev()
        elif event.key() == QtCore.Qt.Key_Right:
            self._go_next()
        else:
            super().keyPressEvent(event)


# ─────────────────────────────────────────────
#  Version Feed Item
# ─────────────────────────────────────────────

class VersionFeedItem(QtWidgets.QFrame):
    """
    Selectable compact version card for the activity feed.
    Wraps VersionCardWidget with highlight + selection state.

    Expected data format:
    {
        "version_name":   "shot_001_v003",
        "project":        "PROJ_NAME",
        "artist":         "Artist Name",
        "status":         "In Review",
        "date":           "2025-07-19 14:30",
        "thumbnail_path": None or path/bytes/QPixmap,
        "mov_path":       "/path/to/render.mov"
    }
    """

    def __init__(self, data: dict, parent=None):
        super().__init__(parent)
        self.data = data
        self.selected = False
        self.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.setAutoFillBackground(True)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(
            VersionCardWidget(data, compact=True, status_editable=False))

    def set_selected(self, selected: bool):
        self.selected = selected
        palette = self.palette()
        color = (QtGui.QPalette.Highlight if selected
                 else QtGui.QPalette.Window)
        palette.setColor(
            QtGui.QPalette.Window,
            self.style().standardPalette().color(color))
        self.setPalette(palette)
        self.update()

    def mousePressEvent(self, event):
        """Pass left-clicks up. Block right-clicks from bubbling to avoid deselection."""
        if event.button() == QtCore.Qt.RightButton:
            event.accept()
            return
        super().mousePressEvent(event)

    def get_version_data(self) -> dict:
        return self.data


# ─────────────────────────────────────────────
#  Status Change Feed Item
# ─────────────────────────────────────────────

class StatusChangeFeedItem(QtWidgets.QWidget):
    """
    ── status change text ──

    Accepts either:
      from_status + to_status  →  "Status changed: X → Y  (date)"
      body                     →  full body text as-is  (date)

    Data format:
    {
        "from_status": "In Review",   # used if body is empty
        "to_status":   "Approved",
        "date":        "2025-07-19 14:30",
        "body":        ""             # optional — overrides from/to if set
    }
    """

    def __init__(self, data: dict, parent=None):
        super().__init__(parent)
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(8, 2, 8, 2)
        layout.setSpacing(6)

        left = QtWidgets.QFrame()
        left.setFrameShape(QtWidgets.QFrame.HLine)
        layout.addWidget(left, 1)

        body = data.get("body", "")
        date = data.get("date", "")
        if body:
            text = f"{body}  ({date})" if date else body
        else:
            text = (f"Status changed:  {data.get('from_status', '')}  →  "
                    f"{data.get('to_status', '')}  ({date})")

        lbl = QtWidgets.QLabel(text)
        f = lbl.font()
        f.setPointSize(f.pointSize() - 1)
        f.setItalic(True)
        lbl.setFont(f)
        lbl.setWordWrap(True)
        layout.addWidget(lbl)

        right = QtWidgets.QFrame()
        right.setFrameShape(QtWidgets.QFrame.HLine)
        layout.addWidget(right, 1)


# ─────────────────────────────────────────────
#  Comment Feed Item
# ─────────────────────────────────────────────

class CommentFeedItem(QtWidgets.QWidget):
    """
    [Avatar]  Author   VERSION TAG   Date
              Comment text
              [image thumbnails — 0 to N]

    Data format:
    {
        "author":      "John Doe",
        "version_tag": "v003",
        "date":        "2025-07-19 14:30",
        "text":        "Comment text here",
        "image_paths": []   # list of: str path | bytes | QPixmap
    }
    """

    def __init__(self, data: dict, parent=None):
        super().__init__(parent)
        self._build_ui(data)

    def _build_ui(self, c):
        root = QtWidgets.QHBoxLayout(self)
        root.setContentsMargins(8, 4, 8, 4)
        root.setSpacing(8)
        root.setAlignment(QtCore.Qt.AlignTop)

        root.addWidget(self._make_avatar(c.get("author", "?")),
                       0, QtCore.Qt.AlignTop)

        right = QtWidgets.QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(4)

        # ── Header: author + version badge + date ──
        hrow = QtWidgets.QHBoxLayout()
        hrow.setSpacing(6)

        author_lbl = QtWidgets.QLabel(c.get("author", ""))
        af = author_lbl.font()
        af.setBold(True)
        author_lbl.setFont(af)
        hrow.addWidget(author_lbl)

        version_tag = c.get("version_tag", "")
        if version_tag:
            badge = QtWidgets.QLabel(version_tag)
            badge.setFrameShape(QtWidgets.QFrame.Box)
            bf = badge.font()
            bf.setPointSize(bf.pointSize() - 2)
            bf.setBold(True)
            badge.setFont(bf)
            badge.setContentsMargins(3, 1, 3, 1)
            hrow.addWidget(badge)

        raw_date = c.get("date", "")
        try:
            from datetime import datetime
            dt = datetime.strptime(raw_date, "%Y-%m-%d %H:%M")
            display_date = dt.strftime("%d %b %Y, %I:%M %p")
        except (ValueError, TypeError):
            display_date = raw_date
        date_lbl = QtWidgets.QLabel(display_date)
        df = date_lbl.font()
        df.setPointSize(df.pointSize() - 1)
        date_lbl.setFont(df)
        hrow.addWidget(date_lbl)
        hrow.addStretch()
        right.addLayout(hrow)

        # ── Comment text ──
        text_lbl = QtWidgets.QLabel(c.get("text", ""))
        text_lbl.setWordWrap(True)
        right.addWidget(text_lbl)

        # ── Images (0 to N) ──
        img_sources = c.get("image_paths") or (
            [c["image_path"]] if c.get("image_path") else [])

        if img_sources:
            img_row = QtWidgets.QHBoxLayout()
            img_row.setSpacing(6)
            img_row.setAlignment(QtCore.Qt.AlignLeft)

            all_pixmaps = []
            all_labels = []
            for src in img_sources:
                lbl, px = self._make_image_thumb(src)
                all_pixmaps.append(px)
                all_labels.append(lbl)

            for idx, lbl in enumerate(all_labels):
                lbl.mousePressEvent = lambda _evt, i=idx, pxs=all_pixmaps: \
                    ImageViewerDialog(pxs, i).exec_()
                img_row.addWidget(lbl)

            img_row.addStretch()
            right.addLayout(img_row)

        root.addLayout(right)

    @staticmethod
    def _make_avatar(name: str) -> QtWidgets.QLabel:
        size = 32
        pix = QtGui.QPixmap(size, size)
        pix.fill(QtCore.Qt.transparent)
        p = QtGui.QPainter(pix)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        p.setBrush(QtGui.QColor(80, 120, 180))
        p.setPen(QtCore.Qt.NoPen)
        p.drawEllipse(0, 0, size, size)
        p.setPen(QtGui.QColor(255, 255, 255))
        p.setFont(QtGui.QFont("Arial", 13, QtGui.QFont.Bold))
        p.drawText(QtCore.QRect(0, 0, size, size),
                   QtCore.Qt.AlignCenter,
                   name[0].upper() if name else "?")
        p.end()
        lbl = QtWidgets.QLabel()
        lbl.setFixedSize(size, size)
        lbl.setPixmap(pix)
        return lbl

    @staticmethod
    def _make_image_thumb(src):
        """Returns (QLabel thumbnail, QPixmap full). src: QPixmap | bytes | str."""
        THUMB_H = 120
        if isinstance(src, QtGui.QPixmap):
            pixmap = src
        else:
            pixmap = QtGui.QPixmap()
            if isinstance(src, (bytes, bytearray)):
                pixmap.loadFromData(src)
            elif isinstance(src, str):
                pixmap.load(src)

        lbl = QtWidgets.QLabel()
        lbl.setFixedHeight(THUMB_H)
        lbl.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        lbl.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        lbl.setToolTip("Click to view full size")

        if not pixmap.isNull():
            lbl.setPixmap(
                pixmap.scaledToHeight(THUMB_H, QtCore.Qt.SmoothTransformation))
            return lbl, pixmap

        ph = QtGui.QPixmap(180, THUMB_H)
        ph.fill(QtGui.QColor(60, 60, 60))
        p = QtGui.QPainter(ph)
        p.setPen(QtGui.QColor(160, 160, 160))
        p.drawText(ph.rect(), QtCore.Qt.AlignCenter, "[image]")
        p.end()
        lbl.setPixmap(ph)
        return lbl, ph


# ─────────────────────────────────────────────
#  My Activity Feed
# ─────────────────────────────────────────────

class MyActivityFeed(QtWidgets.QWidget):
    """
    Scrollable flat activity feed.
    Renders version / status / comment items in order.
    Handles selection and emits signals for business logic.

    Signals:
        load_requested(dict)     — single version selected → Load to Timeline
        compare_requested(list)  — 2+ versions selected   → Compare

    To add a new right-click option:
        1. Add a Signal here
        2. Add menu.addAction() in show_context_menu()
        3. Emit the new signal in the action handler
        4. Connect it in ActivityTab

    feed_items format:
    [
        {"type": "version", "data": {...}},
        {"type": "status",  "data": {...}},
        {"type": "comment", "data": {...}},
    ]
    """

    load_requested = QtCore.Signal(dict)  # single version → load to timeline
    compare_requested = QtCore.Signal(list)  # multiple versions → compare

    # ── ADD NEW SIGNALS HERE ──
    # example: preview_requested = QtCore.Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.version_widgets = []  # all VersionFeedItem in current feed
        self._build_ui()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QtWidgets.QFrame.NoFrame)

        self.content = QtWidgets.QWidget()
        self.feed_layout = QtWidgets.QVBoxLayout(self.content)
        self.feed_layout.setContentsMargins(4, 4, 4, 4)
        self.feed_layout.setSpacing(6)
        self.feed_layout.addStretch()

        self.scroll.setWidget(self.content)
        layout.addWidget(self.scroll)

    # ── Public API ───────────────────────────

    def load_feed(self, feed_items: list):
        """
        Clear and rebuild the feed from a flat list of typed items.
        Selection state is NOT preserved (new feed = fresh state).
        """
        # Clear existing widgets (keep trailing stretch)
        while self.feed_layout.count() > 1:
            item = self.feed_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.version_widgets = []

        for item in feed_items:
            widget = self._make_widget(item)
            if widget:
                self.feed_layout.insertWidget(
                    self.feed_layout.count() - 1, widget)

        # Scroll to top
        self.scroll.verticalScrollBar().setValue(0)

    def clear_feed(self):
        self.load_feed([])

    def selected_versions(self) -> list:
        """Returns list of version_data dicts for all selected VersionFeedItems."""
        return [w.get_version_data() for w in self.version_widgets if w.selected]

    # ── Widget factory ───────────────────────

    def _make_widget(self, item: dict):
        t = item.get("type")
        data = item.get("data", {})

        if t == "version":
            w = VersionFeedItem(data)
            w.mousePressEvent = lambda evt, _w=w: self._on_version_click(evt, _w)
            w.customContextMenuRequested.connect(
                lambda pos, _w=w: self._show_context_menu(pos, _w))
            self.version_widgets.append(w)
            return w

        elif t == "status":
            return StatusChangeFeedItem(data)

        elif t == "comment":
            return CommentFeedItem(data)

        return None

    # ── Selection ────────────────────────────

    def _on_version_click(self, event, widget: VersionFeedItem):
        """Left-click: toggle selection. Ctrl+click: multi-select. Right-click: do nothing."""
        if event.button() != QtCore.Qt.LeftButton:
            return
        if not (event.modifiers() & QtCore.Qt.ControlModifier):
            for w in self.version_widgets:
                if w is not widget and w.selected:
                    w.set_selected(False)
        widget.set_selected(not widget.selected)

    # ── Context menu ─────────────────────────

    def _show_context_menu(self, pos, clicked_widget: VersionFeedItem):
        # Auto-select the right-clicked widget if not already selected
        if not clicked_widget.selected:
            for w in self.version_widgets:
                w.set_selected(False)
            clicked_widget.set_selected(True)

        selected = self.selected_versions()
        menu = QtWidgets.QMenu(self)

        if len(selected) == 1:
            load_act = menu.addAction("Load to Timeline")

            # ── ADD NEW SINGLE-SELECT OPTIONS HERE ──
            # example: preview_act = menu.addAction("Preview")

        elif len(selected) >= 2:
            names = [v.get("version_name", "?") for v in selected]
            cmp_act = menu.addAction(f"Compare: {' | '.join(names)}")

            # ── ADD NEW MULTI-SELECT OPTIONS HERE ──

        action = menu.exec_(clicked_widget.mapToGlobal(pos))
        if action is None:
            return

        if len(selected) == 1:
            if action == load_act:
                self.load_requested.emit(selected[0])

            # ── HANDLE NEW SINGLE-SELECT OPTIONS HERE ──
            # example:
            # elif action == preview_act:
            #     self.preview_requested.emit(selected[0])

        elif len(selected) >= 2:
            if action == cmp_act:
                self.compare_requested.emit(selected)


class CheckableComboBox(QtWidgets.QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.view().pressed.connect(self.handle_item_pressed)
        self._changed = False

    def handle_item_pressed(self, index):
        item = self.model().itemFromIndex(index)
        if item.checkState() == QtCore.Qt.Checked:
            item.setCheckState(QtCore.Qt.Unchecked)
        else:
            item.setCheckState(QtCore.Qt.Checked)
        self._changed = True

    def hidePopup(self):
        # Only hide the popup if the user clicks outside or finishes selecting
        if not self._changed:
            super().hidePopup()
        self._changed = False

    def get_checked_items(self):
        """Returns a list of strings representing all checked items."""
        checked = []
        model = self.model()
        if model:
            for i in range(model.rowCount()):
                item = model.item(i)
                if item and item.checkState() == QtCore.Qt.Checked:
                    checked.append(item.text())
        return checked


from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPainter, QPen, QColor
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout


class CircularProgress(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.value = 0
        self.setFixedSize(100, 100)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.updateProgress)
        self.timer.start(30)  # speed

    def updateProgress(self):
        self.value += 2
        if self.value > 100:
            self.value = 0
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        margin = 6
        rect = self.rect().adjusted(margin, margin, -margin, -margin)

        # Background circle
        bg_pen = QPen(QColor("white"), 1)
        painter.setPen(bg_pen)
        painter.drawEllipse(rect)

        # Progress arc
        pen = QPen(Qt.gray, 4)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)

        span = int(360 * self.value / 100)
        painter.drawArc(rect, 90 * 16, -span * 16)

