from __future__ import annotations

from typing import Optional

from .. import models
from .base import ReviewPipeline
from .artist_dailies import ArtistDailiesPipeline
from .project_dailies import ProjectDailiesPipeline
from .dept_dailies import DeptDailiesPipeline
from .sequence import SequencePipeline
from .sg_playlist import SgPlaylistPipeline
from ..services.ayon_service import AyonService
from ..services.shotgrid_service import ShotgridService

PIPELINE_REGISTRY: dict[models.ReviewType, type[ReviewPipeline]] = {
    models.ReviewType.ARTIST_DAILIES: ArtistDailiesPipeline,
    models.ReviewType.PROJECT_DAILIES: ProjectDailiesPipeline,
    models.ReviewType.DEPT_DAILIES: DeptDailiesPipeline,
    models.ReviewType.SEQUENCE: SequencePipeline,
    models.ReviewType.SG_PLAYLIST: SgPlaylistPipeline,
}


def get_pipeline(
    review_type: models.ReviewType,
    ayon_service: AyonService,
    sg_service: Optional[ShotgridService] = None,
) -> ReviewPipeline:
    cls = PIPELINE_REGISTRY.get(review_type)
    if cls is None:
        raise ValueError(f"No pipeline registered for review type: {review_type}")
    return cls(ayon_service, sg_service)
