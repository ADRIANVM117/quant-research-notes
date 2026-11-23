# Regime-aware momentum

Esta línea estudia si la estabilidad de las exposiciones sistemáticas cambia entre periodos y si esos cambios ayudan a contextualizar la atribución de momentum. No presupone que haya un régimen discreto ni que un deterioro de atribución implique una pérdida de rentabilidad.

La primera notebook reproduce la atribución factorial congelada de `02_factor_momentum` para QQQ, XLE y XLF: MKT, SIZE y GV, OLS rolling de 252 sesiones y datos diarios Gold. La segunda compara ese benchmark con un filtro de Kalman de parámetros congelados, usando una cronología causal de actualización. No incluye HMM, changepoints, factores nuevos ni estrategias.

Los análisis consumen exclusivamente `data/gold/daily_series/etf/<SYMBOL>.parquet`.
