from __future__ import annotations

from typing import Optional

from .. import models
from .base import ReviewPipeline, ProgressCallback
from ._shared import build_versions, filter_reviewable_representations
from ..services.date_utils import is_within_range


class ProjectDailiesPipeline(ReviewPipeline):
    """Published versions updated today (or in options.date_from/date_to,
    if set) across every selected project. Ports the original
    Process.process_project_dailies, generalized to multi-project."""

    def fetch(self, options: models.ReviewOptions, on_progress: Optional[ProgressCallback] = None) -> list[models.Version]:
        all_versions: list[models.Version] = []
        project_count = len(options.projects) or 1

        for i, project in enumerate(options.projects):
            base = i / project_count

            edges = self.ayon.get_versions(project)
            self._notify(on_progress, int((base + 0.33 / project_count) * 100), f"Fetching versions ({project})…")

            todays_edges = [
                e for e in edges
                if is_within_range(e["node"]["updatedAt"], options.date_from, options.date_to)
            ]
            version_ids = [e["node"]["id"] for e in todays_edges]
            rep_edges = filter_reviewable_representations(
                self.ayon.get_representations(project, version_ids)
            )
            self._notify(on_progress, int((base + 0.66 / project_count) * 100), f"Fetching representations ({project})…")

            all_versions.extend(build_versions(todays_edges, rep_edges))
            self._notify(on_progress, int((i + 1) / project_count * 100), f"Built results ({project})")

        self._notify(on_progress, 100, "Done")
        return all_versions
