from __future__ import annotations

from typing import Optional

from .. import models
from .base import ReviewPipeline, ProgressCallback
from ._shared import build_versions


class SequencePipeline(ReviewPipeline):
    """Latest published version per shot under the selected sequence.
    Ports the original Process.process_sequence_playlist, generalized to
    multi-project (options.projects, each looked up for a sequence with
    the same id — this assumes sequence_id is meaningful across the
    selected projects; if sequences need to be picked per-project
    individually, the Sequence page in the Options tab will need a
    sequence picker per selected project rather than one shared picker)."""

    def fetch(self, options: models.ReviewOptions, on_progress: Optional[ProgressCallback] = None) -> list[models.Version]:
        all_versions: list[models.Version] = []
        project_count = len(options.projects) or 1

        for i, project in enumerate(options.projects):
            base = i / project_count

            shot_folders = self.ayon.get_children_folders(project, options.sequence_id)
            shot_ids = [f["id"] for f in shot_folders]
            self._notify(on_progress, int((base + 0.33 / project_count) * 100), f"Fetching shots ({project})…")

            version_edges = self.ayon.get_versions_by_folder(project, shot_ids)
            version_ids = [e["node"]["id"] for e in version_edges]
            self._notify(on_progress, int((base + 0.66 / project_count) * 100), f"Fetching versions ({project})…")

            rep_edges = self.ayon.get_representations(project, version_ids)
            all_versions.extend(build_versions(version_edges, rep_edges))
            self._notify(on_progress, int((i + 1) / project_count * 100), f"Built results ({project})")

        self._notify(on_progress, 100, "Done")
        return all_versions
