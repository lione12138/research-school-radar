from __future__ import annotations

from datetime import date
from pathlib import Path

from .models import Candidate


def write_report(candidates: list[Candidate], output_dir: Path, errors: list[str] | None = None) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{date.today().isoformat()}.md"
    path.write_text(render_report(candidates, errors or []), encoding="utf-8")
    return path


def render_report(candidates: list[Candidate], errors: list[str]) -> str:
    full = [item for item in candidates if item.fully_qualified][:10]
    near = [item for item in candidates if not item.fully_qualified and item.deadline_status != "closed"][:5]
    lines = [f"# Research Seasonal School Radar Report - {date.today().isoformat()}", ""]

    if errors:
        lines.extend(["## Collection Notes", ""])
        lines.extend(f"- {error}" for error in errors[:20])
        lines.append("")

    if full:
        lines.extend(["## Fully Qualified Opportunities", ""])
        lines.append("| # | title | type | organizer | location | duration | deadline | funding / fee | topic | eligibility | reason |")
        lines.append("|---|---|---|---|---|---|---|---|---|---|---|")
        for index, candidate in enumerate(full, start=1):
            lines.append(
                "| "
                + " | ".join(
                    [
                        str(index),
                        f"[{_cell(candidate.title)}]({candidate.source_url})",
                        _cell(candidate.type),
                        _cell(candidate.organizer),
                        _cell(candidate.location),
                        _cell(_duration(candidate)),
                        _cell(candidate.deadline.isoformat() if candidate.deadline else "uncertain"),
                        _cell(candidate.financial_summary),
                        _cell(", ".join(candidate.topic_keywords)),
                        _cell(candidate.eligibility or candidate.target_level),
                        _cell(candidate.recommendation_reason),
                    ]
                )
                + " |"
            )
    else:
        lines.extend(["**No fully qualified opportunities found.**", ""])
        if near:
            lines.extend(["## Closest Still-Open Near-Matches", ""])
            lines.append("| title | type | organizer | location | duration | deadline | funding / fee | topic |")
            lines.append("|---|---|---|---|---|---|---|---|")
            for candidate in near:
                lines.append(
                    "| "
                    + " | ".join(
                        [
                            f"[{_cell(candidate.title)}]({candidate.source_url})",
                            _cell(candidate.type),
                            _cell(candidate.organizer),
                            _cell(candidate.location),
                            _cell(_duration(candidate)),
                            _cell(candidate.deadline.isoformat() if candidate.deadline else "uncertain"),
                            _cell(candidate.financial_summary),
                            _cell(", ".join(candidate.topic_keywords) or "uncertain"),
                        ]
                    )
                    + " |"
                )
        else:
            lines.append("No still-open near-matches were found.")

    lines.append("")
    return "\n".join(lines)


def _duration(candidate: Candidate) -> str:
    return f"{candidate.duration_days} days" if candidate.duration_days else "uncertain"


def _cell(value: str) -> str:
    return str(value or "uncertain").replace("|", "\\|").replace("\n", " ").strip()
