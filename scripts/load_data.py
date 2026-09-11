"""
Combine the monthly CSVs into two parquet files: discovery and holdout.

Discovery = every complete month before the holdout window. All exploration,
signal-hunting and parameter choices happen here.

Holdout = the most recent months. Not read, plotted, or peeked at until a
strategy is fully specified on discovery data alone - the same rule that
found the crypto bot's breakout/momentum signals were noise: if you tune
against the test set, you're not testing anything.

Usage:
    python scripts/load_data.py --holdout-months 6
"""
import argparse
from pathlib import Path

import pandas as pd

RAW_MONTHLY = Path(__file__).resolve().parent.parent / "data" / "raw" / "monthly"
PROCESSED = Path(__file__).resolve().parent.parent / "data" / "processed"

DTYPES = {
    "TRACK": "category",
    "STATE_CODE": "category",
    "RACE_TYPE": "category",
    "RACING_TYPE": "category",
    "WIN_RESULT": "category",
    "PLACE_RESULT": "category",
    "SELECTION_NAME": "string",
}


def load_all() -> pd.DataFrame:
    files = sorted(RAW_MONTHLY.glob("ANZ_Thoroughbreds_*.csv"))
    if not files:
        raise SystemExit(f"No CSVs in {RAW_MONTHLY} — run scripts/fetch_data.py first.")
    frames = []
    for f in files:
        df = pd.read_csv(f, dtype=DTYPES, low_memory=False)
        frames.append(df)
    out = pd.concat(frames, ignore_index=True)
    out["LOCAL_MEETING_DATE"] = pd.to_datetime(out["LOCAL_MEETING_DATE"], errors="coerce")
    out["year_month"] = out["LOCAL_MEETING_DATE"].dt.to_period("M")
    return out


def split(df: pd.DataFrame, holdout_months: int):
    months = sorted(df["year_month"].dropna().unique())
    cutoff = months[-holdout_months]
    discovery = df[df["year_month"] < cutoff].copy()
    holdout = df[df["year_month"] >= cutoff].copy()
    return discovery, holdout


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--holdout-months", type=int, default=6,
                    help="most recent N months withheld as the out-of-sample test")
    args = p.parse_args()

    PROCESSED.mkdir(parents=True, exist_ok=True)
    df = load_all()
    discovery, holdout = split(df, args.holdout_months)

    discovery.to_parquet(PROCESSED / "discovery.parquet", index=False)
    holdout.to_parquet(PROCESSED / "holdout.parquet", index=False)

    print(f"total rows:     {len(df):,}")
    print(f"discovery:      {len(discovery):,} rows, "
          f"{discovery['year_month'].min()} -> {discovery['year_month'].max()}")
    print(f"holdout:        {len(holdout):,} rows, "
          f"{holdout['year_month'].min()} -> {holdout['year_month'].max()}  (untouched)")
    print(f"markets (disc): {discovery['WIN_MARKET_ID'].nunique():,}")
