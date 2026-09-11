# horse-racing-model

A quantitative crack at Australian/NZ thoroughbred racing, built with the same
discipline as [`coinbase-momentum-bot`](../coinbase-momentum-bot): measure
first, distrust anything that looks good on the first pass, and never tune
against the out-of-sample window.

**Status: closed.** Four independent angles tested, none survive. See
"Final summary" at the bottom.

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
predictive model of who wins; what it's good for is testing whether the
*market itself* is mispriced in any exploitable, systematic way.

```
python scripts/fetch_data.py          # re-fetch everything; data/ is gitignored
python scripts/load_data.py --holdout-months 8
```

`load_data.py` splits by calendar month: everything before the most recent
N months is `data/processed/discovery.parquet` (Jan 2023 – Dec 2025, ~563k
runners / 57k markets); the rest is `holdout.parquet` (Jan–Aug 2026, ~125k
runners). **Holdout was never read** — no hypothesis here survived long
enough on discovery data to earn that look.

A small second dataset, `data/racing_com_pilot/`, holds one scraped meeting
used for finding 4 below — see that section for what it is and its (very
different, much smaller) scale.

## Findings

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

### 2. Price drift (steamers vs drifters) — looked real, didn't survive (`scripts/price_drift_signal.py`, `scripts/drift_robustness.py`)

Tested whether runners whose price *shortened* into the jump ("steamers")
over- or under-perform runners whose price *drifted* out, independent of
final BSP level.

First pass looked genuinely promising: across BSP 3–30, drifters flat-staked
at **+2.7% ROI** before commission, steamers at **−3.7%**, a clean monotonic
gradient across 5 buckets of ~72k runners each — and it held up when odds
level was controlled for (BSP 6–10 band: +3.4% to −4.1%).

It didn't survive stress-testing. Run on the BSP 6–15 band (163k runners,
55k markets):

- *Year-by-year*: no consistent gradient. 2023 alone looked monotonic;
  2024 and especially 2025 don't (2025: −2.6, +3.7, +0.1, −2.5, +4.0 — no
  trend).
- *Liquidity terciles* and *field-size quartiles*: same story — the
  gradient appears in some slices, flips or vanishes in others.
- *Market-clustered bootstrap* (1,000 resamples) on the pooled sample:
  drifters-minus-steamers ROI gap = **+5.2 pts, 95% CI [+0.27, +10.13]**.
  Technically excludes zero, but the lower bound sits right on it — and
  that's after already picking the odds band and grouping that looked
  cleanest, which is itself a look-back that manufactures significance out
  of noise.

**Verdict: parked, not confirmed.** A result that needs everything pooled
together to look significant, and falls apart under year/liquidity/field-size
splits, is indistinguishable from noise that happened to look structured.
There's also no clean mechanism — it runs opposite to the "steam = smart
money" folklore, and "the backtest said so" isn't a mechanism. Not run
against the holdout: freezing an unstable method and spending the one
honest look at 2026 data on it would waste it for no information.

### 3. Track / distance / time of day — also nothing (`scripts/track_distance_time_signal.py`)

No finish or sectional times exist in the Betfair data (see "Data" above),
so "time run" here means scheduled time of day, not race duration. Grouped
runners by distance bucket, time-of-day bucket, and individual track (71
tracks with 3,000+ runners), and checked market calibration in each group —
same test as finding 1, sliced a different way.

**Calibration gap is 0.00–0.09 percentage points everywhere** — the market
prices Hawkesbury as accurately as Muswellbrook, sprints as accurately as
staying races, morning racing as accurately as twilight. Flat-stake ROI
swings wildly by track (+17% to −25%) but that's noise, not signal: a
track's ROI in 2023–24 has essentially zero correlation with its own ROI in
2025 (r = 0.06; Murray Bridge went from the best track, +27%, to one of the
worst, −20%, the very next period).

### 4. Actual speed (distance ÷ time) — blocked by data access, then shown to be circular at any reachable scale (`scripts/racing_com_pilot_backtest.py`)

