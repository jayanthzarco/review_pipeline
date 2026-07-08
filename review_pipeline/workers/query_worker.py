"""
Generic background-thread worker.

Every network call in the original code (GraphQL queries, ShotGrid
queries, thumbnail downloads) ran synchronously on the UI thread — e.g.
`ReviewPipelineUI._on_load` calling `data.process_project_dailies()`
directly. In Nuke Studio that freezes the whole application for however
long AYON takes to respond. `Worker` wraps any callable so it runs on
Qt's global QThreadPool instead, communicating back to the UI thread only
via signals (safe across threads; touching widgets directly from `run()`
is not).

Usage:
    worker = Worker(pipeline.fetch, options)
    worker.signals.result.connect(self._on_versions_loaded)
    worker.signals.error.connect(self._on_load_error)
    worker.signals.finished.connect(self._hide_loading_overlay)
    QtCore.QThreadPool.globalInstance().start(worker)
"""
from __future__ import annotations

import traceback

from ..ui.qt import QtCore


class WorkerSignals(QtCore.QObject):
    finished = QtCore.Signal()
    error = QtCore.Signal(str)
    result = QtCore.Signal(object)
    progress = QtCore.Signal(int, str)  # (percent, status text) for the circular progress ring


class Worker(QtCore.QRunnable):
    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    @QtCore.Slot()
    def run(self):
        try:
            result = self.fn(*self.args, **self.kwargs)
        except Exception as exc:  # noqa: BLE001 — deliberately broad: any
            # pipeline/network failure must reach the UI as an error signal
            # rather than crashing the worker thread silently.
            traceback.print_exc()
            self.signals.error.emit(str(exc))
        else:
            self.signals.result.emit(result)
        finally:
            self.signals.finished.emit()
