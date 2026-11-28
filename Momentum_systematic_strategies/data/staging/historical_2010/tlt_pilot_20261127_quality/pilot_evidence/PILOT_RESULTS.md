# QR-DMN-09 - Historical TLT pilot results

## Execution

- Authorization: one real Alpha Vantage request for TLT only.
- Provider function: `TIME_SERIES_DAILY_ADJUSTED`, `outputsize=full`.
- Start date requested: `2010-01-01`.
- Last completed US session required: `2026-11-27` (NYSE early close at 13:00 ET).
- Pipeline result: `COMPLETE`, effective date `2026-11-27`, quality result `GOLD_APPROVED`, promotion `NO`.
- No retry and no second provider request were made.

## Preserved isolated artifacts

- Raw JSON: `Momentum_systematic_strategies/data/staging/historical_2010/tlt_pilot_20261127/raw/TLT_2026-11-27.json`
- Raw SHA-256: `62b03f8c40bb7fa9cc92678a48a82cacf026ef58f1f5e5c064de92acbd74922d`
- Parquet: `Momentum_systematic_strategies/data/staging/historical_2010/tlt_pilot_20261127/parquet/etf/TLT.parquet`
- Parquet SHA-256: `81fb80209a69cab30c14d4c129f3b9128e89791d607e24f9e09af3ac54f85d01`
- Quality reports: `Momentum_systematic_strategies/data/staging/historical_2010/tlt_pilot_20261127_quality`

## Data quality and coverage

- Rows: 4252
- Date range: 2010-01-04 through 2026-11-27
- Schema columns: 14
- Adjusted close available for every row: YES
- Null counts: {"adjusted_close": 0, "close": 0, "dividend_amount": 0, "high": 0, "ingested_at_utc": 0, "low": 0, "open": 0, "provider_last_refreshed": 0, "provider_timezone": 0, "session_date": 0, "source": 0, "split_coefficient": 0, "symbol_requested": 0, "volume": 0}
- Duplicate symbol/date rows: 0
- Invalid or non-positive price rows: {"adjusted_close": 0, "close": 0, "high": 0, "low": 0, "open": 0}
- OHLC consistency violations: 0
- Positive dividend sessions: 202
- Non-unit split sessions: 0
- Maximum gap between retained session dates: 5 calendar days; gaps over seven days: 0
- Gap count is descriptive only; it does not replace a formal exchange-calendar completeness check.

## Silver comparison

- 2,203 sessions overlap with the existing Silver (2018-01-02 through 2026-10-07). OHLC, volume, dividends, and splits match exactly; `adjusted_close` differs on all overlap dates. See `TLT_SILVER_COMPARISON.md` and `.json` for details.

## Frozen Gold integrity

- All eight frozen Gold ETF SHA-256 values match the pre-pilot baseline. See `GOLD_INTEGRITY.csv`.

## Limits

- This is staging evidence only. TLT was not promoted to Gold and is not yet an approved research input.
- Provider provenance is preserved locally as Raw JSON; the review ZIP intentionally excludes large market-data files.
