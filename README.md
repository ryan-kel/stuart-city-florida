# Stuart City Commission map

Official citywide results and archived unofficial precinct map of the August 18, 2026 City of Stuart commission primary. Live at [electoralanalytics.net/projects/stuart-city-commission](https://electoralanalytics.net/projects/stuart-city-commission/).

## Refresh

```bash
bash scripts/poll_results.sh
```

Open `map.html` from a local server. The live site file is `primary_map.html`. Both repositories now use manual polling only. The election-night precinct snapshot is dated August 18, 2026; it must not be presented as the final precinct allocation.

## Official results and archived precincts

`data/official_results.json` records citywide totals from the City of Stuart's
[official election page](https://www.stuartfl.gov/160/Election-Information).
The city's [August 21 notice](https://www.stuartfl.gov/CivicSend/ViewMessage/message/298453)
confirms that results were finalized August 20. Group I is Rich 1,783 and
Laughlin 1,764; Group III is Matheson 2,087 and Ogden 1,500; Group V is Clarke
1,869, Oldenborg 1,153, and Micciche 566.

The builder attaches those totals as `official_result` and uses them for the
citywide summary and winner. It preserves the older `totals`, `by_type`, and
precinct votes as the unofficial election-night record. The map, popup, and
table identify that earlier snapshot. Do not allocate the citywide difference
to precincts without a verified precinct source.

```bash
python3 scripts/test_official_results.py
```

The tests check the city's published totals, reject incomplete or inconsistent
results, and verify that attaching official totals does not alter precinct votes.

## Publish

```bash
cd ../electoralanalytics-site
npm run publish:project -- stuart-city-commission [--push]
```
