"""
Preview the Options tab with dummy/canned data — no AYON server, no
network access, no config.json required.

Run:
    pip install PySide6
    python run_options_tab_demo.py

Click "Load" after selecting a project (and any review-type-specific
fields) to see the real pipeline logic run against the canned data,
including the loading spinner (each dummy call has a small artificial
delay) and the date/department filtering actually excluding some of the
dummy versions.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from review_pipeline.ui.qt import QtWidgets
from review_pipeline.ui.options_tab import OptionsTab
from demo.dummy_services import DummyAyonService, DummyShotgridService


def main():
    app = QtWidgets.QApplication(sys.argv)

    window = QtWidgets.QMainWindow()
    window.setWindowTitle("Review Pipeline — Options Tab (DUMMY DATA)")
    window.resize(560, 660)

    tab = OptionsTab(ayon_service=DummyAyonService(), sg_service=DummyShotgridService())
    tab.versions_loaded.connect(_print_versions)
    tab.load_failed.connect(lambda msg: print(f"[demo] load_failed: {msg}"))

    window.setCentralWidget(tab)
    window.show()
    sys.exit(app.exec())


def _print_versions(versions):
    print(f"[demo] versions_loaded: {len(versions)} version(s)")
    for v in versions:
        print(f"   - {v.display_name:30s} project={v.project:10s} artist={v.artist:12s} status={v.status:16s} path={v.path}")


if __name__ == "__main__":
    main()
