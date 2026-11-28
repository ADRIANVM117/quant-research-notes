# TLT adjusted-close reconciliation

## Inputs

- Staging Parquet SHA-256: `81fb80209a69cab30c14d4c129f3b9128e89791d607e24f9e09af3ac54f85d01`
- Silver Parquet SHA-256: `09c3c14f9ecd3f163cfd1c6bb670ee2a7b1c1db2bde0b882b81726fb7bf28fcf`
- Preserved Raw SHA-256: `62b03f8c40bb7fa9cc92678a48a82cacf026ef58f1f5e5c064de92acbd74922d`
- Provider metadata last refreshed: `2026-11-27`

## Scale ratio

- Overlap sessions: 2203
- Min / median / max: 0.995818646085 / 0.995818646085 / 0.995818646085
- Standard deviation: 4.28859985307e-16; range: 2.10942374679e-15
- Annual detail is in `ratio_by_year.csv`.

## Return comparison

- Return pairs: 2202
- Maximum absolute simple-return difference: 3.03576608296e-16
- Maximum absolute log-return difference: 8.881784197e-16
- Absolute log-return p95 / p99: 8.881784197e-16 / 8.881784197e-16
- Largest differences are listed in `largest_return_differences.csv`.

## Post-Silver dividends and boundary

- Silver ends on 2026-10-07; staging has 1 positive-dividend sessions after that date.
- `dividends_after_silver_end.csv` contrasts the observed historical ratio with a simple prior-close dividend factor. It is an arithmetic compatibility check, not causal attribution.
- On 2026-11-02, the simple prior-close dividend factor is 0.995806451613; the observed historical ratio differs by 1.21944716771e-05. This is similar in magnitude, but not exact and is not causal proof.
- `staging_boundary_continuity.csv` uses the staging vintage alone; no synthetic splice was created.

## Calendar coverage

- XNYS expected / observed: 4252 / 4252.
- Missing XNYS sessions: 0; extraordinary observed dates: 0.

## Decision

- `INNOCUOUS_SCALE_FOR_RETURNS`.
- Within the recorded numerical tolerance, the adjusted-close difference preserves daily returns and behaves as a scale transformation.
