# QR-DMN-12 - BIL low-volatility quality review

## Evidence

- BIL staging rows: 4252; date range: 2010-01-04 through 2026-11-27.
- Raw SHA-256: `6b7b3678df47589b7e7c3fb267dc1c4dd93e32c42f1fc990891b606d65a14880`; provider last refreshed: `2026-11-27`.
- Quality state: `SUBGOLD_REVIEW` with 106 warnings and 0 rejections.

## R8 identical OHLC runs

- Runs: 106; sessions inside runs: 373.
- Runs with positive reported volume on every session: 106 of 106; zero-volume sessions inside runs: 0.
- The provider reports transactions/volume during these runs, so the warnings are not evidence of an absence of trading. They remain a data-granularity warning, not a global rule exception.

## Corporate actions

- The expected split is present on 2017-11-30 with coefficient 0.5.
- Adjusted return across the split session: 0; inspect `split_2017_11_30_window.csv` rather than splicing any vintage.
- Dividend sessions: 99; all associated adjusted returns are finite.

## Low-volatility implications

- Rolling 63-session zero-standard-deviation windows: 0.
- EWMA annual-volatility observations at or below the 12% target: 4231 of 4231.
- BIL is exposure-capped at 1x in every eligible EWMA session under a 12% target. Sharpe-style training must preserve a variance epsilon even when observed rolling variance is nonzero.

## Separate decisions

- Historical integrity: CONDITIONALLY SUPPORTED. Calendar coverage, reported volume, split evidence, and adjusted-return checks do not show a material break, but R8 should remain visible as a BIL-specific review condition.
- DMN training eligibility: CONDITIONALLY ELIGIBLE with variance safeguards and explicit documentation of low-volatility/capped-exposure behavior.
- No automatic exception, validator change, or promotion is created by this review.
