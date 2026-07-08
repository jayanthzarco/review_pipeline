"""
Shared helpers used by every ReviewPipeline implementation.

`build_versions` replaces the original `helpers.Helpers.build_version_list`
— same join logic (version edges + representation edges -> one merged
record), but returns typed `models.Version` objects instead of a raw dict,
and lives in one place instead of being re-implemented per review type.
"""
from __future__ import annotations

import json

from .. import models

# Representation names accepted as a "reviewable" file, per the original
# Process.process_project_dailies (`acp_rep = ['mov', 'exr']`).
ACCEPTED_REPRESENTATION_NAMES = ("mov", "exr")


def _safe_json(raw: str | None) -> dict:
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def build_versions(version_edges: list[dict], representation_edges: list[dict]) -> list[models.Version]:
    """
    :param version_edges: raw `edges` list from a `versions(...)` GraphQL query
    :param representation_edges: raw `edges` list from a `representations(...)` query
    :return: list[models.Version], each with its representations attached
             and `.path` set to the first representation with a usable path
    """
    rep_lookup: dict[str, list[dict]] = {}
    for r in representation_edges:
        node = r.get("node", {})
        vid = node.get("versionId")
        if vid:
            rep_lookup.setdefault(vid, []).append(node)

    versions: list[models.Version] = []
    for v in version_edges:
        vnode = v.get("node", {})
        vid = vnode.get("id")
        attrib = _safe_json(vnode.get("allAttrib"))

        path = None
        representations: list[models.Representation] = []
        for r in rep_lookup.get(vid, []):
            rep_attrib = _safe_json(r.get("allAttrib"))
            rep_path = rep_attrib.get("path") or r.get("path")
            representations.append(models.Representation(
                version_id=vid,
                name=r.get("name"),
                path=rep_path,
                status=r.get("status"),
                created_at=r.get("createdAt"),
                updated_at=r.get("updatedAt"),
            ))
            if rep_path and path is None:
                path = rep_path

        product = vnode.get("product") or {}
        versions.append(models.Version(
            id=vid,
            name=vnode.get("name"),
            product_name=product.get("name", ""),
            project=vnode.get("projectName"),
            artist=vnode.get("author"),
            status=vnode.get("status"),
            updated_at=vnode.get("updatedAt"),
            is_latest=vnode.get("isLatest"),
            thumbnail_id=vnode.get("thumbnailId"),
            product_id=vnode.get("productId"),
            task_id=vnode.get("taskId"),
            comment=attrib.get("comment"),
            path=path,
            representations=representations,
        ))
    return versions


def filter_reviewable_representations(representation_edges: list[dict]) -> list[dict]:
    """Keep only mov/exr representations, matching the original
    Process.process_project_dailies filtering behaviour."""
    return [
        r for r in representation_edges
        if r.get("node", {}).get("name") in ACCEPTED_REPRESENTATION_NAMES
    ]


def organize_sg_versions(sg_versions: list[dict]) -> tuple[list[dict], list[str]]:
    """Ported from helpers.Helpers.organize_sg_versions: extracts the
    AYON version ids (`sg_ayon_id`) linked to each ShotGrid version."""
    versions = []
    version_ids = []
    for each in sg_versions:
        versions.append({
            "name": each.get("code", ""),
            "ayon_id": each.get("sg_ayon_id", ""),
            "project": (each.get("project") or {}).get("name"),
        })
        version_id = each.get("sg_ayon_id")
        if version_id:
            version_ids.append(version_id)
    return versions, version_ids
