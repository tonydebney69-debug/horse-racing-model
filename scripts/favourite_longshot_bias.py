"""
Does the classic favourite-longshot bias show up in AU/NZ Betfair win markets,
and is it big enough to clear Betfair's commission?

Method
------
1. For every runner, take the overround-adjusted implied probability from its
   Betfair Starting Price (BSP): raw = 1/BSP, then normalise so each market's
   runners sum to 1. That removes the exchange's own ~2% back-side margin and
   gives the market's best estimate of each runner's true win chance.
2. Bucket runners into deciles by implied probability.
3. Compare each bucket's average implied probability to its actual win rate.
   A perfectly calibrated market has them equal. The literature's bias is:
   favourites (high implied prob) win slightly MORE than their price says,
   longshots win LESS - the market is a bit too generous on long prices.
4. Translate that into a flat-stake return, before and after commission, to
   see whether the bias survives real costs.

Run on --set discovery while building; run once on --set holdout at the end
to check the finding wasn't a discovery-window fluke. Nothing here should be
tuned after looking at holdout numbers.
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

PROCESSED = Path(__file__).resolve().parent.parent / "data" / "processed"
COMMISSION_RATES = [0.0, 0.065, 0.08]  # illustrative — Betfair AU varies by customer tier


def load(which: str) -> pd.DataFrame:
    df = pd.read_parquet(PROCESSED / f"{which}.parquet")
    df = df.dropna(subset=["WIN_BSP", "WIN_RESULT"]).copy()
    df = df[df["WIN_BSP"] > 1.0]
    df["won"] = (df["WIN_RESULT"] == "WINNER").astype(int)
    df["raw_p"] = 1.0 / df["WIN_BSP"]
    market_sum = df.groupby("WIN_MARKET_ID")["raw_p"].transform("sum")
    df["implied_p"] = df["raw_p"] / market_sum
    df["overround"] = market_sum  # >1 => favourite side is "taxed" a bit
    return df


def calibration_table(df: pd.DataFrame, n_buckets: int = 10) -> pd.DataFrame:
    df = df.copy()
    df["bucket"] = pd.qcut(df["implied_p"], n_buckets, labels=False, duplicates="drop")
    g = df.groupby("bucket")
    out = pd.DataFrame({
        "n_runners": g.size(),
        "avg_bsp": g["WIN_BSP"].mean(),
        "implied_win_pct": g["implied_p"].mean() * 100,
        "actual_win_pct": g["won"].mean() * 100,
    })
    out["edge_pct_pts"] = out["actual_win_pct"] - out["implied_win_pct"]
    # flat $1-stake return backing every runner in the bucket, before commission
    stake = 1.0
    g_ret = df.groupby("bucket").apply(
        lambda d: (d["won"] * (d["WIN_BSP"] - 1) * stake - (1 - d["won"]) * stake).sum(),
        include_groups=False,
    )
    turnover = g.size() * stake
    out["flat_stake_roi_pct"] = (g_ret / turnover) * 100
    for c in COMMISSION_RATES:
        # commission is charged on net winnings per market, not per bet, but as
        # a bucket-level approximation: apply it to the gross profit on winning bets only
        gross_profit_on_wins = g.apply(
            lambda d: (d["won"] * (d["WIN_BSP"] - 1) * stake).sum(), include_groups=False
        )
        losses = g.apply(lambda d: ((1 - d["won"]) * stake).sum(), include_groups=False)
        net = gross_profit_on_wins * (1 - c) - losses
        out[f"roi_pct_after_{int(c*100)}c_commission"] = (net / turnover) * 100
    return out.round(2)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--set", choices=["discovery", "holdout"], default="discovery")
    p.add_argument("--buckets", type=int, default=10)
    args = p.parse_args()

    df = load(args.set)
    print(f"{args.set}: {len(df):,} runners, {df['WIN_MARKET_ID'].nunique():,} markets, "
          f"avg market overround {df.groupby('WIN_MARKET_ID')['overround'].first().mean():.3f}\n")

    table = calibration_table(df, args.buckets)
    print("Bucket 0 = shortest prices (favourites) ... bucket N = longest prices (longshots)\n")
    print(table.to_string())

    fav_row = table.iloc[0]
    long_row = table.iloc[-1]
    print(f"\nFavourites (bucket 0): implied {fav_row['implied_win_pct']}%, "
          f"actual {fav_row['actual_win_pct']}%, edge {fav_row['edge_pct_pts']:+.2f} pts")
    print(f"Longshots (bucket {table.index[-1]}): implied {long_row['implied_win_pct']}%, "
          f"actual {long_row['actual_win_pct']}%, edge {long_row['edge_pct_pts']:+.2f} pts")
