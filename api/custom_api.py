import json

from review_pipeline.api import graphql_query, ayon_helpers
import importlib

importlib.reload(graphql_query)
importlib.reload(ayon_helpers)


def get_on_load_activity(version_data):
    project = version_data.get('project')
    task_id = version_data.get('taskId')
    act_q, act_v = graphql_query.Query.query_task_activity(project, task_id)
    result = graphql_query.run_query(act_q, act_v)
    act_data = result['data']['project']['task']['activities']['edges']

    bucket = []
    for each in act_data:
        data = each.get('node', '')
        activity_type = data.get('activityType')
        if activity_type == "version.publish":
            projectName = data.get('projectName')
            vr_data = json.loads(data.get('activityData'))
            versionId = vr_data.get('origin', '').get('id')
            vq, vr = graphql_query.Query.query_version_by_id(project=projectName, version_id=versionId)
            result = graphql_query.run_query(vq, vr)
            vr_data = result['data']['project']['version']

            if vr_data['thumbnailId']:
                thumb_content = ayon_helpers.AyonHelper.get_thumbnail_content(
                    project=projectName,
                    thumb_id=vr_data['thumbnailId']
                )
            else:
                thumb_content = None
            sort_data = {
                "type": "version",
                "data": {
                    "version_name": vr_data.get('name'),
                    "thumbnail_path": thumb_content,
                    "project": projectName,
                    "artist": vr_data.get('author'),
                    "status": vr_data.get('status'),
                    'date': vr_data.get('updatedAt'),
                    "representations": vr_data['representations']['edges']

                },
                'order': data.get('creationOrder')
            }
            bucket.append(sort_data)

        elif activity_type == "comment":
            cmt_data = json.loads(data.get('activityData'))
            print(data)
            images = data.get('files')
            image_pixmap = []
            if images:
                for px in images:
                    px_map = ayon_helpers.AyonHelper.get_file_pixmap(
                        project_name=data.get('projectName'),
                        file_id=px.get('id')
                    )
                    if px_map and not px_map.isNull():
                        image_pixmap.append(px_map)

            sort_data = {
                'type': 'comment',
                'data': {
                    'author': cmt_data.get('author'),
                    'version_tag': cmt_data.get('origin').get("name", ''),
                    'data': data.get('updatedAt'),
                    'text': data.get('body'),
                    'image_paths': image_pixmap
                },
                'order': data.get('creationOrder')
            }
            bucket.append(sort_data)

        elif activity_type == "status.change":
            sts_data = json.loads(data.get('activityData'))
            sort_data = {
                "type": "status",
                'data': {
                    'body': f"{sts_data.get('author')} Changed from {sts_data.get('oldValue')} --> {sts_data.get('newValue')}"},
                'order': data.get('creationOrder')
            }
            bucket.append(sort_data)

    return bucket
