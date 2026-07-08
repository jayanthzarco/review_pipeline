from __future__ import annotations

from typing import Optional

from .. import models
from .base import ReviewPipeline, ProgressCallback
from ._shared import build_versions, organize_sg_versions


class SgPlaylistPipeline(ReviewPipeline):
    """Versions linked to a ShotGrid Playlist. A playlist belongs to a
    single ShotGrid project, so — unlike the other pipelines — this one
    does not iterate options.projects; it uses options.projects[0] (the
    project the chosen playlist lives in) purely to resolve the matching
    AYON versions by id."""

    def fetch(self, options: models.ReviewOptions, on_progress: Optional[ProgressCallback] = None) -> list[models.Version]:
        if self.sg is None:
            raise RuntimeError("SgPlaylistPipeline requires a ShotgridService instance")
        if not options.playlist_id:
            self._notify(on_progress, 100, "No playlist selected")
            return []

        sg_versions = self.sg.get_versions_from_playlist(
            options.playlist_id, custom_fields=["project"]
        )
        self._notify(on_progress, 33, "Fetching ShotGrid playlist…")

        _, version_ids = organize_sg_versions(sg_versions)
        if not version_ids:
            self._notify(on_progress, 100, "Done")
            return []

        project = options.projects[0] if options.projects else None
        version_edges = self.ayon.get_versions_by_id(project, version_ids)
        self._notify(on_progress, 66, "Fetching AYON versions…")

        rep_edges = self.ayon.get_representations(project, version_ids)
        result = build_versions(version_edges, rep_edges)
        self._notify(on_progress, 100, "Done")
        return result
