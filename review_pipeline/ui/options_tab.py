"""
Options Tab — matches the "Main_ui / Options Tab" section of the sketch.

Replaces `ReviewPipelineUI`'s options portion in the original main_ui.py.
Responsibilities kept deliberately narrow: collect a ReviewOptions from
the user, dispatch it to the right pipeline off the UI thread, and emit
the resulting versions. It does not know about Nuke Studio, the Versions
tab, or the Activity tab — those consume `versions_loaded` from the
outside (main_window.py, next phase).

Layout, per the sketch:
    [ REVIEW PIPELINE   User: <name> ]
    [ Review Type combo                ]
    [ Search Options (collapsible) ---- ]
    [   <dynamic per-review-type form>  ]
    [ ] Inputs
    [ ] Include Older Versions
    [ Load ]
"""
from __future__ import annotations

import os

from .qt import QtWidgets, QtCore
from .widgets.multi_project_select import MultiProjectSelect
from .widgets.collapsible_section import CollapsibleSection
from .widgets.loading_overlay import LoadingOverlay

from ..config import get_settings
from ..core import models
from ..core.services.ayon_service import AyonService, AyonQueryError
from ..core.services.shotgrid_service import ShotgridService
from ..core.pipelines.registry import get_pipeline
from ..workers.query_worker import Worker


