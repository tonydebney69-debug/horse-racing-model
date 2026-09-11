"""
A hunt for market mispricing using only three physical/scheduling factors -
track, distance, time of day - rather than anything price- or volume-based.

The dataset has no finish times or sectional times (it's exchange market
data, not a form database - see README), so "time run" here means time of
DAY the race is scheduled, not how fast the race was run. Flagged clearly so
the substitution is visible rather than silently assumed.

Same method as favourite_longshot_bias.py: overround-adjusted implied
probability from WIN_BSP vs actual win rate, and flat $1-stake ROI backing
every runner in the slice. The difference is what we group by - not the
odds themselves, but where and when the race is run. The question: is the
market worse-calibrated on some tracks / distances / times than others,
independent of the price level itself?

Run:
    python scripts/track_distance_time_signal.py
"""
from pathlib import Path

import numpy as np
import pandas as pd

PROCESSED = Path(__file__).resolve().parent.parent / "data" / "processed"
MIN_RUNNERS = 3000  # drop thin groups (tracks etc.) before ranking


def load(which: str) -> pd.DataFrame:
    df = pd.read_parquet(PROCESSED / f"{which}.parquet")
    df = df.dropna(subset=["WIN_BSP", "WIN_RESULT", "WIN_MARKET_ID", "DISTANCE",
                            "TRACK", "SCHEDULED_RACE_TIME"]).copy()
    df = df[df["WIN_BSP"] > 1.0]
    df["won"] = (df["WIN_RESULT"] == "WINNER").astype(int)
    raw_p = 1.0 / df["WIN_BSP"]
    df["implied_p"] = raw_p / raw_p.groupby(df["WIN_MARKET_ID"]).transform("sum")

    df["distance_bucket"] = pd.cut(
        df["DISTANCE"], [0, 1200, 1600, 2000, 10000],
        labels=["Sprint (<=1200m)", "Mile (1201-1600m)", "Middle (1601-2000m)", "Staying (2000m+)"],
    )
    hour = pd.to_datetime(df["SCHEDULED_RACE_TIME"], format="%H:%M:%S.%f", errors="coerce").dt.hour
    df["time_bucket"] = pd.cut(
        hour, [-1, 12, 15, 17, 24],
        labels=["Morning (<=12)", "Midday (13-15)", "Late arvo (16-17)", "Twilight/night (18+)"],
    )
    return df


def calibration(df: pd.DataFrame, group_col: str, min_n: int = MIN_RUNNERS) -> pd.DataFrame:
    g = df.groupby(group_col, observed=True)
    n = g.size()
    ret = g.apply(lambda x: (x["won"] * (x["WIN_BSP"] - 1) - (1 - x["won"])).sum(),
                  include_groups=False)
    out = pd.DataFrame({
        "n": n,
        "implied_win_pct": (g["implied_p"].mean() * 100).round(2),
        "actual_win_pct": (g["won"].mean() * 100).round(2),
        "roi_pct": (ret / n * 100).round(2),
    })
    out["edge_pct_pts"] = (out["actual_win_pct"] - out["implied_win_pct"]).round(2)
    out = out[out["n"] >= min_n]
    return out.sort_values("roi_pct", ascending=False)


if __name__ == "__main__":
    df = load("discovery")
    print(f"discovery: {len(df):,} runners with track/distance/time available\n")

    print("=== By distance ===")
    print(calibration(df, "distance_bucket", min_n=1).to_string())

    print("\n=== By time of day ===")
    print(calibration(df, "time_bucket", min_n=1).to_string())

    print(f"\n=== By track (min {MIN_RUNNERS:,} runners, top/bottom 10 by ROI) ===")
    by_track = calibration(df, "TRACK")
    print(f"{len(by_track)} tracks qualify\n")
    print("-- best --")
    print(by_track.head(10).to_string())
    print("\n-- worst --")
    print(by_track.tail(10).to_string())

    print("\n=== Distance x time (cells with >=1500 runners) ===")
    combo = calibration(df.assign(cell=df["distance_bucket"].astype(str) + " / " + df["time_bucket"].astype(str)),
                         "cell", min_n=1500)
    print(combo.to_string())
