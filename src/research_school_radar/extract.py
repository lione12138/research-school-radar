from __future__ import annotations

import re
from datetime import date

from dateutil import parser as date_parser

from .models import Candidate, Page, Source
from .parse import OPPORTUNITY_TERMS, has_programme_signal
from .utils import clean_space, evidence_window, first_match


FUNDING_PATTERNS = {
    "travel grant": r"travel grant[s]?",
    "scholarship": r"scholarship[s]?",
    "tuition waiver": r"tuition waiver[s]?",
    "stipend": r"stipend[s]?",
    "accommodation support": r"accommodation support|covered accommodation|accommodation is covered",
    "financial support": r"financial support|funding available|support is available",
}

ONLINE_ONLY_PATTERNS = [r"online-only", r"fully online", r"online course", r"webinar"]
IN_PERSON_PATTERNS = [r"in[- ]person", r"on[- ]site", r"residential", r"field school", r"venue", r"hosted in"]
SUPPORTED_FEE_CURRENCIES = {
    "EUR",
    "USD",
    "GBP",
    "CHF",
    "CNY",
    "RMB",
    "JPY",
    "INR",
    "KRW",
    "SGD",
    "AUD",
    "CAD",
}


def extract_candidate(page: Page, profile: dict) -> Candidate | None:
    if not _has_opportunity_signal(page.text):
        return None

    text = page.text
    preferred_topics = profile.get("preferred_topics", [])
    topics = [topic for topic in preferred_topics if _topic_in_text(topic, text)]
    programme_type = _programme_type(text)
    start, end = _extract_dates(text)
    deadline = _extract_deadline(text)
    funding_types = [
        label for label, pattern in FUNDING_PATTERNS.items() if re.search(pattern, text, flags=re.IGNORECASE)
    ]
    funding_evidence = evidence_window(text, r"scholarship|travel grant|tuition waiver|stipend|financial support|funding")
    mode = _extract_mode(text)
    title = _extract_title(page, programme_type)
    eligibility = first_match(
        text,
        [
            r"(?:eligibility|eligible participants|who should apply)[:\s-]+([^.;\n]{20,220})",
            r"((?:PhD|doctoral|MSc|master|postdoc|early-career)[^.;\n]{0,160})",
        ],
    )
    fee = _extract_fee(text)

    return Candidate(
        title=title,
        type=programme_type,
        organizer=page.source.name,
        source_layer=str(page.source.layer),
        region_priority=_region_priority(page.source.region, profile),
        location=_extract_location(page.html, text, page.source.region),
        mode=mode,
        start_date=start,
        end_date=end,
        duration_days=_duration_days(start, end),
        deadline=deadline,
        deadline_status=_deadline_status(deadline),
        funding_available=True if funding_types else None,
        funding_type=funding_types,
        funding_evidence=funding_evidence,
        topic_keywords=topics,
        eligibility=eligibility,
        target_level=_target_level(text),
        fee=fee,
        fee_eur=_fee_to_eur(fee, profile),
        application_link=page.url,
        source_url=page.url,
        summary=_summary(text),
        recommendation_reason="",
        risk_points="",
    )


def sample_candidate(profile: dict) -> Candidate:
    start_year = date.today().year + 1
    deadline_year = date.today().year + 1
    page = Page(
        url="https://example.org/hydrology-winter-school",
        title="Example Hydrology Winter School",
        text=(
            "Example Hydrology Winter School is an in-person residential training school hosted in Germany. "
            f"Dates: 10 January {start_year} to 20 January {start_year}. "
            f"Application deadline: 15 October {deadline_year}. "
            "Travel grants and tuition waivers are available for selected PhD, MSc and early-career researchers. "
            "Topics include hydrology, climate extremes, water resources, environmental modelling and remote sensing. "
            "Fee: 300 EUR."
        ),
        html="",
        source=Source(
            name="Sample Institute",
            url="https://example.org/hydrology-winter-school",
            layer="sample",
            region="continental Europe",
            source_type="sample",
        ),
        fetched_at=date.today(),
    )
    candidate = extract_candidate(page, profile)
    if candidate is None:
        raise RuntimeError("sample candidate failed extraction")
    return candidate


