"""
Standalone preview for the Options tab — runs it in a plain PySide window,
no Nuke/Hiero required. Useful for checking layout and interactions while
we build the rest of the tabs.

Run:
    python run_options_tab_standalone.py

Requires:
    pip install PySide6 requests ayon_api
    # (shotgun_api3 only if you want to test the SG_Playlist review type)

Before running, copy review_pipeline/config.json.example to
review_pipeline/config.json and fill in your real AYON_SERVER_URL /
AYON_API_KEY (and SG_* fields if you use ShotGrid).
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from review_pipeline.ui.qt import QtWidgets
from review_pipeline.ui.options_tab import OptionsTab


def main():
    app = QtWidgets.QApplication(sys.argv)

    window = QtWidgets.QMainWindow()
    window.setWindowTitle("Review Pipeline — Options Tab Preview")
    window.resize(520, 640)

    tab = OptionsTab()
    tab.versions_loaded.connect(
        lambda versions: print(f"[preview] versions_loaded: {len(versions)} version(s)")
    )
    tab.load_failed.connect(lambda msg: print(f"[preview] load_failed: {msg}"))

    window.setCentralWidget(tab)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
