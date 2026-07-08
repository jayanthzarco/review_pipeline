from __future__ import annotations

import os
from typing import Optional

from .. import models
from .base import ReviewPipeline, ProgressCallback
from ._shared import build_versions, filter_reviewable_representations
from ..services.date_utils import is_within_range


class ArtistDailiesPipeline(ReviewPipeline):
    """New review type from the sketch: published versions authored by
    the *current logged-in artist* (the sketch shows the panel header as
    "Review Pipeline  User: JAYNTHK" and this review type's box only asks
    for Project + a date range — no artist picker — so "artist" here
    means "me", not an arbitrary selectable artist).

    ASSUMPTION TO CONFIRM: the current user's AYON username is read from
    the AYON_USERNAME env var (falling back to AYON_USER). If your AYON
    launcher exposes it under a different variable, update
    `_current_username()` below.
    """

    def fetch(self, options: models.ReviewOptions, on_progress: Optional[ProgressCallback] = None) -> list[models.Version]:
        current_user = self._current_username()
        all_versions: list[models.Version] = []
        project_count = len(options.projects) or 1

        for i, project in enumerate(options.projects):
            base = i / project_count

            edges = self.ayon.get_versions(project)
            self._notify(on_progress, int((base + 0.33 / project_count) * 100), f"Fetching versions ({project})…")

            filtered_edges = [
                e for e in edges
                if is_within_range(e["node"]["updatedAt"], options.date_from, options.date_to)
                and (not current_user or e["node"].get("author") == current_user)
            ]
            version_ids = [e["node"]["id"] for e in filtered_edges]
            rep_edges = filter_reviewable_representations(
                self.ayon.get_representations(project, version_ids)
            )
            self._notify(on_progress, int((base + 0.66 / project_count) * 100), f"Fetching representations ({project})…")

            all_versions.extend(build_versions(filtered_edges, rep_edges))
            self._notify(on_progress, int((i + 1) / project_count * 100), f"Built results ({project})")

        self._notify(on_progress, 100, "Done")
        return all_versions

    @staticmethod
    def _current_username() -> str:
        return os.environ.get("AYON_USERNAME") or os.environ.get("AYON_USER", "")
