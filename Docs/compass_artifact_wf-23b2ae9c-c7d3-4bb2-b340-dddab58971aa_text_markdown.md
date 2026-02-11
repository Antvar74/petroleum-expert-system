# Framework integral de RCA para pegas de tubería en pozos petroleros

**La pega de tubería es el problema operacional más costoso en perforación, generando pérdidas de $2 mil millones anuales a nivel global y representando hasta el 25% del presupuesto total de pozos profundos.** Este framework presenta un sistema estructurado de clasificación, diagnóstico y análisis de causa raíz que puede automatizarse para detectar, clasificar y reportar eventos de pega en tiempo real, respaldado por estándares API, IADC, SPE, ISO y NORSOK. El sistema se fundamenta en una taxonomía de 13 tipos de pega, un árbol de decisión binario con matriz de puntuación probabilística, y una arquitectura de datos de **más de 70 parámetros** organizados por criticidad y fuente. El objetivo es proporcionar outputs tanto operacionales (para el perforador en pozo) como ejecutivos (para dirección corporativa).

---

## Taxonomía completa: 13 mecanismos documentados de pega

La industria clasifica las pegas en dos categorías mayores según API RP 13D, IADC Drilling Manual 13th Ed. y múltiples papers SPE: **pega diferencial (~30% de incidentes)** y **pega mecánica (~70%)**. Dentro de estas categorías se identifican 13 mecanismos distintos, cada uno con firma diagnóstica específica.

### Categoría A — Pega diferencial

Opera cuando la sarta contacta el revoque (filter cake) en formaciones permeables bajo condición de sobrebalance. Se requieren **cinco condiciones simultáneas** (acrónimo STOPS): **S**arta estática, revoque **T**hick (grueso), **O**verbalance, formación **P**ermeable, **S**uperficie de contacto. La fuerza de retención se calcula como F = ΔP × Área de Contacto × Coeficiente de Fricción. Con 700 psi de sobrebalance, 360 in de contacto y fricción de 0.25, la fuerza puede alcanzar **189,000 lbs** (Courteille & Zurdo, 1985, SPE). El indicador diagnóstico clave es que **la circulación permanece normal** — no hay bloqueo anular. Adams (1977, SPE-6716) documentó que solo 1 de 310 pegas ocurrió con OBM, demostrando que los sistemas base aceite reducen el riesgo en >99%.

### Categoría B — Pegas mecánicas (12 sub-tipos)

| Tipo | Mecanismo | Indicador diferenciador clave |
|---|---|---|
| **Pack-off / empacamiento** | Sólidos móviles se empaquetan entre BHA y pared del pozo | Circulación **restringida/imposible**; SPP aumenta 500–1500 psi |
| **Limpieza deficiente** | Acumulación de recortes en lechos (pozos >30° inclinación) | Torque/drag gradual ↑; recortes redondeados en zarandas; ECD ↑ |
| **Ojo de llave (key seat)** | DP rota contra dogleg, talla ranura; BHA se atasca al sacar | Solo al sacar (POOH); libre hacia abajo; circulación normal |
| **Pozo bajo-calibre** | Formaciones duras desgastan barrena; nueva queda apretada | Ocurre al meter nueva barrena; verificar gauge de barrena anterior |
| **Geometría (ledges/doglegs)** | Salientes de formación dura o curvas severas atrapan BHA rígido | Overpull a profundidades específicas de cambio litológico |
| **Chatarra en pozo** | Debris metálico se traba entre BHA y pared | Torque errático; virutas metálicas en zarandas |
| **Cemento (fragmentos)** | Trozos de cemento de zapata/rathole bloquean espacio anular | Fragmentos de cemento en zarandas; torque repentino |
| **Cemento fresco (green cement)** | Sarta entra en cemento sin fraguar; flash-set alrededor del pipe | Chances de liberar "muy limitadas, si no inexistentes" |
| **Hinchamiento reactivo (shale)** | Arcillas esmectíticas absorben agua del filtrado WBM | Tight hole progresivo; MBT, PV, YP ↑; cavings hidratados |
| **Colapso de formación** | Arenas/gravas no consolidadas colapsan al pozo | Fill on bottom; SPP ↑; síntomas similares a pack-off |
| **Flujo plástico (sal/shale)** | Sobrecarga comprime formaciones móviles hacia el pozo | Pozo bajo-calibre progresivo; requiere MW cercano a gradiente overburden |
| **Barite sag** | Barita (ρ=4.2 g/cc) sedimenta en lado bajo de pozos inclinados | Variación de MW hasta **±4.0 ppg** en retornos; ángulo crítico 40–60° |

