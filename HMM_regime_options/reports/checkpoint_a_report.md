# Checkpoint A — resultado de auditoría

La metodología, muestra y límites se fijaron antes de las consultas en `docs/checkpoint_a_protocol.md`.

| Fecha | Candidatos put/call | Put seleccionado | Call seleccionado | Precio diario | Alineación |
|---|---:|---|---|---:|---|
| 2025-04-04 | 90/134 | SPY250430P00470000; DTE=26; delta=-0.25088; IV=0.46365; |Δ error|=0.00088; |DTE−30|=4 | SPY250502C00540000; DTE=28; delta=0.25002; IV=0.31731; |Δ error|=2e-05; |DTE−30|=2 | 505.2800 | sí |
| 2025-01-17 | 89/45 | SPY250221P00582000; DTE=35; delta=-0.24976; IV=0.15146; |Δ error|=0.00024; |DTE−30|=5 | SPY250221C00615000; DTE=35; delta=0.24553; IV=0.11244; |Δ error|=0.00447; |DTE−30|=5 | 597.5800 | sí |
| 2024-08-05 | 95/66 | SPY240913P00485000; DTE=39; delta=-0.24908; IV=0.34658; |Δ error|=0.00092; |DTE−30|=9 | SPY240913C00547500; DTE=39; delta=0.25062; IV=0.21975; |Δ error|=0.00062; |DTE−30|=9 | 517.3800 | sí |
| 2023-10-27 | 50/52 | SPY231208P00394000; DTE=42; delta=-0.24959; IV=0.21975; |Δ error|=0.00041; |DTE−30|=12 | SPY231201C00427500; DTE=35; delta=0.2493; IV=0.16122; |Δ error|=0.0007; |DTE−30|=5 | 410.6800 | sí |
| 2022-06-13 | 57/106 | SPY220722P00350000; DTE=39; delta=-0.25032; IV=0.34658; |Δ error|=0.00032; |DTE−30|=9 | SPY220705C00393000; DTE=22; delta=0.25124; IV=0.26853; |Δ error|=0.00124; |DTE−30|=8 | 375.0000 | sí |
| 2021-11-26 | 183/78 | SPY220107P00431000; DTE=42; delta=-0.2502; IV=0.2978; |Δ error|=0.0002; |DTE−30|=12 | SPY220107C00476000; DTE=42; delta=0.24773; IV=0.15146; |Δ error|=0.00227; |DTE−30|=12 | 458.9700 | sí |

## Cobertura de campos y exclusiones

### 2025-04-04
- Registros recibidos: 10376
- Fechas reportadas en cadena: `{"2025-04-04": 10376}`
- Requeridos faltantes/inválidos: `{}`
- Presencia de last/mark/bid/ask/volume/open_interest: `{"last": 10376, "mark": 10376, "bid": 10376, "ask": 10376, "volume": 10376, "open_interest": 10376}`
- Precio/bid/ask/volumen/OI faltantes o inválidos: `{}`
- Exclusiones: `{"DTE_outside_21_45": 8758, "delta_outside_tolerance": 1394}`

### 2025-01-17
- Registros recibidos: 9410
- Fechas reportadas en cadena: `{"2025-01-17": 9410}`
- Requeridos faltantes/inválidos: `{}`
- Presencia de last/mark/bid/ask/volume/open_interest: `{"last": 9410, "mark": 9410, "bid": 9410, "ask": 9410, "volume": 9410, "open_interest": 9410}`
- Precio/bid/ask/volumen/OI faltantes o inválidos: `{}`
- Exclusiones: `{"DTE_outside_21_45": 8230, "delta_outside_tolerance": 1046}`

### 2024-08-05
- Registros recibidos: 9994
- Fechas reportadas en cadena: `{"2024-08-05": 9994}`
- Requeridos faltantes/inválidos: `{}`
- Presencia de last/mark/bid/ask/volume/open_interest: `{"last": 9994, "mark": 9994, "bid": 9994, "ask": 9994, "volume": 9994, "open_interest": 9994}`
- Precio/bid/ask/volumen/OI faltantes o inválidos: `{}`
- Exclusiones: `{"DTE_outside_21_45": 9192, "delta_outside_tolerance": 641}`

### 2023-10-27
- Registros recibidos: 8246
- Fechas reportadas en cadena: `{"2023-10-27": 8246}`
- Requeridos faltantes/inválidos: `{}`
- Presencia de last/mark/bid/ask/volume/open_interest: `{"last": 8246, "mark": 8246, "bid": 8246, "ask": 8246, "volume": 8246, "open_interest": 8246}`
- Precio/bid/ask/volumen/OI faltantes o inválidos: `{}`
- Exclusiones: `{"DTE_outside_21_45": 7340, "delta_outside_tolerance": 804}`

### 2022-06-13
- Registros recibidos: 9226
- Fechas reportadas en cadena: `{"2022-06-13": 9226}`
- Requeridos faltantes/inválidos: `{}`
- Presencia de last/mark/bid/ask/volume/open_interest: `{"last": 9226, "mark": 9226, "bid": 9226, "ask": 9226, "volume": 9226, "open_interest": 9226}`
- Precio/bid/ask/volumen/OI faltantes o inválidos: `{}`
- Exclusiones: `{"DTE_outside_21_45": 7604, "delta_outside_tolerance": 1459}`

### 2021-11-26
- Registros recibidos: 10076
- Fechas reportadas en cadena: `{"2021-11-26": 10076}`
- Requeridos faltantes/inválidos: `{}`
- Presencia de last/mark/bid/ask/volume/open_interest: `{"last": 10076, "mark": 10076, "bid": 10076, "ask": 10076, "volume": 10076, "open_interest": 10076}`
- Precio/bid/ask/volumen/OI faltantes o inválidos: `{}`
- Exclusiones: `{"DTE_outside_21_45": 7858, "delta_outside_tolerance": 1957}`

## Disponibilidad temporal

La documentación de Alpha Vantage especifica que `HISTORICAL_OPTIONS` devuelve la cadena para una fecha y que el parámetro de fecha omitido devuelve la sesión previa, pero no publica una marca de tiempo histórica de disponibilidad EOD. Se aplica por tanto la regla conservadora fijada: una cadena de t no se considera utilizable antes de una decisión posterior al cierre de t y, operativamente, se reserva para la siguiente sesión. Falta confirmar un SLA/timestamp de publicación del proveedor.

## Decisión de viabilidad

**GO.** Las seis fechas tienen selección put/call y calendario alineado.

Aspectos no verificados: hora exacta de publicación EOD, campos de liquidez suficientes, estabilidad de contrato al extender la muestra y coherencia de ajustes del subyacente.
