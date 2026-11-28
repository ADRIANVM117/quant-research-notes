# Comparacion TLT staging vs Silver existente

- Silver path: `Momentum_systematic_strategies/data/parquet/etf/TLT.parquet`
- Staging coverage: 2010-01-04 through 2026-11-27 (4252 sessions).
- Silver coverage: 2018-01-02 through 2026-10-07 (2203 sessions).
- Overlap sessions: 2203.

## Field-level result

| Field | Mismatched sessions | Detail |
| --- | ---: | --- |
| open | 0 | identical for all overlap sessions |
| high | 0 | identical for all overlap sessions |
| low | 0 | identical for all overlap sessions |
| close | 0 | identical for all overlap sessions |
| adjusted_close | 2203 | max abs=0.5897634307484907; mean abs=0.41444184855977495 |
| volume | 0 | identical for all overlap sessions |
| dividend_amount | 0 | identical for all overlap sessions |
| split_coefficient | 0 | identical for all overlap sessions |

## Interpretation

- OHLC, volume, dividend amount, and split coefficient agree exactly over the 2,203 shared sessions.
- `adjusted_close` differs on all shared sessions. This is consistent with a provider adjustment history being recalculated after the earlier Silver ingestion, but this pilot does not adjudicate which adjusted series should become canonical.
- Silver was read only; no existing Silver or Gold file was changed.