---

## Árbol de decisión binario para clasificación automática

El siguiente algoritmo sintetiza los frameworks de spANALYZE (Ejike et al., 2020), Merlin ERD, Kingdom Drilling Services (Aird, 2020) y el IADC Drilling Manual. Está diseñado para implementación programática directa.

**La pregunta discriminadora más potente es: "¿Se puede circular?"** Si la respuesta es SÍ → diferencial o key seat. Si es NO → mecánica/pack-off. La segunda pregunta clave: "¿La sarta estaba estática o en movimiento?" Si estática + circulación normal → **pega diferencial con alta confianza**.

```
INICIO: SARTA PEGADA
│
├─ Q1: ¿Sarta ESTÁTICA cuando se pegó?
│   ├─ SÍ →
│   │   ├─ Q2: ¿Se puede CIRCULAR a presión normal?
│   │   │   ├─ SÍ → Q3: ¿Frente a formación PERMEABLE?
│   │   │   │   ├─ SÍ → ★ PEGA DIFERENCIAL [Confianza ALTA]
│   │   │   │   └─ NO → Q3b: ¿Existe sobrebalance >200 psi?
│   │   │   │       ├─ SÍ → ★ PEGA DIFERENCIAL [Confianza MEDIA]
│   │   │   │       └─ NO → Evaluar otros mecanismos
│   │   │   └─ NO (circulación restringida/imposible) →
│   │   │       └─ ★ PACK-OFF ESTÁTICO / COLAPSO [SPP ↑ confirma]
│   │
│   └─ NO (sarta EN MOVIMIENTO) →
│       ├─ Q4: ¿Dirección del movimiento?
│       │   ├─ SACANDO (POOH) →
│       │   │   ├─ Q5: ¿Puede moverse HACIA ABAJO?
│       │   │   │   ├─ SÍ + circulación normal → ★ KEY SEAT [Alta]
│       │   │   │   ├─ SÍ + circulación restringida → ★ BAJO-CALIBRE/LEDGE
│       │   │   │   └─ NO → Q6: ¿Circulación?
│       │   │   │       ├─ Restringida → ★ PACK-OFF (recortes/cavings)
│       │   │   │       └─ Normal → ★ GEOMETRÍA (dogleg severo)
│       │   │
│       │   ├─ METIENDO (RIH) →
│       │   │   ├─ Circulación normal → ★ BAJO-CALIBRE / LEDGE / CEMENTO
│       │   │   └─ Circulación restringida → ★ PACK-OFF por surge
│       │   │
│       │   └─ ROTANDO (perforando) →
│       │       ├─ Torque súbito + pérdida circulación → ★ COLAPSO/PACK-OFF
│       │       ├─ Torque gradual ↑ + SPP ↑ → ★ LIMPIEZA DEFICIENTE
│       │       └─ En sal/shale plástico → ★ FLUJO PLÁSTICO
```

### Matriz de puntuación probabilística para diagnóstico automatizado

Cuando los síntomas son ambiguos, el sistema asigna puntos por cada indicador observado. **El tipo con mayor puntuación es el diagnóstico más probable**; si los dos primeros están dentro de 2 puntos, el caso es ambiguo y requiere datos adicionales.

