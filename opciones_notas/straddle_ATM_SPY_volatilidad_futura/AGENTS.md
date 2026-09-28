# Reglas de trabajo del proyecto

## Datos y alcance

- Las cadenas originales de SPY en `../../HMM_regime_options/data/raw/` son **solo de lectura**. No se mueven, copian, sobrescriben ni regeneran desde este proyecto.
- Las rutas compartidas y su procedencia se mantienen en `docs/data_inventory.md`. No se descargan datos ni se consulta una API salvo una instrucción posterior y explícita.
- Los resultados, incluidos los negativos, nulos, bloqueados o inconclusos, se conservan. No se modifican reglas, muestras o salidas para mejorar un resultado ya observado.

## Implementación reproducible

- Los cálculos reutilizables viven en `scripts/`; las notebooks los llaman y no duplican toda la lógica.
- Cada análisis sustantivo requiere una notebook `.ipynb` **ejecutada** en `notebooks/`, con código, tablas o gráficos visibles, interpretación y una sección para notas del investigador.
- No se presenta como resultado una celda de código que no haya terminado correctamente. La notebook debe indicar sus fuentes y controles de calidad.
- Los artefactos de otros proyectos, en particular `HMM_regime_options`, permanecen fuera de alcance salvo lectura explícita de sus datos compartidos.

## Disciplina de investigación

- Antes de calcular resultados futuros o desempeño se registran reglas de selección, tratamiento de ausencias, controles de calidad y particiones temporales.
- Todo documento debe distinguir con claridad entre **hechos verificados en archivos/código** y **supuestos** (por ejemplo, disponibilidad EOD de la cadena antes de la siguiente sesión).
- Las limitaciones de cobertura, calidad de cotizaciones, disponibilidad temporal y periodos ya observados se reportan junto con cualquier conclusión.
