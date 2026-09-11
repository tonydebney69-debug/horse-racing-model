"""
Robustness checks on the price-drift finding from price_drift_signal.py,
before it's allowed anywhere near the holdout set.

The finding to stress-test: backing drifters (price lengthened into the
jump) flat-staked returns ~+2.7% before commission in the 6-30 BSP range;
backing steamers (price shortened) returns ~-3.7%. That's the OPPOSITE of
racing folklore ("steam = smart/informed money, drift = weak support"),
which on its own is a reason for suspicion, not confidence — a surprising
sign flip on a folklore prior needs more evidence than a friendly result
would.

Checks run here:
  1. Year-by-year stability (2023 / 2024 / 2025 separately) - a real effect
     should show up in each year, not be driven by one regime.
  2. Liquidity split - is this a genuine price-discovery signal, or a
     microstructure artifact of thin markets where one small trade creates
     a wide, meaningless preplay range?
  3. Field-size split - drift is mechanically easier to measure in bigger
     fields; check the gradient isn't just a field-size proxy.
  4. Market-clustered bootstrap on the bucket0-vs-bucket4 ROI gap, for an
     honest confidence interval instead of eyeballing point estimates.

Run:
    python scripts/drift_robustness.py
"""
from pathlib import Path

import numpy as np
import pandas as pd

PROCESSED = Path(__file__).resolve().parent.parent / "data" / "processed"
BSP_LO, BSP_HI = 6, 15  # the band where the original signal looked cleanest
N_BUCKETS = 5
RNG = np.random.default_rng(20260911)


def load_discovery() -> pd.DataFrame:
    df = pd.read_parquet(PROCESSED / "discovery.parquet")
    cols = ["WIN_BSP", "WIN_RESULT", "WIN_MARKET_ID", "LOCAL_MEETING_DATE",
            "WIN_PREPLAY_MAX_PRICE_TAKEN", "WIN_PREPLAY_MIN_PRICE_TAKEN",
            "WIN_PREPLAY_VOLUME"]
    df = df.dropna(subset=cols).copy()
    df = df[df["WIN_BSP"] > 1.0]
    df["won"] = (df["WIN_RESULT"] == "WINNER").astype(int)
    raw_p = 1.0 / df["WIN_BSP"]
    df["implied_p"] = raw_p / raw_p.groupby(df["WIN_MARKET_ID"]).transform("sum")
    df["field_size"] = df.groupby("WIN_MARKET_ID")["WIN_MARKET_ID"].transform("size")

    df = df[(df["WIN_BSP"] >= BSP_LO) & (df["WIN_BSP"] <= BSP_HI)]
    rng_ = df["WIN_PREPLAY_MAX_PRICE_TAKEN"] - df["WIN_PREPLAY_MIN_PRICE_TAKEN"]
    df = df[rng_ > 0.05]
    df["steam_score"] = ((df["WIN_PREPLAY_MAX_PRICE_TAKEN"] - df["WIN_BSP"]) / rng_).clip(0, 1)
    df["year"] = df["LOCAL_MEETING_DATE"].dt.year
    return df


def bucket_roi(df: pd.DataFrame, n_buckets: int = N_BUCKETS) -> pd.DataFrame:
    d = df.copy()
    d["bucket"] = pd.qcut(d["steam_score"], n_buckets, labels=False, duplicates="drop")
    g = d.groupby("bucket")
    ret = g.apply(lambda x: (x["won"] * (x["WIN_BSP"] - 1) - (1 - x["won"])).sum(),
                  include_groups=False)
    n = g.size()
    return pd.DataFrame({
        "n": n,
        "avg_bsp": g["WIN_BSP"].mean().round(2),
        "actual_win_pct": (g["won"].mean() * 100).round(2),
        "roi_pct": (ret / n * 100).round(2),
    })


def edges_from(df: pd.DataFrame, n_buckets: int = N_BUCKETS) -> np.ndarray:
    qs = np.linspace(0, 1, n_buckets + 1)
    return np.quantile(df["steam_score"], qs)


def roi_gap_fixed_edges(df: pd.DataFrame, edges: np.ndarray) -> float:
    b = pd.cut(df["steam_score"], edges, labels=False, include_lowest=True)
    d = df.assign(bucket=b)
    lo = d[d["bucket"] == 0]
    hi = d[d["bucket"] == d["bucket"].max()]

    def roi(x):
        if len(x) == 0:
            return np.nan
        return (x["won"] * (x["WIN_BSP"] - 1) - (1 - x["won"])).sum() / len(x) * 100

    return roi(lo) - roi(hi)  # drifters minus steamers, positive = drifters win the trade


def market_clustered_bootstrap(df: pd.DataFrame, edges: np.ndarray, n_boot: int = 1000):
    market_ids = df["WIN_MARKET_ID"].unique()
    by_market = dict(df.groupby("WIN_MARKET_ID").indices.items())
    arr = df.reset_index(drop=True)
    gaps = np.empty(n_boot)
    n_markets = len(market_ids)
    for i in range(n_boot):
        sample = RNG.choice(market_ids, size=n_markets, replace=True)
        idx = np.concatenate([by_market[m] for m in sample])
        gaps[i] = roi_gap_fixed_edges(arr.iloc[idx], edges)
    return gaps


if __name__ == "__main__":
    df = load_discovery()
    print(f"discovery, BSP {BSP_LO}-{BSP_HI}: {len(df):,} runners, "
          f"{df['WIN_MARKET_ID'].nunique():,} markets\n")

    print("=== 1. Year-by-year stability ===")
    for y, sub in df.groupby("year"):
        print(f"\n-- {y} ({len(sub):,} runners) --")
        print(bucket_roi(sub).to_string())

    print("\n=== 2. Liquidity split (WIN_PREPLAY_VOLUME terciles) ===")
    df["liq_bucket"] = pd.qcut(df["WIN_PREPLAY_VOLUME"], 3, labels=["thin", "mid", "deep"])
    for name, sub in df.groupby("liq_bucket", observed=True):
        print(f"\n-- liquidity: {name} ({len(sub):,} runners, "
              f"median preplay volume ${sub['WIN_PREPLAY_VOLUME'].median():,.0f}) --")
        print(bucket_roi(sub).to_string())

    print("\n=== 3. Field-size split ===")
    df["field_bucket"] = pd.cut(df["field_size"], [0, 7, 10, 13, 100],
                                 labels=["<=7", "8-10", "11-13", "14+"])
    for name, sub in df.groupby("field_bucket", observed=True):
        print(f"\n-- field size: {name} ({len(sub):,} runners) --")
        print(bucket_roi(sub).to_string())

    print("\n=== 4. Market-clustered bootstrap: drifter ROI - steamer ROI ===")
    edges = edges_from(df)
    point = roi_gap_fixed_edges(df, edges)
    gaps = market_clustered_bootstrap(df, edges, n_boot=1000)
    lo, hi = np.percentile(gaps, [2.5, 97.5])
    print(f"point estimate: {point:+.2f} pct pts (drifters - steamers)")
    print(f"95% bootstrap CI (clustered by market, 1000 resamples): [{lo:+.2f}, {hi:+.2f}]")
    print(f"fraction of bootstrap draws <= 0: {(gaps <= 0).mean():.3f}")