| Indicador observado | Diferencial | Pack-off | Key seat | Geometría | Inestabilidad | Limpieza |
|---|---|---|---|---|---|---|
| Sarta estática al pegarse | **+3** | +1 | 0 | 0 | +1 | 0 |
| Movimiento POOH al pegarse | 0 | +1 | **+3** | +2 | +1 | 0 |
| Circulación NORMAL | **+3** | 0 | +2 | +1 | 0 | 0 |
| Circulación restringida/imposible | 0 | **+3** | 0 | 0 | **+3** | +2 |
| SPP aumentó significativamente | 0 | **+3** | 0 | 0 | +2 | +2 |
| Puede moverse abajo, no arriba | 0 | 0 | **+3** | +2 | 0 | 0 |
| Formación permeable presente | **+3** | 0 | 0 | 0 | 0 | 0 |
| Sobrebalance >200 psi | +2 | 0 | 0 | 0 | 0 | 0 |
| DLS >3°/100ft en trayectoria | 0 | 0 | **+3** | +2 | 0 | 0 |
| Shale reactiva / formación inestable | 0 | +1 | 0 | 0 | **+3** | 0 |
| Cavings en zarandas | 0 | +2 | 0 | 0 | **+3** | 0 |
| Recortes redondeados/ausentes | 0 | +1 | 0 | 0 | 0 | **+3** |
| Overpull creciente en conexiones | **+3** | 0 | 0 | 0 | 0 | +1 |
| Variación MW in/out >0.5 ppg | 0 | +1 | 0 | 0 | 0 | 0 |

**Confianza**: >12 puntos = Alta (>80%); 8–12 = Media (50–80%); <8 = Baja (<50%, solicitar datos adicionales).

---

## Estándares internacionales aplicables al framework

El sistema se respalda en un corpus de **más de 25 estándares y normas internacionales**. A continuación, los más relevantes organizados por aplicación específica al RCA de pegas.

### Estándares primarios para diagnóstico de fluidos y mecánica

**API RP 13B-1/13B-2** (5th Ed., 2019/2014; equivalente ISO 10414-1/2) define los métodos estandarizados para evaluar todas las propiedades del fluido que contribuyen a pega diferencial: densidad, filtrado API/HTHP, espesor de revoque, gel strengths, y contenido de sólidos. La **Sección 6** (filtración) y el **Anexo K** (Permeability Plugging Test) son directamente diagnósticos para evaluar riesgo de pega diferencial. El **Anexo J** cubre pruebas de sag de barita.

**API RP 13D** (7th Ed., 2023) es fundamental para análisis de limpieza de pozo. Su **Sección 9** proporciona la metodología para evaluar eficiencia de transporte de recortes, carrying capacity, y formación de lechos. La **Sección 8** cubre swab/surge, relevante para pegas inducidas por colapso durante maniobras.

**API RP 7G/7G-1** (16th Ed./2023) proporciona los cálculos de límites operacionales para operaciones de liberación: máximo overpull, torque, cargas combinadas, y el **método de elongación (stretch) para determinación de punto libre** (Sección DS-16 del IADC Manual). La fórmula clave: **Longitud libre (ft) = (Elongación en pulgadas × FPC) ÷ Fuerza de tracción (klbs)**, donde FPC = Área seccional × 2,500.

### Estándares de integridad de pozo y gestión de riesgo

**NORSOK D-010** (Rev. 5, 2021) es el estándar más prescriptivo globalmente para integridad de pozo. Su **Sección 4.10** manda la recopilación sistemática de datos operacionales y reporte de incidentes — directamente aplicable al reporte post-evento de pegas. El principio de doble barrera y las **50 tablas de criterios de aceptación** del Capítulo 15 proporcionan el marco para evaluar si las barreras del pozo estaban mantenidas al momento de la pega.

