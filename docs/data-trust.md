# Data trust

The report checks its own data. Four checks run as DAX measures against the loaded model, so the result on screen is always the result for the data on screen. They show in the Data trust panel on the overview page, in the header pill, and in detail on page 3.

## The checks

| # | Check | Rule | Passes when | Scope | Status if it fails |
|---|---|---|---|---|---|
| 1 | Freshness | Latest `LoadLog[loaded_at]` compared with the last business date in `FactDaily` | Last load is before 07:00 CET on the day after the last business date | Latest load, whatever month is selected | Fail |
| 2 | Reconciliation | Revenue from `FactDaily` (all regions) minus `FactLedger` revenue | Absolute gap below €1 | Selected month | Fail |
| 3 | Completeness | Rows in `FactDaily` ÷ (countries × segments × days up to the last business date) | 100% | Selected month, follows the region filter | Fail |
| 4 | Late files | Count of `LoadLog` rows with status `pending` | 0 | All files | Warning only |

Measures: `Freshness Pass`, `Reconciliation Pass`, `Completeness Pass`, `Late Files Pass`; values `Freshness Value`, `Reconciliation Gap CM`, `Completeness CM`, `Late Files`; text `Check Detail`.

**Data trusted** (the header pill) means checks 1–3 pass. A late file alone keeps the pill mint, because the numbers already on screen are complete for the days they cover; it shows as a warning in the panel.

## Trust score

A single number from 0 to 100 for the panel header:

| Part | Weight | How it scores |
|---|---|---|
| Freshness | 30 | all or nothing |
| Reconciliation | 30 | all or nothing |
| Completeness | 25 | pro rata (99.9% complete gives 24.98) |
| Files loaded in the last 7 days | 15 | pro rata (20 of 21 files gives 14.3) |

## Issues present in the data

The synthetic data carries four known issues, so every check has something to show:

| Issue | Where it shows | Expected result |
|---|---|---|
| Ledger revenue for SaaS & subscriptions in March 2026 is €38,412.60 lower than the daily fact | Page 3 reconciliation chart: the gap line jumps in Mar 2026. Select Mar 2026 and the reconciliation tile fails. | Gap €38,413 in March, €0 in every other month |
| Two country × segment days missing in August 2026 (PL Travel & mobility on 14 Aug, NL Gaming on 22 Aug) | Page 3 heatmap: two amber cells in Aug 2026. Select Aug 2026 and the completeness tile fails. | 3,098 of 3,100 rows (99.94%) |
| The acquirer file `acq_south_20261031.csv` is still pending | Page 3 load log table and late-files tile; warning icon on the overview panel | 1 pending file |
| Latest load at 06:02 CET on 1 Nov 2026 | Header pill "Data trusted · 06:02", freshness tile | Pass (deadline 07:00) |

These values are also in `tests/expected_kpis.csv` and are checked by `tests/validation_queries.dax`.

## Why it is built this way

- The checks are measures, not a separate pipeline report. They run under the same filters as the visuals, so selecting a month checks that month.
- Every check has one threshold and one sentence of evidence (`Check Detail`), so a reader sees why it passed or failed without opening anything.
- Reconciliation ignores the region filter on purpose: the ledger has no country, so a regional comparison would always show a gap.
