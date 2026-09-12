# Paper bet log — Flemington, 12 September 2026

No real money. This is a live, forward-looking test of two things this
project already has an opinion on — one boring and expected to lose at a
known rate, one already rejected on 3 years of historical data and
tracked here only out of curiosity.

## Races covered

Races 4–10 only. Races 1–3 had already jumped or were mid-running when
this started (~1:16pm) — betting on them would be hindsight, not a paper
bet, so they're excluded.

## Two strategies, $10 flat stake each, per race

1. **FAVOURITE** — back the shortest-priced runner at the *late* snapshot
   (closest to jump). This is the honest baseline: expected to lose
   roughly the market's overround, no more, no less. The point of
   tracking it is to see whether live results roughly match that
   expectation — a real-time sanity check on the project's own
   calibration finding, not a strategy.
2. **DRIFT** — back whichever runner's price lengthened the most between
   the early snapshot (taken ~1:16pm, hours before some of these races)
   and the late snapshot (just before jump). This is the exact pattern
   `price_drift_signal.py` found promising and `drift_robustness.py` then
   showed didn't survive year/liquidity/field-size splits. Tracked here
   explicitly labelled **already rejected** — if it wins today that's a
   coincidence, not vindication; the repo's conclusion doesn't change on
   one afternoon's results either way.

## Data source and known limitations

racing.com's public Field page, not Betfair's exchange — `W` price shown
is a fixed-odds price (not necessarily the same venue throughout the
day), and the "early" snapshot for later races was taken hours before
their jump (up to ~4 hours for Race 10), which is a much longer and less
comparable window than the horse-racing project's Betfair-based drift
work used. Treat this whole exercise as illustrative, not a rerun of the
original methodology at the same rigor.

## Settlement

Flat $10 paper stake per bet. Profit if the pick wins = stake × (SP − 1).
Loss if it doesn't run place = −stake. Results and running P&L logged in
`2026-09-12_flemington.csv` and summarised at the end of the meeting.

## Session stopped early — final summary

Stopped after Race 9 at the user's call ("not using anything useful").
Race 10 left unresolved, not counted.

| Race | FAVOURITE | Result | P&L | DRIFT | Result | P&L |
|---|---|---|---|---|---|---|
| 4 | Mbube $2.80 | 2nd | -$10 | Honour The Bassett $46 | 9th | -$10 |
| 5 | Shockletz $3.20 | 1st | +$22 | Taramansour $81 | 9th | -$10 |
| 8 | Sheza Alibi $1.45 | 1st | +$4.50 | Autumn Boy $23 | 2nd | -$10 |
| 9 | Gold Coast Belle $1.90 | unplaced | -$10 | Charisse $151 | unplaced | -$10 |

**FAVOURITE: 2W-2L, net +$6.50. DRIFT: 0W-4L, net -$40. Combined: -$33.50 on $90 staked.**

Also logged: Races 1-3 excluded (already run before tracking started),
Races 6-7 missed (resulted before their late snapshot was captured -
a real check-in cadence problem, not backfilled to avoid hindsight
bias).

**Honest read:** four races settles nothing statistically. DRIFT going
0-for-4 is consistent with the repo's existing conclusion (rejected,
no edge) - not new evidence either way. FAVOURITE finishing up $6.50
is also unremarkable at this sample size - a well-calibrated market
losing roughly its overround over time looks exactly like this in a
four-race sample that happened to land two winners. The operational
value was real, though: this exercise surfaced a genuine execution-risk
lesson (races 6-7 missed because live tracking has a check-in cadence
cost a backtest never shows) that's arguably more useful than the
P&L number itself.
