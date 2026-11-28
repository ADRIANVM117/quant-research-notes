# QR-DMN-14 — Historical Research Dataset Freeze: cierre

## Resultado

El congelamiento autorizado de `dmn_historical_2010_v1` finalizó correctamente el 2026-11-28. La única escritura de la operación fue el destino versionado:

`Momentum_systematic_strategies/data/gold_versions/dmn_historical_2010_v1/`

La promoción utilizó una copia temporal en el mismo volumen, verificación SHA-256 de todos los archivos y cambio atómico de directorio. El directorio de destino no existía antes de la ejecución y no se volvió a invocar `--execute-freeze` después de su creación.

## Controles previos

- Verificador read-only del panel QR-DMN-13: correcto.
- Preflight de `freeze_historical_panel.py` sin `--execute-freeze`: correcto; confirmó diez instrumentos principales y exclusión de BIL.
- Las validaciones offline de QR-DMN-14 v2 permanecen completas: 7/7, repetidas desde la raíz del repositorio. Ejecutarlas desde la carpeta profunda del panel excede la longitud de ruta de Windows para el fixture temporal; la suite está documentada para ejecutarse desde una raíz de extracción o del repositorio.
- El destino físico resuelto es el árbol versionado autorizado; no es un enlace ni está dentro de Raw, Silver, Gold habitual o Quality.

## Dataset congelado

- Versión: `dmn_historical_2010_v1`.
- Panel principal: SPY, QQQ, IWM, IWD, IWF, XLE, XLF, GLD, TLT y SHY.
- BIL: excluido. Su estado continúa siendo `SUBGOLD_REVIEW`; no hay matrices `conditional_bil_*` ni artefactos BIL en el destino.
- Cobertura del panel: 4,252 sesiones comunes, del 2010-01-04 al 2026-11-27; 4,251 retornos por matriz.

## Integridad fuente → destino

Los nueve artefactos promovidos conservan exactamente los mismos SHA-256 en staging y en el destino versionado:

| Archivo | SHA-256 |
| --- | --- |
| `main_adjusted_close.parquet` | `468a589340512c23aa311816848564f9e1b1ef4a23fca4f374224a0e6d986c9a` |
| `main_simple_returns.parquet` | `a424c58e6d30943905e74b693bc4b7848924c74d21ca4eb2b17b3a3739827293` |
| `main_log_returns.parquet` | `39c46adac15f9b59b28d034949d173d09e6d9ac82442888e4034fe36c252488e` |
| `PANEL_MANIFEST.json` | `f64810597bf38af740b39c25eabb87bbc34244309d59cdd8ccd7ea946129b90b` |
| `LINEAGE.csv` | `be5d0d93280a3ac6e9adbb3bc1df3b79b7610e86e4b4403eaa26ca1b6d508275` |
| `PANEL_VALIDATION.md` | `e24a32323519f9c6d2f9950a7b2b022b227fd9f6689f7e4e6e382db38bf28bd1` |
| `PANEL_TEST_RESULTS.md` | `3eefb587dd9e0880261f42d7958da83bd802ede9038dfc3dbbb8bcf9ace3ff8f` |
| `FROZEN_GOLD_INTEGRITY.csv` | `6e5ec999c4e0f74c803fbf51f4e97213fef41b6e3289580d9663c74d940a7db1` |
| `PRIOR_REFERENCE_RECONCILIATION.csv` | `b1425793dd60bf8416620913be9562758d26371a022025788967f30e4a866471` |

El destino incluye además `FREEZE_MANIFEST.json`, generado por la operación y con la lista de exclusiones, método de promoción y hashes anteriores.

## Protección de datos preexistentes

Se volvieron a calcular los SHA-256 de los ocho Gold congelados: GLD, IWD, IWF, IWM, QQQ, SPY, XLE y XLF. Los ocho coinciden con `FROZEN_GOLD_INTEGRITY.csv`.

La operación no escribe en `data/raw`, `data/silver`, `data/gold`, `data/quality` ni en notebooks. No se realizaron consultas a proveedores, commits ni pushes.

## Material de cierre

El paquete de cierre contiene este informe, el script y pruebas del congelamiento, el manifiesto de origen, el manifiesto final generado en el destino y los resultados de preflight. No contiene Parquet completos, credenciales ni datos de proveedor.
