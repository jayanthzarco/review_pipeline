"""
Single point of PySide version resolution.

Import Qt everywhere else via:

    from review_pipeline.ui.qt import QtWidgets, QtCore, QtGui

so the PySide2/PySide6 try/except (needed because Nuke and Maya versions
pin different Qt bindings) lives in exactly one place instead of being
repeated at the top of every UI module, as it was in the original code.
"""
try:
    from PySide2 import QtWidgets, QtCore, QtGui
    PYSIDE_VERSION = 2
except ImportError:
    from PySide6 import QtWidgets, QtCore, QtGui
    PYSIDE_VERSION = 6

__all__ = ["QtWidgets", "QtCore", "QtGui", "PYSIDE_VERSION"]