def _extract_fee(text: str) -> str:
    free = first_match(
        text,
        [
            r"\b(free of charge)\b",
            r"\b(no (?:registration|participation|tuition) fee)\b",
            r"\b(participation is free)\b",
        ],
    )
    if free:
        return free
    return first_match(
        text,
        [
            r"(?:registration fee|participation fee|tuition fee|course fee|fee|cost)[:\s-]+([^.;\n]{1,100})",
            r"((?:(?:EUR|USD|GBP|CHF|CNY|RMB|JPY|INR|KRW|SGD|AUD|CAD)|[€$£])\s?\d[\d ,.]*\d\s+(?:registration|participation|tuition|course)?\s*(?:fee|cost))",
        ],
    )


def _fee_to_eur(fee: str, profile: dict) -> float | None:
    if not fee:
        return None
    if re.search(r"\bfree of charge\b|\bno (?:registration|participation|tuition) fee\b|\bparticipation is free\b", fee, re.IGNORECASE):
        return 0.0

    currency = _fee_currency(fee)
    if currency is None:
        return None

    rates = profile.get("financial_access", {}).get("approximate_currency_to_eur", {})
    rate = rates.get(currency)
    if rate is None and currency == "RMB":
        rate = rates.get("CNY")
    if rate is None:
        return None

    amounts = [_parse_amount(value) for value in re.findall(r"\d[\d ,.]*\d|\d", fee)]
    valid_amounts = [amount for amount in amounts if amount is not None]
    if not valid_amounts:
        return None
    return round(max(valid_amounts) * float(rate), 2)


def _fee_currency(fee: str) -> str | None:
    code = re.search(r"\b(" + "|".join(sorted(SUPPORTED_FEE_CURRENCIES)) + r")\b", fee, re.IGNORECASE)
    if code:
        return code.group(1).upper()
    if "€" in fee:
        return "EUR"
    if "£" in fee:
        return "GBP"
    if "$" in fee:
        return "USD"
    return None


def _parse_amount(value: str) -> float | None:
    compact = value.replace(" ", "")
    if not compact:
        return None
    if "," in compact and "." in compact:
        decimal_separator = "," if compact.rfind(",") > compact.rfind(".") else "."
        thousands_separator = "." if decimal_separator == "," else ","
        compact = compact.replace(thousands_separator, "").replace(decimal_separator, ".")
    elif "," in compact:
        compact = compact.replace(",", "" if len(compact.rsplit(",", 1)[1]) == 3 else ".")
    elif "." in compact and len(compact.rsplit(".", 1)[1]) == 3:
        compact = compact.replace(".", "")
    try:
        return float(compact)
    except ValueError:
        return None


def _has_opportunity_signal(text: str) -> bool:
    return has_programme_signal(text)


def _programme_type(text: str) -> str:
    lowered = text.lower()
    for term in OPPORTUNITY_TERMS:
        if term in lowered:
            return term
    return "research training"


def _extract_title(page: Page, programme_type: str) -> str:
    title = page.title
    if len(title) > 140:
        title = title[:137].rstrip() + "..."
    return title or programme_type.title()


def _extract_dates(text: str) -> tuple[date | None, date | None]:
    patterns = [
        r"(\d{1,2}\s+[A-Z][a-z]+\s+20\d{2})\s*(?:to|-|–|until)\s*(\d{1,2}\s+[A-Z][a-z]+\s+20\d{2})",
        r"([A-Z][a-z]+\s+\d{1,2},?\s+20\d{2})\s*(?:to|-|–|until)\s*([A-Z][a-z]+\s+\d{1,2},?\s+20\d{2})",
        r"(20\d{2}-\d{2}-\d{2})\s*(?:to|-|–|until)\s*(20\d{2}-\d{2}-\d{2})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        try:
            return date_parser.parse(match.group(1), dayfirst=True).date(), date_parser.parse(match.group(2), dayfirst=True).date()
        except (ValueError, OverflowError):
            continue
    return None, None


def _extract_deadline(text: str) -> date | None:
    match = re.search(
        r"(?:application deadline|deadline|apply by|applications close)[:\s]*(\d{1,2}\s+[A-Z][a-z]+\s+20\d{2}|[A-Z][a-z]+\s+\d{1,2},?\s+20\d{2}|20\d{2}-\d{2}-\d{2})",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    try:
        return date_parser.parse(match.group(1), dayfirst=True).date()
    except (ValueError, OverflowError):
        return None


def _deadline_status(deadline: date | None) -> str:
    if deadline is None:
        return "uncertain"
    return "open" if deadline >= date.today() else "closed"


def _duration_days(start: date | None, end: date | None) -> int | None:
    if not start or not end:
        return None
    return (end - start).days + 1


def _extract_mode(text: str) -> str:
    if any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in IN_PERSON_PATTERNS):
        if re.search(r"hybrid", text, flags=re.IGNORECASE):
            return "hybrid"
        return "in-person"
    if any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in ONLINE_ONLY_PATTERNS):
        return "online"
    if re.search(r"hybrid", text, flags=re.IGNORECASE):
        return "hybrid"
    return "uncertain"


