import json
import os.path
from datetime import datetime
import pytz


def format_date_ist(iso_string):
    try:
        utc_time = datetime.fromisoformat(iso_string)
        ist = pytz.timezone("Asia/Kolkata")
        ist_time = utc_time.astimezone(ist)
        return ist_time.strftime("%Y-%m-%d %I:%M %p")
    except Exception:
        return None


class Helpers:
    @staticmethod
    def build_version_list(version_data, rep):
        result = []

        # Build lookup: versionId → representations
        rep_lookup = {}
        for r in rep:
            node = r.get("node", {})
            vid = node.get("versionId")
            if vid:
                rep_lookup.setdefault(vid, []).append(node)

        for v in version_data:
            vnode = v.get("node", {})
            vid = vnode.get("id")

            # Parse version attributes
            try:
                attrib = json.loads(vnode.get("allAttrib", "{}"))
            except json.JSONDecodeError:
                attrib = {}

            # Extract path from rep
            file_path = None
            for r in rep_lookup.get(vid, []):
                try:
                    rep_attrib = json.loads(r.get("allAttrib", "{}"))
                    if rep_attrib.get("path"):
                        file_path = rep_attrib.get("path")
                        break
                except json.JSONDecodeError:
                    continue

            data = {
                "version_name": f"{vnode.get('product', {}).get('name', '')}_{vnode.get('name', '')}",
                "thumbnail_path": None,
                "project": vnode.get("projectName"),
                "artist": vnode.get("author"),
                "status": vnode.get("status"),
                "date": format_date_ist(vnode.get("updatedAt")) if vnode.get("updatedAt") else None,
                "comments": attrib.get("comment"),
                "isLatest": vnode.get("isLatest"),
                "path": file_path,
                'thumbnailId': vnode.get('thumbnailId'),
                'productId':vnode.get('productId'),
                'taskId':vnode.get('taskId'),
                'productName':vnode.get('product', {}).get('name', ''),
                "versionId":vnode.get('id')
            }

            result.append(data)

        return result

    @staticmethod
    def organize_sg_versions(sg_versions):
        versions = []
        version_ids = []
        for each in sg_versions:
            version_dict = {
                "name":each.get('code', ''),
                'ayon_id': each.get('sg_ayon_id', ''),
                'project': each.get('project').get('name')

            }
            version_id = each.get('sg_ayon_id')
            versions.append(version_dict)
            if version_id:
                version_ids.append(version_id)
        return versions, version_ids

    @staticmethod
    def organize_dept_versions(dept, avl_version):
        pass

    @staticmethod
    def organize_ayon_version(version_data):
        """
        :param version_data:
        :return: version list
        """
        version_list = []
        for each in version_data:
            version_list.append(each['node'].get('id'))
        return version_list

    @staticmethod
    def filter_render_versions(versions):
        render_types = ['exr', 'dpx']
        filtered_versions = []
        paths = []

        for each in versions:
            path = each.get('path') or ''
            _, ext = os.path.splitext(path)
            if ext:
                if ext.lstrip('.').lower() in render_types:
                    filtered_versions.append(each)
                    paths.append(path)

        return filtered_versions, paths

