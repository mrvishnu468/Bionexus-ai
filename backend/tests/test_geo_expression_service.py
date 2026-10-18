
import asyncio
import gzip

import httpx
import pytest

from app.services.geo_expression_service import (
    GeoExpressionService,
    GeoRetrievalError,
)


def matrix_payload():
    text = (
        '!Series_title\t"Example study"\n'
        '!Sample_geo_accession\t"GSM10001"\t"GSM10002"\n'
        '!series_matrix_table_begin\n'
        'ID_REF\tGSM10001\tGSM10002\n'
        'probe1\t2.1\t3.4\n'
        'probe2\t5.0\t4.8\n'
        '!series_matrix_table_end\n'
    )
    return gzip.compress(text.encode("utf-8"))


class MemoryCache:
    def __init__(self):
        self.values = {}
        self.put_calls = 0

    def get(self, key):
        return self.values.get(key)

    def put(self, key, data, category="default"):
        self.put_calls += 1
        self.values[key] = data


def run(coro):
    return asyncio.run(coro)


def test_builds_expected_geo_series_url():
    url = GeoExpressionService.build_source_url("gse10072")
    assert url == (
        "https://ftp.ncbi.nlm.nih.gov/geo/series/"
        "GSE10nnn/GSE10072/matrix/GSE10072_series_matrix.txt.gz"
    )


@pytest.mark.parametrize(
    "accession", ["", "GSM12345", "GSE12", "GSE-1234"]
)
def test_rejects_invalid_accessions(accession):
    with pytest.raises(ValueError):
        GeoExpressionService.build_source_url(accession)


def test_downloads_validates_and_caches_matrix():
    payload = matrix_payload()
    cache = MemoryCache()

    async def handler(request):
        return httpx.Response(200, content=payload, request=request)

    async def scenario():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler)
        ) as client:
            service = GeoExpressionService(cache=cache, client=client)
            result = await service.fetch("GSE10072")

            assert result.title == "Example study"
            assert result.sample_accessions == ("GSM10001", "GSM10002")
            assert result.matrix_rows == 2
            assert result.matrix_columns == 2
            assert result.cache_hit is False
            assert result.retrieved_at is not None
            assert len(result.sha256) == 64
            assert cache.put_calls == 1

    run(scenario())


def test_uses_valid_cached_matrix_without_network():
    cache = MemoryCache()
    cache.values["geo-series-matrix:GSE10072"] = matrix_payload()

    async def handler(request):
        raise AssertionError("Network should not be called for a cache hit")

    async def scenario():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler)
        ) as client:
            service = GeoExpressionService(cache=cache, client=client)
            result = await service.fetch("GSE10072")

            assert result.cache_hit is True
            assert result.retrieved_at is not None
            assert result.matrix_rows == 2

    run(scenario())


def test_retries_transient_server_error():
    calls = {"count": 0}
    payload = matrix_payload()

    async def handler(request):
        calls["count"] += 1
        if calls["count"] == 1:
            return httpx.Response(503, request=request)
        return httpx.Response(200, content=payload, request=request)

    async def scenario():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler)
        ) as client:
            service = GeoExpressionService(client=client, max_attempts=2)
            result = await service.fetch("GSE10072")

            assert result.matrix_rows == 2
            assert calls["count"] == 2

    run(scenario())


def test_rejects_non_gzip_payload():
    async def handler(request):
        return httpx.Response(200, content=b"not gzip", request=request)

    async def scenario():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler)
        ) as client:
            service = GeoExpressionService(client=client)
            with pytest.raises(GeoRetrievalError, match="valid UTF-8 gzip"):
                await service.fetch("GSE10072")

    run(scenario())


def test_rejects_download_over_configured_limit():
    payload = matrix_payload()

    async def handler(request):
        return httpx.Response(200, content=payload, request=request)

    async def scenario():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler)
        ) as client:
            service = GeoExpressionService(
                client=client, max_download_bytes=8
            )
            with pytest.raises(GeoRetrievalError, match="exceeds"):
                await service.fetch("GSE10072")

    run(scenario())
