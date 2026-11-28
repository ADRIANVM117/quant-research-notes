# QR-DMN-14 — Authorized-freeze procedure

Run this procedure only after an explicit authorization to create the versioned dataset.

## Preconditions

1. Confirm that `data/gold_versions/dmn_historical_2010_v1/` is absent.
2. Run the read-only verifier and dry run:

```powershell
Momentum_systematic_strategies/.venv/Scripts/python.exe Momentum_systematic_strategies/data/staging/historical_2010/panels/dmn_historical_2010_v1/verify_historical_panel.py
Momentum_systematic_strategies/.venv/Scripts/python.exe Momentum_systematic_strategies/data/staging/historical_2010/panels/dmn_historical_2010_v1/freeze_historical_panel.py
```

3. Require `PRECHECK=PASS`, `DRY_RUN=PASS`, ten main symbols, and `BIL=SUBGOLD_REVIEW (excluded)`.

## One authorized write

```powershell
Momentum_systematic_strategies/.venv/Scripts/python.exe Momentum_systematic_strategies/data/staging/historical_2010/panels/dmn_historical_2010_v1/freeze_historical_panel.py --execute-freeze
```

The script copies the approved inventory into a same-volume uniquely named temporary sibling of the final directory, verifies every copied SHA-256, writes `FREEZE_MANIFEST.json`, and atomically renames the completed directory to:

`Momentum_systematic_strategies/data/gold_versions/dmn_historical_2010_v1/`

It rejects any existing or partial final destination, any destination other than that exact direct child of `data/gold_versions`, altered source matrices, missing support artifacts, non-approved main symbols, or any change to BIL's conditional status.

## Postconditions

1. Rerun `verify_historical_panel.py` against staging.
2. Hash every file in the versioned inventory and compare it with `FREEZE_MANIFEST.json` and the source inventory.
3. Confirm no `conditional_bil_*` file or BIL entry exists in the versioned directory.
4. Rehash the eight original Gold Parquets using `FROZEN_GOLD_INTEGRITY.csv`.
5. Record the final directory path and all hashes in the authorization report.

The procedure never overwrites existing versioned data and never writes Raw, Silver, the established Gold tree, or normal Quality paths.

## Review ZIP test command

After a standard extraction of the review ZIP, change into its top-level extracted directory and run:

```powershell
python tests/test_freeze_historical_panel.py
```

The ZIP keeps `freeze_historical_panel.py` beside `tests/`, so the test imports it directly without moving files or depending on repository-local datasets.
