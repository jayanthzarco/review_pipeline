"""
ReviewPipeline: one implementation per ReviewType.

This replaces the original `Process` class, which had one
`process_x_dailies` method per review type, each re-implementing the same
query -> representations -> build_version_list sequence with small
variations (and, for Dept Dailies, not implementing it at all).

Each pipeline now owns exactly one `fetch(options, on_progress) ->
list[Version]` method. Pipelines are looked up via `registry.get_pipeline()`
from a `ReviewType`, so adding a new review type means adding one new
pipeline class + one registry entry — nothing in the UI needs to change.

`on_progress`, if given, is called as `on_progress(percent: int, message:
str)` at real milestones (after fetching versions, after fetching
representations, after building results) — this drives the circular
progress ring in the loading overlay with genuine stage progress rather
than a fake indeterminate animation.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable, Optional

from .. import models
from ..services.ayon_service import AyonService
from ..services.shotgrid_service import ShotgridService

ProgressCallback = Callable[[int, str], None]


class ReviewPipeline(ABC):
    def __init__(self, ayon_service: AyonService, sg_service: Optional[ShotgridService] = None):
        self.ayon = ayon_service
        self.sg = sg_service

    @abstractmethod
    def fetch(self, options: models.ReviewOptions, on_progress: Optional[ProgressCallback] = None) -> list[models.Version]:
        """Run the pipeline for the given options and return a flat,
        deduplicated list of Version. Per the "single merged list" design
        decision, pipelines that iterate `options.projects` concatenate
        results across projects rather than grouping/returning per-project."""
        raise NotImplementedError

    @staticmethod
    def _notify(on_progress: Optional[ProgressCallback], percent: int, message: str) -> None:
        if on_progress:
            on_progress(percent, message)