**ISO 16530-1:2017** establece el framework de gobernanza del ciclo de vida del pozo. La fase de Construcción (Sección 8) aborda directamente operaciones de perforación, y el **Anexo A** proporciona técnicas de evaluación de riesgo aplicables a pegas.

### Papers SPE clave para el framework automatizado

| Paper | Contribución al framework |
|---|---|
| **SPE-56628** (Aadnøy et al., 1999) | Ecuaciones de punto libre en pozos direccionales; análisis de fuerzas en pega diferencial |
| **SPE-27529** (Biegler & Kuhn, 1994) | Modelo estadístico multivariable que cuantifica probabilidad de pega por día de perforación |
| **SPE-98378** (Siruvuri et al., 2006) | Red neuronal convolucional para predicción; 3 casos del Golfo de México |
| **IADC/SPE-178888** (Salminen et al., 2016) | Sistema de predicción en tiempo real con **38 minutos de alerta promedio** antes del evento |
| **SPE-123374** (Gulsrud et al., 2009) | Método estadístico usando correlación BHP/SPP/torque para detección temprana |
| **IPTC-24141-MS** (2024) | **Primera implementación en campo** de modelo Bayesiano + física para identificación de causa raíz |

Los algoritmos de ML han demostrado precisión de hasta **99.45%** con SVM y **100%** con Extra Trees (Elmousalami & Elaskary, 2020, Gulf of Suez). El enfoque más prometedor para un sistema automatizado es la combinación de **modelos físicos (T&D + hidráulica) con redes Bayesianas** (IPTC-24141-MS), que proporciona tanto predicción como causa raíz probable con puntuación de probabilidad.

---

## Framework RCA estructurado: del síntoma a la causa raíz

### Metodología 5-Whys por tipo de pega

Para cada tipo, la cadena causal sigue patrones predecibles que pueden pre-programarse en el sistema. El ejemplo para **pega diferencial** ilustra la profundidad requerida:

1. **¿Por qué se pegó?** → Sarta embebida en revoque contra formación permeable por presión diferencial
2. **¿Por qué era tan alta la presión diferencial?** → Peso de lodo excesivo respecto a presión de poro (sobrebalance >200 psi)
3. **¿Por qué el peso de lodo era excesivo?** → Zona depletada no identificada; margen de seguridad excesivo aplicado
4. **¿Por qué no se identificó la zona depletada?** → Datos de pozos offset insuficientes; modelo geomecánico no actualizado en tiempo real
5. **¿Por qué no se actualizó el modelo?** → Ausencia de procedimiento estándar para calibración en tiempo real; brecha organizacional entre geología y perforación

**Causa raíz: Procedural/Organizacional** — proceso de planeación deficiente y comunicación interdisciplinaria inadecuada.

Para **limpieza deficiente**, la cadena típica termina en: gasto de flujo inadecuado por limitación de equipo de bombeo → conflicto no resuelto entre límites de ECD y requisitos mínimos de limpieza → ausencia de plan hidráulico integrado y monitoreo de transporte de recortes en tiempo real. **Causa raíz: Técnica/Procedural**.

Para **key seat**: BHA se traba en ranura en dogleg severo → DLS excesivo no corregido → viajes de limpieza (wiper trips) no realizados por presión de tiempo → procedimientos insuficientes de gestión de doglegs. **Causa raíz: Factores humanos/Procedural**.

### Diagrama Ishikawa adaptado a pegas

El análisis fishbone utiliza **6 categorías** adaptadas de la metodología estándar:

