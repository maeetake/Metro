#!/usr/bin/env python3
"""
build_station_school_kml.py
===========================
Generate a KML that combines
  • station placemarks
  • 800‑m radius circles around each station
  • school placemarks that fall inside each circle
"""
from __future__ import annotations

import argparse
import math
import pandas as pd
import simplekml
import numpy as np

EARTH_RADIUS_M = 6371000.0  # WGS‑84 mean radius


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def destination_point(lat: float, lon: float, bearing_deg: float, distance_m: float) -> tuple[float, float]:
    """Return lat,lon reached by moving *distance_m* at *bearing_deg* from (lat,lon)."""
    bearing = math.radians(bearing_deg)
    lat1 = math.radians(lat)
    lon1 = math.radians(lon)
    ang_dist = distance_m / EARTH_RADIUS_M
    lat2 = math.asin(math.sin(lat1) * math.cos(ang_dist) + math.cos(lat1) * math.sin(ang_dist) * math.cos(bearing))
    lon2 = lon1 + math.atan2(math.sin(bearing) * math.sin(ang_dist) * math.cos(lat1),
                             math.cos(ang_dist) - math.sin(lat1) * math.sin(lat2))
    return math.degrees(lat2), math.degrees(lon2)


def build_circle(lat: float, lon: float, radius_m: float, segments: int = 36) -> list[tuple[float, float]]:
    """円を構成する座標のリストを返す。始点と終点を一致させて円を閉じる。"""
    points = [destination_point(lat, lon, b, radius_m)[::-1] for b in np.linspace(0, 360, segments, endpoint=True)]
    # endpoint=Trueにすることで、始点と終点が同じになり円が閉じる
    return points

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description="Create KML with station circles and schools")
    ap.add_argument("-s", "--stations", default="station_coordinates_157.csv", help="CSV with station coordinates")
    ap.add_argument("-w", "--within", default="schools_within_800m.csv", help="CSV output from find_schools_within_radius.py")
    ap.add_argument("-o", "--outfile",  default="stations_schools_800m.kml", help="Output KML filename")
    ap.add_argument("-r", "--radius",   type=float, default=800.0, help="Circle radius in metres (default 800)")
    args = ap.parse_args()

    try:
        st_df = pd.read_csv(args.stations)
        sc_df = pd.read_csv(args.within)
    except FileNotFoundError as e:
        print(f"エラー: ファイルが見つかりません。 {e.filename}")
        return

    # --- 列名を自動判定するロジック ---
    if "name" in st_df.columns: st_col = "name"
    elif "station" in st_df.columns: st_col = "station"
    else:
        print(f"エラー: 駅ファイル '{args.stations}' に 'name' または 'station' の列がありません。")
        return

    if "name" in sc_df.columns: sc_col = "name"
    elif "station" in sc_df.columns: sc_col = "station"
    else:
        print(f"エラー: 学校ファイル '{args.within}' に 'name' または 'station' の列がありません。")
        return

    if "latitude" in st_df.columns: lat_col = "latitude"
    elif "lat" in st_df.columns: lat_col = "lat"
    else:
        print(f"エラー: 駅ファイル '{args.stations}' に 'latitude' または 'lat' の列がありません。")
        return

    if "longitude" in st_df.columns: lon_col = "longitude"
    elif "lon" in st_df.columns: lon_col = "lon"
    else:
        print(f"エラー: 駅ファイル '{args.stations}' に 'longitude' または 'lon' の列がありません。")
        return
    # --- 自動判定ここまで ---

    kml = simplekml.Kml()

    # スタイルの事前定義
    # ★駅のピンを見やすいアイコンに変更
    station_style = simplekml.Style()
    station_style.iconstyle.icon.href = 'http://maps.google.com/mapfiles/kml/paddle/red-circle.png'
    station_style.iconstyle.scale = 1.2 # アイコンサイズを少し大きくする

    # ★学校用のピンのスタイルを定義
    school_style = simplekml.Style()
    school_style.iconstyle.icon.href = 'http://maps.google.com/mapfiles/kml/paddle/ylw-blank.png'
    school_style.iconstyle.scale = 0.8 # アイコンサイズを少し小さくする

    poly_style = simplekml.Style()
    poly_style.polystyle.color = simplekml.Color.changealphaint(60, simplekml.Color.blue)

    for _, row in st_df.iterrows():
        st_name = str(row[st_col])
        lat = float(row[lat_col])
        lon = float(row[lon_col])

        # 駅のピンをKMLに直接追加
        pnt = kml.newpoint(name=st_name, coords=[(lon, lat)])
        pnt.style = station_style

        # 円をKMLに直接追加
        circle_coords = build_circle(lat, lon, args.radius)
        pol = kml.newpolygon(name=f"{st_name} {int(args.radius)}m radius", outerboundaryis=circle_coords)
        pol.style = poly_style

        # ★学校のピンを表示する処理を復元
        subset = sc_df[sc_df[sc_col] == st_name]
        for _, sc in subset.iterrows():
            p_school = kml.newpoint(name=sc["school"], coords=[(sc["school_lon"], sc["school_lat"])])
            p_school.description = f"{sc['distance_m']} m from {st_name}"
            p_school.style = school_style

    kml.save(args.outfile)
    print(f"✅ KML written to {args.outfile}")

if __name__ == "__main__":
    main()