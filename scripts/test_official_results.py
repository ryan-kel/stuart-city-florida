"""Keep official citywide results separate from the election-night map."""
import copy
import json
from pathlib import Path
import unittest

from build_map import apply_official_results

ROOT = Path(__file__).resolve().parents[1]


class OfficialResultsTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT / "data/map_data.json").read_text())
        self.official = json.loads((ROOT / "data/official_results.json").read_text())

    def test_official_totals_match_city_publication(self):
        apply_official_results(self.data, self.official)
        expected = [(1783, 1764), (2087, 1500), (1869, 1153, 566)]
        for race, votes in zip(self.data["races"], expected):
            result = race["official_result"]
            self.assertEqual(tuple(result["totals"][c["id"]] for c in race["candidates"]), votes)
            self.assertEqual(result["total"], sum(votes))
            self.assertEqual(race["callKind"], "official")
        self.assertEqual(self.data["races"][0]["calledWinner"], "Campbell Rich")

    def test_precinct_votes_and_vote_methods_are_not_invented_from_city_totals(self):
        before = copy.deepcopy(self.data)
        apply_official_results(self.data, self.official)
        self.assertEqual(self.data["precincts"], before["precincts"])
        for race, old in zip(self.data["races"], before["races"]):
            for field in ("precincts", "by_type", "totals", "total"):
                self.assertEqual(race[field], old[field])
        self.assertTrue(self.data["meta"]["unofficial"])
        self.assertEqual(self.data["meta"]["precinct_status"], "unofficial")
        self.assertEqual(self.data["meta"]["summary_status"], "official")

    def test_invalid_or_incomplete_city_results_fail(self):
        for kind in ("total", "candidate", "winner", "race", "negative"):
            with self.subTest(kind=kind):
                source = copy.deepcopy(self.official)
                result = source["races"]["group1"]
                if kind == "total": result["total"] += 1
                if kind == "candidate": result["totals"]["unknown"] = 0
                if kind == "winner": result["winner"] = "laughlin"
                if kind == "race": del source["races"]["group3"]
                if kind == "negative": result["totals"]["rich"] = -1
                with self.assertRaises(ValueError):
                    apply_official_results(self.data, source)


if __name__ == "__main__":
    unittest.main()
