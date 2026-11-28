# QR-DMN-13 execution evidence

- Build command: `Momentum_systematic_strategies/.venv/Scripts/python.exe build_historical_panel.py`
- Build result: PASS; 4,252 common XNYS sessions from 2010-01-04 through 2026-11-27; each return matrix has 4,251 rows.
- Read-only verification command: `Momentum_systematic_strategies/.venv/Scripts/python.exe verify_historical_panel.py`
- Read-only verification result: PASS; each saved simple and log return matrix is exactly recomputed from its saved adjusted-close matrix, all matrix hashes match `PANEL_MANIFEST.json`, and the BIL conditional policy is unchanged.
- Input quality check: canonical schema, unique dates, positive `adjusted_close`, and preserved XNYS coverage audit all passed for the eleven staging vintages.
- Frozen-data check: all eight pre-existing Gold Parquet SHA-256 values match `FROZEN_GOLD_INTEGRITY.csv`.

No provider request, Gold promotion, or write to existing Raw, Silver, Gold, or Quality paths was made during this construction.
