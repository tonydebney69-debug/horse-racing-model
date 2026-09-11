"""
Second hypothesis, since raw BSP buckets showed no favourite-longshot bias:
does pre-play price MOVEMENT carry information the closing BSP hasn't priced in?

"Steamers" (backed in - price shortens toward the jump) are folk wisdom to
outperform their price; "drifters" (price lengthens) to underperform. This is
literally what the Betfair Automation Hub's own tutorials test for, so it's a
fair second thing to check against three years of real results.

steam_score = (preplay_max - BSP) / (preplay_max - preplay_min)
  1.0  => BSP sits at the low of its pre-play range (steamed in hard)
  0.0  => BSP sits at the high of its pre-play range (drifted out hard)

Restricted to runners with a real pre-play range (max > min) so the ratio is
defined, and to BSP 3-30 to keep extreme-longshot noise (which dominated the
tails in the favourite-longshot check) from swamping the read.
"""
import argparse
from pathlib import Path

import pandas as pd

PROCESSED = Path(__file__).resolve().parent.parent / "data" / "processed"


def load(which: str, bsp_lo: float = 3, bsp_hi: float = 30) -> pd.DataFrame:
    df = pd.read_parquet(PROCESSED / f"{which}.parquet")
    cols = ["WIN_BSP", "WIN_RESULT", "WIN_MARKET_ID",
            "WIN_PREPLAY_MAX_PRICE_TAKEN", "WIN_PREPLAY_MIN_PRICE_TAKEN"]
    df = df.dropna(subset=cols).copy()
    df = df[df["WIN_BSP"] > 1.0]

    # implied_p MUST be normalised against the whole market (every runner),
    # before any odds-band filter — normalising against a partial field
    # inflates implied probabilities and fakes a calibration gap.
    df["won"] = (df["WIN_RESULT"] == "WINNER").astype(int)
    df["raw_p"] = 1.0 / df["WIN_BSP"]
    df["implied_p"] = df["raw_p"] / df.groupby("WIN_MARKET_ID")["raw_p"].transform("sum")

    df = df[(df["WIN_BSP"] >= bsp_lo) & (df["WIN_BSP"] <= bsp_hi)]
    rng = df["WIN_PREPLAY_MAX_PRICE_TAKEN"] - df["WIN_PREPLAY_MIN_PRICE_TAKEN"]
    df = df[rng > 0.05]
    df["steam_score"] = ((df["WIN_PREPLAY_MAX_PRICE_TAKEN"] - df["WIN_BSP"])
                          / (df["WIN_PREPLAY_MAX_PRICE_TAKEN"] - df["WIN_PREPLAY_MIN_PRICE_TAKEN"]))
    df["steam_score"] = df["steam_score"].clip(0, 1)
    return df


def table(df: pd.DataFrame, n_buckets: int = 5) -> pd.DataFrame:
    df = df.copy()
    df["bucket"] = pd.qcut(df["steam_score"], n_buckets, labels=False, duplicates="drop")
    g = df.groupby("bucket")
    out = pd.DataFrame({
        "n_runners": g.size(),
        "avg_steam_score": g["steam_score"].mean(),
        "avg_bsp": g["WIN_BSP"].mean(),
        "implied_win_pct": g["implied_p"].mean() * 100,
        "actual_win_pct": g["won"].mean() * 100,
    })
    out["edge_pct_pts"] = out["actual_win_pct"] - out["implied_win_pct"]
    stake = 1.0
    g_ret = df.groupby("bucket").apply(
        lambda d: (d["won"] * (d["WIN_BSP"] - 1) * stake - (1 - d["won"]) * stake).sum(),
        include_groups=False,
    )
    out["flat_stake_roi_pct"] = (g_ret / (g.size() * stake) * 100).round(2)
    return out.round(3)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--set", choices=["discovery", "holdout"], default="discovery")
    p.add_argument("--buckets", type=int, default=5)
    p.add_argument("--bsp-lo", type=float, default=3)
    p.add_argument("--bsp-hi", type=float, default=30)
    args = p.parse_args()

    df = load(args.set, args.bsp_lo, args.bsp_hi)
    print(f"{args.set}: {len(df):,} runners after filters "
          f"(BSP {args.bsp_lo}-{args.bsp_hi}, real pre-play range)\n")
    print("Bucket 0 = drifted out hardest ... bucket N = steamed in hardest\n")
    print(table(df, args.buckets).to_string())
