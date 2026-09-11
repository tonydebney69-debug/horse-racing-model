# horse-racing-model

A quantitative crack at Australian/NZ thoroughbred racing, built with the same
discipline as [`coinbase-momentum-bot`](../coinbase-momentum-bot): measure
first, distrust anything that looks good on the first pass, and never tune
against the out-of-sample window.

**Where this sits in the honest landscape:** takeout/commission means the
average bettor loses money by construction. The only way this is worth
building is if a real, cost-surviving edge shows up in the data — not assumed
going in.

## Data

Source: [Betfair's Automation Hub](https://betfair-datascientists.github.io/data/dataListing/)
— free AU/NZ thoroughbred **exchange** data, 2020 to present. Betfair
publishes it themselves with no accuracy warranty.

Each row is one runner in one win market:
- `WIN_BSP` — the Betfair Starting Price (the exchange's closing/settlement
  price — a well-informed, highly liquid "fair value")
- pre-play min/max/weighted-average matched price and volume
- `WIN_RESULT` / `PLACE_RESULT`
- market overround at scheduled off

**This is market data, not form data** — no jockey, trainer, weight, barrier,
sectional times, or past-run history. That rules out building a genuine
predictive model of who wins for now; what it's good for is testing whether
the *market itself* is mispriced in any exploitable, systematic way. A form
database (PuntingForm, Racing Australia data feeds — mostly paid) would be
the next real investment if a market-based angle runs out.

```
python scripts/fetch_data.py          # re-fetch everything; data/ is gitignored
python scripts/load_data.py --holdout-months 8
```

`load_data.py` splits by calendar month: everything before the most recent
N months is `data/processed/discovery.parquet` (currently Jan 2023 – Dec
2025, ~563k runners / 57k markets); the rest is `holdout.parquet` (currently
Jan–Aug 2026, ~125k runners). **Holdout is not read until a hypothesis is
fully specified on discovery data alone.**

## Findings so far

### 1. Favourite-longshot bias — not present in BSP (`scripts/favourite_longshot_bias.py`)

The classic literature finding (favourites undervalued, longshots overvalued)
does **not** show up in Betfair's Australian BSP. Bucketing runners into
deciles by overround-adjusted implied probability, implied vs actual win
rate track each other within ~0.2 points across the whole odds spectrum —
essentially perfect calibration. Flat-stake ROI is negative in every bucket
before commission, worse after it. **BSP is a well-calibrated closing price;
there's no free lunch from price level alone.** This makes sense — BSP is a
late, high-liquidity exchange price, not the softer bookmaker/tote prices
where the published bias was originally documented.

### 2. Price drift (steamers vs drifters) — a real pattern, not yet trusted (`scripts/price_drift_signal.py`)

Tested whether runners whose price *shortened* into the jump ("steamers")
over- or under-perform runners whose price *drifted* out, independent of
final BSP level.

- Across BSP 3–30: drifters (price lengthened) flat-stake at **+2.7% ROI**
  before commission; steamers (price shortened) at **−3.7%**, a clean
  monotonic gradient across 5 buckets of ~72k runners each.
- Holding odds roughly constant (BSP 6–10 band): the same gradient holds,
  **+3.4% to −4.1%** — so it isn't just an odds-level confound.
  In BSP 10–15 the gradient is much weaker and non-monotonic — a genuine
  concern, not swept under the rug.

**Read this as "worth the next round of scrutiny," not "found an edge."**
Before this goes near a holdout check it needs: a significance test (the
per-bucket win-rate gaps are only ~1–2 standard errors on their own — the
signal so far is the *shape* across buckets, not any single point estimate),
robustness checks by field size / track tier / distance, and a realistic
commission and execution model (can you actually get the drifter's BSP, or
does backing drift-based selections move the price yourself?). Any of those
could kill it, the way every refinement killed the crypto bot's momentum
signals.

## Rules for this repo

1. Nothing gets called a "signal" until it survives a holdout check that
   happened *after* the method was fully frozen.
2. Every backtest reports returns net of a realistic commission, not just
   gross.
3. A result needs a plausible mechanism (order-flow, information, a named
   behavioural bias) — not just "the backtest liked it." Two of the crypto
   bot's most convincing-looking backtests were pure overfitting; assume the
   same risk here.
4. If nothing survives, that's a reportable result. `strategy-has-no-edge`
   was the honest, useful conclusion for the crypto side of this — it's an
   acceptable outcome here too.

## Layout

```
scripts/
  fetch_data.py              # download the raw CSVs (gitignored)
  load_data.py                # combine + discovery/holdout split -> parquet
  favourite_longshot_bias.py  # finding 1
  price_drift_signal.py       # finding 2 (in progress)
data/
  raw/                        # gitignored — re-fetch with fetch_data.py
  processed/                  # gitignored — rebuild with load_data.py
```
