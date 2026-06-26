try:
    from PySide2 import QtWidgets, QtCore, QtGui
except ImportError:
    from PySide6 import QtWidgets, QtCore, QtGui

# Import all feed widgets from custom_feed
from review_pipeline.ui.custom_feed import (
    VersionCardWidget,
    MyActivityFeed,
)
import json
from review_pipeline.api import custom_api, nuke_studio, ayon_helpers
import importlib

importlib.reload(custom_api)
importlib.reload(nuke_studio)
importlib.reload(ayon_helpers)

STATUSES = ["In Review", "Lead Review", "Approved", "Retake"]


# ─────────────────────────────────────────────
#  Activity Tab
# ─────────────────────────────────────────────

class ActivityTab(QtWidgets.QWidget):
    """
    ┌─ Selected version card (status editable) ─┐
    ├─ MyActivityFeed (flat scrollable feed) ───┤
    ├─ Annotation input + Submit ───────────────┤
    └───────────────────────────────────────────┘

    MyActivityFeed signals wired here:
        load_requested    → load_version_to_timeline(version_data)
        compare_requested → compare_versions(list[version_data])

    To add a new right-click option:
        1. Add signal in MyActivityFeed
        2. Add action in MyActivityFeed._show_context_menu()
        3. Connect here:  self._feed.new_signal.connect(self.new_stub)
        4. Add stub below: def new_stub(self, version_data): print(...)

    Submit → submit_annotation(version_data, text)
    """

    status_change_requested = QtCore.Signal(str, str)  # (version_name, new_status)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_version = None
        self._build_ui()

    # ── Build ────────────────────────────────

    def _build_ui(self):
        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(6, 6, 6, 6)
        outer.setSpacing(6)

        # ── Header card (selected version) ──
        self._header_container = QtWidgets.QWidget()
        self._header_layout = QtWidgets.QVBoxLayout(self._header_container)
        self._header_layout.setContentsMargins(0, 0, 0, 0)
        self._placeholder = QtWidgets.QLabel(
            "← Select a version from the Versions tab")
        self._placeholder.setAlignment(QtCore.Qt.AlignCenter)
        self._header_layout.addWidget(self._placeholder)
        outer.addWidget(self._header_container)

        sep = QtWidgets.QFrame()
        sep.setFrameShape(QtWidgets.QFrame.HLine)
        outer.addWidget(sep)

        # ── Activity feed ──
        self._feed = MyActivityFeed()
        self._feed.load_requested.connect(self.load_version_to_timeline)
        self._feed.compare_requested.connect(self.compare_versions)
        # ── CONNECT NEW SIGNALS HERE ──
        # example: self._feed.preview_requested.connect(self.preview_version)
        outer.addWidget(self._feed, 1)

        sep2 = QtWidgets.QFrame()
        sep2.setFrameShape(QtWidgets.QFrame.HLine)
        outer.addWidget(sep2)

        # ── Annotation input ──
        anno = QtWidgets.QHBoxLayout()
        anno.setSpacing(6)

        self.annotation_input = QtWidgets.QTextEdit()
        self.annotation_input.setPlaceholderText(
            "Submit new annotation for this version…")
        self.annotation_input.setFixedHeight(60)
        anno.addWidget(self.annotation_input, 1)

        self.submit_btn = QtWidgets.QPushButton("Submit")
        self.submit_btn.setFixedSize(70, 60)
        self.submit_btn.clicked.connect(self._on_submit)
        anno.addWidget(self.submit_btn)

        outer.addLayout(anno)

    # ── Public API ───────────────────────────

    def load_activity(self, version_data: dict, feed_items: list):
        """
        Populate the tab.

        version_data : the version selected in VersionsTab (for header card)
        feed_items   : flat list from build_activity_feed_items()
                       [{"type": "version|status|comment", "data": {...}}, ...]
        """
        self._current_version = version_data

        # Rebuild header card
        while self._header_layout.count():
            item = self._header_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        card = VersionCardWidget(version_data, compact=False, status_editable=True)
        card.status_changed.connect(self.status_change_requested)
        frame = QtWidgets.QFrame()
        frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        fl = QtWidgets.QVBoxLayout(frame)
        fl.setContentsMargins(0, 0, 0, 0)
        fl.addWidget(card)
        self._header_layout.addWidget(frame)

        # Load feed
        self._feed.load_feed(feed_items)
        self.annotation_input.clear()

    def clear(self):
        self._current_version = None
        while self._header_layout.count():
            item = self._header_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._header_layout.addWidget(self._placeholder)
        self._feed.clear_feed()
        self.annotation_input.clear()

    # ── Stub functions (replace with real calls) ──────────────

    @staticmethod
    def load_version_to_timeline(version_data: dict):
        """Load single version to Nuke Studio timeline."""
        paths = []
        reps = version_data.get('representations')
        for each in reps:
            all_attrib = json.loads(each.get('node').get('allAttrib'))
            path = all_attrib.get('path')
            if path.endswith('exr'):
                paths.append(path)
            elif path.endswith('dpx'):
                paths.append(path)
        if paths:
            nuke_studio.load_single_clip(clip_path=paths[0])

    @staticmethod
    def compare_versions(versions: list):
        """Compare 2+ versions in Nuke Studio timeline."""
        versions = [x.get("representations") for x in versions]
        paths = []
        acceptable_reps = ['exr', 'dpx']
        for each in versions:
            for x in each:
                all_attrib = json.loads(x.get('node').get('allAttrib'))
                path = all_attrib.get('path')
                if path.endswith('exr'):
                    paths.append(path)
                elif path.endswith('dpx'):
                    paths.append(path)
        nuke_studio.load_multiple_clips_for_compare(clip_paths_list=paths)
        # for v in versions:
        #     print("[COMPARE]", v)

    @staticmethod
    def submit_annotation(version_data: dict, text: str):
        # TODO : need to find a way to export nuke studio annotations
        ayon_helpers.AyonHelper.create_comment(project=version_data.get('project'),
                                               entity_id=version_data.get('versionId'),
                                               entity_type='version',
                                               cmt_type='comment',
                                               body=text)

    def _on_submit(self):
        text = self.annotation_input.toPlainText().strip()
        if not text or not self._current_version:
            return
        self.submit_annotation(self._current_version, text)
        self.annotation_input.clear()


