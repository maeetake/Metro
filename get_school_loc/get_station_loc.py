from __future__ import annotations

import sys
import time
import json
from pathlib import Path
from typing import Tuple, List, Optional

import pandas as pd
import requests

# ---------------------------------------------------------------------------
# Configuration -------------------------------------------------------------
# ---------------------------------------------------------------------------
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
TIMEOUT      = 25       # seconds per query
THROTTLE     = 0.1      # seconds between requests; be kind to OSM!

# Prefectures to keep the search within. Admin‑level 4 = prefecture.
PREFECTURES = (
    "大阪府",
    "京都府",
    "奈良県",
    "兵庫県",
)

# ---------------------------------------------------------------------------
# Helpers -------------------------------------------------------------------
# ---------------------------------------------------------------------------

def build_prefecture_union() -> str:
    """Return an Overpass QL fragment that unions Kansai prefecture areas."""
    lines = [
        f"  area[\"name\"=\"{pref}\"][\"boundary\"=\"administrative\"][\"admin_level\"=\"4\"];"  # noqa: E501
        for pref in PREFECTURES
    ]
    # Wrap in parentheses and assign to .search
    return (
        "(\n" + "\n".join(lines) + "\n)->.searchArea;"
    )


PREF_UNION_Q = build_prefecture_union()


def overpass_query_for(name: str) -> str:
    """Return an Overpass QL query limited to the Kansai prefectures."""
    escaped = name.replace("\"", "\\\"")  # escape double‑quotes
    return (
        f"[out:json][timeout:{TIMEOUT}];\n"
        f"{PREF_UNION_Q}\n"
        "(\n"
        f"  node[\"railway\"=\"station\"][\"name\"=\"{escaped}\"](area.searchArea);\n"
        f"  relation[\"railway\"=\"station\"][\"name\"=\"{escaped}\"](area.searchArea);\n"
        ");\n"
        "out center 1;"
    )


def query_station(name: str) -> Tuple[Optional[float], Optional[float]]:
    """Return (lat, lon) for *name* or (None, None) if not found."""
    q = overpass_query_for(name)
    try:
        r = requests.get(OVERPASS_URL, params={"data": q})
        r.raise_for_status()
    except requests.RequestException as e:
        print(f"⚠️  network error for {name!r}: {e}", file=sys.stderr)
        return None, None

    try:
        data = r.json()
    except json.JSONDecodeError:
        print(f"⚠️  JSON parse error for {name!r}", file=sys.stderr)
        return None, None

    if not data.get("elements"):
        return None, None

    el = data["elements"][0]
    if el["type"] == "node":
        lat, lon = el["lat"], el["lon"]
    else:  # relation or way with center
        lat, lon = el["center"]["lat"], el["center"]["lon"]
    return round(lat, 6), round(lon, 6)


# ---------------------------------------------------------------------------
# Main script ---------------------------------------------------------------
# ---------------------------------------------------------------------------

def main(argv: List[str] | None = None) -> None:
    argv = argv if argv is not None else sys.argv[1:]
    input_path  = Path(argv[0]) if argv else Path("駅名.txt")
    output_path = Path(argv[1]) if len(argv) > 1 else Path("station_coordinates_157.csv")

    if not input_path.exists():
        sys.exit(f"❌ station name file not found: {input_path}")

    names = [line.strip() for line in input_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    print(f"▶️  Fetching coordinates for {len(names)} stations within {', '.join(PREFECTURES)}…\n")

    records = []
    for idx, name in enumerate(names, 1):
        lat, lon = query_station(name)
        records.append({"name": name, "latitude": lat, "longitude": lon})
        status = "OK" if lat is not None else "MISS"
        print(f"{idx:3}/{len(names)}  {name:<20} : {status}")
        time.sleep(THROTTLE)

    df = pd.DataFrame(records)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")

    missing = df[df["latitude"].isna()]
    if not missing.empty:
        print("\n⚠️  Stations NOT found (please verify names or check if they lie outside the target prefectures):")
        for n in missing["name"]:
            print("  -", n)
    else:
        print("\n✅ All stations resolved successfully!")

    print(f"\n📄 CSV written to: {output_path.resolve()}")


if __name__ == "__main__":
    main()
