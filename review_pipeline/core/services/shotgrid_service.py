"""
ShotGrid service layer (wraps shotgun_api3).

Only used by the SG_Playlist review type. `shotgun_api3` is imported
lazily inside __init__ rather than at module level, so sites without
ShotGrid configured can import this package freely and simply never
construct a ShotgridService (Options tab hides the SG_Playlist option
entirely when settings.has_shotgrid is False — see config.Settings).
"""
from __future__ import annotations

from ...config import Settings


class ShotgridService:
    def __init__(self, settings: Settings):
        import shotgun_api3
        self._sg = shotgun_api3.Shotgun(
            base_url=settings.sg_url,
            script_name=settings.sg_script_name,
            api_key=settings.sg_script_key,
            http_proxy=settings.sg_proxy,
        )

    def get_playlists_for_project(self, project_id: int) -> list[dict]:
        filters = [["project", "is", {"type": "Project", "id": project_id}]]
        fields = ["id", "code", "project", "description"]
        return self._sg.find("Playlist", filters=filters, fields=fields)

    def get_versions_from_playlist(self, playlist_id: int, custom_fields: list[str] | None = None) -> list[dict]:
        fields = ["id", "code", "sg_ayon_id"] + (custom_fields or [])
        filters = [["playlists", "is", {"type": "Playlist", "id": playlist_id}]]
        return self._sg.find("Version", filters, fields)
