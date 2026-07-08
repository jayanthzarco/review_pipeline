"""
Checkable multi-select combobox for projects.

The sketch's note — "there can be multiple projects selected" — and the
"SRV_TST/AYN_TST/ALL" style label in every Project field means the old
single-select, editable QComboBox (`self.project` in the original
main_ui.py) needs to become a checklist-style dropdown. Qt doesn't ship
one, so this subclasses QComboBox with a checkable QStandardItemModel and
keeps the popup open across clicks so multiple boxes can be ticked in one
go.
"""
from __future__ import annotations

from ..qt import QtWidgets, QtCore, QtGui


class MultiProjectSelect(QtWidgets.QComboBox):
    selection_changed = QtCore.Signal(list)  # list[str] of selected project names

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setEditable(True)
        self.lineEdit().setReadOnly(True)
        self.lineEdit().installEventFilter(self)

        self._model = QtGui.QStandardItemModel(self)
        self.setModel(self._model)
        self.view().pressed.connect(self._on_item_pressed)

        self._placeholder = "Select project(s)…"
        self._update_text()

    def set_projects(self, project_names: list[str]) -> None:
        previously_selected = set(self.selected_projects())
        self._model.clear()
        for name in project_names:
            item = QtGui.QStandardItem(name)
            item.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsUserCheckable)
            state = QtCore.Qt.Checked if name in previously_selected else QtCore.Qt.Unchecked
            item.setData(state, QtCore.Qt.CheckStateRole)
            self._model.appendRow(item)
        self._update_text()

    def selected_projects(self) -> list[str]:
        selected = []
        for row in range(self._model.rowCount()):
            item = self._model.item(row)
            if item.checkState() == QtCore.Qt.Checked:
                selected.append(item.text())
        return selected

    def set_selected_projects(self, project_names: list[str]) -> None:
        wanted = set(project_names)
        for row in range(self._model.rowCount()):
            item = self._model.item(row)
            item.setCheckState(QtCore.Qt.Checked if item.text() in wanted else QtCore.Qt.Unchecked)
        self._update_text()
        self.selection_changed.emit(self.selected_projects())

    def _on_item_pressed(self, index: QtCore.QModelIndex) -> None:
        item = self._model.itemFromIndex(index)
        new_state = QtCore.Qt.Unchecked if item.checkState() == QtCore.Qt.Checked else QtCore.Qt.Checked
        item.setCheckState(new_state)
        self._update_text()
        self.selection_changed.emit(self.selected_projects())
        # QComboBox closes the popup by default whenever an item is
        # clicked. Re-open it on the next event-loop tick so multiple
        # checkboxes can be ticked in one interaction; the popup still
        # closes normally on focus-out / Escape since we're not blocking
        # hidePopup() itself.
        QtCore.QTimer.singleShot(0, self.showPopup)

    def _update_text(self) -> None:
        selected = self.selected_projects()
        self.lineEdit().setText(", ".join(selected) if selected else self._placeholder)

    def eventFilter(self, obj, event):
        # Open (rather than toggle) the popup on click, and keep it open
        # after each item click, so several checkboxes can be ticked in
        # one interaction instead of the popup closing after the first pick.
        if obj is self.lineEdit() and event.type() == QtCore.QEvent.MouseButtonPress:
            self.showPopup()
            return True
        return super().eventFilter(obj, event)