# ─────────────────────────────────────────────
#  Versions Tab
# ─────────────────────────────────────────────

class VersionsTab(QtWidgets.QWidget):
    """
    Search + list of VersionCardWidgets.
    Right-click single → Load to Timeline / Load Activity
    Right-click multi  → Compare (dynamic label)
    """

    activity_requested = QtCore.Signal(dict)
    compare_requested = QtCore.Signal(list)
    load_requested = QtCore.Signal(dict)
    remove_requested = QtCore.Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._all_versions = []
        self._build_ui()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        self.search_bar = QtWidgets.QLineEdit()
        self.search_bar.setPlaceholderText("Search versions…")
        self.search_bar.setClearButtonEnabled(True)
        self.search_bar.textChanged.connect(self._filter)
        layout.addWidget(self.search_bar)

        self.list_widget = QtWidgets.QListWidget()
        self.list_widget.setSpacing(2)
        self.list_widget.setSelectionMode(
            QtWidgets.QAbstractItemView.ExtendedSelection)
        self.list_widget.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self._context_menu)
        layout.addWidget(self.list_widget)
        self.remove_requested.connect(self.remove_version)

    def load_versions(self, versions: list):
        self._all_versions = versions
        self._populate(versions)

    def clear_versions(self):
        self._all_versions = []
        self.list_widget.clear()

    def _populate(self, versions):
        self.list_widget.clear()
        for v in versions:
            card = VersionCardWidget(v)
            item = QtWidgets.QListWidgetItem()
            item.setSizeHint(card.sizeHint() + QtCore.QSize(0, 4))
            item.setData(QtCore.Qt.UserRole, v)
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, card)

    def _filter(self, text):
        t = text.lower()
        self._populate([v for v in self._all_versions
                        if t in v.get("version_name", "").lower()])

    def _context_menu(self, pos):
        item = self.list_widget.itemAt(pos)
        if not item:
            return
        selected = self.list_widget.selectedItems()
        menu = QtWidgets.QMenu(self)

        if len(selected) == 1:
            load_act = menu.addAction("Load to Timeline")
            activity_act = menu.addAction("Load Activity")
            remove_act = menu.addAction("Clear")
            action = menu.exec_(self.list_widget.mapToGlobal(pos))
            data = selected[0].data(QtCore.Qt.UserRole)
            if action == load_act:
                self.load_requested.emit(data)
            elif action == activity_act:
                self.activity_requested.emit(data)
            elif action == remove_act:
                self.remove_requested.emit(data)
        else:
            names = [i.data(QtCore.Qt.UserRole).get("version_name", "?")
                     for i in selected]
            cmp_act = menu.addAction(f"Compare: {' | '.join(names)}")
            if menu.exec_(self.list_widget.mapToGlobal(pos)) == cmp_act:
                self.compare_requested.emit(
                    [i.data(QtCore.Qt.UserRole) for i in selected])

    def remove_version(self, version_data: dict):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.data(QtCore.Qt.UserRole) == version_data:
                self._all_versions = [
                    v for v in self._all_versions
                    if v != version_data]
                self.list_widget.takeItem(i)
                break


# ─────────────────────────────────────────────
#  Review Tab Widget
# ─────────────────────────────────────────────

class ReviewTabWidget(QtWidgets.QTabWidget):
    """
    Drop below Load/Clear buttons in ReviewPipelineUI.

    Signals:
        status_change_requested (version_name, new_status)
        compare_requested       (list[dict])
        load_requested          (dict)
    """

    status_change_requested = QtCore.Signal(str, str)
    compare_requested = QtCore.Signal(list)
    load_requested = QtCore.Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(400)

        self.versions_tab = VersionsTab()
        self.activity_tab = ActivityTab()
        self.addTab(self.versions_tab, "Versions")
        self.addTab(self.activity_tab, "Activity")

        self.versions_tab.activity_requested.connect(self._on_activity)
        self.versions_tab.compare_requested.connect(self.compare_requested)
        self.versions_tab.load_requested.connect(self.load_requested)
        self.activity_tab.status_change_requested.connect(
            self.status_change_requested)

    def _on_activity(self, version_data: dict):
        try:
            feed_items = custom_api.get_on_load_activity(version_data)
            feed_items.reverse()
        except Exception as e:
            print(f"[activity] falling back to dummy data: {e}")
            feed_items = _get_dummy_feed_items(version_data)

        self.activity_tab.load_activity(version_data, feed_items)
        self.setCurrentWidget(self.activity_tab)