The Betfair data has no race times, so this needed a new source. Racenet
and Punters.com.au explicitly prohibit automated collection in their
robots.txt; Racing and Sports blocks bots outright (HTTP 403 regardless of
robots.txt); racing.com allows crawling and its terms were checked and
confirmed clear before anything was fetched. racing.com's schedule UI also
only exposes ~11 days of past results without already knowing a track's
exact URL slug for a given date — a real ceiling on how far back this path
can reach without a lot more reconnaissance.

One meeting was pulled (Sandown Hillside, 5 Sep 2026, 8 races, 65 runners,
`data/racing_com_pilot/`) and each runner's time estimated from the
winner's official time plus beaten margin (1 length ≈ 0.2s, the standard
approximation). Running the same "does it beat the market" test on it
surfaced the deeper problem directly: **the fastest-on-day runner was the
race winner in all 8 of 8 races.** That is not a finding — it's a tautology
of the estimation method. The winner has a beaten margin of zero by
definition, so it always computes as fastest. Same-day speed vs same-day
result can't be anything but circular, at any sample size. A speed signal
only means something as a horse's *past* races predicting a *future* one,
which needs the same-horse-reappears-over-weeks-or-months history that the
11-day access ceiling above already ruled out at useful scale.

(The 65-runner calibration table in that script is included for
completeness. With ~9-point standard errors on a win rate, it isn't a
result and shouldn't be read as one.)

## Rules this project followed

1. Nothing gets called a "signal" until it survives a holdout check that
   happened *after* the method was fully frozen.
2. Every backtest reports returns net of a realistic commission, not just
   gross.
3. A result needs a plausible mechanism (order-flow, information, a named
   behavioural bias) — not just "the backtest liked it."
4. If nothing survives, that's a reportable result, not a dead end reported
   as one. `strategy-has-no-edge` was the honest, useful conclusion for the
   crypto side of this project — it's an acceptable outcome here too.

## Final summary

Four independent angles, all on real data, none survive:

| # | Angle | Scale | Verdict |
|---|---|---|---|
| 1 | Favourite-longshot bias in BSP | 562k runners, 3 yrs | Market is well-calibrated — nothing to exploit |
| 2 | Price drift (steamers vs drifters) | 163k–358k runners | Looked real, killed by year/liquidity/field-size splits |
| 3 | Track / distance / time-of-day | 562k runners, 71 tracks | Calibration gap ~0 everywhere; ROI spread is pure noise |
| 4 | Actual speed (distance ÷ time) | 65 runners (data-access limited) | Structurally circular same-day; needs history this session couldn't reach |

**What this adds up to:** the Betfair exchange market for Australian
thoroughbreds is genuinely efficient — three separate, well-powered tests
of the market's own pricing found nothing to exploit, before or after
commission. The one angle that could plausibly still hold something
(modelling the horse itself, via real form and speed data) is blocked not
by a failed hypothesis but by a data-access wall: no free, legitimate,
bulk source of race times or form exists the way Betfair's own market data
was freely given. Getting past that wall means paying for it
(PuntingForm, Racing Australia feeds) — a real cost decision, not a
follow-up script.

**Recommendation: stop here.** Even setting the data-access wall aside,
turning a confirmed small edge into real income would still run into the
account-limiting and commission problems that make retail betting
structurally hard regardless of model quality. This project's real value
was answering the question cheaply, with free data, before considering
whether to spend money on form data — and the answer is that the
market-only version of this has nothing left in it.

## Layout

```
scripts/
  fetch_data.py                  # download the raw Betfair CSVs (gitignored)
  load_data.py                   # combine + discovery/holdout split -> parquet
  favourite_longshot_bias.py     # finding 1 — no bias in BSP
  price_drift_signal.py          # finding 2 — drift gradient, looked promising
  drift_robustness.py            # finding 2, stress-tested — doesn't survive
  track_distance_time_signal.py  # finding 3 — no calibration gap by track/distance/time
  racing_com_pilot_backtest.py   # finding 4 — speed idea, blocked then shown circular
data/
  raw/                           # gitignored — re-fetch with fetch_data.py
  processed/                     # gitignored — rebuild with load_data.py
  racing_com_pilot/              # small scraped sample used in finding 4 (committed, tiny)
```
