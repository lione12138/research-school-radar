from __future__ import annotations

import responses

from research_school_radar.search import BRAVE_ENDPOINT, run_discovery_queries


def test_discovery_skipped_without_api_key(monkeypatch) -> None:
    monkeypatch.delenv("BRAVE_SEARCH_API_KEY", raising=False)
    results, errors = run_discovery_queries(["hydrology summer school"])
    assert results == []
    assert len(errors) == 1
    assert "BRAVE_SEARCH_API_KEY is not set" in errors[0]


@responses.activate
def test_discovery_parses_brave_results(monkeypatch) -> None:
    monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "test-key")
    responses.add(
        responses.GET,
        BRAVE_ENDPOINT,
        json={
            "web": {
                "results": [
                    {
                        "title": "Hydrology Summer School",
                        "url": "https://example.org/school",
                        "description": "Travel grants available.",
                    }
                ]
            }
        },
        status=200,
    )
    results, errors = run_discovery_queries(["hydrology summer school"])
    assert not errors
    assert len(results) == 1
    assert results[0].title == "Hydrology Summer School"
    assert results[0].url == "https://example.org/school"
    assert results[0].snippet == "Travel grants available."
    assert results[0].query == "hydrology summer school"


@responses.activate
def test_discovery_reports_failed_queries(monkeypatch) -> None:
    monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "test-key")
    responses.add(responses.GET, BRAVE_ENDPOINT, status=429)
    results, errors = run_discovery_queries(["hydrology summer school"])
    assert results == []
    assert len(errors) == 1
    assert "Discovery query failed" in errors[0]
