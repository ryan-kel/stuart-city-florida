#!/usr/bin/env python3
"""Join Clarity precinct votes to Stuart geometry and apply race calls."""

from __future__ import annotations

import json
import os
import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(os.environ.get("STUART_ROOT", Path(__file__).resolve().parents[1]))
RAW = Path(os.environ.get("STUART_RAW", ROOT / "data" / "raw"))
GIS = RAW / "gis"
OUT = Path(os.environ.get("STUART_OUT", ROOT / "data"))

# NYC primary-tracker palette, skipping purple (#7c3aed) so two-way races stay distinct.
COLOR_A = "#1d4ed8"  # blue
COLOR_B = "#0d9488"  # teal
COLOR_C = "#b45309"  # amber

CONTESTS = {
    "0024": {
        "id": "group1",
        "label": "Group I",
        "office": "City Commissioner Group I",
        "focus": True,
        "candidates": [
            {"id": "rich", "name": "Campbell Rich", "color": COLOR_A, "incumbent": True},
            {"id": "laughlin", "name": "Will Laughlin", "color": COLOR_B, "incumbent": False},
        ],
    },
    "0025": {
        "id": "group3",
        "label": "Group III",
        "office": "City Commissioner Group III",
        "focus": False,
        "candidates": [
            {"id": "matheson", "name": "Merritt Matheson", "color": COLOR_A, "incumbent": True},
            {"id": "ogden", "name": "Derreck Ogden", "color": COLOR_B, "incumbent": False},
        ],
    },
    "0026": {
        "id": "group5",
        "label": "Group V",
        "office": "City Commissioner Group V",
        "focus": False,
        "candidates": [
            {"id": "clarke", "name": "Eula R. Clarke", "color": COLOR_A, "incumbent": True},
            {"id": "oldenborg", "name": "Dayne Oldenborg", "color": COLOR_B, "incumbent": False},
            {"id": "micciche", "name": "Kylie Micciche", "color": COLOR_C, "incumbent": False},
        ],
    },
}

NAME_TO_ID = {
    "Campbell Rich": "rich",
    "Will Laughlin": "laughlin",
    "Merritt Matheson": "matheson",
    "Derreck Ogden": "ogden",
    "Eula R. Clarke": "clarke",
    "Dayne Oldenborg": "oldenborg",
    "Kylie Micciche": "micciche",
}

VOTE_TYPES = ("Election Day", "Vote by Mail", "Early Voting")
FL_RECOUNT_SHARE = 0.005
FL_RECOUNT_UNOFFICIAL_SHARE = 0.0055
APPARENT_MIN_MARGIN_SHARE = 0.025
MAJORITY_SHARE = 0.5


def slug_vote_type(name: str) -> str:
    return {"Election Day": "election_day", "Vote by Mail": "mail", "Early Voting": "early"}[name]


def polygons_only(geom):
    from shapely import make_valid
    from shapely.ops import unary_union

    geom = make_valid(geom)
    if geom.is_empty:
        return None
    if geom.geom_type in ("Polygon", "MultiPolygon"):
        return geom
    if geom.geom_type == "GeometryCollection":
        parts = [
            g for g in geom.geoms if g.geom_type in ("Polygon", "MultiPolygon") and not g.is_empty
        ]
        if not parts:
            return None
        return make_valid(unary_union(parts))
    return None


def parse_results():
    root = ET.parse(RAW / "xml" / "detail.xml").getroot()
    meta = {
        "election": root.findtext("ElectionName"),
        "election_date": root.findtext("ElectionDate"),
        "timestamp": root.findtext("Timestamp"),
        "region": root.findtext("Region"),
    }
    version_path = RAW / "current_ver.txt"
    meta["clarity_version"] = version_path.read_text().strip() if version_path.exists() else None
    races = {}
    for contest in root.findall("Contest"):
        spec = CONTESTS.get(contest.get("key"))
        if not spec:
            continue
        race = {
            **spec,
            "precincts_reporting": int(contest.get("precinctsReported") or 0),
            "precincts_total": int(contest.get("precinctsReporting") or 0),
            "precincts": {},
            "totals": {c["id"]: 0 for c in spec["candidates"]},
            "by_type": {
                slug_vote_type(vt): {c["id"]: 0 for c in spec["candidates"]} for vt in VOTE_TYPES
            },
        }
        for choice in contest.findall("Choice"):
            cid = NAME_TO_ID[choice.get("text")]
            for vote_type in choice.findall("VoteType"):
                vt_name = vote_type.get("name")
                if vt_name not in VOTE_TYPES:
                    continue
                vt_key = slug_vote_type(vt_name)
                for precinct in vote_type.findall("Precinct"):
                    pid = precinct.get("name")
                    votes = int(precinct.get("votes") or 0)
                    slot = race["precincts"].setdefault(
                        pid,
                        {
                            "votes": defaultdict(int),
                            "by_type": {slug_vote_type(vt): defaultdict(int) for vt in VOTE_TYPES},
                        },
                    )
                    slot["votes"][cid] += votes
                    slot["by_type"][vt_key][cid] += votes
                    race["totals"][cid] += votes
                    race["by_type"][vt_key][cid] += votes
        races[spec["id"]] = race
    return meta, races


