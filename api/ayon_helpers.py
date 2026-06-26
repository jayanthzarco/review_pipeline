import json
import ayon_api
import os
import io
from PySide2 import QtGui

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))

with open(PROJECT_ROOT + "/config.json", 'r') as conf:
    conf_data = json.load(conf)


def get_ayon_connection():
    # Only set if not already in environment
    if not os.environ.get('AYON_SERVER_URL'):
        os.environ['AYON_SERVER_URL'] = conf_data['AYON_SERVER_URL']
    if not os.environ.get('AYON_API_KEY'):
        os.environ['AYON_API_KEY'] = conf_data['AYON_API_KEY']
    return ayon_api.get_server_api_connection()


con = get_ayon_connection()


class AyonHelper:
    @staticmethod
    def get_thumbnail_content(project, thumb_id):
        data_ = con.get_thumbnail_by_id(project_name=project, thumbnail_id=thumb_id)
        return data_.content

    @staticmethod
    def get_file_pixmap(project_name: str, file_id: str) -> QtGui.QPixmap:
        try:
            # Build URL (no /api prefix)
            url = f"/projects/{project_name}/files/{file_id}"

            # Download to memory
            buffer = io.BytesIO()
            con.download_file_to_stream(url, buffer)
            buffer.seek(0)

            # Convert to pixmap
            pixmap = QtGui.QPixmap()
            pixmap.loadFromData(buffer.getvalue())

            return pixmap

        except Exception as e:
            print(f"Error: {e}")
            return QtGui.QPixmap()

    @staticmethod
    def get_global_task_types():
        an = con.get_project_anatomy_preset(con.get_default_anatomy_preset_name())
        task_types = [x['name'] for x in an['task_types']]
        return task_types

    @staticmethod
    def get_current_task_type(project, folder_path, task_name):
        task = con.get_task_by_folder_path(project_name=project,
                                           folder_path=folder_path,
                                           task_name=task_name,
                                           fields=['taskType'])

        return task.get('taskType', '')

    @staticmethod
    def create_comment(project, entity_id, entity_type, cmt_type, body):
        con.create_activity(project_name=project,
                            entity_id=entity_id,
                            entity_type=entity_type,
                            activity_type=cmt_type,
                            body=body)
