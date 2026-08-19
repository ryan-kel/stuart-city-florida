# Stuart City Commission map

Unofficial precinct map of the August 18, 2026 City of Stuart commission primary. Live at [electoralanalytics.net/projects/stuart-city-commission](https://electoralanalytics.net/projects/stuart-city-commission/).

## Refresh

```bash
bash scripts/poll_results.sh
```

Open `map.html` from a local server. The page reloads `data/map_data.json` every 60 seconds. The live site file is `primary_map.html`.

## Calls

A race is called as an apparent winner when every precinct has reported and the margin is above Florida's automatic-recount threshold. Group I stays in recount while that threshold applies. Override in `data/race_call_overrides.json`.

## Publish

```bash
cd ../electoralanalytics-site
npm run publish:project -- stuart-city-commission [--push]
```
