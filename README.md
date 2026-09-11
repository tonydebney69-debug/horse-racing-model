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

**Update — it didn't survive scrutiny (`scripts/drift_robustness.py`).**
Run on the BSP 6–15 band (163k runners, 55k markets):

- *Year-by-year*: no consistent gradient. 2023 alone looked monotonic
  (+9.5% → −1.7% across buckets); 2024 and especially 2025 don't
  (2025: −2.6, +3.7, +0.1, −2.5, +4.0 — no trend).
- *Liquidity terciles* and *field-size quartiles*: same story — the
  gradient appears in some slices, flips or vanishes in others.
- *Market-clustered bootstrap* (1,000 resamples) on the pooled sample:
  drifters-minus-steamers ROI gap = **+5.2 pts, 95% CI [+0.27, +10.13]**.
  Technically excludes zero, but the lower bound sits right on it — and
  that's after already picking the odds band and grouping that looked
  cleanest, which is exactly the kind of look-back that manufactures
  significance out of noise.

**Verdict: parked, not confirmed.** A result that needs everything pooled
together to look significant, and falls apart under year/liquidity/field-size
splits, is indistinguishable from noise that happened to look structured.
There's also no clean mechanism — it runs opposite to the "steam = smart
money" folklore, and "the backtest said so" isn't a mechanism. Not
proceeding to the holdout check: freezing an unstable method and spending
the one honest look at 2026 data on it would waste it for no real
information.

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

## Where this leaves things

Two market-microstructure hypotheses tested on three years of real data,
neither survives: BSP is well-calibrated (no favourite-longshot bias to
exploit), and the price-drift pattern doesn't replicate across natural
splits. That's a legitimate result, not a dead end reported as one — same
conclusion as `strategy-has-no-edge` on the crypto side.

**What's left to try, roughly in order of how much it'd actually cost:**

1. Other market-only angles: same drift idea but measured differently (e.g.
   last-60-seconds price move instead of full pre-play range), overreaction
   to a market favourite scratching, in-play markets. Cheap to test, same
   free data, but same odds of ending up here again given how thin this
   data's information content is once BSP is already this well-calibrated.
2. **Form data** — jockey, trainer, weight, barrier, recent form, sectional
   times. This is the real missing ingredient; Benter's and every serious
   syndicate's edge comes from modelling the *horse*, not the *market*.
   Mostly paid (PuntingForm, Racing Australia feeds) — a real cost decision,
   not a weekend project.
3. Accept the conclusion and stop here. Given the account-limiting problem
   on retail bookmakers and Betfair's commission (discussed elsewhere), even
   a confirmed small edge would be hard to turn into real income — the
   market-only version of this was always the cheap way to find out whether
   there was anything here before spending money on form data.

## Layout

```
scripts/
  fetch_data.py               # download the raw CSVs (gitignored)
  load_data.py                 # combine + discovery/holdout split -> parquet
  favourite_longshot_bias.py   # finding 1 — no bias in BSP
  price_drift_signal.py        # finding 2 — drift gradient, looked promising
  drift_robustness.py          # finding 2, stress-tested — doesn't survive
data/
  raw/                         # gitignored — re-fetch with fetch_data.py
  processed/                   # gitignored — rebuild with load_data.py
```
