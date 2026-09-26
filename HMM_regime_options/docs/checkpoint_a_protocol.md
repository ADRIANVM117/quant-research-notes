# Checkpoint A — protocolo de auditoría de datos v1

Fecha de registro: 2026-09-25  
Estado previo: fijado antes de consultar las cadenas.

## Muestra preespecificada

| Fecha | Contexto usado para elegirla (no depende del skew) |
|---|---|
| 2025-04-04 | Sesión de tensión por la fuerte venta global posterior a anuncios arancelarios de EE. UU. |
| 2025-01-17 | Sesión reciente de mercado relativamente tranquilo, elegida como contraste de comienzos de año. |
| 2024-08-05 | Sesión de tensión por el episodio de volatilidad global de inicios de agosto. |
| 2023-10-27 | Sesión de tensión durante la venta de renta variable de octubre de 2023. |
| 2022-06-13 | Sesión de tensión en el ajuste bajista asociado a inflación y tipos. |
| 2021-11-26 | Sesión de tensión por la reacción inicial a la variante Ómicron. |

Las fechas se fijaron por acontecimientos/entornos de mercado publicados y no
por resultados de IV o skew. Son sesiones regulares de negociación de EE. UU.;
la alineación final se comprobará frente a la serie diaria del proveedor.

## Criterios fijados antes de la selección

- Objetivo de vencimiento: 30 días naturales hasta vencimiento (DTE).
- Ventana de vencimiento: 21 a 45 DTE, inclusiva.
- Objetivos de delta: put = -0.25; call = +0.25.
- Tolerancia de delta: error absoluto menor o igual a 0.10. Por tanto, puts
  en [-0.35, -0.15] y calls en [+0.15, +0.35].
- Un contrato es candidato solo si cumple simultáneamente tipo, DTE y delta,
  y tiene identificador, fecha de cadena, vencimiento, strike, IV y delta
  válidos.
- Por cada tipo, el contrato seleccionado es el candidato que minimiza, en
  este orden: (1) error absoluto de delta, (2) distancia absoluta a 30 DTE,
  (3) identificador de contrato en orden alfabético. No se emplean precios,
  volumen ni open interest para desempatar en esta auditoría.

## Consulta y trazabilidad

Se consultará `HISTORICAL_OPTIONS` para SPY y cada fecha, sin filtros de
contrato ni vencimiento, para auditar la cadena completa. Se consultará una
sola serie `TIME_SERIES_DAILY` de SPY con historia completa para comprobar las
seis fechas. Las respuestas se guardarán tal como las devuelva el proveedor en
`data/raw/`, sin URL de solicitud ni credenciales. El informe registra el
endpoint y parámetros no sensibles, pero nunca la clave.

## Regla temporal conservadora

El proveedor documenta el contenido histórico por fecha, pero no una marca de
tiempo histórica verificable de publicación EOD. Hasta verificarla, una cadena
con fecha t se considerará utilizable como pronto para una decisión posterior
al cierre de t y, operativamente, se tratará como señal disponible para la
siguiente sesión bursátil. No se le atribuye disponibilidad intradía ni se usa
para decisión al cierre de t.
