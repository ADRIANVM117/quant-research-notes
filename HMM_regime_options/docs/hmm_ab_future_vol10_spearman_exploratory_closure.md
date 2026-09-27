# Cierre — evaluación HMM A/B frente a `vol20` para volatilidad realizada a 10 sesiones

Fecha: 2026-09-27  
Estado del experimento evaluado: **INCONCLUSA**.

## Resultado registrado

La muestra común tuvo 659 fechas elegibles. Las correlaciones de Spearman con `future_vol10` fueron:

| Predictor | Correlación |
|---|---:|
| `vol20_t` | 0.197562 |
| `A_predictive_risk_next` | 0.297447 |
| `B_predictive_risk_next` | 0.308399 |

Las comparaciones preespecificadas fueron:

| Comparación | Diferencia | IC exploratorio 95 % | Cierre |
|---|---:|---|---|
| A menos `vol20` | 0.099884 | [-0.132622, 0.313986] | INCONCLUSA |
| B menos A | 0.010952 | [-0.086623, 0.149053] | INCONCLUSA |

Ambos intervalos incluyen cero. Conforme al protocolo fijado antes de ejecutar, esto es inconcluso respecto a mejora.

## Límites del cierre

2024–2026 ya era un periodo visto. Esta evaluación es histórica exploratoria y no una prueba prospectiva intacta. No se demostró utilidad para decisiones de riesgo, ni una diferencia de correlación se interpreta como utilidad económica.

Estos resultados no justifican seleccionar otra distribución, horizonte o métrica usando el mismo periodo. Se conservan intactos código, datos y resultados de la evaluación.

Este documento cierra únicamente el experimento de correlación HMM A/B frente a `vol20` para volatilidad realizada a diez sesiones; no declara cerrado el proyecto completo.