- **Man (Humano)**: Deficiencia de entrenamiento en señales de alerta, fatiga (turnos >12 hrs), comunicación deficiente en cambio de turno, "normalización de la desviación" — aceptar condiciones deterioradas como normales
- **Machine (Equipo)**: Diseño de BHA inadecuado, jars no funcionales, capacidad de bombeo insuficiente, calibración de sensores deficiente, equipo de control de sólidos inadecuado
- **Method (Procedimiento)**: Parámetros de perforación incorrectos, prácticas de maniobra sin viajes de limpieza, manejo de lodo deficiente, tiempo de conexión excesivo, circulación insuficiente antes de maniobras
- **Material (Fluidos/Formación)**: MW excesivo o insuficiente, revoque grueso/permeable, reología inadecuada, tipo de lodo incorrecto para formación, contaminación del sistema
- **Measurement (Datos)**: Surveys inexactos, ECD no calculado en tiempo real, presión de poro mal estimada, monitoreo de recortes inadecuado, trending de torque/drag no implementado
- **Mother Nature (Ambiente)**: Tipo de formación imprevisto, ventana de presión estrecha, condiciones HPHT, geometría de pozo con alta inclinación

### Modelo Bowtie para gestión de riesgo

El análisis Bowtie coloca la **pega de sarta** como Top Event, con amenazas a la izquierda (sobrebalance, inestabilidad, limpieza deficiente, key seating, bajo-calibre, cemento/chatarra) y consecuencias a la derecha (NPT/costo, pesca requerida, sidetrack, pérdida de sección, abandono, incidente HSE). Las **barreras preventivas** incluyen: manejo de MW, protocolo de limpieza de pozo, revisión de diseño de BHA, monitoreo en tiempo real de T&D, procedimientos de wiper trip, requisitos de circulación pre-maniobra. Las **barreras de mitigación** incluyen: procedimiento de respuesta, jarring, spotting fluid, determinación de punto libre, back-off, herramientas de pesca en stand-by, plan contingente de sidetrack.

---

## Umbrales cuantitativos y KPIs de alerta temprana

### Límites operacionales seguros por estándar

