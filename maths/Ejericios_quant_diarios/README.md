1. 
---
---
2. <b> Semana 02 </b> 
> Volatilidad, actualizacion de creencias, Esperanza condicional, entropy pooling
  - 03: la varianza es lineal, la volatilidad no es lineal en el tiempo  
  - 04 : El orden de los retornos importa
  - 06 : Dependencia en las colas & correlacion $ \neq$  probabilidad conjunta de crash
  - 07: Entropy pooling
    - Prior p+informacion nueva⟶posterior q
    - pero bajo el principio: no cambies de p mas de lo necesario para satisfacer la informacion nueva.
	​


3.<b> Semana 03 </b>
> mercados + series de tiempo + research 
  - 01 :Informacion predictiva  
    - $ Market→\mathcal{F}_t​​→Features→E[rt+1​∣\mathcal{F}_t​]→Alpha→Portfolio→Execution $
  - 02 :<b> $\beta$ como exposición de mercado y construcción de  posiciones de portafolio </b>  
    - En research $ r=α+Xf+ε $  y su contraparte en portfolio: $ b=X^⊤w$  : La primera pregunta de dónde vinieron los retornos; la segunda pregunta qué riesgos/exposiciones estás construyendo con tus posiciones.
  - 03 : <b> Una beta estimada no es una constante física. qué significa estimarla, qué incertidumbre tiene y qué ocurre cuando cambia el régimen </b>
  -04 : <b>microestructura y ejecución: Una señal puede ser estadísticamente real y aun así no ser económicamente operable después de spread, fees e impacto. </b>
     - distinción importante a lo que hemos construido :
     -  $\underbrace{E[r_{t+1} \mid \mathcal{F}_t]}_{\text{statistical alpha}} \longrightarrow \underbrace{\text{position}}_{\text{portfolio decision}} \longrightarrow \underbrace{\text{cost} + \text{execution}}_{\text{implementation}} \longrightarrow \boxed{\text{realized P\&L}}$

