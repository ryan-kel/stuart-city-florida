# Stuart City Commission map — AGENTS.md

Project-specific orientation. Read this file and `README.md` before editing.

## Standards (shared, do not duplicate)

- Style: `~/sites/electoralanalytics-site/docs/style/README.md`
- Prose: `prose-voice.md` Part 1 + `prose-mechanics.md`
- Charts / maps: `dataviz.md` §2 and §4
- Lint: `node ~/shared/tools/ea-lint.mjs .`

## What this is

Official citywide results and archived unofficial precinct map of the City of Stuart, Florida, August 18, 2026 city commission primary. Groups I, III, and V. Page: `electoralanalytics.net/projects/stuart-city-commission/`. `featured` is false; it is not on the homepage.

Chrome, fonts, and candidate colors follow the NYC primary tracker (`ny-primary-2026`): Georgia titles, Segoe UI chrome, navy/gold header, Leaflet fills from the tracker palette (blue / teal / amber). The live page file is `primary_map.html`.

## Data provenance

- Official citywide votes: `data/official_results.json`, transcribed from the City of Stuart official election page. See README for source links.
- Archived precinct votes: Martin County Supervisor of Elections Clarity unofficial detail XML (`data/raw/xml/detail.xml`), election 126768.
- Geography: Martin County GIS `Administrative_Areas/Administrative_Areas` MapServer, Voting Districts (layer 13) clipped to Municipal Boundaries City of Stuart (layer 0).
- Polling-place labels: Supervisor of Elections Google My Maps KML linked from [Precinct Maps](https://www.martinvotes.gov/election-information/precinct-maps/).

## Pipeline

```bash
bash scripts/poll_results.sh
```

Writes `data/map_data.json`. Open `map.html` from a local server. Both repositories use manual polling only; no scheduled refresh runs.

## Eligibility / accuracy rules

- Map only the precincts that reported city-commission votes, clipped to the city boundary.
- Do not treat the archived Clarity precinct file as final. Official citywide results live in the separate `official_result` field; never allocate their difference to precincts without a verified source.
- Verify totals from `data/map_data.json`, not from news copy.

## Deployment

```bash
cd ~/sites/electoralanalytics-site
npm run publish:project -- stuart-city-commission
```

Do not pass `--push` while unrelated site files are dirty. Commit only the Stuart paths, then push `main`.