class OptionsTab(QtWidgets.QWidget):
    versions_loaded = QtCore.Signal(list)   # list[models.Version]
    load_failed = QtCore.Signal(str)
    load_started = QtCore.Signal()          # emitted the instant Load is clicked, before fetching
    load_progress = QtCore.Signal(int, str)  # relayed from the pipeline worker's real progress

    def __init__(self, parent=None, ayon_service=None, sg_service=None):
        super().__init__(parent)

        if ayon_service is not None:
            # Dependency-injection path: used by the dummy-data demo, and
            # by tests. Real config.json / network is never touched here.
            self.ayon = ayon_service
            self.sg = sg_service
        else:
            settings = get_settings()
            self.ayon = AyonService(settings)
            self.sg = ShotgridService(settings) if settings.has_shotgrid else None

        self._thread_pool = QtCore.QThreadPool.globalInstance()
        self._all_projects: list[models.Project] = []
        # Keep a strong Python reference to in-flight workers. Without
        # this, nothing outside QThreadPool holds a reference to the
        # Worker/WorkerSignals QObjects, and PySide can garbage-collect
        # them mid-run ("Signal source has been deleted") before the
        # background thread finishes and tries to emit.
        self._active_workers: list[Worker] = []

        self._build_ui()
        self._connect()
        self._overlay = LoadingOverlay(self)

        self._populate_projects()
        self._populate_departments()
        self._on_review_type_changed()

    # ── UI construction ──────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QtWidgets.QVBoxLayout(self)

        header = QtWidgets.QHBoxLayout()
        title = QtWidgets.QLabel("REVIEW PIPELINE")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        user_label = QtWidgets.QLabel(f"User: {self._current_username()}")
        header.addWidget(title)
        header.addStretch()
        header.addWidget(user_label)
        root.addLayout(header)

        self.review_type = QtWidgets.QComboBox()
        self.review_type.addItems([rt.value for rt in models.ReviewType])
        root.addWidget(self.review_type)

        self.search_options = CollapsibleSection("SEARCH OPTIONS")
        root.addWidget(self.search_options)

        self.pages = QtWidgets.QStackedWidget()
        self.search_options.content_layout.addWidget(self.pages)
        self._build_pages()

        options_box = QtWidgets.QGroupBox("Options")
        options_layout = QtWidgets.QVBoxLayout(options_box)
        self.inputs_checkbox = QtWidgets.QCheckBox("Inputs")
        self.older_versions_checkbox = QtWidgets.QCheckBox("Include Older Versions")
        options_layout.addWidget(self.inputs_checkbox)
        options_layout.addWidget(self.older_versions_checkbox)
        root.addWidget(options_box)

        self.load_btn = QtWidgets.QPushButton("Load")
        self.load_btn.setMinimumHeight(32)
        root.addWidget(self.load_btn)

        self.status_label = QtWidgets.QLabel("")
        self.status_label.setStyleSheet("color: #c0392b;")
        self.status_label.setWordWrap(True)
        root.addWidget(self.status_label)

        root.addStretch()

    def _build_pages(self) -> None:
        # order must match models.ReviewType iteration order used above
        self.artist_page, self.artist_projects, self.date_from, self.date_to = self._build_artist_dailies_page()
        self.pages.addWidget(self.artist_page)

        self.project_page, self.project_projects = self._build_project_dailies_page()
        self.pages.addWidget(self.project_page)

        self.dept_page, self.dept_projects, self.department_combo = self._build_dept_dailies_page()
        self.pages.addWidget(self.dept_page)

        self.sequence_page, self.sequence_projects, self.sequence_combo = self._build_sequence_page()
        self.pages.addWidget(self.sequence_page)

        self.playlist_page, self.playlist_projects, self.playlist_combo = self._build_sg_playlist_page()
        self.pages.addWidget(self.playlist_page)

    def _build_artist_dailies_page(self):
        page = QtWidgets.QWidget()
        layout = QtWidgets.QFormLayout(page)
        projects = MultiProjectSelect()
        date_from = QtWidgets.QDateEdit(calendarPopup=True)
        date_to = QtWidgets.QDateEdit(calendarPopup=True)
        today = QtCore.QDate.currentDate()
        date_from.setDate(today)
        date_to.setDate(today)
        layout.addRow("Project", projects)
        date_row = QtWidgets.QHBoxLayout()
        date_row.addWidget(QtWidgets.QLabel("From"))
        date_row.addWidget(date_from)
        date_row.addWidget(QtWidgets.QLabel("To"))
        date_row.addWidget(date_to)
        layout.addRow("Date", date_row)
        return page, projects, date_from, date_to

    def _build_project_dailies_page(self):
        page = QtWidgets.QWidget()
        layout = QtWidgets.QFormLayout(page)
        projects = MultiProjectSelect()
        layout.addRow("Project", projects)
        return page, projects

    def _build_dept_dailies_page(self):
        page = QtWidgets.QWidget()
        layout = QtWidgets.QFormLayout(page)
        projects = MultiProjectSelect()
        department = QtWidgets.QComboBox()
        department.setEditable(True)
        department.setInsertPolicy(QtWidgets.QComboBox.NoInsert)
        layout.addRow("Project", projects)
        layout.addRow("Department", department)
        return page, projects, department

    def _build_sequence_page(self):
        page = QtWidgets.QWidget()
        layout = QtWidgets.QFormLayout(page)
        projects = MultiProjectSelect()
        sequence = QtWidgets.QComboBox()
        sequence.setEditable(True)
        sequence.setInsertPolicy(QtWidgets.QComboBox.NoInsert)
        layout.addRow("Project", projects)
        layout.addRow("Sequence", sequence)
        return page, projects, sequence

    def _build_sg_playlist_page(self):
        page = QtWidgets.QWidget()
        layout = QtWidgets.QFormLayout(page)
        projects = MultiProjectSelect()
        playlist = QtWidgets.QComboBox()
        playlist.setEditable(True)
        playlist.setInsertPolicy(QtWidgets.QComboBox.NoInsert)
        layout.addRow("Project", projects)
        layout.addRow("PlayList", playlist)
        return page, projects, playlist

    def _connect(self) -> None:
        self.review_type.currentIndexChanged.connect(self._on_review_type_changed)
        self.load_btn.clicked.connect(self._on_load_clicked)

        # Sequence / SG_Playlist pages need to repopulate their secondary
        # dropdown whenever the project selection on that page changes.
        self.sequence_projects.selection_changed.connect(self._populate_sequences)
        self.playlist_projects.selection_changed.connect(self._populate_playlists)

    # ── Data population (threaded) ──────────────────────────────

    def _run_async(self, fn, on_success, message="Loading…", *args, **kwargs):
        """For calls with no real sub-steps to report (populating a
        dropdown from one network call) — the ring climbs to ~90% and
        holds, then completes on finish. See _run_pipeline_async for
        calls that do have real staged progress."""
        self._overlay.show_overlay(message)
        self._overlay.animate_indeterminate()

        worker = Worker(fn, *args, **kwargs)
        self._active_workers.append(worker)

        def _cleanup():
            if worker in self._active_workers:
                self._active_workers.remove(worker)
            self._overlay.complete_and_hide()

        worker.signals.result.connect(on_success)
        worker.signals.error.connect(self._on_async_error)
        worker.signals.finished.connect(_cleanup)
        self._thread_pool.start(worker)

    def _run_pipeline_async(self, pipeline, options, on_success, message="Fetching versions…"):
        """Unlike _run_async, this does NOT show OptionsTab's own overlay —
        the Load action switches to the Versions tab immediately (see
        MainWindow._on_load_started) and the loading visual lives there
        instead, driven by relaying this worker's real progress through
        `load_progress`."""
        worker = Worker(pipeline.fetch, options, on_progress=lambda p, m: worker.signals.progress.emit(p, m))
        self._active_workers.append(worker)

        def _cleanup():
            if worker in self._active_workers:
                self._active_workers.remove(worker)

        worker.signals.progress.connect(self.load_progress)
        worker.signals.result.connect(on_success)
        worker.signals.error.connect(self._on_async_error)
        worker.signals.finished.connect(_cleanup)
        self._thread_pool.start(worker)

    def _populate_projects(self) -> None:
        self._run_async(self.ayon.get_projects, self._on_projects_loaded, "Loading projects…")

    def _on_projects_loaded(self, projects: list[models.Project]) -> None:
        self._all_projects = [p for p in projects if p.active]
        names = [p.name for p in self._all_projects]
        for combo in (
            self.artist_projects, self.project_projects, self.dept_projects,
            self.sequence_projects, self.playlist_projects,
        ):
            combo.set_projects(names)

    def _populate_departments(self) -> None:
        self._run_async(self.ayon.get_task_types, self._on_departments_loaded, "Loading departments…")

    def _on_departments_loaded(self, departments: list[str]) -> None:
        self.department_combo.clear()
        self.department_combo.addItems(departments)
        completer = QtWidgets.QCompleter(departments, self.department_combo)
        completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.department_combo.setCompleter(completer)

    def _populate_sequences(self, selected_projects: list[str]) -> None:
        if not selected_projects:
            self.sequence_combo.clear()
            return
        # Sequences are queried per-project; with multiple projects
        # selected we show the first project's sequences and prefix the
        # combo's placeholder so it's clear this isn't a merged list yet.
        # TODO(next iteration): decide whether Sequence review type should
        # support cross-project sequence selection or stay single-project.
        project = selected_projects[0]
        self._run_async(self.ayon.get_sequences, self._on_sequences_loaded, "Loading sequences…", project)

    def _on_sequences_loaded(self, sequences: list[dict]) -> None:
        self.sequence_combo.clear()
        names = []
        for seq in sequences:
            self.sequence_combo.addItem(seq.get("name"), seq)
            names.append(seq.get("name"))
        completer = QtWidgets.QCompleter(names, self.sequence_combo)
        completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.sequence_combo.setCompleter(completer)

    def _populate_playlists(self, selected_projects: list[str]) -> None:
        if not selected_projects or self.sg is None:
            self.playlist_combo.clear()
            return
        project = selected_projects[0]

        def _load():
            sg_id = self.ayon.get_project_shotgrid_id(project)
            if sg_id is None:
                return []
            return self.sg.get_playlists_for_project(sg_id)

        self._run_async(_load, self._on_playlists_loaded, "Loading playlists…")

    def _on_playlists_loaded(self, playlists: list[dict]) -> None:
        self.playlist_combo.clear()
        names = []
        for play in playlists:
            self.playlist_combo.addItem(play.get("code"), play)
            names.append(play.get("code"))
        completer = QtWidgets.QCompleter(names, self.playlist_combo)
        completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.playlist_combo.setCompleter(completer)

    # ── Review type switching ───────────────────────────────────

    def _on_review_type_changed(self) -> None:
        self.pages.setCurrentIndex(self.review_type.currentIndex())
        review_type = models.ReviewType(self.review_type.currentText())
        if review_type == models.ReviewType.SG_PLAYLIST and self.sg is None:
            self.status_label.setText(
                "ShotGrid is not configured (missing SG_URL/SG_SCRIPT_NAME/SG_SCRIPT_KEY) "
                "— SG_Playlist will not return results."
            )
        else:
            self.status_label.setText("")

    # ── Load ─────────────────────────────────────────────────────

    def get_options(self) -> models.ReviewOptions:
        review_type = models.ReviewType(self.review_type.currentText())
        options = models.ReviewOptions(
            review_type=review_type,
            include_inputs=self.inputs_checkbox.isChecked(),
            include_older_versions=self.older_versions_checkbox.isChecked(),
        )

        if review_type == models.ReviewType.ARTIST_DAILIES:
            options.projects = self.artist_projects.selected_projects()
            options.date_from = self.date_from.date().toPython() if hasattr(self.date_from.date(), "toPython") \
                else self.date_from.date().toPyDate()
            options.date_to = self.date_to.date().toPython() if hasattr(self.date_to.date(), "toPython") \
                else self.date_to.date().toPyDate()
        elif review_type == models.ReviewType.PROJECT_DAILIES:
            options.projects = self.project_projects.selected_projects()
        elif review_type == models.ReviewType.DEPT_DAILIES:
            options.projects = self.dept_projects.selected_projects()
            options.department = self.department_combo.currentText()
        elif review_type == models.ReviewType.SEQUENCE:
            options.projects = self.sequence_projects.selected_projects()
            options.sequence_name = self.sequence_combo.currentText()
            seq_data = self.sequence_combo.currentData()
            options.sequence_id = seq_data.get("id") if seq_data else None
        elif review_type == models.ReviewType.SG_PLAYLIST:
            options.projects = self.playlist_projects.selected_projects()
            playlist_data = self.playlist_combo.currentData()
            options.playlist_id = playlist_data.get("id") if playlist_data else None
            options.playlist_code = self.playlist_combo.currentText()

        return options

    def _on_load_clicked(self) -> None:
        options = self.get_options()
        if not options.projects:
            self.status_label.setText("Select at least one project.")
            return
        self.status_label.setText("")
        self.load_started.emit()

        pipeline = get_pipeline(options.review_type, self.ayon, self.sg)
        self._run_pipeline_async(pipeline, options, self._on_load_success, "Fetching versions…")

    def _on_load_success(self, versions: list[models.Version]) -> None:
        self.versions_loaded.emit(versions)
        if not versions:
            self.status_label.setText("No versions found for the selected options.")

    def _on_async_error(self, message: str) -> None:
        self.status_label.setText(message)
        self.load_failed.emit(message)

    # ── Misc ─────────────────────────────────────────────────────

    @staticmethod
    def _current_username() -> str:
        return os.environ.get("AYON_USERNAME") or os.environ.get("AYON_USER", "unknown")
