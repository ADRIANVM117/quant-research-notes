# QR-DMN-14 — Preflight results

## Read-only checks executed

1. `verify_historical_panel.py`: PASS. The six staging matrices match their recorded SHA-256 values and the return matrices exactly recompute from adjusted closes.
2. `freeze_historical_panel.py` without `--execute-freeze`: PASS. It verified the source manifest, all six source matrix hashes, the manifest hashes of `LINEAGE.csv`, `FROZEN_GOLD_INTEGRITY.csv`, and `PRIOR_REFERENCE_RECONCILIATION.csv`, ten `GOLD_APPROVED` main instruments, and BIL as excluded `SUBGOLD_REVIEW`.
3. Fresh rehash of the eight original Gold Parquets: PASS.
4. Required destination `data/gold_versions/dmn_historical_2010_v1/`: absent, therefore neither existing nor partial.
5. Offline test suite `test_freeze_historical_panel.py`: 7 passed. It covers byte-identical atomic copy, BIL exclusion, rejection of existing/partial destinations, rejection of a non-versioned destination, non-modification of fixture Raw/Silver/Gold/Quality roots, rejection of a resolved version root redirected into Gold, and rejection of a tampered lineage hash before copy.

## Freeze inventory

The future versioned dataset contains only these source files:

- `main_adjusted_close.parquet`
- `main_simple_returns.parquet`
- `main_log_returns.parquet`
- `PANEL_MANIFEST.json`
- `LINEAGE.csv`
- `PANEL_VALIDATION.md`
- `PANEL_TEST_RESULTS.md`
- `FROZEN_GOLD_INTEGRITY.csv`
- `PRIOR_REFERENCE_RECONCILIATION.csv`

The three `conditional_bil_*` matrices and BIL itself are explicitly excluded.

## Current decision

No versioned dataset directory has been created. The only promotion-capable code is guarded by `--execute-freeze` and must not be invoked without a new, explicit authorization.
