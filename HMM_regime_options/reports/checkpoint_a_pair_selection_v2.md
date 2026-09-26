# Checkpoint A — reevaluación por par v2

Esta salida usa exclusivamente respuestas crudas existentes. No modifica `docs/checkpoint_a_protocol.md` ni `reports/checkpoint_a_report.md`.

**Fechas elegibles: 6 de 6.**

| Fecha | Elegible | Vencimiento / DTE | Put (ID; delta; IV; bid / ask / spread; banderas) | Call (ID; delta; IV; bid / ask / spread; banderas) |
|---|---|---|---|---|
| 2025-04-04 | sí | 2025-05-02 / 28 | SPY250502P00470000; Δ=-0.25665 (err=0.00665); IV=0.46365; 10.45 / 10.68 / 0.23; none | SPY250502C00540000; Δ=0.25002 (err=2e-05); IV=0.31731; 6.13 / 6.35 / 0.22; none |
| 2025-01-17 | sí | 2025-02-14 / 28 | SPY250214P00583000; Δ=-0.24542 (err=0.00458); IV=0.15146; 3.86 / 3.89 / 0.03; none | SPY250214C00612000; Δ=0.25997 (err=0.00997); IV=0.11244; 3.02 / 3.05 / 0.03; none |
| 2024-08-05 | sí | 2024-09-06 / 32 | SPY240906P00487000; Δ=-0.25124 (err=0.00124); IV=0.35633; 8.64 / 8.85 / 0.21; none | SPY240906C00545000; Δ=0.2538 (err=0.0038); IV=0.22951; 4.96 / 5.2 / 0.24; none |
| 2023-10-27 | sí | 2023-11-24 / 28 | SPY231124P00396000; Δ=-0.24332 (err=0.00668); IV=0.21975; 3.59 / 3.61 / 0.02; none | SPY231124C00425000; Δ=0.25665 (err=0.00665); IV=0.16122; 2.91 / 2.93 / 0.02; none |
| 2022-06-13 | sí | 2022-07-13 / 30 | SPY220713P00350000; Δ=-0.23174 (err=0.01826); IV=0.35633; 5.37 / 5.49 / 0.12; none | SPY220713C00396000; Δ=0.24567 (err=0.00433); IV=0.25877; 3.85 / 3.97 / 0.12; none |
| 2021-11-26 | sí | 2021-12-27 / 31 | SPY211227P00435000; Δ=-0.25391 (err=0.00391); IV=0.2978; 4.32 / 8 / 3.68; wide_spread | SPY211227C00475000; Δ=0.24017 (err=0.00983); IV=0.16122; 2.1 / 4.09 / 1.99; wide_spread |

## Interpretación de banderas

`missing_or_invalid_bid_ask` se refiere exclusivamente a ausencia/valor no numérico/no finito. `bid_zero`, `ask_below_bid` y `wide_spread` se reportan por separado, con `wide_spread` definido antes del cálculo como spread/mid > 20%. La selección no usa cotizaciones.

Regla y desempates: `docs/checkpoint_a_pair_selection_v2.md`.
