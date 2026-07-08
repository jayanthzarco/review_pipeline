"""
Full demo — Options + Versions + Activity tabs, all wired together,
running entirely on dummy data (no AYON server, no network, no config.json).

Run:
    pip install PySide6
    python run_full_demo.py

Flow to try:
    1. Options tab: pick "Project Dailies", check SRV_TST, click Load.
    2. You're switched to the Versions tab — click a version card to see
       its detail panel; right-click a card for the Load-to-Timeline /
       Compare / Load Activity / Clear menu.
    3. Right-click -> "Load Activity" switches to the Activity tab and
       loads a dummy comment/status feed for that version, plus 2
       synthesized "previous versions".
    4. Click a comment's image thumbnail to open the full-screen viewer.
    5. Type something in the comment box at the bottom and hit Submit —
       it appends to the feed live (no real AYON push in demo mode).
    6. Change the Status dropdown on the Master Version card — a
       status-change line appends to the feed automatically.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from review_pipeline.ui.qt import QtWidgets
from review_pipeline.ui.main_window import ReviewPipelineMainWindow
from demo.dummy_services import DummyAyonService, DummyShotgridService


def main():
    app = QtWidgets.QApplication(sys.argv)

    window = QtWidgets.QMainWindow()
    window.setWindowTitle("Review Pipeline — Full Demo (DUMMY DATA)")
    window.resize(1200, 760)

    main_widget = ReviewPipelineMainWindow(
        ayon_service=DummyAyonService(),
        sg_service=DummyShotgridService(),
    )
    window.setCentralWidget(main_widget)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
