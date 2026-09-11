"""
A backtest on the racing.com pilot data - ONE meeting, 65 runners.

READ THE SAMPLE SIZE BEFORE THE RESULT. Every other finding in this repo
ran on 500,000+ runners. This runs on 65. Nothing here is a result; it's a
demonstration of what the pipeline would produce if the data-access wall
documented in the README (schedule UI only exposes ~11 days of history, no
bulk source of race times) weren't there.

Method
------
racing.com gives the winner's official time and every other runner's
beaten margin, not each runner's own time. Estimate it with the standard
handicapping approximation: 1 length = 0.2 seconds. This is a real
approximation used industry-wide, not exact - margins compress at the
finish and the true lengths-per-second varies with pace, so treat these
times as indicative, not photo-finish accurate.

estimated_time = winner_time + margin_lengths * 0.2
speed_kmh = (distance_m / estimated_time) * 3.6

Then run the same test as favourite_longshot_bias.py, at a scale where it
cannot possibly produce a trustworthy answer: does actual speed on the day
line up with what the market (SP) priced in?
"""
from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parent.parent / "data" / "racing_com_pilot" / "2026-09-05_sandown_hillside.csv"

WINNER_TIME_SEC = {
    1: 95.79,   # 1:35.79
    2: 101.55,  # 1:41.55
    3: 58.19,
    4: 80.17,   # 1:20.17
    5: 79.07,   # 1:19.07
    6: 79.73,   # 1:19.73
    7: 93.66,   # 1:33.66
    8: 57.22,
}
LENGTH_SECONDS = 0.2


def load() -> pd.DataFrame:
    df = pd.read_csv(DATA)
    df = df[df["scratched"] == 0].copy()
    df["margin_l"] = df["margin_l"].fillna(0.0)
    df["winner_time_s"] = df["race"].map(WINNER_TIME_SEC)
    df["est_time_s"] = df["winner_time_s"] + df["margin_l"] * LENGTH_SECONDS
    df["speed_kmh"] = (df["distance_m"] / df["est_time_s"]) * 3.6
    df["won"] = (df["pos"] == 1).astype(int)
    raw_p = 1.0 / df["sp"]
    df["implied_p"] = raw_p / raw_p.groupby(df["race"]).transform("sum")
    return df


if __name__ == "__main__":
    df = load()
    print(f"n = {len(df)} runners, {df['race'].nunique()} races, ONE meeting, ONE day.")
    print("This is a demonstration of method, not a finding. See docstring.\n")

    print(df[["race", "pos", "runner", "distance_m", "margin_l", "est_time_s",
               "speed_kmh", "sp", "implied_p"]].round(2).to_string(index=False))

    print("\n--- naive 'fastest on the day' vs 'shortest price' agreement ---")
    for race, g in df.groupby("race"):
        fastest = g.loc[g["speed_kmh"].idxmax(), "runner"]
        shortest_price = g.loc[g["sp"].idxmin(), "runner"]
        winner = g.loc[g["won"] == 1, "runner"].values[0]
        print(f"race {race}: winner={winner!r:26} "
              f"fastest-on-day={fastest!r:26} favourite={shortest_price!r}")

    print("\n--- market calibration, this meeting only (n=65 - do not trust this) ---")
    df["bucket"] = pd.qcut(df["implied_p"], 3, labels=["longest 1/3", "mid 1/3", "shortest 1/3"])
    g = df.groupby("bucket", observed=True)
    calib = pd.DataFrame({
        "n": g.size(),
        "implied_win_pct": (g["implied_p"].mean() * 100).round(1),
        "actual_win_pct": (g["won"].mean() * 100).round(1),
        "avg_speed_kmh": g["speed_kmh"].mean().round(2),
    })
    print(calib.to_string())
    print("\nWith ~20 runners per bucket, standard error on a win rate here is "
          "roughly +/-9 percentage points. Nothing in that table is distinguishable "
          "from noise - which is the whole point of showing it.")
