from __future__ import annotations

from typing import Optional

from .. import models
from .base import ReviewPipeline, ProgressCallback
from ._shared import build_versions, filter_reviewable_representations
from ..services.date_utils import is_within_range


class DeptDailiesPipeline(ReviewPipeline):
    """
    Today's (or the given range's) published versions, filtered to one
    department/task-type.

    This was a stub in the original code (`Process.process_department_dailies`
    just had `# TODO: Need to find a proper logic` and returned `[]`). The
    missing piece was that versions don't carry a task *type* directly —
    only a `taskId` — so resolving "department" requires a second query
    to map task ids to task types. That's what
    AyonService.get_task_type_map does (and it required fixing
    QueryBuilder.query_task_type, which didn't return task ids in the
    original — see query_builder.py docstring).
    """

    def fetch(self, options: models.ReviewOptions, on_progress: Optional[ProgressCallback] = None) -> list[models.Version]:
        all_versions: list[models.Version] = []
        project_count = len(options.projects) or 1

        for i, project in enumerate(options.projects):
            base = i / project_count

            edges = self.ayon.get_versions(project)
            todays_edges = [
                e for e in edges
                if is_within_range(e["node"]["updatedAt"], options.date_from, options.date_to)
            ]
            self._notify(on_progress, int((base + 0.25 / project_count) * 100), f"Fetching versions ({project})…")

            task_ids = list({
                e["node"]["taskId"] for e in todays_edges if e["node"].get("taskId")
            })
            task_type_by_id = self.ayon.get_task_type_map(task_ids)
            self._notify(on_progress, int((base + 0.5 / project_count) * 100), f"Resolving task types ({project})…")

            dept_edges = [
                e for e in todays_edges
                if task_type_by_id.get(e["node"].get("taskId")) == options.department
            ]

            version_ids = [e["node"]["id"] for e in dept_edges]
            rep_edges = filter_reviewable_representations(
                self.ayon.get_representations(project, version_ids)
            )
            self._notify(on_progress, int((base + 0.75 / project_count) * 100), f"Fetching representations ({project})…")

            all_versions.extend(build_versions(dept_edges, rep_edges))
            self._notify(on_progress, int((i + 1) / project_count * 100), f"Built results ({project})")

        self._notify(on_progress, 100, "Done")
        return all_versions
