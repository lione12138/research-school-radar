# Research Seasonal School Radar

An open-source radar for research seasonal training opportunities in water, climate, hydrology, geoscience, remote sensing, AI, and scientific machine learning.

It monitors trusted academic sources, extracts deadline/funding/fee/duration evidence, separates fully qualified opportunities from near-matches, and publishes a static website that can update daily for free on GitHub Pages.

[Technical README](docs/TECHNICAL.md) | [中文技术说明](docs/TECHNICAL.zh-CN.md) | [MIT License](LICENSE)

## Upcoming Research Training Opportunities

The generated website shows maintainer-reviewed opportunities first, followed by scanner results.

- **Curated Opportunities**: high-confidence records reviewed by maintainers.
- **Fully Qualified Opportunities**: scanner results that satisfy every hard condition.
- **Closest Still-Open Near-Matches**: relevant opportunities with explicit failed conditions.
- **Sources & Coverage**: the configured trusted source registry, including disabled sources and notes.

The site includes filters for keyword, status, topic, financial access, and deadline status. Rows with a known application deadline include an **Add to calendar** link that downloads a standard `.ics` event.

```text
site/index.html
site/candidates.json
site/curated.json
site/sources.html
site/sources.json
reports/YYYY-MM-DD.md
```

## What Counts As Fully Qualified?

An opportunity must satisfy all hard conditions:

| Condition | Requirement |
|---|---|
| Deadline | Application is still open or deadline has not passed |
| Duration | At least 8 days |
| Financial access | Explicit funding is available, or the confirmed total fee is no more than approximately EUR 400 |
| Mode | In-person or substantially on-site, not online-only |
| Topic | Relevant to water, hydrology, hydrogeology, climate, environmental modelling, remote sensing, geoscience, disaster risk, AI, or scientific ML |

Near-matches are never presented as qualified results.

Foreign-currency fees are converted with configurable fixed reference rates so the default workflow remains free and API-key-free. The rates are deliberately conservative, not real-time. Unknown currencies or ambiguous fees remain near-matches.

`Training school` is retained because many research networks use it for the same kind of short, intensive programme as a summer school. A generic conference workshop is excluded; workshops are considered only when they clearly describe hands-on, field, practical, or capacity-building training and still satisfy the duration and other hard conditions.

## Why Not Another Summer School List?

Most summer school lists are plain link collections. This project is different:

- trusted source registry instead of random web crawling
- structured extraction for deadline, funding, duration, mode, eligibility, and location
- hard filters with visible failed conditions
- maintainer-reviewed curated layer
- static public website plus Markdown and JSON outputs
- daily free automation with GitHub Actions and GitHub Pages
- source coverage transparency through a generated Sources & Coverage page

## Doctoral Schools Scope

The radar may include short-term doctoral schools or PhD schools when they are seasonal research training opportunities, such as a one-week or two-week thematic training school for doctoral researchers.

It does **not** target PhD admissions, PhD positions, full-time doctoral degree programmes, or ordinary graduate school enrollment.

## Quick Start

```powershell
git clone <this-repository>
cd <this-repository>
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
python -m research_school_radar.cli scan --offline-sample
```

Then open:

- `site/index.html`
- `reports/YYYY-MM-DD.md`

Run a real fixed-source scan:

```powershell
python -m research_school_radar.cli scan
```

## Daily Free Publishing

The included GitHub Actions workflow can:

1. run the scanner every day
2. commit the Markdown report and seen database
3. build `site/index.html`
4. deploy the static site to GitHub Pages

For a public repository, the default workflow does not require a paid search API key.

## Development

```powershell
pip install -e ".[dev]"
pytest
```

Tests run automatically in CI on every push and pull request. See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Contributing Opportunities

Use the GitHub issue template:

```text
.github/ISSUE_TEMPLATE/submit-opportunity.yml
```

Maintainers can review submitted or scanned opportunities and add high-confidence records to:

```text
data/opportunities.yml
```

## Project Shape

```text
config/sources.yaml
        |
        v
collect -> parse -> extract -> filter -> rank
        |
        +--> reports/YYYY-MM-DD.md
        +--> site/index.html
        +--> site/candidates.json
        +--> data/seen.sqlite
```

See [docs/TECHNICAL.md](docs/TECHNICAL.md) for implementation details, current limitations, and the improvement roadmap.
