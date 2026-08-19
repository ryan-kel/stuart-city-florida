#!/usr/bin/env python3
"""Download the Martin County Clarity unofficial detail XML."""

from __future__ import annotations

import io
import os
import zipfile
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(os.environ.get("STUART_ROOT", Path(__file__).resolve().parents[1]))
RAW = Path(os.environ.get("STUART_RAW", ROOT / "data" / "raw"))
XML_DIR = RAW / "xml"

CLARITY_ELECTION = "https://results.enr.clarityelections.com/FL/Martin/126768"
UA = "ElectoralAnalytics/1.0 (+https://electoralanalytics.net)"


def http_get(url: str) -> bytes:
    req = Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urlopen(req, timeout=60) as resp:
        return resp.read()


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    version = http_get(f"{CLARITY_ELECTION}/current_ver.txt").decode("utf-8").strip()
    (RAW / "current_ver.txt").write_text(version + "\n")
    blob = http_get(f"{CLARITY_ELECTION}/{version}/reports/detailxml.zip")
    (RAW / "reports_detailxml.zip").write_bytes(blob)
    XML_DIR.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(blob)) as zf:
        zf.extractall(XML_DIR)
    print(f"Clarity version {version} -> {XML_DIR / 'detail.xml'}")


if __name__ == "__main__":
    main()
