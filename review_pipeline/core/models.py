"""
Typed data models shared across services, pipelines, workers and UI.

These replace the loose `{'node': {...}}` dicts and hand-built dicts
(see the old `helpers.build_version_list`) that the original codebase
passed around everywhere. A dataclass gives every layer a single agreed
field set with autocomplete, instead of `each['node'].get('id')` sprinkled
through the UI code.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class ReviewType(str, Enum):
    ARTIST_DAILIES = "Artist Dailies"
    PROJECT_DAILIES = "Project Dailies"
    DEPT_DAILIES = "Dept Dailies"
    SEQUENCE = "Sequence"
    SG_PLAYLIST = "SG_Playlist"


@dataclass
class Project:
    name: str
    code: str
    active: bool = True


@dataclass
class ReviewOptions:
    """Everything the Options tab collects, independent of review type.
    Fields irrelevant to the chosen review_type are simply left at default."""
    review_type: ReviewType
    projects: list[str] = field(default_factory=list)  # multi-select, per sketch note
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    department: Optional[str] = None
    sequence_id: Optional[str] = None
    sequence_name: Optional[str] = None
    playlist_id: Optional[int] = None
    playlist_code: Optional[str] = None
    include_inputs: bool = False
    include_older_versions: bool = False


@dataclass
class Representation:
    version_id: str
    name: str
    path: Optional[str]
    status: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass
class Version:
    id: str
    name: str
    product_name: str
    project: str
    artist: Optional[str]
    status: Optional[str]
    updated_at: Optional[str]
    is_latest: Optional[bool]
    thumbnail_id: Optional[str]
    product_id: Optional[str]
    task_id: Optional[str]
    comment: Optional[str] = None
    path: Optional[str] = None
    thumbnail_bytes: Optional[bytes] = None
    representations: list[Representation] = field(default_factory=list)

    @property
    def display_name(self) -> str:
        return f"{self.product_name}_{self.name}"


@dataclass
class ActivityItem:
    """One entry in the Activity tab feed: a comment, status change, or
    version-publish event. `order` is AYON's creationOrder, used to sort
    the feed chronologically."""
    kind: str  # "comment" | "status" | "version"
    order: int
    payload: dict
