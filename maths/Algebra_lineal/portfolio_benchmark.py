import numpy as np
import time

def run_benchmark():
    """
    Benchmark comparativo de simulación de portafolios en trading cuantitativo:
    Método Secuencial (Arreglos 1D en bucle) vs Método Vectorizado (Matriz 2D en Batch).
    Fundamentado en los principios geométricos de 'Mathematics for Machine Learning'
    por Tivadar Danka.
    """
    # Fijar semilla para reproducibilidad
    np.random.seed(42)
    
    # Parámetros de la simulación
    T = 1000   # Número de días de observaciones históricas de retornos
    n = 100    # Número de activos financieros en el universo
    P = 1000   # Número de portafolios con ponderaciones distintas a evaluar
    
    print("================================================================================")
    print("INICIANDO BENCHMARK DE RENDIMIENTO GEOMÉTRICO (QUANTFRAME)")
    print("================================================================================")
    print(f"Configuración:")
    print(f" - Universo de Activos (n): {n}")
    print(f" - Serie Temporal (T):     {T} días")
    print(f" - Portafolios a evaluar:  {P}")
    print("================================================================================")

    # 1. Matriz de retornos históricos de los activos: X (T x n)
    # Cada fila es un día, cada columna representa el retorno de un activo específico.
    X = np.random.normal(0.0005, 0.015, (T, n))
    
    # 2. Generar matriz de pesos iniciales crudos: W_raw (n x P)
    # Donde cada columna representa el vector de pesos crudos de un portafolio.
    W_raw = np.random.uniform(0.1, 1.0, (n, P))
    
    # --------------------------------------------------------------------------
    # ESCENARIO A: Enfoque Secuencial (Uso de Arreglos Unidimensionales planos (n,))
    # --------------------------------------------------------------------------
    # Extraemos cada columna como un vector plano 1D (shape: (n,)), imitando la
    # flexibilidad de la notación sobre papel que critica el autor.
    portafolios_1D = [W_raw[:, i] for i in range(P)]
    
    start_seq = time.perf_counter()
    
    retornos_seq = []
    for w_1D in portafolios_1D:
        # Normalizar el vector 1D para que la suma sea 1 (hiperplano afín de inversión)
        suma_w = np.sum(w_1D)
        w_val = w_1D / suma_w  # Sigue teniendo forma (n,)
        
        # Calcular serie temporal de retornos individuales del portafolio: y_p = X @ w
        y_p = X @ w_val  # Resulta en un vector plano (T,)
        retornos_seq.append(y_p)
        
    # Reconstruimos la matriz total de retornos apilando columnas: (T x P)
    retornos_seq_matrix = np.column_stack(retornos_seq)
    
    end_seq = time.perf_counter()
    time_seq = end_seq - start_seq
    
    # --------------------------------------------------------------------------
    # ESCENARIO B: Enfoque Vectorizado Estricto (Matriz Bidimensional 2D en Batch)
    # --------------------------------------------------------------------------
    # Mantenemos las dimensiones alineadas geométricamente. W_raw ya es (n, P).
    start_vec = time.perf_counter()
    
    # Normalizar los pesos de manera vectorizada utilizando Broadcasting controlado.
    # np.sum(axis=0, keepdims=True) produce un arreglo de forma (1, P) en lugar de plano.
    # Al dividir (n, P) / (1, P), NumPy propaga la división correctamente por columnas.
    W_valid_2D = W_raw / np.sum(W_raw, axis=0, keepdims=True)  # Matriz estricta (n x P)
    
    # Multiplicación matricial pura de un solo paso: Y = X @ W
    # Dimensiones: (T x n) @ (n x P) -> Resultado: (T x P)
    retornos_vec_matrix = X @ W_valid_2D
    
    end_vec = time.perf_counter()
    time_vec = end_vec - start_vec
    
    # --------------------------------------------------------------------------
    # CONTROL DE CALIDAD Y COMPARACIÓN
    # --------------------------------------------------------------------------
    # Garantizar que la equivalencia matemática es absoluta
    assert np.allclose(retornos_seq_matrix, retornos_vec_matrix), "¡Falla de equivalencia matemática!"
    
    speedup = time_seq / time_vec
    
    print(f"RESULTADOS DEL BENCHMARK:")
    print(f" -> Tiempo Secuencial (Bucle For, 1D arrays): {time_seq:.6f} segundos")
    print(f" -> Tiempo Vectorizado (Batch 2D, Matmul):     {time_vec:.6f} segundos")
    print(f" -> Factor de Aceleración (Speedup):           {speedup:.2f}x")
    print("================================================================================")
    print("ANÁLISIS TEÓRICO (Tivadar Danka):")
    print("1. En el enfoque secuencial, Python incurre en una enorme sobrecarga por")
    print("   la interpretación de bucles y la creación repetitiva de arreglos.")
    print("2. En el enfoque vectorizado, al estructurar los datos como una matriz")
    print("   bidimensional estricta de (n, P), permitimos que NumPy ejecute")
    print("   multiplicaciones a través de bibliotecas BLAS de bajo nivel altamente")
    print("   optimizadas que aprovechan el hardware de forma paralela (SIMD).")
    print("================================================================================")

if __name__ == "__main__":
    run_benchmark()
