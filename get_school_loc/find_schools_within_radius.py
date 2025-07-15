#!/usr/bin/env python3
"""
find_schools_within_radius.py  (v3.3)
====================================
List every (<station>, <school>) pair where the school lies within *radius*
(default 800 m) of a station.

**v3.3 change:** Only schools whose *name* contains either **「中学校」** or
**「高等学校」** are considered.  Elementary schools, cram schools, piano
studios, ballet schools, universities, etc. are all excluded regardless of
OSM tags.

Strategy
--------
* **Live mode:** Overpass query filters `amenity=school` and
  `name~"中学校|高等学校"`.  The name check is repeated locally to be safe.
* **Offline mode:** Loaded CSV rows are filtered with the same regex.
* **Common helper `is_target_name()`** centralises the rule.
"""
from __future__ import annotations

import argparse
import math
import re
import sys
import time
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd
import requests

EARTH_RADIUS_M = 6_371_000.0  # metres, WGS‑84 mean radius
OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# ---------------------------------------------------------------------------
# Target‑name helper
# ---------------------------------------------------------------------------
TARGET_RE = re.compile(r"(中学校|高等学校)")

def is_target_name(name: str | None) -> bool:  # noqa: D401 – simple function
    """Return *True* if *name* includes the target keywords."""
    if not name:
        return False
    return bool(TARGET_RE.search(name))

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def normalise_station_df(df: pd.DataFrame) -> pd.DataFrame:
    """Rename columns so that we always have: station, lat, lon."""
    col_map = {
        "station": ["station", "name", "駅名", "駅", "st"],
        "lat": ["lat", "latitude", "緯度", "lat_deg", "Lat", "Latitude"],
        "lon": ["lon", "lng", "longitude", "経度", "Lon", "Lng", "Longitude"],
    }
    new_names = {}
    for canonical, candidates in col_map.items():
        for c in candidates:
            if c in df.columns and canonical not in df.columns:
                new_names[c] = canonical
                break
    df = df.rename(columns=new_names)

    missing = [c for c in ("station", "lat", "lon") if c not in df.columns]
    if missing:
        raise SystemExit(
            "❌ Required column(s) not found: "
            + ", ".join(missing)
            + f"\n   👉 Available columns: {list(df.columns)}"
        )
    return df[["station", "lat", "lon"]]


def haversine_np(lat1: float, lon1: float, lats2: np.ndarray, lons2: np.ndarray) -> np.ndarray:
    """Vectorised Haversine distance from one point to many (in metres)."""
    lat1_rad, lon1_rad = map(math.radians, (lat1, lon1))
    lats2_rad = np.radians(lats2)
    lons2_rad = np.radians(lons2)

    dlat = lats2_rad - lat1_rad
    dlon = lons2_rad - lon1_rad

    a = (
        np.sin(dlat / 2) ** 2
        + np.cos(lat1_rad) * np.cos(lats2_rad) * np.sin(dlon / 2) ** 2
    )
    c = 2 * np.arcsin(np.sqrt(a))
    return EARTH_RADIUS_M * c

# ---------------------------------------------------------------------------
# Overpass helpers
# ---------------------------------------------------------------------------

def _run_overpass(query: str) -> dict:
    """Execute raw Overpass QL query and return parsed JSON."""
    try:
        resp = requests.post(OVERPASS_URL, data=query.encode("utf-8"), timeout=90)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        print(f"⚠️  Overpass error: {e}", file=sys.stderr)
        return {"elements": []}


def fetch_schools_live(lat: float, lon: float, radius: float) -> List[Dict[str, float]]:
    """Query Overpass for *target* schools within *radius* of (lat, lon)."""

    query = f"""
[out:json][timeout:60];
// Only amenity=school and name contains 中学校 or 高等学校
nwr["amenity"="school"]["name"~"中学校|高等学校"](around:{int(radius)},{lat},{lon});
out center;"""

    js = _run_overpass(query)

    results: List[Dict[str, float]] = []
    for el in js.get("elements", []):
        name = el.get("tags", {}).get("name")
        if not is_target_name(name):
            continue

        if el["type"] == "node":
            lat_s, lon_s = el["lat"], el["lon"]
        else:  # way / relation
            center = el.get("center")
            if not center:
                continue
            lat_s, lon_s = center["lat"], center["lon"]

        results.append({"name": name, "lat": lat_s, "lon": lon_s})

    return results

# ---------------------------------------------------------------------------
# Distance assembly helpers
# ---------------------------------------------------------------------------

