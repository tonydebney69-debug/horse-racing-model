"""
Fetch Betfair's free AU/NZ thoroughbred exchange data (the Automation Hub).

Source: https://betfair-datascientists.github.io/data/dataListing/
Betfair publishes their own disclaimer: no warranty on accuracy/completeness.

Each row is one runner in one win (or place) market, with:
  - the Betfair Starting Price (BSP) - the exchange-derived "true" price
  - pre-play / in-play min/max/weighted-average matched prices and volume
  - the win/place result
  - the market's back/lay overround at scheduled off

This is exchange market data, not runner form data (no jockey/trainer/weight/
barrier/sectional history) - see README for what that limits us to.

Usage:
    python scripts/fetch_data.py            # fetch everything currently listed
    python scripts/fetch_data.py --years 2024 2025
"""
import argparse
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

BASE = "https://betfair-datascientists.github.io/data/assets"
RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
MONTHLY = RAW / "monthly"

# Full calendar years available as one zip of 12 monthly CSVs.
YEARS = [2020, 2021, 2022, 2023, 2024, 2025]
# Current year: published as separate monthly CSVs as each month closes.
CURRENT_YEAR = 2026
CURRENT_MONTHS = range(1, 13)


def _download(url: str, dest: Path, timeout: int = 60) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            data = r.read()
    except Exception as e:
        print(f"  skip {url.rsplit('/', 1)[-1]}: {e}")
        return False
    dest.write_bytes(data)
    return True


def fetch_years(years):
    RAW.mkdir(parents=True, exist_ok=True)
    MONTHLY.mkdir(parents=True, exist_ok=True)
    for y in years:
        zpath = RAW / f"ANZ_Thoroughbreds_{y}.zip"
        print(f"fetching {y}...")
        if _download(f"{BASE}/ANZ_Thoroughbreds_{y}.zip", zpath):
            with zipfile.ZipFile(zpath) as z:
                z.extractall(RAW / f"_tmp_{y}")
            for f in (RAW / f"_tmp_{y}").glob("*.csv"):
                f.replace(MONTHLY / f.name)
            for f in (RAW / f"_tmp_{y}").iterdir():
                f.unlink()
            (RAW / f"_tmp_{y}").rmdir()
            zpath.unlink()
        time.sleep(0.3)


def fetch_current_year_months(year, months):
    MONTHLY.mkdir(parents=True, exist_ok=True)
    for m in months:
        name = f"ANZ_Thoroughbreds_{year}_{m:02d}.csv"
        print(f"fetching {name}...")
        _download(f"{BASE}/{name}", MONTHLY / name)
        time.sleep(0.3)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--years", nargs="*", type=int, default=YEARS,
                    help="full calendar years to fetch as zips")
    p.add_argument("--skip-current", action="store_true",
                    help="don't fetch the in-progress current year")
    args = p.parse_args()

    fetch_years(args.years)
    if not args.skip_current:
        fetch_current_year_months(CURRENT_YEAR, CURRENT_MONTHS)

    n = len(list(MONTHLY.glob("*.csv")))
    print(f"\n{n} monthly files in {MONTHLY}")
    sys.exit(0)
