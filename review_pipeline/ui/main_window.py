"""
Main window — combines Options / Versions / Activity into one tabbed
widget, matching the sketch's overall Main_ui structure. This is the
piece that will eventually get wrapped by Nuke's panel registration
(main_ui.py, still to come); for now it's plain PySide so it can run
standalone or inside the demo runner.

Wiring:
    OptionsTab.versions_loaded      -> VersionsTab.set_versions (+ switch tab)
    VersionsTab.activity_requested  -> ActivityTab.load_for_version (+ switch tab)
    {Versions,Activity}Tab.timeline_action_requested -> logged to the
        status bar for now; this is where a HostAdapter.load_to_timeline
        etc. call will plug in once Nuke Studio integration is wired up.
"""
from __future__ import annotations

from .qt import QtWidgets, QtCore
from .options_tab import OptionsTab
from .versions_tab import VersionsTab
from .activity_tab import ActivityTab
from ..core import models


class ReviewPipelineMainWindow(QtWidgets.QWidget):
    def __init__(self, ayon_service=None, sg_service=None, parent=None):
        super().__init__(parent)

        self.options_tab = OptionsTab(ayon_service=ayon_service, sg_service=sg_service)
        self.versions_tab = VersionsTab()
        self.activity_tab = ActivityTab(ayon_service=self.options_tab.ayon)

        self.tabs = QtWidgets.QTabWidget()
        self.tabs.addTab(self.options_tab, "Options")
        self.tabs.addTab(self.versions_tab, "Versions")
        self.tabs.addTab(self.activity_tab, "Activity")

        self.status_bar = QtWidgets.QLabel("")
        self.status_bar.setStyleSheet("color: #888; padding: 2px 4px;")

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.tabs)
        layout.addWidget(self.status_bar)

        self._connect()

    def _connect(self) -> None:
        self.options_tab.load_started.connect(self._on_load_started)
        self.options_tab.load_progress.connect(self.versions_tab.set_loading_progress)
        self.options_tab.versions_loaded.connect(self._on_versions_loaded)
        self.options_tab.load_failed.connect(self._on_load_failed)

        self.versions_tab.activity_requested.connect(self._on_activity_requested)
        self.versions_tab.timeline_action_requested.connect(self._on_timeline_action)
        self.activity_tab.timeline_action_requested.connect(self._on_timeline_action)

    def _on_load_started(self) -> None:
        # Switch to the Versions tab immediately — the loading spinner is
        # shown there, not on the Options tab, so the user watches it load
        # in the place the results will actually appear.
        self.tabs.setCurrentWidget(self.versions_tab)
        self.versions_tab.show_loading("Fetching versions…")

    def _on_load_failed(self, message: str) -> None:
        self.versions_tab.hide_loading()
        self.status_bar.setText(message)

    def _on_versions_loaded(self, versions: list[models.Version]) -> None:
        self.versions_tab.set_versions(versions)  # also hides the loading overlay

    def _on_activity_requested(self, version: models.Version) -> None:
        self.tabs.setCurrentWidget(self.activity_tab)
        self.activity_tab.load_for_version(version)

    def _on_timeline_action(self, action: str, versions: list[models.Version]) -> None:
        # Nuke Studio integration (HostAdapter) is deferred — see the
        # architecture discussion. For now this just surfaces what would
        # have been sent to the host, so the UI flow is testable end to
        # end without Nuke running.
        names = ", ".join(v.display_name for v in versions)
        message = f"[{action}] would load: {names}  (Nuke Studio integration pending)"
        self.status_bar.setText(message)
        print(message)
