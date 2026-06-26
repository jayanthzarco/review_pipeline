import sys
import os
import json

try:
    from PySide2 import QtWidgets, QtCore, QtGui
except ImportError:
    from PySide6 import QtWidgets, QtCore, QtGui

from review_pipeline.api import graphql_query, nuke_studio, helpers, ayon_helpers, flow
from review_pipeline.ui import version_ui, custom_feed
import importlib
from datetime import datetime, timezone, timedelta

importlib.reload(graphql_query)
importlib.reload(nuke_studio)
importlib.reload(helpers)
importlib.reload(ayon_helpers)
importlib.reload(version_ui)
importlib.reload(custom_feed)
importlib.reload(flow)


class DATETIME:

    @staticmethod
    def get_today():
        now = datetime.now(timezone.utc)
        today_start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)  #  now.day
        return today_start.isoformat()

    @staticmethod
    def is_today(timestamp_str):
        # Parse input timestamp
        ts = datetime.fromisoformat(timestamp_str)

        # If timestamp is naive, assume UTC; otherwise convert to UTC
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        else:
            ts = ts.astimezone(timezone.utc)

        # Get today's range (UTC)
        now = datetime.now(timezone.utc)
        start_today = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
        end_today = start_today + timedelta(days=1)

        # Check if timestamp is within today
        return start_today <= ts < end_today


class Data:
    QUERY = graphql_query.Query()

    def get_projects(self):
        """
        all_projects: list[dict, dict]
        current_project:str
        """
        proj_query, proj_var = self.QUERY.query_projects()
        result = graphql_query.run_query(proj_query, proj_var)
        all_projects = result['data']['projects']['edges']
        current_project = os.environ.get('AYON_PROJECT_NAME')
        return all_projects, current_project


class Process:
    def __init__(self, review_type, options):
        self.review_type = review_type
        self.options = options

    def process_project_dailies(self):
        PROJECT = self.options['project']
        version_query, version_var = Data.QUERY.query_versions(project=PROJECT)
        result = graphql_query.run_query(version_query, version_var)
        versionIds = []
        version_data = []
        for each in result['data']['project']['versions']['edges']:
            is_or = DATETIME.is_today(each['node']['updatedAt'])
            if is_or:
                versionIds.append(each['node']['id'])
                version_data.append(each)
        rep_query, rep_var = Data.QUERY.query_representations(project=PROJECT, version_ids=versionIds)
        result = graphql_query.run_query(rep_query, rep_var)
        acp_rep = ['mov', 'exr']
        representations = []
        for each in result['data']['project']['representations']['edges']:
            if each['node']['name'] in acp_rep:
                # attrs = json.loads(each['node']['allAttrib'])
                representations.append(each)

        # build version list
        version_list = helpers.Helpers.build_version_list(version_data, representations)
        # for each in version_list:
        #     nuke_studio.load_sequence(each['path'])

        return version_list

    def process_shotgrid_dailies(self, sg_versions):
        versions, version_ids = helpers.Helpers.organize_sg_versions(sg_versions)
        if not version_ids:
            return []

        PROJECT = self.options['project']
        version_query, version_var = graphql_query.Query.query_versions_by_id(version_ids, PROJECT)
        result = graphql_query.run_query(version_query, version_var)
        version_data = [x for x in result['data']['project']['versions']['edges']]

        rep_query, rep_var = graphql_query.Query.query_representations(project=PROJECT, version_ids=version_ids)
        result = graphql_query.run_query(rep_query, rep_var)

        representations_data = [x for x in result['data']['project']['representations']['edges']]

        version_list = helpers.Helpers.build_version_list(version_data, representations_data)

        return version_list

    def process_department_dailies(self, department):
        PROJECT = self.options['project']
        version_query, var = graphql_query.Query.query_all_versions()
        result = graphql_query.run_query(version_query, var)
        avl_version = [x for x in result['data']['projects']['edges']]
        # TODO: Need to find a proper logic
        return []

    def process_sequence_playlist(self, sequence):
        PROJECT = self.options['project']
        # query all the shots to given sequences  : done
        # query the latest versions linked to that shot : done
        cq, cv = graphql_query.Query.children_query_by_parent(project=PROJECT, parent_id=sequence.get('id'))
        result = graphql_query.run_query(cq, cv)
        shot_ids = [x['node'].get('id') for x in result['data']['project']['folders']['edges']]

        vq, vv = graphql_query.Query.version_query_by_folder(project=PROJECT, folder_ids=shot_ids)
        result = graphql_query.run_query(vq, vv)
        version_data = [x for x in result['data']['project']['versions']['edges']]
        version_ids = helpers.Helpers.organize_ayon_version(version_data)

        rep_query, rep_var = graphql_query.Query.query_representations(project=PROJECT, version_ids=version_ids)
        result = graphql_query.run_query(rep_query, rep_var)
        representation_data = [x for x in result['data']['project']['representations']['edges']]
        version_list = helpers.Helpers.build_version_list(version_data, representation_data)
        return version_list


