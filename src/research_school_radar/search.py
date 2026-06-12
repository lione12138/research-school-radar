from __future__ import annotations

import os
import time
from dataclasses import dataclass

import requests


BRAVE_ENDPOINT = "https://api.search.brave.com/res/v1/web/search"
# The Brave Search free plan allows roughly one request per second.
REQUEST_INTERVAL_SECONDS = 1.1


@dataclass(slots=True)
class SearchResult:
    title: str
    url: str
    snippet: str
    query: str


def run_discovery_queries(queries: list[str], max_results_per_query: int = 5) -> tuple[list[SearchResult], list[str]]:
    api_key = os.getenv("BRAVE_SEARCH_API_KEY")
    if not api_key:
        return [], [
            "Controlled discovery skipped: BRAVE_SEARCH_API_KEY is not set. "
            "(Bing Web Search was retired by Microsoft in 2025 and is no longer supported.)"
        ]

    results: list[SearchResult] = []
    errors: list[str] = []
    headers = {"X-Subscription-Token": api_key, "Accept": "application/json"}
    for index, query in enumerate(queries):
        if index:
            time.sleep(REQUEST_INTERVAL_SECONDS)
        try:
            response = requests.get(
                BRAVE_ENDPOINT,
                headers=headers,
                params={"q": query, "count": max_results_per_query},
                timeout=20,
            )
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as exc:
            errors.append(f"Discovery query failed for {query!r}: {exc}")
            continue
        for item in payload.get("web", {}).get("results", []):
            results.append(
                SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=item.get("description", ""),
                    query=query,
                )
            )
    return results, errors