def load_poll_places():
    kml_path = GIS / "mymaps_34aad4a7.kml"
    if not kml_path.exists():
        return {}
    from lxml import etree

    ns = {"k": "http://www.opengis.net/kml/2.2"}
    tree = etree.parse(str(kml_path))
    places = {}
    for folder in tree.findall(".//k:Folder", ns):
        if (folder.findtext("k:name", namespaces=ns) or "") != "Precincts":
            continue
        for pm in folder.findall("k:Placemark", ns):
            name = pm.findtext("k:name", namespaces=ns) or ""
            m = re.search(r"(\d+)", name)
            if not m:
                continue
            places[m.group(1)] = (pm.findtext("k:description", namespaces=ns) or "").strip()
    return places


def build_geometry():
    from shapely.geometry import mapping, shape

    muni = json.loads((GIS / "municipal.geojson").read_text())
    city_feat = next(f for f in muni["features"] if f["properties"].get("DESC_") == "City of Stuart")
    city = polygons_only(shape(city_feat["geometry"]))
    if city is None:
        raise SystemExit("City of Stuart boundary is empty")
    city = city.simplify(0.00005, preserve_topology=True)

    vtd = json.loads((GIS / "voting_districts.geojson").read_text())
    places = load_poll_places()
    features = []
    for feat in vtd["features"]:
        pid = str(feat["properties"]["DISTRICT"]).lstrip("0") or "0"
        geom = polygons_only(shape(feat["geometry"]))
        if geom is None:
            continue
        clipped = polygons_only(geom.intersection(city))
        if clipped is None or clipped.is_empty:
            continue
        clipped = clipped.simplify(0.00008, preserve_topology=True)
        features.append(
            {
                "type": "Feature",
                "properties": {"precinct": pid, "poll_place": places.get(pid, "")},
                "geometry": mapping(clipped),
            }
        )
    precincts = {"type": "FeatureCollection", "features": features}
    city_fc = {
        "type": "Feature",
        "properties": {"name": "City of Stuart"},
        "geometry": mapping(city),
    }
    (OUT / "precincts.geojson").write_text(json.dumps(precincts) + "\n")
    (OUT / "city.geojson").write_text(json.dumps(city_fc) + "\n")
    return city_fc, precincts


def load_geometry():
    precincts_path = OUT / "precincts.geojson"
    city_path = OUT / "city.geojson"
    if precincts_path.exists() and city_path.exists():
        return json.loads(city_path.read_text()), json.loads(precincts_path.read_text())
    return build_geometry()


def freeze_race(race):
    precincts = {}
    for pid, slot in race["precincts"].items():
        votes = {k: int(v) for k, v in slot["votes"].items()}
        total = sum(votes.values())
        by_type = {
            vt: {k: int(v) for k, v in counts.items()} for vt, counts in slot["by_type"].items()
        }
        winner = max(votes, key=votes.get) if total else None
        precincts[pid] = {"votes": votes, "total": total, "winner": winner, "by_type": by_type}
    totals = {k: int(v) for k, v in race["totals"].items()}
    return {
        "id": race["id"],
        "label": race["label"],
        "office": race["office"],
        "focus": race["focus"],
        "candidates": race["candidates"],
        "precincts_reporting": race["precincts_reporting"],
        "precincts_total": race["precincts_total"],
        "totals": totals,
        "total": sum(totals.values()),
        "by_type": {vt: {k: int(v) for k, v in counts.items()} for vt, counts in race["by_type"].items()},
        "precincts": precincts,
        "calledWinner": None,
        "raceCallStatus": None,
        "callSources": [],
        "calledAt": None,
        "callKind": None,
    }


def ranked_candidates(race):
    return sorted(
        ((c, race["totals"].get(c["id"], 0)) for c in race["candidates"]),
        key=lambda item: -item[1],
    )