class ReviewPipelineUI(QtWidgets.QWidget):
    load_requested = QtCore.Signal(str, str, dict)
    clear_requested = QtCore.Signal()

    REVIEW_TYPES = ['Project Dailies', "Dept Dailies", "Sequence", "SG_Playlist"]
    DATA = Data()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.env_data()
        self.setWindowTitle("Review")
        self._build_ui()
        self._connect()
        self._toggle_fields()
        self.current_tabs = None

    def env_data(self):
        self.env_project = os.environ.get('AYON_PROJECT_NAME', '')
        self.env_task = os.environ.get('AYON_TASK_NAME', '')
        self.env_folder = os.environ.get('AYON_FOLDER_PATH', '')

    def _build_ui(self):
        self.layout = QtWidgets.QVBoxLayout(self)

        # Header
        self.layout.addWidget(self._label("REVIEW PIPELINE", "mainTitle"))
        self.layout.addWidget(self._label("NUKE STUDIO", "subTitle"))
        self.layout.addWidget(self._sep())

        # Review Type
        self.layout.addWidget(self._label("REVIEW TYPE"))
        self.review_type = QtWidgets.QComboBox()
        self.review_type.addItems(self.REVIEW_TYPES)
        self.layout.addWidget(self.review_type)

        # Project
        self.project_label = self._label("PROJECT")
        self.project = QtWidgets.QComboBox()

        # Make editable (input + dropdown)
        self.project.setEditable(True)
        self.project.setInsertPolicy(QtWidgets.QComboBox.NoInsert)

        self.populate_projects()
        self.layout.addWidget(self.project_label)
        self.layout.addWidget(self.project)

        self.layout.addWidget(self._sep())

        # Dept Dailies
        self.dept_label = self._label("DEPARTMENT")
        self.department = QtWidgets.QComboBox()

        # make Editable
        self.department.setEditable(True)
        self.department.setInsertPolicy(QtWidgets.QComboBox.NoInsert)

        self.populate_departments()
        self.layout.addWidget(self.dept_label)
        self.layout.addWidget(self.department)

        # Sequence
        self.seq_label = self._label('SEQUENCE')
        self.sequence = QtWidgets.QComboBox()
        self.populate_sequences()

        # make Editable
        self.sequence.setEditable(True)
        self.sequence.setInsertPolicy(QtWidgets.QComboBox.NoInsert)

        self.layout.addWidget(self.seq_label)
        self.layout.addWidget(self.sequence)

        # ----Sg playlist field ----
        self.playlist_label = self._label("PLAYLIST")
        self.playlist = QtWidgets.QComboBox()
        self.playlist.setEditable(True)
        self.playlist.setInsertPolicy(QtWidgets.QComboBox.NoInsert)
        self.populate_playlists()
        self.layout.addWidget(self.playlist_label)
        self.layout.addWidget(self.playlist)
        self.layout.addWidget(self._sep())

        # Options
        self.layout.addWidget(self._label("OPTIONS"))
        self.older_versions = QtWidgets.QCheckBox("Include older versions")
        self.inputs = QtWidgets.QCheckBox("Inputs")
        self.older_versions.setChecked(True)
        self.inputs.setChecked(True)

        self.layout.addWidget(self.older_versions)
        self.layout.addWidget(self.inputs)

        self.layout.addWidget(self._sep())

        # Buttons
        btn_row = QtWidgets.QHBoxLayout()

        self.load_btn = QtWidgets.QPushButton("Load")
        self.load_btn.setObjectName("primaryBtn")

        self.clear_btn = QtWidgets.QPushButton("Clear")

        btn_row.addWidget(self.load_btn)
        btn_row.addWidget(self.clear_btn)

        self.layout.addLayout(btn_row)
        # self.layout.addStretch()
        self.layout.addWidget(self._sep())

    def populate_projects(self):
        all_proj, current_proj = self.DATA.get_projects()
        plane_list = []
        for proj in all_proj:
            plane_list.append(proj['node']['name'])

        self.project.addItems(plane_list)
        if current_proj:
            self.project.setCurrentText(current_proj)

        # Auto-complete (search behavior)
        completer = QtWidgets.QCompleter(plane_list)
        completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.project.setCompleter(completer)

    def populate_departments(self):
        # DEPARTMENTS = ["Comp", "Lighting", "FX", "Anim", "Layout"]
        DEPARTMENTS = ayon_helpers.AyonHelper.get_global_task_types()
        default_task_type = ayon_helpers.AyonHelper.get_current_task_type(project=self.env_project,
                                                                          folder_path=self.env_folder,
                                                                          task_name=self.env_task)
        self.department.addItems(DEPARTMENTS)
        if default_task_type and default_task_type in DEPARTMENTS:
            self.department.setCurrentText(default_task_type)

        # Auto-complete
        completer = QtWidgets.QCompleter(DEPARTMENTS)
        completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.department.setCompleter(completer)

    def populate_sequences(self):
        project = self.project.currentText()
        sq, sv = graphql_query.Query.query_sequences(project=project)
        result = graphql_query.run_query(sq, sv)
        SEQUENCES = result['data']['project']['folders']['edges']
        self.sequence.clear()
        plane_list = []
        for seq in SEQUENCES:
            self.sequence.addItem(seq['node'].get('name'), seq.get('node'))
            plane_list.append(seq['node'].get('name'))
        self.sequence.setCurrentIndex(1)

        # Auto complete
        completer = QtWidgets.QCompleter(plane_list)
        completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.sequence.setCompleter(completer)

    def process_project_change(self):
        current_type = self.review_type.currentText()
        if current_type == "SG_Playlist":
            self.populate_playlists()
        elif current_type == "Sequence":
            self.populate_sequences()

    def populate_playlists(self):

        current_project = self.project.currentText()
        project_query, project_var = graphql_query.Query.query_project_by_name(current_project)
        result = graphql_query.run_query(project_query, project_var)
        project_data = json.loads(result['data']['project']['allAttrib'])
        PLAYLISTS = flow.get_playlist_by_project(project_id=int(project_data['shotgridId']))
        plane_list = []
        self.playlist.clear()
        for play in PLAYLISTS:
            self.playlist.addItem(play['code'], play)
            plane_list.append(play['code'])
        # Auto-complete (search behavior)
        completer = QtWidgets.QCompleter(plane_list)
        completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.playlist.setCompleter(completer)

    def _toggle_fields(self):
        review_type = self.review_type.currentText()
        is_sequence = review_type == "Sequence"
        is_dept = review_type == "Dept Dailies"
        is_project = review_type == "Project Dailies"
        is_sg_playlist = review_type == "SG_Playlist"

        self.dept_label.setVisible(is_dept)
        self.department.setVisible(is_dept)

        self.project_label.setVisible(is_project or is_sg_playlist or is_sequence)
        self.project.setVisible(is_project or is_sg_playlist or is_sequence)

        self.playlist_label.setVisible(is_sg_playlist)
        self.playlist.setVisible(is_sg_playlist)

        self.seq_label.setVisible(is_sequence)
        self.sequence.setVisible(is_sequence)
        if review_type == "SG_Playlist":
            self.populate_playlists()

    @staticmethod
    def _label(text, name='sectionTitle'):
        lbl = QtWidgets.QLabel(text)
        lbl.setObjectName(name)
        return lbl

    @staticmethod
    def _sep():
        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.HLine)
        return line

    def _connect(self):
        self.review_type.currentIndexChanged.connect(self._toggle_fields)
        self.load_btn.clicked.connect(self._on_load)
        self.clear_btn.clicked.connect(self._on_clear)
        self.project.currentIndexChanged.connect(self.process_project_change)

    def _on_load(self):
        review_type = self.review_type.currentText()
        sequence = ""
        department = ""
        project = ""
        project = self.project.currentText()
        options = {
            'sequence': sequence,
            'department': department,
            'project': project,
            'older_versions': self.older_versions.isChecked(),
            'inputs': self.inputs.isChecked()
        }
        data = Process(review_type=review_type, options=options)

        if review_type == "Project Dailies":
            # process the project Dailies
            version_list = data.process_project_dailies()
        elif review_type == "Dept Dailies":
            department = self.department.currentText()
            version_list = data.process_department_dailies(department)
        elif review_type == "Sequence":
            sequence = self.sequence.currentData()
            version_list = data.process_sequence_playlist(sequence=sequence)
        elif review_type == "SG_Playlist":
            selected_playlist = self.playlist.currentData()
            avl_versions = flow.get_version_from_playlist(selected_playlist['id'], custom_fields=["project"])
            version_list = data.process_shotgrid_dailies(avl_versions)
        else:
            version_list = []
        options = {
            'sequence': sequence,
            'department': department,
            'project': project,
            'older_versions': self.older_versions.isChecked(),
            'inputs': self.inputs.isChecked()
        }

        self.load_requested.emit(review_type, project, options)

        # need to find a better way for this
        new_list = []
        for each in version_list:
            if each['thumbnailId']:
                thumb_content = ayon_helpers.AyonHelper.get_thumbnail_content(
                    project=each['project'],
                    thumb_id=each['thumbnailId']
                )
                each['thumbnail_path'] = thumb_content
            new_list.append(each)

        if self.current_tabs:
            self.current_tabs.deleteLater()
            self.current_tabs = None

        tabs = version_ui.ReviewTabWidget()
        tabs.versions_tab.load_versions(new_list)
        tabs.load_requested.connect(self._on_version_load)
        tabs.compare_requested.connect(self._on_version_compare)
        self.layout.addWidget(tabs)
        self.current_tabs = tabs

        # need to find better logic aftermath

        # building sequence timeline
        if review_type == "Sequence":
            filtered_versions, paths = helpers.Helpers.filter_render_versions(version_list)
            nuke_studio.load_sequence_dailies(paths, "latest_versions", sequence.get('name'))

    def _on_clear(self):
        self.clear_requested.emit()

    @staticmethod
    def _on_version_load(version_data: dict):
        # path to load the time-line
        if version_data:
            nuke_studio.load_single_clip(clip_path=version_data.get('path'))

    @staticmethod
    def _on_version_compare(versions: list):
        versions = [x.get("path") for x in versions]
        nuke_studio.load_multiple_clips_for_compare(clip_paths_list=versions)


# Nuke Panel Registration
def register_review_panel():
    import nuke
    import nukescripts
    panel_name = "Review Pipeline"
    panel_id = "com.ayon.reviewpipeline"

    pane = nuke.getPaneFor('Properties.1')

    nukescripts.panels.registerWidgetAsPanel(
        'main_ui.ReviewPipelineUI',
        panel_name,
        panel_id,
        True
    ).addToPane(pane)


def _get_dummy_versions():
    """Returns a list of dummy version dicts for development/testing."""
    import random
    statuses = ["In Review", "Lead Review", "Approved", "Retake"]
    artists = ["Jayanth K", "Priya S", "Arjun M", "Deepa R"]
    versions = []
    for i in range(19, 12, -1):
        versions.append({
            "version_name": f"mnf_sh014_Comp_v0{i:02d}",
            "thumbnail_path": None,  # replace with real path
            "project": "mnf",
            "artist": random.choice(artists),
            "status": random.choice(statuses),
            "date": f"2025-07-{i:02d} 10:3{i % 10}",
        })
    return versions


# Auto-register when imported in Nuke
# register_review_panel()
# Launch code in nuke-studio
"""
from review_pipeline import main_ui
import importlib

importlib.reload(main_ui)
main_ui.register_review_panel()
"""
