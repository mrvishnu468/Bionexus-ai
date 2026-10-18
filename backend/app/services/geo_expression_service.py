from __future__ import annotations

import asyncio
import gzip
import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

import httpx


class GeoRetrievalError(Exception):
    """Raised when a GEO Series Matrix cannot be retrieved or validated."""


class CacheLike(Protocol):
    """Minimal interface required from the project cache."""

    def get(self, key: str) -> bytes | None:
        ...

    def put(
        self,
        key: str,
        data: bytes,
        category: str = "default",
    ) -> object:
        ...


@dataclass(frozen=True)
class GeoSeriesMatrix:
    """Validated GEO Series Matrix data and retrieval provenance."""

    accession: str
    source_url: str
    title: str
    sample_accessions: tuple[str, ...]
    matrix_rows: int
    matrix_columns: int
    compressed_bytes: int
    sha256: str
    accessed_at: str
    retrieved_at: str
    cache_hit: bool
    payload: bytes


class GeoExpressionService:
    """Retrieve and validate processed expression data from NCBI GEO."""

    MAX_DOWNLOAD_BYTES = 256 * 1024 * 1024
    MAX_ATTEMPTS = 3
    CACHE_MAGIC = b"BIONEXUS_GEO_CACHE_V1\n"

    def __init__(
        self,
        cache: CacheLike | None = None,
        client: httpx.AsyncClient | None = None,
        timeout_seconds: float = 60.0,
        max_download_bytes: int = MAX_DOWNLOAD_BYTES,
        max_attempts: int = MAX_ATTEMPTS,
    ) -> None:
        self.cache = cache
        self.client = client
        self.timeout_seconds = timeout_seconds
        self.max_download_bytes = max_download_bytes
        self.max_attempts = max_attempts

    @staticmethod
    def build_source_url(accession: str) -> str:
        """Build the official NCBI FTP URL for a GEO Series Matrix."""
        normalized = accession.strip().upper()

        if not re.fullmatch(r"GSE\d{3,}", normalized):
            raise ValueError(
                "Accession must be a valid GEO Series ID, such as GSE10072."
            )

        digits = normalized[3:]

        if len(digits) <= 3:
            folder = "GSEnnn"
        else:
            folder = f"GSE{digits[:-3]}nnn"

        return (
            "https://ftp.ncbi.nlm.nih.gov/geo/series/"
            f"{folder}/{normalized}/matrix/"
            f"{normalized}_series_matrix.txt.gz"
        )

    async def fetch(
        self,
        accession: str,
        force_refresh: bool = False,
    ) -> GeoSeriesMatrix:
        """Retrieve a matrix, using the cache when a valid entry exists."""
        normalized = accession.strip().upper()
        url = self.build_source_url(normalized)
        cache_key = f"geo-series-matrix:{normalized}"
        accessed_at = self._now()

        if self.cache is not None and not force_refresh:
            try:
                cached = self.cache.get(cache_key)

                if cached:
                    try:
                        payload, cached_retrieved_at = (
                            self._unpack_cache_record(cached)
                        )
                        legacy_entry = cached_retrieved_at is None

                        if legacy_entry:
                            cached_retrieved_at = accessed_at

                        result = self._inspect(
                            normalized,
                            url,
                            payload,
                            accessed_at,
                            cached_retrieved_at,
                            True,
                        )

                        if legacy_entry:
                            try:
                                self.cache.put(
                                    cache_key,
                                    self._pack_cache_record(
                                        payload,
                                        cached_retrieved_at,
                                    ),
                                    category="geo_series_matrix",
                                )
                            except Exception:
                                pass

                        return result

                    except GeoRetrievalError:
                        pass

            except Exception:
                pass

        payload = await self._download(url)
        retrieved_at = self._now()

        result = self._inspect(
            normalized,
            url,
            payload,
            accessed_at,
            retrieved_at,
            False,
        )

        if self.cache is not None:
            try:
                self.cache.put(
                    cache_key,
                    self._pack_cache_record(payload, retrieved_at),
                    category="geo_series_matrix",
                )
            except Exception:
                pass

        return result

    async def _download(self, url: str) -> bytes:
        """Download compressed data with bounded retries."""
        last_error: Exception | None = None

        for attempt in range(self.max_attempts):
            try:
                return await self._download_with_client(url)

            except GeoRetrievalError:
                raise

            except (httpx.HTTPError, OSError) as exc:
                last_error = exc

                if attempt + 1 < self.max_attempts:
                    await asyncio.sleep(min(2**attempt, 8))

        raise GeoRetrievalError(
            f"Download failed after {self.max_attempts} attempts: "
            f"{last_error}"
        ) from last_error

    async def _download_with_client(self, url: str) -> bytes:
        """Stream a response while enforcing the compressed-byte limit."""
        owns_client = self.client is None
        client = self.client or httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout_seconds),
            follow_redirects=True,
        )

        try:
            async with client.stream("GET", url) as response:
                if response.status_code == 404:
                    raise GeoRetrievalError(
                        "No Series Matrix file was found for this accession."
                    )

                if response.status_code == 429 or response.status_code >= 500:
                    response.raise_for_status()

                if response.status_code >= 400:
                    raise GeoRetrievalError(
                        f"NCBI returned HTTP {response.status_code}."
                    )

                chunks: list[bytes] = []
                total_bytes = 0

                async for chunk in response.aiter_bytes():
                    total_bytes += len(chunk)

                    if total_bytes > self.max_download_bytes:
                        raise GeoRetrievalError(
                            "GEO download exceeds the configured size limit."
                        )

                    chunks.append(chunk)

                payload = b"".join(chunks)

                if not payload:
                    raise GeoRetrievalError(
                        "NCBI returned an empty GEO Series Matrix file."
                    )

                return payload

        finally:
            if owns_client:
                await client.aclose()

    def _inspect(
        self,
        accession: str,
        url: str,
        payload: bytes,
        accessed_at: str,
        retrieved_at: str,
        cache_hit: bool,
    ) -> GeoSeriesMatrix:
        """Validate the compressed matrix and extract basic metadata."""
        try:
            text = gzip.decompress(payload).decode("utf-8")
        except (gzip.BadGzipFile, EOFError, OSError, UnicodeDecodeError) as exc:
            raise GeoRetrievalError(
                "The GEO Series Matrix is not valid UTF-8 gzip data."
            ) from exc

        lines = text.splitlines()
        title = accession
        sample_accessions: tuple[str, ...] = ()
        table_start: int | None = None

        for index, line in enumerate(lines):
            if line.startswith("!Series_title"):
                parts = line.split("\t", 1)

                if len(parts) == 2:
                    title = parts[1].strip().strip('"') or accession

            elif line.startswith("!Sample_geo_accession"):
                parts = line.split("\t")[1:]
                sample_accessions = tuple(
                    value.strip().strip('"')
                    for value in parts
                    if value.strip().strip('"')
                )

            elif line.startswith("!series_matrix_table_begin"):
                table_start = index + 1
                break

        if not sample_accessions:
            raise GeoRetrievalError(
                "The matrix contains no sample accession metadata."
            )

        if table_start is None:
            raise GeoRetrievalError(
                "The GEO file does not contain a series matrix table."
            )
        matrix_rows = 0
        matrix_columns = 0
        header_seen = False

        for line in lines[table_start:]:
            if line.startswith("!series_matrix_table_end"):
                break

            if not line.strip():
                continue

            if not header_seen:
                matrix_columns = len(line.split("\t")) - 1
                header_seen = True
                continue

            matrix_rows += 1

        if matrix_rows == 0 or matrix_columns < 2:
            raise GeoRetrievalError(
                "The GEO matrix table is empty or has an invalid structure."
            )

        return GeoSeriesMatrix(
            accession=accession,
            source_url=url,
            title=title,
            sample_accessions=sample_accessions,
            matrix_rows=matrix_rows,
            matrix_columns=matrix_columns,
            compressed_bytes=len(payload),
            sha256=hashlib.sha256(payload).hexdigest(),
            accessed_at=accessed_at,
            retrieved_at=retrieved_at,
            cache_hit=cache_hit,
            payload=payload,
        )

    @classmethod
    def _pack_cache_record(
        cls,
        payload: bytes,
        retrieved_at: str,
    ) -> bytes:
        """Store retrieval time and compressed matrix in one cache entry."""
        return (
            cls.CACHE_MAGIC
            + retrieved_at.encode("ascii")
            + b"\n"
            + payload
        )

    @classmethod
    def _unpack_cache_record(
        cls,
        cached: bytes,
    ) -> tuple[bytes, str | None]:
        """Read a metadata-bearing entry or identify a legacy raw entry."""
        if not cached.startswith(cls.CACHE_MAGIC):
            return cached, None

        header, separator, payload = cached[len(cls.CACHE_MAGIC):].partition(
            b"\n"
        )

        if not separator or not header or not payload:
            raise GeoRetrievalError("Invalid GEO cache record.")

        try:
            retrieved_at = header.decode("ascii")
            datetime.fromisoformat(retrieved_at)
        except (UnicodeDecodeError, ValueError) as exc:
            raise GeoRetrievalError(
                "Invalid GEO cache timestamp."
            ) from exc

        return payload, retrieved_at

    @staticmethod
    def _now() -> str:
        """Return the current UTC time in ISO 8601 format."""
        return datetime.now(timezone.utc).isoformat()