def build_within_radius(st_df: pd.DataFrame, sc_df: pd.DataFrame, radius: float) -> pd.DataFrame:
    """Return DataFrame of schools within *radius* metres of each station."""
    records: List[pd.DataFrame] = []
    sc_lats = sc_df["lat"].to_numpy()
    sc_lons = sc_df["lon"].to_numpy()

    for _, st in st_df.iterrows():
        dists = haversine_np(st["lat"], st["lon"], sc_lats, sc_lons)
        mask = dists <= radius
        if not np.any(mask):
            continue
        subset = sc_df[mask].copy()
        subset["distance_m"] = dists[mask].round(1)
        subset["station"] = st["station"]
        records.append(subset[["station", "name", "distance_m", "lat", "lon"]])

    if not records:
        return pd.DataFrame(
            columns=["station", "school", "distance_m", "school_lat", "school_lon"]
        )

    df_out = pd.concat(records, ignore_index=True)
    df_out.rename(
        columns={"name": "school", "lat": "school_lat", "lon": "school_lon"},
        inplace=True,
    )
    df_out.sort_values(["station", "distance_m"], inplace=True)
    return df_out

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    p = argparse.ArgumentParser(
        description="List nearby schools whose name includes ‘中学校’ or ‘高等学校’."
    )
    p.add_argument("-s", "--stations", default="station_coordinates_157.csv", help="CSV with station coordinates")
    p.add_argument("-c", "--schools",  default="school_coordinates_kansai.csv", help="CSV with school coordinates (offline mode)")
    p.add_argument("-r", "--radius",   type=float, default=800.0, help="Radius in metres (default 800)")
    p.add_argument("-o", "--outfile",  default=None, help="Output CSV filename")
    p.add_argument("--live", action="store_true", help="Fetch schools on‑the‑fly via Overpass (ignore --schools)")
    p.add_argument("-d", "--delay", type=float, default=1.0, help="Delay between Overpass calls in live mode (s)")
    args = p.parse_args()

    # -------------------------------------------------------------------
    # Load stations CSV & normalise
    # -------------------------------------------------------------------
    st_path = Path(args.stations)
    if not st_path.exists():
        raise SystemExit(f"❌ station CSV not found: {st_path}")
    try:
        st_df_raw = pd.read_csv(st_path)
    except Exception as e:
        raise SystemExit(f"❌ failed to read station CSV: {e}")

    st_df = normalise_station_df(st_df_raw)

    # -------------------------------------------------------------------
    # Live mode
    # -------------------------------------------------------------------
    if args.live or not Path(args.schools).exists():
        print("🛰  Live Overpass mode – this may take a few minutes…")
        rows: List[Dict[str, object]] = []
        for idx, st in st_df.iterrows():
            schools = fetch_schools_live(float(st["lat"]), float(st["lon"]), args.radius)
            for sc in schools:
                dist = haversine_np(
                    st["lat"],
                    st["lon"],
                    np.array([sc["lat"]]),
                    np.array([sc["lon"]]),
                )[0]
                if dist <= args.radius:
                    rows.append({
                        "station": st["station"],
                        "school": sc["name"],
                        "distance_m": round(dist, 1),
                        "school_lat": sc["lat"],
                        "school_lon": sc["lon"],
                    })
            print(f"  · {idx + 1}/{len(st_df)} {st['station']} – {len(schools)} schools ✓")
            if idx < len(st_df) - 1:
                time.sleep(args.delay)

        df_out = pd.DataFrame(rows)
        df_out.sort_values(["station", "distance_m"], inplace=True)

    # -------------------------------------------------------------------
    # Offline mode
    # -------------------------------------------------------------------
    else:
        sc_path = Path(args.schools)
        try:
            sc_df_raw = pd.read_csv(sc_path)
        except Exception as e:
            raise SystemExit(f"❌ failed to read school CSV: {e}")

        try:
            sc_df = sc_df_raw.rename(columns={
                "latitude": "lat", "Latitude": "lat", "緯度": "lat",
                "longitude": "lon", "Longitude": "lon", "経度": "lon",
            })[["name", "lat", "lon"]].dropna()
        except KeyError as e:
            raise SystemExit(
                "❌ school CSV must contain columns for name, lat, lon. "
                f"Missing {e}."
            )

        df_out = build_within_radius(st_df, sc_df, args.radius)

    # -------------------------------------------------------------------
    # Save results
    # -------------------------------------------------------------------
    out_path = args.outfile or f"schools_within_{int(args.radius)}m.csv"
    df_out.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"✅ {len(df_out)} pairs written to {out_path} (radius {args.radius} m)")


if __name__ == "__main__":
    main()
