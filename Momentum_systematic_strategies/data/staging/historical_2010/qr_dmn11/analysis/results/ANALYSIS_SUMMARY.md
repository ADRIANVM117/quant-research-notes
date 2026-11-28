# QR-DMN-11 isolated historical universe

## Acquisition boundary

- Ten authorized `TIME_SERIES_DAILY_ADJUSTED` requests were made once each: SPY, QQQ, IWM, IWD, IWF, XLE, XLF, GLD, SHY, and BIL.
- All were written under isolated staging with `--no-promote`; Raw, Silver, Gold, and normal Quality locations were not changed.
- TLT is incorporated as the prior QR-DMN-09 isolated staging series only.

## Coverage

- Eleven-instrument common intersection: 4252 XNYS sessions, 2010-01-04 through 2026-11-27.
- Individual coverage and corporate-action counts: `universe_coverage.csv`.
- XNYS completeness by staged instrument: `calendar_coverage.csv`.
- The eight frozen Gold files still match their pre-acquisition SHA-256 baseline: `frozen_gold_integrity.csv`.

## Quality

- Per-symbol quality state: `quality_summary.csv`.
- A `SUBGOLD_REVIEW` state remains staging-only and is not a promotion decision.

## Reference reconciliation

- Existing Gold is preferred as reference; Silver is used only where Gold is absent.
- Ratio, return, dividend, and split comparisons: `reference_reconciliation.csv`.
- `RETURNS_EQUIVALENT_CONSTANT_SCALE` means the staged and prior adjusted-close returns agree under the fixed diagnostic tolerance; it does not authorize combining raw price levels or promoting data.

## Limits

- No canonical vintage was selected, no adjusted-close series were merged, and no instrument was promoted to Gold.
- Any later promotion requires separate review of quality status and reference-vintage policy.
