import shotgun_api3
import os
import json

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_sg_connection():
    with open(project_root + "/config.json", "r") as conf:
        conf_data = json.load(conf)
    return shotgun_api3.Shotgun(base_url=conf_data.get('SG_URL', ''), script_name=conf_data.get('SG_SCRIPT_NAME', ''),
                                api_key=conf_data.get('SG_SCRIPT_KEY', ''), http_proxy=conf_data.get('SG_PROXY', ''))


sg = get_sg_connection()


def get_playlist_by_project(project_id):
    """ :returns all the playlist from given project id"""
    filters = [
        ['project', 'is', {'type': 'Project', 'id':project_id}]
    ]
    fields = ['id', 'code', 'project', 'description']
    playlists = sg.find(
        'Playlist',
        filters=filters,
        fields=fields)
    return playlists


def get_version_from_playlist(playlist_id, custom_fields=[]):
    """:returns  all the versions linked to given playlist_id in a single query"""

    fields = ['id', 'code', 'sg_ayon_id'] + custom_fields
    filters = [
        ['playlists', 'is', {'type': 'Playlist', 'id':playlist_id}]
              ]
    versions = sg.find('Version', filters, fields)
    return versions

