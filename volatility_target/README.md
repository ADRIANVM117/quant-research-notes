# Volatility target

## Portable daily-data pipeline

This project carries a reusable Alpha Vantage daily-data pipeline. Its code never
uses an absolute project path: copy `data/`, `data_ingest/`, `data_quality/`,
`.gitignore`, `requirements.txt`, and a private `.env` into a new project.

Required local configuration (never commit it):

```text
ALPHAVANTAGE_API_KEY=...
```

Install the pinned dependencies once:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Update one instrument and run its quality gate in a single command. The expected
date must be the latest *completed* US trading session, avoiding an accidental
claim of freshness during a weekend, holiday, or before the market close.

```powershell
python data_ingest/run_daily_pipeline.py --symbol SPY --asset-class etf --expected-session-date 2026-11-10
```

The contract is:

- `data/raw/`: immutable API responses, named by symbol and requested date.
- `data/parquet/<asset_class>/`: canonical Silver daily histories.
- `data/gold/daily_series/<asset_class>/`: validated copies approved for research.
- `data/quality/`: generated quality report and issue/status CSVs.

To audit an existing Silver series without downloading:

```powershell
python data_quality/validate_daily_sanity.py --asset-class etf --symbol SPY
```

The data directories are intentionally Git-ignored. The scripts, catalogue, and
quality logic are versioned and portable.
