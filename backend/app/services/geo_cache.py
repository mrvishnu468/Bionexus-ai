
from __future__ import annotations

from pathlib import Path

from app.core.cache_manager import DiskCache
from app.services.geo_expression_service import GeoExpressionService


def create_geo_expression_service(
    cache_root: str | Path,
    max_cache_bytes: int = 1024 * 1024 * 1024,
) -> GeoExpressionService:
    """Build the GEO retrieval service using BioNexus's existing disk cache."""
    cache = DiskCache(
        root=cache_root,
        max_bytes=max_cache_bytes,
    )
    return GeoExpressionService(cache=cache)
