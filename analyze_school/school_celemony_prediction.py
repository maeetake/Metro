from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional, List

import pandas as pd
import matplotlib.pyplot as plt

FALLBACK_ENCODINGS: List[str] = [
    "utf-8",
    "utf-8-sig",
    "cp932",
    "shift_jis",
    "latin1",
]

def read_csv_with_fallback(path: Path, encoding: Optional[str] = None, **kwargs) -> pd.DataFrame:
    encodings = [encoding] if encoding else []
    encodings += [e for e in FALLBACK_ENCODINGS if e not in encodings]
    tried: List[str] = []
    for enc in encodings:
        try:
            return pd.read_csv(path, encoding=enc, **kwargs)
        except UnicodeDecodeError:
            tried.append(enc or "(default)")
    raise UnicodeDecodeError("read_csv", bytes(), 0, 0, f"Unable to decode {path}; tried {tried}")

def load_data(rides_path: Path, schools_path: Path, *, encoding: Optional[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    rides = read_csv_with_fallback(
        rides_path,
        encoding=encoding,
        parse_dates=["data_date"],
        dtype={
            "depature_station": "string",
            "arrival_station": "string",
            "depature_station_time": "string",
            "arrival_station_time": "string",
        },
    )
    rides["depature_station"] = rides["depature_station"].str.strip().str.replace("　", "", regex=False)

    schools = read_csv_with_fallback(
        schools_path,
        encoding=encoding,
        dtype={
            "station": "string",
            "school": "string",
            "distance_m": "float64",
            "school_lat": "float64",
            "school_lon": "float64",
        },
    )
    schools["station"] = schools["station"].str.strip().str.replace("　", "", regex=False)
    return rides, schools

def aggregate_daily_counts(rides: pd.DataFrame) -> pd.DataFrame:
    return (
        rides.groupby(["data_date", "depature_station"], observed=True)
        .size()
        .reset_index(name="departures")
        .rename(columns={"depature_station": "station"})
    )

def _fallback_date(df: pd.DataFrame) -> pd.Timestamp:
    """Fallback: day with maximum departures (ties → earliest)."""
    max_dep = df["departures"].max()
    return df.loc[df["departures"] == max_dep, "data_date"].iloc[0]

def detect_start_date(
    df: pd.DataFrame,
    *,
    window: int,
    multiplier: float,
    min_count: int,
    guarantee: bool,
) -> pd.Timestamp:
    df = df.sort_values("data_date").copy()
    df["baseline"] = df["departures"].rolling(window, min_periods=window).median()
    df["ratio"] = df["departures"] / df["baseline"]

    # 1) strict spike
    mask_spike = df["baseline"].ge(min_count) & df["ratio"].ge(multiplier)
    if mask_spike.any():
        return df.loc[mask_spike, "data_date"].iloc[0]

    if not guarantee:
        return pd.NaT

    after_baseline = df[df["baseline"].notna()].copy()
    if not after_baseline.empty and after_baseline["ratio"].notna().any():
        idx = after_baseline["ratio"].idxmax()
        return df.loc[idx, "data_date"]

    return _fallback_date(df)

def predict_ceremony_dates(
    daily: pd.DataFrame,
    schools: pd.DataFrame,
    *,
    window: int,
    multiplier: float,
    min_count: int,
    guarantee: bool,
) -> pd.DataFrame:
    target = schools["station"].unique()
    subset = daily[daily["station"].isin(target)]

    recs = [
        {
            "station": s,
            "pred_ceremony_date": detect_start_date(
                g, window=window, multiplier=multiplier, min_count=min_count, guarantee=guarantee
            ),
        }
        for s, g in subset.groupby("station", observed=True)
    ]
    return pd.DataFrame(recs)

def choose_overall_date(preds: pd.DataFrame) -> Optional[pd.Timestamp]:
    cnts = preds["pred_ceremony_date"].value_counts()
    return None if cnts.empty else min(cnts[cnts == cnts.iloc[0]].index)

def save_bar_chart(preds: pd.DataFrame, out_path: Path):
    counts = preds["pred_ceremony_date"].value_counts().sort_index()
    if counts.empty:
        print("[WARN] Nothing to plot – bar chart skipped.")
        return
    plt.figure(figsize=(8, 4))
    plt.bar(counts.index.astype(str), counts.values)
    plt.title("Predicted ceremony dates – station count")
    plt.ylabel("# Stations")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()
    print(f"Saved: {out_path}")

def save_station_timeline(g: pd.DataFrame, date: pd.Timestamp, out_path: Path, *, window: int):
    g = g.sort_values("data_date").copy()
    g["baseline"] = g["departures"].rolling(window, min_periods=window).median()
    plt.figure(figsize=(9, 4))
    plt.plot(g["data_date"], g["departures"], label="Departures")
    plt.plot(g["data_date"], g["baseline"], label="Baseline (median)")
    plt.axvline(date, linestyle="--", label="Predicted", linewidth=1.2)
    plt.title(f"{g.iloc[0]['station']} – daily departures")
    plt.ylabel("Trips")
    plt.xticks(rotation=45, ha="right")
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()
    print(f"Saved: {out_path}")

def save_date_summary(preds: pd.DataFrame, out_path: Path):
    grouped = (
        preds.groupby("pred_ceremony_date")["station"]
        .apply(lambda s: ", ".join(s))
        .reset_index()
        .rename(columns={"station": "stations"})
    )
    grouped["count"] = grouped["stations"].apply(lambda x: len(x.split(", ")))
    grouped = grouped[["pred_ceremony_date", "stations", "count"]]
    grouped = grouped.sort_values("pred_ceremony_date")
    grouped.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"Saved: {out_path}")

def main():
    p = argparse.ArgumentParser(description="Predict & visualise school ceremony dates from ridership (April 2025)")
    p.add_argument("--rides", type=Path, required=True)
    p.add_argument("--schools", type=Path, required=True)
    p.add_argument("--encoding")
    p.add_argument("--window", type=int, default=7)
    p.add_argument("--multiplier", type=float, default=1.5)
    p.add_argument("--min_count", type=int, default=50)
    p.add_argument("--guarantee", dest="guarantee", action="store_true", default=True, help="Always output a date (fallback mode)")
    p.add_argument("--no-guarantee", dest="guarantee", action="store_false", help="Disable fallback date")
    p.add_argument("--bar-chart", action="store_true")
    p.add_argument("--timeline", action="store_true")

    args = p.parse_args()

    # ★★ 画像保存用ディレクトリ(outputs)を自動作成
    outdir = Path("outputs")
    outdir.mkdir(exist_ok=True)

    rides, schools = load_data(args.rides, args.schools, encoding=args.encoding)
    daily = aggregate_daily_counts(rides)
    preds = predict_ceremony_dates(
        daily,
        schools,
        window=args.window,
        multiplier=args.multiplier,
        min_count=args.min_count,
        guarantee=args.guarantee,
    )

    overall = choose_overall_date(preds)

    print("\nPredicted ceremony date by station:\n")
    print(preds.sort_values("pred_ceremony_date").to_string(index=False))

    print("\n--------------------------------------")
    if overall is not None:
        print(f"Overall predicted start-of-term ceremony date: {overall.date()}")
    else:
        print("Unable to determine an overall common date.")

    # 棒グラフ画像をoutputs内に保存
    if args.bar_chart:
        save_bar_chart(preds, outdir / "ceremony_distribution.png")

    # 日付ごと集計CSVはルート直下
    save_date_summary(preds, Path("ceremony_summary_by_date.csv"))

    # タイムライン画像もoutputs内に保存
    if args.timeline:
        for _, row in preds.iterrows():
            g = daily[daily["station"] == row["station"]]
            out = outdir / f"timeline_{row['station']}.png"
            save_station_timeline(g, row["pred_ceremony_date"], out, window=args.window)

if __name__ == "__main__":
    main()
