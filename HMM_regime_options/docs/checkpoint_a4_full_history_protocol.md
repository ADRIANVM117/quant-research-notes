# Checkpoint A4 — cobertura histórica completa v1

Fecha de registro: 2026-09-25. Esta variante no modifica A, A3 ni la regla v2.

## Universo y calendario fijados antes de las consultas

Se auditan todas las sesiones presentes en la serie diaria de SPY ya archivada
desde 2020-01-01 hasta 2026-08-31: 1,674 sesiones, desde 2020-01-02 hasta
2026-08-31. El calendario se fija por la serie diaria, no por la respuesta de
opciones, IV, skew o liquidez.

Las respuestas válidas ya guardadas se reutilizan sin modificarlas. Para una
fecha sin respuesta válida, la cadena se descarga y se conserva comprimida de
forma reversible como JSON en `data/raw/`. Si una consulta falla, su respuesta
se conserva bajo `data/raw/failures/` y la fecha queda disponible para reintento
posterior. Una respuesta válida jamás se consulta de nuevo.

## Selección y cotización sin cambios

Se reutilizan literalmente `checkpoint_a_pair_selection_v2.md` y
`checkpoint_a3_continuity_protocol.md`: mismo vencimiento; 21–45 DTE; delta
put [-.35, -.15] y call [.15, .35]; desempate por DTE, suma de error delta,
mayor error individual e IDs. Bid/ask no intervienen en la selección.

Una cotización de par es utilizable si ambos contratos tienen bid/ask finitos,
bid > 0 y ask >= bid. `wide_spread` es spread/mid > .20; bid cero, ask menor
que bid y bid/ask inválidos se registran por separado. El skew es IV put menos
IV call. Un salto extremo es |cambio de skew| > .05 respecto al último skew
disponible; se registra si coincide con cambio de vencimiento, sin inferir causa.

La fecha de cadena es t y su disponibilidad se mantiene como supuesto para la
siguiente sesión, al no contar con timestamp histórico de publicación EOD.

## Muestra fijada para IV idénticas

Se inspeccionan las primeras sesiones esperadas de enero y julio de cada año
2020–2026 (14 fechas). Para cada una se conserva el texto original de IV put y
call del par seleccionado y se agrupan valores exactamente iguales entre fechas.
La muestra depende exclusivamente del calendario, no de valores de IV.

## Decisión de suficiencia para investigación

- **GO:** al menos 95% de respuestas y pares elegibles en cada año completo,
  al menos 95% de pares utilizables, y ningún hueco consecutivo > 5 sesiones.
- **REVISAR:** existe una serie material pero algún año/mes incumple cobertura,
  continuidad o calidad de cotización; requiere acotar el periodo disponible.
- **STOP:** no existe un tramo multianual material con cadenas comparables.

Esta decisión solo evalúa calidad/suficiencia de datos. No prueba anticipación,
capacidad predictiva ni entrena modelos.