def apply_call(race, overrides, now_iso):
    override = overrides.get(race["id"])
    if override:
        race["calledWinner"] = override.get("calledWinner")
        race["raceCallStatus"] = override.get("raceCallStatus") or (
            f"{override.get('calledWinner')} declared winner (Manual)"
            if override.get("calledWinner")
            else override.get("status")
        )
        race["callSources"] = override.get("callSources") or ["manual"]
        race["calledAt"] = override.get("calledAt") or now_iso
        race["callKind"] = override.get("callKind") or "manual"
        return

    reporting = race["precincts_total"] and race["precincts_reporting"] >= race["precincts_total"]
    ranked = ranked_candidates(race)
    if not reporting or len(ranked) < 2 or race["total"] <= 0:
        return

    leader, leader_votes = ranked[0]
    runner, runner_votes = ranked[1]
    margin = leader_votes - runner_votes
    if margin <= 0:
        return

    margin_share = margin / race["total"]
    top_two = leader_votes + runner_votes
    top_two_share = margin / top_two if top_two else 0
    leader_share = leader_votes / race["total"]

    if margin_share <= FL_RECOUNT_SHARE or margin_share <= FL_RECOUNT_UNOFFICIAL_SHARE:
        race["callKind"] = "recount"
        race["raceCallStatus"] = (
            f"Automatic recount. {leader['name']} leads by {margin} votes, "
            f"{margin_share * 100:.2f} percent of ballots in the race."
        )
        race["callSources"] = ["soe"]
        return

    if top_two_share < APPARENT_MIN_MARGIN_SHARE:
        return

    if len(race["candidates"]) >= 3 and leader_share < MAJORITY_SHARE:
        race["callKind"] = "runoff"
        race["raceCallStatus"] = (
            f"{leader['name']} leads without a majority. The seat is not decided in this primary."
        )
        race["callSources"] = ["soe"]
        return

    race["calledWinner"] = leader["name"]
    race["callKind"] = "apparent"
    race["callSources"] = ["soe"]
    race["calledAt"] = now_iso
    race["raceCallStatus"] = f"{leader['name']} apparent winner (Martin County SOE)"


def main():
    meta, races = parse_results()
    city, precincts = load_geometry()
    city_races = {rid: freeze_race(race) for rid, race in races.items()}
    overrides = {}
    override_path = OUT / "race_call_overrides.json"
    if override_path.exists():
        overrides = json.loads(override_path.read_text()) or {}
    now_iso = datetime.now(timezone.utc).isoformat()
    for race in city_races.values():
        apply_call(race, overrides, now_iso)

    participating = sorted(
        {pid for race in city_races.values() for pid in race["precincts"]},
        key=lambda x: int(x),
    )
    geom_by_id = {str(f["properties"]["precinct"]): f for f in precincts["features"]}

    features = []
    for pid in participating:
        base = geom_by_id.get(pid)
        if not base:
            print(f"warning: precinct {pid} has votes but no clipped geometry")
            continue
        props = {
            "precinct": pid,
            "poll_place": base["properties"].get("poll_place", ""),
            "races": {rid: race["precincts"].get(pid) for rid, race in city_races.items()},
        }
        features.append({"type": "Feature", "properties": props, "geometry": base["geometry"]})

    payload = {
        "meta": {
            **meta,
            "source_results": "Martin County Supervisor of Elections, Clarity unofficial detail file",
            "source_results_url": "https://results.enr.clarityelections.com/FL/Martin/126768/",
            "source_geometry": "Martin County GIS Voting Districts, clipped to the City of Stuart municipal boundary",
            "source_polls": "Martin County Supervisor of Elections precinct map",
            "unofficial": True,
            "liveFeed": {"enabled": True, "refreshSeconds": 60},
            "lastBuilt": now_iso,
        },
        "races": [city_races[k] for k in ("group1", "group3", "group5")],
        "city": city,
        "precincts": {"type": "FeatureCollection", "features": features},
    }

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "map_data.json").write_text(json.dumps(payload) + "\n")

    print(f"timestamp {meta['timestamp']}")
    print(f"clipped precincts {len(features)}")
    for race in payload["races"]:
        print(f"\n{race['office']} n={race['total']:,}  call={race['callKind']} {race.get('calledWinner') or ''}")
        print(f"  {race.get('raceCallStatus')}")
        for cand in race["candidates"]:
            votes = race["totals"][cand["id"]]
            pct = 100 * votes / race["total"] if race["total"] else 0
            print(f"  {cand['name']:<22} {votes:5d}  {pct:5.2f}%")


if __name__ == "__main__":
    main()
