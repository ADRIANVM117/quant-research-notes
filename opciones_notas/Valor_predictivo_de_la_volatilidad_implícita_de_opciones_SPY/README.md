# Valor predictivo de la volatilidad implícita de opciones SPY

## Pregunta de investigación

¿La volatilidad implícita de opciones SPY cercana a 30 días informa mejor sobre la volatilidad realizada de las próximas 20 sesiones que `vol20`?

## Hipótesis económica

Las opciones pueden incorporar información prospectiva sobre la volatilidad futura, aunque la volatilidad implícita también incluye una prima por riesgo.

## Estado actual

La factibilidad de datos está reportada en [docs/options_iv30_data_feasibility_audit.md](docs/options_iv30_data_feasibility_audit.md). La investigación predictiva está **NO INICIADA**.

## Primer entregable

Una notebook descriptiva de las cadenas SPY: IV por strike y vencimiento, y calidad de cotizaciones.

## Límite temporal visible

La hora de publicación/cotización no está verificada. Usar datos fechados en `t` para una decisión en `t+1` sigue siendo un supuesto EOD, no un hecho demostrado por los archivos locales.
