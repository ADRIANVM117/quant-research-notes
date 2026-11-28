# QR-DMN-14 — Historical Research Dataset Freeze Review

## Purpose

This package prepares, but does not perform, the versioned freeze of the QR-DMN-13 main historical research panel. It contains no full matrix, Raw response, credential, or promoted dataset.

## Source and intended destination

- Verified source: `Momentum_systematic_strategies/data/staging/historical_2010/panels/dmn_historical_2010_v1/`
- Intended one-time destination: `Momentum_systematic_strategies/data/gold_versions/dmn_historical_2010_v1/`
- Dataset inventory: three main matrices plus six provenance/quality artifacts listed in `PREFLIGHT_RESULTS.md`.
- BIL: excluded from the freeze; its separate conditional matrices remain staging-only and its status remains `SUBGOLD_REVIEW`.

## Security and integrity controls

- The normal script action is a read-only preflight. Promotion requires an explicit `--execute-freeze` flag.
- The version root must resolve to the physical authorized `data/gold_versions` sibling. A symlink or redirection resolving into Raw, Silver, Gold, Quality, or staging is rejected.
- The only accepted final destination is the exact direct child `data/gold_versions/dmn_historical_2010_v1`; existing or partial destinations are rejected.
- The freeze uses a same-volume temporary sibling directory, hashes all copied bytes, writes `FREEZE_MANIFEST.json`, then atomically renames only the verified temporary directory.
- The source manifest requires all ten main symbols to be `GOLD_APPROVED`, validates its three provenance-file SHA-256 values before copying, and rejects BIL if its conditional status changes.
- Tests use synthetic files only and prove the protected fixture Raw, Silver, Gold, and Quality roots are unchanged.

## Evidence included

- Freeze script and offline test suite.
- QR-DMN-13 manifest, lineage, validation, matrix-hash results, and samples.
- QR-DMN-14 preflight results and the exact future procedure.

## Result

The freeze mechanism is ready for a separately authorized one-time promotion. This review performed no promotion and created no `data/gold_versions/dmn_historical_2010_v1` directory.
