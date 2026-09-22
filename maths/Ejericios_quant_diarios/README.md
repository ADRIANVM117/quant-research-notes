1. 
---
---
<b> Semana 02 </b> 
> Volatilidad, actualizacion de creencias, Esperanza condicional, entropy pooling
  - 03: la varianza es lineal, la volatilidad no es lineal en el tiempo  
  - 04 : El orden de los retornos importa
  - 06 : Dependencia en las colas & correlacion $ \neq$  probabilidad conjunta de crash
  - 07: Entropy pooling
    - Prior p+informacion nueva⟶posterior q
    - pero bajo el principio: no cambies de p mas de lo necesario para satisfacer la informacion nueva.
	​


<b>Semana 03 </b>
> mercados + series de tiempo + research 
  - 01 :Informacion predictiva  
    - $ Market→\mathcal{F}_t​​→Features→E[rt+1​∣\mathcal{F}_t​]→Alpha→Portfolio→Execution $
  - 02 :<b> $\beta$ como exposición de mercado y construcción de  posiciones de portafolio </b>  
    - En research $ r=α+Xf+ε $  y su contraparte en portfolio: $ b=X^⊤w$  : La primera pregunta de dónde vinieron los retornos; la segunda pregunta qué riesgos/exposiciones estás construyendo con tus posiciones.
  - 03 : <b> Una beta estimada no es una constante física. qué significa estimarla, qué incertidumbre tiene y qué ocurre cuando cambia el régimen </b>
  - 04 : <b>microestructura y ejecución: Una señal puede ser estadísticamente real y aun así no ser económicamente operable después de spread, fees e impacto. </b>
     - distinción importante a lo que hemos construido :
     -  $\underbrace{E[r_{t+1} \mid \mathcal{F}_t]}_{\text{statistical alpha}} \longrightarrow \underbrace{\text{position}}_{\text{portfolio decision}} \longrightarrow \underbrace{\text{cost} + \text{execution}}_{\text{implementation}} \longrightarrow \boxed{\text{realized P\&L}}$
  - 05 : <b> separar una señal estadísticamente detectable de una señal económicamente útil y decidir si una hipótesis merece sobrevivir. </b>
     - $\boxed{\text{predictable}} \neq \boxed{\text{tradable}} \neq \boxed{\text{robust}}.$
     - $\mathcal{F}_t \rightarrow \text{Hypothesis} \rightarrow \text{Signal} \rightarrow \text{OOS} \rightarrow \text{Costs} \rightarrow \boxed{\text{Research Decision}} \rightarrow \text{Portfolio/Execution.}$
     - Una señal  puede ser predictable estadísticamente, desaparecer después de costes y por tanto no ser tradable, o sobrevivir costes pero haber sido seleccionada entre tantas pruebas que todavía no tengas evidencia suficiente de que sea robust.
  - 06 : <b> Diagnóstico de research </b>
     - Aprender a decidir qué investigar después cuando un modelo OOS mejora, sin caer inmediatamente en más features o modelos
       - Tiene que ser falsable:
\[
\boxed{\text{Si ocurre X, abandono } H_1.}
\]
     - $\text{OOS result} \rightarrow \boxed{\text{conditional diagnosis}} \rightarrow \text{competing explanations} \rightarrow \text{falsifiable experiment} \rightarrow \text{Keep/Kill}$

  - 07 : <b> incertidumbre en una estimación no es lo mismo que riesgo del mercado.    </b>
     - Data→Estimate​→Uncertainty​→Decision.
     - point estimate $ \neq $known parameter   

--- 

 <b>Semana 04 </b>

> Alpha aporta evidencia sobre oportunidades; Portfolio/Risk decide cuánto de esa evidencia es económicamente soportable dadas las dependencias, liquidez y riesgo actuales.
>
> $ informacion disponible→estimacion→incertidumbre→distribucion→dependencia→decision​.$


  - 01: <b> Un estimador estadísticamente más directo no necesariamente produce la mejor decisión económica. </b>

     - $ \text{Data} \rightarrow \hat{\theta} \rightarrow \underbrace{\text{estimation uncertainty}}_{\text{ayer}} \rightarrow \boxed{\text{shrinkage}} \rightarrow \tilde{\theta} \rightarrow \text{Decision.}
 $
  - 02 : <b> Actualización bayesiana ¿cuánto debería cambiar mi creencia cuando llegan datos nuevos? </b>
     - Bayesian updating empieza a explicar **cuánto**:
       - $$\text{Prior precision} + \text{Data precision} \rightarrow \text{Posterior}$$
       - $$\text{evidence strength} \neq \text{effect magnitude.}$$
 
  - 03 : <b> Una predicción no sólo debe tener una media; debería tener una distribución </b> 
     - $ \text{point estimate} \rightarrow (\hat{\mu}, \, \text{uncertainty}) \rightarrow \boxed{\text{distribution}} \rightarrow \text{decision.} $

     - $ (R,p) \rightarrow \text{Research View} \rightarrow (R,q). $
  - 04 : <b>Existen infinitos \(q\) que podrían satisfacer una view, así que ¿por qué elegir uno sobre los demás? Ésta es la entrada correcta a Entropy Pooling  </b>
     - concretar : $ p \xrightarrow{\text{view}} \boxed{q^*} $
        -  $ {q^* = \arg\min_q D_{KL}(q \| p) \quad \text{s.a. views}} $ 
   - 05 <b> una view no sólo puede ser incierta; puede estar equivocada o entrar en conflicto con otra evidencia </b>
     - \[
\hat{\theta} \rightarrow \text{uncertainty} \rightarrow \text{shrinkage} \rightarrow \text{Bayesian updating} \rightarrow (R,p) \rightarrow \text{views} \rightarrow q^*
\]

     - hoy añadimos la pieza que evita convertir todo esto en matemática decorativa:

       - \[
\boxed{\text{evidence} \rightarrow \text{view} \rightarrow \text{decision} \rightarrow \text{falsification}}.
\]
   - 06 <b> dependencia temporal y leakage: una estimación puede ser matemáticamente impecable y aun así ser información imposible de conocer en \(t\). </b>
       - una decisión sólo puede condicionarse a información disponible en ese momento. 
       - En portfolio escribíamos:
          - $$ q(\cdot\mid\text{views disponibles en }t). $$
       - En alpha research:
          - $$ E[r_{t+1} ∣F_t] $$  
   - 07 <b> Riesgo condicional conocido en $t$ frente a error porque el régimen que estimaste dejó de representar el presente </b> 
    - $ \underbrace{E[R_{t+1} \mid \mathcal{F}_t]}_{\text{Alpha}} \neq \underbrace{\mathcal{D}(R_{t+1} \mid \mathcal{F}_t)}_{\text{Risk state}}.$
 
--- 

 <b>Semana 05 </b>

> Riesgo de estrategia y portfolio desde P&L.
> Pasar de medir riesgo a entender cómo una estrategia contribuye al riesgo total, cuándo el sizing debe cambiar y qué evidencia justificaría intervenir una estrategia live.

   - 01 <b> Sharpe responde aproximadamente cuánto retorno recibiste por unidad de variabilidad. Drawdown responde algo diferente: qué ocurrió en el camino desde un máximo anterior. Y ninguno de los dos, por sí solo, demuestra que una hipótesis económica haya muerto. </b>
      - $$ \boxed{\text{Alpha quality}} \neq \boxed{\text{Risk}} \neq \boxed{\text{Path}} $$


