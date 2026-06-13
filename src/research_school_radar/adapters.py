"""Source-specific extraction adapters.

The generic rule-based extractor in ``extract.py`` works across every source,
but high-value sites with a stable page structure deserve a precise parser.
An adapter receives a fetched :class:`Page` and returns a dict of field
overrides; any value it supplies replaces the generic guess for that field.

Adapters are intentionally conservative: they only return a field when they
can read it from the page's known structure, and otherwise stay silent so the
generic extractor remains the fallback.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Any, Callable
from urllib.parse import urlparse

from dateutil import parser as date_parser

from .models import Page
from .utils import clean_space


def adapter_for(url: str) -> Callable[[Page], dict[str, Any]] | None:
    host = (urlparse(url).hostname or "").lower()
    for domain, func in _ADAPTERS.items():
        if host == domain or host.endswith("." + domain):
            return func
    return None


def _parse_date(value: str) -> date | None:
    try:
        return date_parser.parse(value, dayfirst=True).date()
    except (ValueError, OverflowError):
        return None


_DATE = r"\d{1,2}\s+[A-Za-z]+\s+20\d{2}"
_GENERIC_VENUES = {"icimod", "icimod lml", "online", "virtual", "hybrid", "tbc", "tba"}


def _icimod(page: Page) -> dict[str, Any]:
    """Parse ICIMOD event pages, which use a fixed ``Venue ... Date & Time ...
    Contact ...`` block and a separate research-funder acknowledgements section."""
    text = page.text
    overrides: dict[str, Any] = {}

    block = re.search(rf"Date\s*&\s*Time\s+({_DATE})\s*(?:to|–|—|-)\s*({_DATE})", text)
    if block:
        start = _parse_date(block.group(1))
        end = _parse_date(block.group(2))
        if start and end:
            overrides["start_date"] = start
            overrides["end_date"] = end

    venue = re.search(r"Venue\s+(.+?)\s+Date\s*&\s*Time", text)
    if venue:
        location = clean_space(venue.group(1))
        if location and location.lower() not in _GENERIC_VENUES:
            overrides["location"] = location

    # Participant support is read only from the body, before the
    # "Funding and acknowledgements" section, which credits research funders
    # rather than describing support for participants.
    body = re.split(r"Funding and acknowledgements", text, maxsplit=1)[0]
    if re.search(
        r"\b(?:will cover|covers|will be covered|fully (?:cover|covers|funded|covered)|cover all)\b"
        r"[^.\n]{0,60}\b(?:cost|costs|travel|airfare|accommodation|expenses|board|lodging)\b",
        body,
        flags=re.IGNORECASE,
    ):
        overrides["funding_available"] = True
        overrides["funding_type"] = ["organiser-covered costs"]

    return overrides


_ADAPTERS: dict[str, Callable[[Page], dict[str, Any]]] = {
    "icimod.org": _icimod,
}
