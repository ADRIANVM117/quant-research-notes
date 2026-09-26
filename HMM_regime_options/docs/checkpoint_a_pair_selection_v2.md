# Checkpoint A — regla de selección por par v2

Fecha de registro: 2026-09-25  
Estado: nueva variante de auditoría; no modifica el protocolo v1 ni sus resultados.

## Propósito

Reevaluar las seis respuestas originales con puts y calls del **mismo
vencimiento**. Esta variante responde a la necesidad de que la diferencia de
IV compare contratos con DTE idéntico; no constituye una nueva prueba de
alerta ni de modelo.

## Elegibilidad, fijada antes del recálculo

Se conserva exactamente la ventana original: DTE entre 21 y 45, inclusiva;
put con delta en [-0.35, -0.15]; call con delta en [+0.15, +0.35]. Cada
contrato debe tener fecha, ID, tipo, vencimiento, strike, IV y delta válidos.

Un vencimiento es elegible si, para una misma fecha de cadena, tiene al menos
un put y un call elegibles. Un par usa dos contratos de ese único vencimiento.
Si no existe ningún vencimiento elegible, la fecha se marca **no elegible**.

## Selección y desempate, fijados antes del recálculo

Para cada combinación put/call de un vencimiento elegible se calcula:

1. distancia del DTE a 30;
2. suma de los errores absolutos de delta respecto de -0.25 y +0.25;
3. máximo de ambos errores de delta;
4. ID del put y después ID del call, en orden lexicográfico.

Se elige el par con el mínimo lexicográfico de esa tupla. Así se privilegia
primero el vencimiento más próximo a 30 DTE; los pasos 2–4 resuelven todos los
empates sin usar precios, volumen, OI ni IV.

## Auditoría separada de cotizaciones

La selección no excluye contratos por bid/ask. Para cada contrato elegido se
registran bid, ask y spread absoluto (`ask - bid`) y, por separado:

- `bid_zero`: bid numérico igual a cero;
- `ask_below_bid`: ask numérico menor que bid;
- `wide_spread`: bid y ask válidos, positivos y con `(ask-bid)/mid > 0.20`,
  donde `mid=(ask+bid)/2`;
- `missing_or_invalid_bid_ask`: bid o ask ausente, no numérico o no finito.

Las banderas pueden coexistir salvo `wide_spread`, que no se calcula para bid
cero, ask menor que bid o valores faltantes/inválidos.
