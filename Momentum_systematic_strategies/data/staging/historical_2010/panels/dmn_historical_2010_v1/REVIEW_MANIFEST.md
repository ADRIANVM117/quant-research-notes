# QR-DMN-13 — Historical Research Panel Construction

## Scope

This review constructs the staging-only candidate `dmn_historical_2010_v1` from eleven preserved, single-vintage Alpha Vantage daily-adjusted Parquets. It does not consult a provider, concatenate price levels across vintages, promote data, or modify any existing Raw, Silver, Gold, Quality, or research notebook.

## Version and execution context

- Repository branch: `main`
- Repository HEAD at execution: `ab22446faad72447f8a92c5728d4a58754e2c7a4`
- Panel calendar: complete preserved XNYS intersection, 4,252 sessions, 2010-01-04 through 2026-11-27.
- Main panel: SPY, QQQ, IWM, IWD, IWF, XLE, XLF, GLD, TLT, SHY.
- Conditional panel: main panel plus BIL.
- BIL policy: BIL remains `SUBGOLD_REVIEW`; its 106 R8 warnings are retained and it is excluded from the main panel.

## Source lineage

`LINEAGE.csv` records the relative preserved Raw and Parquet paths, SHA-256 values, provider metadata, coverage, dividend/split counts, quality status, and single-vintage rule for every input. `PRIOR_REFERENCE_RECONCILIATION.csv` preserves the prior conclusion that all pre-existing overlap comparisons are returns-equivalent constant-scale transformations.

## Full local outputs (not included in the review ZIP)

All six full matrices are retained beside this manifest under:

`Momentum_systematic_strategies/data/staging/historical_2010/panels/dmn_historical_2010_v1/`

Their SHA-256 values are immutable entries in `PANEL_MANIFEST.json`. The ZIP contains only small CSV samples, manifests, source, validation artifacts, and quality/coverage evidence.

## Methods and controls

- `adjusted_close` is read from a single preserved historical Parquet per instrument.
- Simple return: `adjusted_close[t] / adjusted_close[t-1] - 1`.
- Log return: `log(adjusted_close[t]) - log(adjusted_close[t-1])`.
- The common XNYS calendar requires a complete observed session for every constituent; no prices are imputed and no nonconsecutive-session return is manufactured.
- Saved matrices are read back and exactly compared to the in-memory matrices. `verify_historical_panel.py` independently recomputes returns from saved adjusted closes and verifies all matrix hashes.
- The warm-up dates for 126-session momentum, EWMA lambda 0.94 with 20 returns, and 63-session LSTM sequences are recorded in `PANEL_MANIFEST.json`.
- `FROZEN_GOLD_INTEGRITY.csv` verifies the eight Gold Parquets that existed before this research-panel work.

## Included review artifacts

- `build_historical_panel.py` — deterministic staging builder.
- `verify_historical_panel.py` — read-only identity and hash verifier.
- `PANEL_MANIFEST.json`, `PANEL_VALIDATION.md`, `PANEL_TEST_RESULTS.md`.
- `LINEAGE.csv`, `FROZEN_GOLD_INTEGRITY.csv`, `PRIOR_REFERENCE_RECONCILIATION.csv`.
- Preserved coverage and quality summaries, plus BIL’s existing low-volatility review summary.
- Six-row endpoint samples for adjusted-close and simple-return matrices.

## Limitations and decision

This is a candidate research panel, not a Gold promotion. The prior overlap result supports return continuity but does not establish that historical vendor vintages are interchangeable in price level. BIL is only conditionally available, pending any future explicit decision on its R8 warnings. No model was trained as part of QR-DMN-13.
