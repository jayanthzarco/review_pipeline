"""
AYON GraphQL + REST service layer.

Single entry point for talking to AYON. Wraps `requests` for GraphQL and
lazily wraps `ayon_api` for REST-only endpoints (thumbnails, file uploads,
activities — those get filled in with the Activity tab phase). Every other
layer (pipelines, UI) depends on AyonService instead of importing
`requests`/`ayon_api` directly, which is what makes the pipelines unit
-testable with a fake service later.
"""
from __future__ import annotations

import json
import logging
from typing import Optional

import requests

from .. import models
from .query_builder import QueryBuilder
from ...config import Settings

logger = logging.getLogger(__name__)


class AyonQueryError(RuntimeError):
    """Raised when a GraphQL query fails, times out, or returns malformed
    data. Callers (pipelines, UI) should catch this specifically rather
    than a bare Exception so unrelated bugs don't get silently swallowed."""


class AyonService:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._headers = {
            "X-Api-Key": settings.ayon_api_key,
            "Content-Type": "application/json",
        }
        self._connection = None  # lazy ayon_api connection

    @property
    def connection(self):
        """Lazy `ayon_api` server connection for REST calls (thumbnails,
        file uploads, activities). Not created until first accessed, so
        importing this module doesn't require ayon_api / a live server —
        useful for testing the GraphQL-only paths in isolation."""
        if self._connection is None:
            import ayon_api
            self._connection = ayon_api.get_server_api_connection()
        return self._connection

    # ── GraphQL transport ────────────────────────────────────────

    def run_query(self, query: str, variables: dict) -> dict:
        response = requests.post(
            self._settings.graphql_url,
            json={"query": query, "variables": variables},
            headers=self._headers,
        )
        if not response.text.strip():
            raise AyonQueryError("Empty response from AYON GraphQL endpoint")
        if response.text.lstrip().startswith("<!DOCTYPE html>"):
            raise AyonQueryError(
                "Received an HTML page instead of JSON — check AYON_SERVER_URL "
                "/ the /graphql endpoint path"
            )
        data = response.json()
        if "errors" in data:
            raise AyonQueryError(str(data["errors"]))
        return data

    # ── Convenience wrappers used by pipelines / UI ─────────────

    def get_projects(self) -> list[models.Project]:
        query, var = QueryBuilder.query_projects()
        result = self.run_query(query, var)
        edges = result["data"]["projects"]["edges"]
        return [
            models.Project(name=e["node"]["name"], code=e["node"]["code"], active=e["node"]["active"])
            for e in edges
        ]

    def get_task_types(self) -> list[str]:
        """Global department/task-type list, for the Dept Dailies dropdown."""
        anatomy = self.connection.get_project_anatomy_preset(
            self.connection.get_default_anatomy_preset_name()
        )
        return [t["name"] for t in anatomy["task_types"]]

    def get_task_type_map(self, task_ids: list[str]) -> dict[str, str]:
        """Resolve {task_id: task_type} for a batch of task ids. Used by
        DeptDailiesPipeline to filter today's versions down to one
        department — this is the piece that was a stubbed TODO in the
        original Process.process_department_dailies."""
        if not task_ids:
            return {}
        query, var = QueryBuilder.query_task_type(task_ids)
        result = self.run_query(query, var)
        mapping: dict[str, str] = {}
        for project_edge in result["data"]["projects"]["edges"]:
            for task_edge in project_edge["node"]["tasks"]["edges"]:
                node = task_edge["node"]
                mapping[node["id"]] = node["type"]
        return mapping

    def get_sequences(self, project: str) -> list[dict]:
        query, var = QueryBuilder.query_sequences(project)
        result = self.run_query(query, var)
        return [e["node"] for e in result["data"]["project"]["folders"]["edges"]]

    def get_project_shotgrid_id(self, project: str) -> Optional[int]:
        query, var = QueryBuilder.query_project_by_name(project)
        result = self.run_query(query, var)
        attrib = json.loads(result["data"]["project"]["allAttrib"] or "{}")
        sg_id = attrib.get("shotgridId")
        return int(sg_id) if sg_id is not None else None

    def get_versions(self, project: str) -> list[dict]:
        query, var = QueryBuilder.query_versions(project)
        result = self.run_query(query, var)
        return result["data"]["project"]["versions"]["edges"]

    def get_representations(self, project: str, version_ids: list[str]) -> list[dict]:
        if not version_ids:
            return []
        query, var = QueryBuilder.query_representations(project, version_ids)
        result = self.run_query(query, var)
        return result["data"]["project"]["representations"]["edges"]

    def get_children_folders(self, project: str, parent_id: str) -> list[dict]:
        query, var = QueryBuilder.children_query_by_parent(project, parent_id)
        result = self.run_query(query, var)
        return [e["node"] for e in result["data"]["project"]["folders"]["edges"]]

    def get_versions_by_folder(self, project: str, folder_ids: list[str]) -> list[dict]:
        query, var = QueryBuilder.version_query_by_folder(project, folder_ids)
        result = self.run_query(query, var)
        return result["data"]["project"]["versions"]["edges"]

    def get_versions_by_id(self, project: str, version_ids: list[str]) -> list[dict]:
        query, var = QueryBuilder.query_versions_by_id(version_ids, project)
        result = self.run_query(query, var)
        return result["data"]["project"]["versions"]["edges"]