| Parámetro | Límite | Estándar/Fuente |
|---|---|---|
| Sobrebalance máximo (pega diferencial) | **≤200 psi** guía general | Industry standard; Drillers Stuck Pipe Handbook |
| Margen seguro MW vs. LOT/FG | **≥0.5 ppg** debajo de LOT | BSEE 30 CFR §250.414/427 |
| ECD acercándose a FG | Alerta a **≤0.3 ppg** de FG | API RP 13D Sección 8 |
| Espesor de revoque (riesgo alto) | **>2 mm (1/16")** | Courteille & Zurdo, 1985, SPE |
| Filtrado API | **≤6 mL/30min** | API RP 13B-1 Sección 6 |
| Coeficiente fricción WBM vs OBM | **0.20–0.35 (WBM)** vs **0.04–0.10 (OBM)** | Adams 1977; datos de industria |
| Tiempo estático máximo (zona permeable) | **≤5 min** por conexión; **alarma >10 min** | IADC Drilling Manual |
| DLS para prevención key seat | **<3°/100 ft** seguro; **<5°/100 ft** máximo | AAPG Wiki; NTNU |
| Velocidad anular mínima (alto ángulo) | **≥150 ft/min**; óptimo ≥200 ft/min | Merlin ERD; múltiples refs SPE |
| Velocidad anular mínima (vertical) | **≥100 ft/min** | Estándar de industria |
| CCI (Carrying Capacity Index) | **≥1.0** | AMOCO/BP; SPE APOGCE 2019 |
| Cutting Transport Ratio | **>50%** = limpieza adecuada | MDPI Applied Sciences 2023 |
| RPM para limpieza en horizontal | **120–180 RPM** | Drillopedia; estándar de industria |
| Yield stress para prevención de sag | **>12 lbf/100ft²** | Nguyen et al. 2011, 2014 |
| Ángulo crítico para lechos de recortes | **>30°** inclinación | Estándar de industria |
| Ángulo crítico para barite sag | **40–60°** (máximo riesgo) | Zamora & Jefferson, OGJ |
| Variación MW tolerable por sag | **<0.5 ppg** en retornos | AADE-14-FTCE-27 |

### Sistema de alertas tempranas

| KPI | Nivel de advertencia (amarillo) | Nivel crítico (rojo) |
|---|---|---|
| **Incremento de torque** vs modelo T&D | >10–15% sobre baseline | **>20%** incremento súbito |
| **Incremento de drag** (overpull) | >10–15 klb sobre predicción | **>25 klb** overpull |
| **SPP trending** sin cambio operacional | >50–100 psi incremento gradual | **>200 psi** spike o fluctuaciones erráticas |
| **MW in vs MW out** | Diferencia >0.3 ppg | **>0.5 ppg** = alarma sag/pack-off |
| **Fill on bottom** después de maniobra | >5 ft | **>15 ft** = inestabilidad/limpieza |
| **Tiempo estático** en zona de riesgo | >5 min | **>10 min** = riesgo alto diferencial |

---

## Gastos mínimos de flujo por tamaño de pozo y ángulo

| Tamaño de pozo | Ángulo <30° | Ángulo 30–60° | Ángulo >60° |
|---|---|---|---|
| 6⅛" – 6½" | 250–350 gpm | 350–450 gpm | 400–500 gpm |
| 8½" | 350–500 gpm | 500–700 gpm | 600–800 gpm |
| 12¼" | 500–700 gpm | 700–900 gpm | 800–1000 gpm |
| 17½" | 700–900 gpm | 800–1000 gpm | Limitado por ECD |

---

## Procedimiento de respuesta inmediata y escalamiento

La tasa de éxito en liberación de pegas disminuye drásticamente con el tiempo: **50% de los eventos se resuelven dentro de 4 horas; menos del 10% después de 4 horas; 40% no se pueden liberar** (Alshaikh et al., 2018). El protocolo de escalamiento debe ejecutarse sin demora:

```
T=0 min       PRIMER CONTACTO: Registrar hora, profundidad, MW, operación.
               NO aplicar fuerza excesiva. Intentar circular a máximo gasto 
               permitido. Aplicar torque ≤80% del make-up torque.
               Trabajar la sarta: overpull/slack-off cíclico con torque.
               → ¿Libre? → Continuar operaciones; investigar causa raíz.

T=15min–2hrs  JARRING: Aplicar torque + jar en dirección apropiada.
               Diferencial → jar ABAJO. Mecánica → jar ARRIBA.
               Ciclos de 10 min; ±20 impactos a máxima carga.
               Preparar spotting fluid EN PARALELO.
               → ¿Libre? → Acondicionar pozo; continuar.

T=2–6hrs      SPOTTING FLUID: Colocar píldora según mecanismo.
               Diferencial (WBM): píldora base aceite (diesel/mineral oil).
               Diferencial (OBM): píldora de base oil + surfactante.
               Mecánica: sweeps de baja viscosidad; reducir ECD.
               Volumen: 100% exceso sobre volumen anular del BHA.
               Calcular punto libre (método stretch).
               → ¿Libre? → Circular píldora; reanudar.

T=6–12hrs     REDUCIR HIDROSTÁTICA (si diferencial): Reducir MW 
               (mantener >PP). Correr FPIT en wireline.
               → ¿Libre? → Restaurar MW; reanudar.

T=12–24hrs    BACK-OFF: Cortar arriba del punto pegado.
               Planificar washover o pesca.

T=24+hrs      SIDETRACK: Cementar; desviar el pozo.
```

### Tipos de spotting fluid por mecanismo

La selección del fluido de liberación depende del mecanismo diagnosticado. Para **pega diferencial con WBM**, se usa píldora base aceite pesada a MW o +0.5–1.0 ppg, con tiempo de remojo de **8–12 horas máximo**. Para **OBM**, píldoras de base oil con surfactantes o ácido si la formación es CaCO₃. Para **pack-off mecánico**, sweeps de baja viscosidad para reducir ECD. Para **cemento fraguado**, ácido HCl 15%.

---

## Base de datos completa de parámetros de entrada

El sistema automatizado requiere **más de 70 parámetros** organizados en 8 categorías. A continuación, los parámetros esenciales con sus atributos para implementación.

### Parámetros de superficie (adquisición continua a 1 Hz)

| Parámetro | Unidad API | Criticidad | Fuente |
|---|---|---|---|
| Weight on Bit (WOB) | klb | Esencial | Sensor hookload cell |
| RPM superficial | rpm | Esencial | Encoder rotario |
| Torque superficial | ft-lb | Esencial | Torque sub / top drive |
| Rate of Penetration (ROP) | ft/hr | Esencial | Encoder draw-works |
| Standpipe Pressure (SPP) | psi | Esencial | Transductor de presión |
| Flow Rate In/Out | gpm | Esencial | Medidor de flujo |
| Hook Load | klb | Esencial | Hookload cell |
| Block Position | ft | Esencial | Encoder draw-works |
| Bit Depth / Hole Depth | ft | Esencial | Calculado/sensor |

### Parámetros downhole MWD/LWD (1–10 segundos)

| Parámetro | Unidad | Criticidad | Fuente |
|---|---|---|---|
| Inclinación / Azimuth | grados | Esencial | MWD |
| ECD (Annular Pressure) | ppg | Esencial | PWD sensor |
| Downhole WOB / Torque | klb / ft-lb | Importante | MWD |
| Vibración (axial/lateral/torsional) | g-rms | Importante | MWD |
| Temperatura downhole | °F | Importante | MWD |
| Gamma Ray | API units | Importante | LWD |

### Propiedades de lodo (cada 4 horas / laboratorio)

| Parámetro | Unidad | Criticidad | Fuente |
|---|---|---|---|
| MW In / MW Out | ppg | Esencial | Densitómetro (continuo) |
| Viscosidad Plástica (PV) | cP | Esencial | Fann viscometer |
| Yield Point (YP) | lb/100ft² | Esencial | Fann viscometer |
| Gel Strength (10s/10min/30min) | lb/100ft² | Esencial | Fann viscometer |
| Lecturas 6-RPM / 3-RPM | dial reading | Esencial | Fann 35 |
| Filtrado API | mL/30min | Esencial | Prensa API |
| Filtrado HTHP | mL/30min | Esencial | Prensa HTHP |
| Espesor de revoque | 32avos pulg | Importante | Medición lab |
| Sólidos totales (LGS/HGS) | % vol | Esencial | Retorta |
| Contenido de arena | % vol | Importante | Kit de arena |
| MBT | lb/bbl | Importante | Lab |
| pH | — | Importante | pH meter |
| ES (OBM) | volts | Esencial (OBM) | ES meter |
| O/W Ratio (OBM) | % | Esencial (OBM) | Retorta |
| Coeficiente de fricción | adimensional | Deseable | Lubricity tester |

### Parámetros calculados de hidráulica

| Parámetro | Unidad | Criticidad | Fuente |
|---|---|---|---|
| ECD calculado | ppg | Esencial | Modelo hidráulico |
| Velocidad anular (por sección) | ft/min | Esencial | Calculado: Q ÷ área anular |
| Pérdidas de presión (string/anular/bit) | psi | Importante | Modelo hidráulico |
| Surge/Swab | psi / ppg equiv | Esencial | Modelo |
| CCI (Carrying Capacity Index) | adimensional | Importante | CCI = (MW×K×AV)/400,000 |

### Parámetros de geometría, formación y contexto

Incluyen: tamaño de pozo nominal/real (caliper), casing ID/OD/profundidad de zapata, descripción de BHA, surveys direccionales (MD/Inc/Az), DLS calculado, litología actual, gradiente de presión de poro y de fractura (ppg), LOT/FIT, tiempo de conexión, tiempo de survey (estático), tiempo desde última circulación, **tiempo acumulado de sarta estática** (parámetro crítico para pega diferencial), operación actual (código WITS), bit on/off bottom, y **bandera de zona de riesgo** (permeable/reactiva) pre-programada del plan de pozo.

---

## Formato de reporte ejecutivo para dirección corporativa

### Estructura del reporte post-incidente

El reporte se estructura en **6 secciones** diseñadas para comunicar el impacto, la causa y las acciones a nivel gerencial:

1. **Resumen ejecutivo** (1 página máx): Pozo, fecha, mecanismo de pega, NPT total (horas), costo estimado ($), resultado (liberado/pescado/sidetrack/abandono), causa raíz en 1–2 oraciones, recomendación principal
2. **Línea de tiempo del incidente**: Condiciones pre-incidente (últimas 24 hrs), secuencia de eventos con timestamps, señales de alerta observadas o no detectadas, acciones tomadas
3. **Análisis de causa raíz**: Diagrama fishbone (visual), cadena 5-Whys, causa raíz primaria, factores contribuyentes, clasificación según taxonomía RCA
4. **Evaluación de impacto**: Horas NPT y costo, equipo perdido, impacto ambiental, exposición HSE, impacto en cronograma
5. **Acciones correctivas**: Tabla con Acción/Responsable/Prioridad/Fecha/Estatus
6. **Lecciones aprendidas**: Qué funcionó, qué mejorar, aplicabilidad a otros pozos

### KPIs para dashboard corporativo

| KPI | Definición | Meta/Benchmark |
|---|---|---|
| NPT por pegas (hrs) | Horas no productivas por pegas de sarta | Tendencia decreciente |
| NPT % | NPT pegas / horas totales × 100 | **<3%** del NPT total |
| Frecuencia de pegas | Eventos por 1000m perforados o por pozo | Benchmark vs. promedio de cuenca |
| Tiempo medio de liberación | Horas promedio desde pega hasta libre | Meta: tendencia decreciente |
| Tasa de éxito de liberación | % eventos liberados sin sidetrack | **>70%** objetivo |
| Distribución de causa raíz | Pareto de causas por tipo de mecanismo | Identificar mecanismo dominante |
| Costo por evento | Costo total promedio por incidente de pega | Tracking de tendencia |
| Cumplimiento de indicadores líderes | % tiempo con propiedades de lodo dentro de spec, tasa de completación de wiper trips, tasa de completación de risk assessments pre-spud | **>95%** cumplimiento |

---

## Conclusión: arquitectura para implementación automatizada

Este framework demuestra que la clasificación automática de pegas es técnicamente viable con alta precisión. **El discriminador primario — estado de circulación — divide el universo de pegas en dos ramas fundamentales con una sola pregunta binaria.** Combinando este árbol de decisión con la matriz de puntuación probabilística y los umbrales cuantitativos documentados, un sistema automatizado puede proporcionar diagnóstico en tiempo real con niveles de confianza cuantificados.

La evidencia de ML/AI (IPTC-24141-MS, 2024) confirma que la combinación de **modelos físicos de T&D/hidráulica + redes Bayesianas** es el enfoque más robusto: proporciona tanto predicción (promedio 38 minutos de alerta pre-evento) como identificación interpretable de causa raíz, superando los enfoques "black-box" de deep learning. El sistema requiere como mínimo los **12 parámetros superficiales en tiempo real** más **ECD downhole** y **propiedades de lodo cada 4 horas** para operar con precisión diagnóstica >90%.

La novedad más relevante para la automatización no está en la clasificación per se, sino en la **integración del RCA estructurado con el diagnóstico**: al vincular cada tipo de pega con sus cadenas causales 5-Whys pre-programadas y las categorías del fishbone, el sistema puede generar automáticamente un borrador de reporte RCA que solo requiere validación del ingeniero, reduciendo el ciclo de análisis post-incidente de días a horas. El framework de estándares (API RP 13B/13D, NORSOK D-010, ISO 16530) proporciona la base normativa para que estos reportes tengan validez ante auditorías corporativas y regulatorias.