def _extract_location(html: str, text: str, fallback_region: str) -> str:
    location = _html_label_value(html, ["Location", "Venue", "Place"])
    if not location:
        location = first_match(
            text,
            [
                r"(?:location|venue|place)\s*:\s*([^.;\n]{2,100})",
                r"hosted in\s+([^.;\n]{2,80})",
            ],
        )
    location = _clean_label_value(location)
    if location and location.split()[0].lower() in {"a", "an", "the", "that", "which"}:
        location = ""
    return _public_region_name(location or fallback_region)


def _public_region_name(value: str) -> str:
    return "Europe" if value.strip().lower() == "continental europe" else value


def _html_label_value(html: str, labels: list[str]) -> str:
    if not html:
        return ""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    for element in soup(["script", "style", "noscript"]):
        element.decompose()
    lines = [clean_space(line) for line in soup.get_text("\n").splitlines()]
    lines = [line for line in lines if line]
    normalized_labels = {label.lower() for label in labels}
    stop_labels = {
        "date",
        "dates",
        "date & time",
        "date and time",
        "time",
        "contact",
        "contacts",
        "organizer",
        "organiser",
        "agenda",
        "application",
        "deadline",
        "fee",
        "fees",
        "funding",
    }
    for index, line in enumerate(lines):
        lowered = line.rstrip(":").lower()
        if lowered not in normalized_labels:
            continue
        values: list[str] = []
        for candidate in lines[index + 1 : index + 4]:
            candidate_lower = candidate.rstrip(":").lower()
            if candidate_lower in stop_labels:
                break
            values.append(candidate)
            if len(" ".join(values)) >= 8:
                break
        return _clean_label_value(" ".join(values))
    return ""


def _clean_label_value(value: str) -> str:
    value = clean_space(value)
    if not value:
        return ""
    stop_patterns = [
        r"\bDate\s*&\s*Time\b",
        r"\bDate\s+and\s+Time\b",
        r"\bContact\b",
        r"\bAgenda\b",
        r"\bApplication\b",
        r"\bDeadline\b",
        r"\bFunding\b",
    ]
    for pattern in stop_patterns:
        match = re.search(pattern, value, flags=re.IGNORECASE)
        if match:
            value = value[: match.start()]
    return clean_space(value).rstrip(" ,;&")


def _topic_in_text(topic: str, text: str) -> bool:
    flags = re.IGNORECASE
    if len(topic) <= 3:
        return re.search(rf"\b{re.escape(topic)}\b", text, flags=flags) is not None
    return re.search(re.escape(topic), text, flags=flags) is not None


def _target_level(text: str) -> str:
    levels = []
    for label, pattern in [
        ("MSc", r"\bMSc\b|master"),
        ("PhD", r"\bPhD\b|doctoral"),
        ("postdoc", r"postdoc"),
        ("early-career researcher", r"early[- ]career"),
    ]:
        if re.search(pattern, text, flags=re.IGNORECASE):
            levels.append(label)
    return ", ".join(levels) if levels else "uncertain"


def _region_priority(region: str, profile: dict) -> str:
    if region in profile.get("priority_regions", []):
        return "priority"
    if region in profile.get("supplementary_regions", []):
        return "supplementary"
    if region == "global":
        return "global"
    return "unclassified"


def _summary(text: str) -> str:
    return clean_space(text[:280])
