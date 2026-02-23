# PetroExpert — Informe Gerencial de Normas, Estándares y Fórmulas

**Sistema Experto de Ingeniería Petrolera con Inteligencia Artificial**
**Fecha:** Febrero 2026 | **Versión:** 1.0 | **Estado:** En desarrollo y pruebas

---

## Resumen Ejecutivo

PetroExpert implementa **16 motores de cálculo** en Python puro, fundamentados en **más de 120 fórmulas y correlaciones** provenientes de normas internacionales de la industria petrolera (API, IWCF, IADC, NORSOK, ICoTA) y publicaciones técnicas de referencia (SPE, Schlumberger, Bourgoyne et al.). El sistema cubre el ciclo completo de perforación, completación y producción a través de **14 módulos de ingeniería**, **71+ gráficas de visualización** y análisis ejecutivo impulsado por inteligencia artificial multimodelo.

### Inventario General

| Categoría | Cantidad |
|---|---|
| Motores de cálculo (Python) | 16 |
| Módulos de ingeniería | 14 |
| Normas/estándares referenciados | 25+ (API, IWCF, IADC, NORSOK, ICoTA) |
| Publicaciones SPE/técnicas citadas | 30+ autores/papers |
| Fórmulas y correlaciones implementadas | 120+ |
| Modelos reológicos | 3 (Bingham, Power Law, Herschel-Bulkley) |
| Modelos de saturación de agua | 3 (Archie, Simandoux, Indonesia) |
| Gráficas de visualización | 71+ (Recharts + SVG custom) |
| Idiomas soportados | 2 (EN/ES — 1,071 claves i18n) |
| Agentes de IA especializados | 13 |

---

## 1. Torque y Arrastre (Torque & Drag)

### 1.1 Normas y Referencias

| Referencia | Descripción |
|---|---|
| **SPE 11380 — Johancsik et al. (1984)** | Modelo Soft-String para cálculo de torque y arrastre |
| **Lubinski, A.** | Análisis de pandeo crítico sinusoidal |
| **Mitchell, R. (1999)** | Corrección de rigidez (stiff-string) y arrastre post-pandeo |
| **Bourgoyne et al.** | Applied Drilling Engineering — fundamento general |
| **Burkhardt** | Constante de adherencia para análisis surge/swab |

### 1.2 Fórmulas Implementadas

#### Método Minimum Curvature (Trayectoria del Pozo)
```
cos(DL) = cos(Δinc) − sin(inc₁) × sin(inc₂) × (1 − cos(Δazi))

RF = (2/DL) × tan(DL/2)     [Factor de ratio, cuando DL ≥ 1×10⁻⁷]

ΔTVD = (ΔMD/2) × (cos(inc₁) + cos(inc₂)) × RF
ΔNorth = (ΔMD/2) × (sin(inc₁)×cos(azi₁) + sin(inc₂)×cos(azi₂)) × RF
ΔEast = (ΔMD/2) × (sin(inc₁)×sin(azi₁) + sin(inc₂)×sin(azi₂)) × RF

DLS = degrees(DL) / ΔMD × 100     [°/100ft]
```

#### Modelo Soft-String de Johancsik (SPE 11380)
```
Factor de Flotabilidad:
    BF = 1.0 − (MW / 65.5)     [65.5 ppg = gravedad específica del acero]

Peso Flotado por Segmento:
    W = (peso_por_pie) × BF × ΔMD

Fuerza Normal (contacto lateral pipe-wellbore):
    Fn = √[(Fa × Δinc + W × sin(inc_avg))² + (Fa × sin(inc_avg) × Δazi)²]

Fuerza de Arrastre:
    F_drag = μ × Fn     [μ = factor de fricción]

Actualización de Fuerza Axial (por intervalo, de fondo a superficie):
    Fa_new = Fa_old + W × cos(inc_avg) + (dirección × F_drag)

Torque (para operaciones rotativas):
    T_increment = μ × Fn × r_contacto     [r = OD/2, en pies]
    T_acumulativo = Σ T_increment
```

#### Modelo Híbrido Stiff-String (Mitchell)
```
Corrección de Rigidez por Flexión:
    I = (π/64) × (OD⁴ − ID⁴)     [Momento de inercia, in⁴]
    EI = E × I     [E = 30×10⁶ psi — Módulo de Young del acero]
    Curvatura = DL / (ΔMD × 12)     [rad/in]
    F_EI = EI × curvatura / (ΔMD × 12)

    Fn_total = √(Fn_soft² + F_EI²)

Condición de aplicación: OD ≥ 6" ó DLS local > 3°/100ft
```

#### Análisis de Pandeo (Lubinski / Mitchell)
```
Pandeo Sinusoidal (Lubinski):
    Fc_sin = 2 × √(E × I × w × sin(inc) / r)

Pandeo Helicoidal (Mitchell):
    Fc_hel = 2√2 × √(E × I × w × sin(inc) / r)

    Donde: w = peso flotado por pulgada, r = holgura radial

Clasificación:
    Si compresión > Fc_hel → HELICOIDAL
    Si compresión > Fc_sin → SINUSOIDAL
    De lo contrario → OK (sin pandeo)
```

#### Retro-Cálculo de Factor de Fricción
```
Método de Bisección:
    Rango: μ_low = 0.05, μ_high = 0.60
    Iteraciones máximas: 50
    Tolerancia: 0.5 klb
    Converge en μ donde |hookload_calculado − hookload_medido| < tolerancia
```

---

## 2. Hidráulica / ECD (Hydraulics)

### 2.1 Normas y Referencias

| Referencia | Descripción |
|---|---|
| **API RP 13D** | Reología e Hidráulica de Fluidos de Perforación |
| **Bourgoyne et al.** | Applied Drilling Engineering — fundamento |
| **Dodge & Metzner** | Reynolds generalizado para fluidos no-Newtonianos |
| **Metzner & Reed** | Viscosidad generalizada y tasa de corte en pared |
| **Hanks** | Reynolds crítico para fluidos Bingham |
| **Blasius** | Factor de fricción turbulento |

### 2.2 Modelos Reológicos

#### Modelo Bingham Plastic
```
τ = YP + PV × γ

Velocidad Anular: Va = 24.5 × Q / (Dh² − Dp²)     [ft/min]
Reynolds (Bingham): Re = 757 × MW × V × Deff / PV
Hedstrom: He = 37,100 × MW × YP × Deff² / PV²
Reynolds Crítico (Hanks): Re_crit = 2100 + 7.3 × He⁰·⁵⁸

Pérdida Laminar (anular):
    ΔP = (PV × V × L) / (1000 × Deff²) + (YP × L) / (200 × Deff)

Pérdida Laminar (pipe):
    ΔP = (PV × V × L) / (1500 × Deff²) + (YP × L) / (225 × Deff)

Turbulento (Blasius): f = 0.0791 / Re⁰·²⁵
    ΔP_anular = (f × MW × V_fps² × L) / (21.1 × Deff)
    ΔP_pipe = (f × MW × V_fps² × L) / (25.8 × Deff)
```

#### Modelo Power Law
```
τ = K × γⁿ     [n < 1: pseudoplástico, n = 1: Newtoniano, n > 1: dilatante]

Reynolds Generalizado (Dodge-Metzner):
    Anular: na = (2 + 1/n) / 3
    Re_g = (109,000 × MW × V^(2−n) × Deff^n) / (K × na^n)

    Pipe: np = (3 + 1/n) / 4
    Re_g = (89,100 × MW × V^(2−n) × Deff^n) / (K × np^n)

Re_crit (Dodge-Metzner) = 3470 − 1370 × n
```

#### Modelo Herschel-Bulkley
```
τ = τ₀ + K × γⁿ

Conversión de Viscosímetro FANN:
    γ = 1.703 × RPM     [tasa de corte, 1/s]
    τ = 1.0678 × Lectura     [esfuerzo de corte, lbf/100ft²]

Ajuste por Mínimos Cuadrados:
    ln(τ − τ₀) = ln(K) + n × ln(γ)
    Estimación inicial: τ₀ = 2×τ₃ − τ₆

Tasa de Corte en Pared (Metzner-Reed):
    γ_w_anular = 144 × V / Deff × (2n+1)/(3n)
    γ_w_pipe = 96 × V / Deff × (3n+1)/(4n)
```

### 2.3 Hidráulica de Barrena
```
Área Total de Flujo (TFA):
    TFA = Σ [π/4 × (d_nozzle)²]     [d = tamaño_32avos / 32]

Caída de presión en barrena:
    ΔP_bit = 8.311×10⁻⁵ × MW × Q² / (Cd² × TFA²)     [Cd = 0.95]

Velocidad de toberas: Vn = Q / (3.117 × TFA)     [fps]
Potencia hidráulica: HHP = ΔP_bit × Q / 1714
HSI (Intensidad Hidráulica): HSI = HHP / Área_barrena     [hp/in²]
Fuerza de impacto: Fi = 0.01823 × Cd × Q × √(MW × ΔP_bit)     [lbf]
```

### 2.4 ECD Dinámico
```
ECD = MW + cuttings_loading + temp_effect + APL / (0.052 × TVD)

Corrección de densidad por P/T:
    ρ(P,T) = ρ₀ × [1 + Cp×(P−P₀)] / [1 + Ct×(T−T₀)]

    WBM: Cp = 3.0×10⁻⁶ /psi,  Ct = 2.0×10⁻⁴ /°F
    OBM: Cp = 5.0×10⁻⁶ /psi,  Ct = 3.5×10⁻⁴ /°F

Corrección de viscosidad por temperatura (Arrhenius):
    PV(T) = PV_ref × exp(−α × (T − T_ref))     [α = 0.015 /°F]
```

### 2.5 Análisis Surge/Swab
```
Constante de Adherencia (Burkhardt):
    kc = 0.30 (d_ratio < 0.3) | 0.45 (default) | 0.60 (d_ratio > 0.7)

Velocidad Efectiva (tubería abierta):
    V_eff = |V_pipe| × (desplazamiento / área_anular) × kc

Caudal Equivalente: Q_equiv = V_eff × (Dh² − Dp²) / 24.5

EMW_surge = presión_surge / (0.052 × TVD)
ECD_surge = MW + EMW_surge     [entrando — presión aumenta]
ECD_swab = MW − EMW_swab     [saliendo — presión disminuye]
```

---

## 3. Control de Pozos (Well Control)

### 3.1 Normas y Referencias

| Referencia | Descripción |
|---|---|
| **IWCF/IADC** | Estándares Internacionales de Control de Pozos |
| **"Well Control for the Drilling Team"** | Manual IWCF |
| **Bourgoyne et al.** | Applied Drilling Engineering |
| **Dranchuk & Abou-Kassem (DAK)** | Correlación de factor Z (11 coeficientes) |
| **Standing** | Correlaciones de propiedades pseudocríticas de gas |

### 3.2 Fórmulas del Kill Sheet
```
Presión Hidrostática:
    Ph = MW × 0.052 × TVD     [0.052 = constante hidrostática psi/ft/ppg]

Presión de Formación:
    FP = Ph + SIDPP     [SIDPP = shut-in drill pipe pressure]

Peso de Lodo de Matado (KMW):
    KMW = FP / (0.052 × TVD)

Presión Inicial de Circulación (ICP):
    ICP = SIDPP + SCR     [SCR = slow circulating rate pressure]

Presión Final de Circulación (FCP):
    FCP = SCR × (KMW / MW_original)

Máxima Presión Anular Permitida (MAASP):
    MAASP = (LOT_EMW − MW) × 0.052 × TVD_shoe
```

### 3.3 Análisis de Influjo (Kick)
```
Altura del influjo: H_influx = Pit_Gain / Capacidad_Anular
Gradiente del influjo: Grad = MW × 0.052 − (SICP − SIDPP) / H_influx

Clasificación del tipo de influjo:
    Gas (seco):           gradiente < 0.10 psi/ft
    Gas (húmedo/condensado): 0.10 − 0.25 psi/ft
    Petróleo:             0.25 − 0.35 psi/ft
    Agua salada:          0.35 − 0.45 psi/ft
```

### 3.4 Factor Z — Correlación Dranchuk-Abou-Kassem (DAK)
```
Propiedades Pseudocríticas (Standing):
    T_pc = 168.0 + 325.0 × SG − 12.5 × SG²     [°R]
    P_pc = 677.0 + 15.0 × SG − 37.5 × SG²     [psia]

Propiedades Pseudorreducidas:
    T_pr = (T + 460) / T_pc
    P_pr = P / P_pc

Resolución: Newton-Raphson con 11 coeficientes DAK
    Máx. iteraciones: 15 | Tolerancia: 1×10⁻⁶

Ley de Gas Real (expansión volumétrica):
    V₂ = V₁ × (P₁/P₂) × (Z₂/Z₁) × (T₂_R / T₁_R)
```

### 3.5 Método Volumétrico y Bullhead
```
Volumétrico:
    Presión de trabajo = SICP + margen_seguridad
    Ciclos de presión/volumen con incrementos controlados

Bullhead:
    P_pump = FP − Hidrostática(KMW) + Pérdida_Fricción
    Fricción estimada: 0.05 psi por cada 1000 ft MD

Fórmula de Barita:
    lbs = 1470 × Vol_sistema(bbl) × (MW_target − MW) / (ρ_barita − MW_target)

Tolerancia al Kick:
    KT = MAASP / (gradiente_lodo − gradiente_gas)
```

---

## 4. Tubería Pegada (Stuck Pipe)

### 4.1 Normas y Referencias

| Referencia | Descripción |
|---|---|
| **IADC** | Guías de Prevención de Tubería Pegada |
| **SPE** | Publicaciones técnicas sobre mecanismos de pegadura |

### 4.2 Punto Libre (Stretch Method)
```
Profundidad de Punto Libre:
    FP (ft) = (E × A × stretch_in) / (Fuerza_halado_lbs × 12)

    E = 30×10⁶ psi (Módulo de Young del acero)
    A = π/4 × (OD² − ID²)     [área de sección transversal, in²]

Límite de halado seguro: 80% del yield del grado de tubería

Grados de tubería y resistencia:
    E75: 75,000 psi  |  X95: 95,000 psi  |  G105: 105,000 psi
    S135: 135,000 psi  |  V150: 150,000 psi  |  UD165: 165,000 psi
```

### 4.3 Fuerza de Pegadura Diferencial
```
Presión Diferencial: ΔP = Sobrebalance(ppg) × 0.052 × TVD

Ancho de Contacto (modelo Hertz):
    W = 2 × √(OD × espesor_revoque)
    Límite: máximo 30% de la circunferencia

Área de Contacto: A = W × longitud_contacto × 12
Fuerza de Pegadura: F_stick = ΔP × A
Fuerza para liberar: F_free = F_stick × μ_fricción

Niveles de riesgo:
    Crítico: > 500,000 lbs | Alto: > 200,000 | Moderado: > 50,000 | Bajo: > 10,000
```

### 4.4 Matriz de Riesgo
```
Score = Probabilidad (1–5) × Severidad (2–5)

    CRÍTICO: ≥ 15  |  ALTO: ≥ 10  |  MEDIO: ≥ 5  |  BAJO: < 5

Mecanismos evaluados (9):
    Pegadura diferencial, Mecánica, Limpieza/Pack-Off,
    Inestabilidad de pozo, Key Seating, Hueco bajo calibre,
    Flujo de formación, Puente/Pack-Off, Cemento/Chatarra
```

---

## 5. Limpieza de Hoyo (Wellbore Cleanup)

### 5.1 Normas y Referencias

| Referencia | Descripción |
|---|---|
| **API RP 13D** | Velocidades anulares mínimas según inclinación |
| **Moore** | Correlación de velocidad de deslizamiento de recortes |
| **Larsen et al. (SPE 36383, 1997)** | Slip velocity en pozos inclinados y horizontales |
| **Luo et al. (1992)** | Índice de Limpieza de Hoyo (HCI) |
| **Bourgoyne et al.** | Applied Drilling Engineering, Cap. 4 |

### 5.2 Velocidades Mínimas (API RP 13D)
```
Vertical (< 30°):     120 ft/min
Transición (30–60°):   130 ft/min
Alto ángulo (> 60°):   150 ft/min
```

### 5.3 Velocidad de Deslizamiento
```
Moore — Régimen de Stokes (Re < 1):
    Vs = 113.4 × d² × Δρ / μa

Moore — Régimen Intermedio/Turbulento (Re > 1):
    Vs = 175.0 × d × √(Δρ / MW)

Larsen — Corrección por Inclinación:
    Factor (10–60°): f_inc = 1.0 + 0.3 × sin(2θ)
    Factor (60–90°): f_inc = 1.0 + 0.2 × (1 − cos(θ))
    Vs_inclinado = Vs_vertical × |cos(θ)| × f_inc

Corrección por RPM (alto ángulo ≥ 75°):
    f_rpm = 1.0 − min(RPM/150, 0.5)
    Vs_efectivo = Vs_inclinado × f_rpm
```

### 5.4 Índice de Limpieza de Hoyo — HCI (Luo et al., 1992)
```
HCI = (Va / Va_min) × f_rpm × f_reología × f_densidad

Factor RPM (inc > 30°): f_rpm = 1.0 + min(RPM/600, 0.25)
Factor Reología (YP/PV):
    YP/PV ≥ 1.0: f_rheo = 1.0 + min((YP/PV − 1) × 0.1, 0.15)
    YP/PV < 0.5: f_rheo = 0.85
Factor Densidad: f_density = 1.0 + min((MW/CD − 0.4) × 0.2, 0.1)

Calidad:  Buena: HCI ≥ 1.0 | Marginal: 0.7–1.0 | Pobre: < 0.7
```

### 5.5 Transporte de Recortes
```
Ratio de Transporte (CTR): CTR = (Va − Vs) / Va     [Adecuado: > 0.55]
Velocidad de Transporte: Vt = Va − Vs

Concentración de Recortes (%):
    Rate_gen = Dh² × (ROP/60) / 144     [ft³/min]
    CC = (Rate_gen / (Flow_ann + Rate_gen)) × 100

Contribución ECD: ECD_cuttings = (CC%/100) × (ρ_cutting − MW)
```

---

## 6. Fuerzas de Packer

### 6.1 Normas y Referencias

| Referencia | Descripción |
|---|---|
| **Lubinski, A. (1962)** | Pandeo helicoidal de tubing sellado en packers |
| **Mitchell & Samuel (2009)** | Aproximación de pared delgada |
| **Adams & MacEachran (1994)** | Impacto de expansión térmica en diseño |
| **API TR 5C3** | Pandeo de casing y tubing en pozos |
| **Halliburton Red Book** | Manual de referencia de completación |
| **Baker Hughes Completion Engineering Guide** | Guía de ingeniería de completación |

### 6.2 Fuerzas Principales
```
Áreas de Sección:
    Ao = π × (OD/2)²  |  Ai = π × (ID/2)²  |  As = Ao − Ai

Fuerza Pistón (efecto PBR):
    F_piston = P_below × (A_seal − Ai) − P_above × (A_seal − Ao)

Efecto Ballooning / Reverse Ballooning:
    F_balloon = −2ν × (ΔPi × Ai − ΔPo × Ao)
    [ν = 0.30 — Relación de Poisson del acero]

Fuerza por Temperatura:
    F_temp = −E × As × α × ΔT
    [E = 30×10⁶ psi, α = 6.9×10⁻⁶ 1/°F]

Movimiento del Tubing (Ley de Hooke):
    ΔL = F × L / (E × As)
```

### 6.3 Pandeo y Estabilidad
```
Fuerza Ficticia de Pandeo (Lubinski):
    Ff = Pi × Ai − Po × Ao

Carga Crítica Helicoidal:
    F_cr = 2 × √(E × I × w × sin(θ) / r)
    I = π × (OD⁴ − ID⁴) / 64

Acortamiento por Pandeo Sinusoidal:
    dL = F² × r² / (8 × E × I × w × sin(inc))

Esfuerzo Máximo por Flexión:
    σ = r × (OD/2) × F / (4 × I)
```

### 6.4 Presión Anular Atrapada (APB)
```
APB = (αf × ΔT × V) / (Cf × V + C_casing + C_tubing)

Compliance de casing: Cc = π × ID² × L / (2E × wall_thickness)
Compliance de tubing: Ct = π × OD² × L / (2E × wall_thickness)

Propiedades de fluidos:
    WBM: αf = 2.0×10⁻⁴ /°F, Cf = 3.0×10⁻⁶ /psi
    OBM: αf = 3.5×10⁻⁴ /°F, Cf = 5.0×10⁻⁶ /psi
    Brine: αf = 2.5×10⁻⁴ /°F, Cf = 3.2×10⁻⁶ /psi

Mitigación con espuma (nitrógeno): C_foam ≈ 1.0×10⁻⁴ /psi (~100× mayor que líquido)
```

---

## 7. Hidráulica de Workover (Coiled Tubing)

### 7.1 Normas y Referencias

| Referencia | Descripción |
|---|---|
| **ICoTA** | Manual de Coiled Tubing |
| **API RP 5C7** | Metodología de fatiga de ciclo bajo para CT |
| **Paslay & Dawson (1984)** | Pandeo helicoidal |
| **Bourgoyne et al.** | Applied Drilling Engineering |
| **Miner (1945)** | Regla de daño acumulado por fatiga |

### 7.2 Fórmulas Principales
```
Pérdida de Presión CT (Bingham Plastic):
    ΔP_pipe = (PV × v × L) / (1500 × D²) + (YP × L) / (225 × D)

Fuerza de Snubbing:
    F_snub = P_wellhead × A_pipe − W_buoyed
    Punto ligero/pesado: L_point = F_pressure / W_buoyed_per_ft

Pandeo CT (Paslay-Dawson):
    F_hb = √(8 × E × I × w_n / r_clearance)
    w_n = W_buoyed × sin(inc) / 12     [lb/in componente normal]
```

### 7.3 Elongación del CT — Cuatro Componentes
```
1. Por peso (carga triangular):   dL_w = W × L / (2 × E × As)
2. Por temperatura:               dL_T = α × ΔT × L
3. Por ballooning (Poisson):      dL_B = −2ν × (Pi×Ai − Po×Ao) × L / (E × As)
4. Por Bourdon (fuerza de punta): dL_Bd = ΔP × Ai × L / (E × As)
```

### 7.4 Fatiga del CT (API RP 5C7)
```
Deformación por flexión: ε_bend = OD / (2 × R_reel)
Deformación por presión: ε_pressure = P × ID / (2 × wall × E)

Curva S-N: N_f = C / ε_total^m     [m = 2.5]
    CT-80: C = 0.038 | CT-90: C = 0.028 | CT-110: C = 0.020

Regla de Miner (daño acumulado):
    Daño = Σ(n_i / N_f_i)     [Falla cuando D ≥ 1.0]
```

---

## 8. Control de Arena (Sand Control)

### 8.1 Normas y Referencias

| Referencia | Descripción |
|---|---|
| **Penberthy & Shaughnessy** | Sand Control (SPE Series) |
| **Saucier (1974)** | Criterio de dimensionamiento de grava |
| **API RP 19C** | Procedimientos de prueba de mallas de control de arena |
| **Mohr-Coulomb** | Criterio de falla de formación |

### 8.2 Fórmulas Principales
```
Análisis Granulométrico:
    Coeficiente de Uniformidad: Cu = D60 / D10
    Clasificación: Cu < 2 (muy bien seleccionado) → Cu > 10 (muy pobremente seleccionado)

Criterio de Saucier:
    D_grava = 5–6 × D50     [formación bien seleccionada]
    D_grava = 5–6 × (D50+D10)/2     [formación pobremente seleccionada, Cu > 5]

Selección de Malla:
    Wire wrap: slot ≈ 2 × D10
    Premium mesh: slot ≈ D10

Drawdown Crítico (Mohr-Coulomb):
    UCS_wet = UCS × (1 − 0.3 × Sw)
    C = UCS_wet × (1 − sin φ) / (2 × cos φ)
    σ_θ = 0.5×(σH + σh) − 0.5×(σH − σh)×cos(2θ)     [Kirsch]
    ΔP_crit = (UCS_wet + σ_θ × (1 − sin φ)) / (1 + sin φ)

Riesgo de arenamiento:
    < 200 psi: Muy Alto | 200–500: Alto | 500–1000: Moderado | > 2000: Muy Bajo
```

---

## 9. Diseño de Completación

### 9.1 Normas y Referencias

| Referencia | Descripción |
|---|---|
| **API RP 19B** | Evaluación de cañones perforadores (corrección Berea) |
| **Karakas & Tariq (1991)** | Modelo semi-analítico de productividad |
| **Haimson & Fairhurst (1967)** | Presión de iniciación de fractura hidráulica |
| **Eaton (1969)** | Predicción de gradiente de fractura |
| **Vogel (1968)** | IPR de pozos con gas en solución |
| **Fetkovich (1973)** | Pruebas isocronales de pozos |
| **Joshi (1991)** | Tecnología de pozos horizontales |

### 9.2 Fórmulas Principales
```
Corrección de Penetración (API RP 19B):
    P_corr = P_berea × CF_stress × CF_temp × CF_fluid × CF_cement × CF_casing

Ratio de Productividad (Karakas-Tariq):
    PR = ln(re/rw) / [ln(re/rw) + S_total]
    re = 660 ft (espaciamiento de 40 acres)

Componentes de Skin:
    S_total = S_p + S_v + S_wb + S_d
    S_p (pseudo-skin): ln(r_eff / (r_w + l_p))
    S_v (convergencia vertical): 10^(a + b×log(r_pd)) × h_d
    S_wb (bloqueo de pozo): c1 × exp(c2 × r_p/r_w)
    S_d (daño): (k_h/k_damage − 1) × ln(r_damaged/r_w)

Iniciación de Fractura (Haimson & Fairhurst):
    P_breakdown = 3σ_min − σ_max + T₀ − α×P_pore
    P_closure = σ_min

Gradiente de Fractura (Eaton):
    FG = [ν/(1−ν)] × (σ_ob − Pp)/D + Pp/D + σ_tect/D
```

### 9.3 Base de Datos de Cañones
```
25+ modelos: WL (wireline), TCP (tubing-conveyed), CT (coiled-tubing)
Especificaciones: OD, casing máx., SPF, phasing, EHD, penetración Berea, P/T máx.
Ejemplo: TCP-7000-DP — EHD 0.85", 38" penetración Berea, 180° phasing
```

---

## 10. Eficiencia de Disparo (Shot Efficiency / Petrophysics)

### 10.1 Normas y Referencias

| Referencia | Descripción |
|---|---|
| **Archie (1942)** | Factor de formación y saturación de agua |
| **Simandoux (1963)** | Modelo arcilloso de saturación de agua |
| **Poupon & Leveaux (1971)** | Modelo Indonesia para alto contenido de arcilla |
| **Timur (1968)** | Permeabilidad desde registros de porosidad |
| **Coates & Dumanoir (1974)** | Estimación de permeabilidad |
| **Wyllie et al. (1956)** | Porosidad sónica — ecuación de tiempo promedio |
| **Raymer, Hunt & Gardner (1980)** | Porosidad sónica mejorada |
| **Larionov (1969)** | Corrección de Vshale para formaciones terciarias |
| **Karakas & Tariq (1991)** | Skin de perforación semi-analítico |

### 10.2 Modelos de Saturación de Agua
```
Archie (arena limpia, Vsh < 0.15):
    Sw = [(a × Rw) / (Rt × φᵐ)]^(1/n)
    Típico: a = 1.0, m = 2.0, n = 2.0

Simandoux (moderadamente arcilloso, 0.15 ≤ Vsh < 0.40):
    1/Rt = Sw^n × φᵐ / (a×Rw) + Vsh × Sw / Rsh
    Solución cuadrática: A×Sw² + B×Sw + C = 0

Indonesia / Poupon-Leveaux (altamente arcilloso, Vsh ≥ 0.40):
    1/√Rt = √(φᵐ/(a×Rw)) × Sw^(n/2) + Vsh^(1−Vsh/2)/√Rsh × Sw
    Resolución iterativa (Newton-Raphson)

Selección automática del modelo según contenido de arcilla (Vsh)
```

### 10.3 Porosidad y Permeabilidad
```
Porosidad Densidad-Neutrón (Crossplot):
    φ_D = (ρ_matrix − ρ_bulk) / (ρ_matrix − ρ_fluid)
    φ = √((φ_D² + φ_N²) / 2)     [RMS crossplot]

Porosidad Sónica:
    Wyllie: φ = (DT_log − DT_matrix) / (DT_fluid − DT_matrix)
    Raymer: φ = 0.625 × (DT_log − DT_matrix) / DT_log

Permeabilidad:
    Timur (1968): k = 8.58×10⁴ × φ⁴·⁴ / Sw_irr²     [mD]
    Coates (1974): k = [(100φ)² × (1−Sw_irr)/Sw_irr]² / 10,000     [mD]

Volumen de Arcilla:
    Lineal: Vsh = (GR − GR_clean) / (GR_shale − GR_clean)
    Larionov (Terciario): Vsh = 0.083 × (2^(3.7×IGR) − 1)
```

### 10.4 Identificación de Intervalos
```
Criterios de net pay: φ > φ_min, Sw < Sw_max, Vsh < Vsh_max

Tipificación de HC (separación densidad-neutrón):
    Índice de HC Movible: MHI = φ × (1 − Sw/Sxo)
    Volumen Bulk de Agua: BVW = φ × Sw
    Gas: DN > 0.04, φ_neutron < φ_density
    Petróleo: Sw < 0.60, MHI > 0.02
    Agua: Sw > 0.80

Score de ranking: w_φ×φ + w_sw×(1−Sw) + w_thick×thick + w_skin×1/(1+|skin|)
```

---

## 11. Vibraciones de BHA

### 11.1 Normas y Referencias

| Referencia | Descripción |
|---|---|
| **Paslay & Dawson (1984)** | Vibraciones laterales y whirl de sarta |
| **Jansen & van den Steen (1995)** | Amortiguación activa de stick-slip |
| **Teale (1965)** | Energía Mecánica Específica (MSE) |
| **Dupriest (2005)** | Optimización de perforación basada en MSE |
| **Dunayevsky (1993)** | Estabilidad de BHA en pozos direccionales |
| **Mitchell (2003)** | Análisis por Matriz de Transferencia (TMM) |
| **Miner (1945)** | Regla de daño acumulado por fatiga |

### 11.2 Vibración Axial (Bit Bounce)
```
Frecuencia natural: f_n = (1/2L) × √(E/ρ)
Velocidad del sonido en acero: c = √(E×g/ρ)
RPM crítico: RPM_crit = f_n × 60
Banda segura: operar 15% alejado de resonancias
```

### 11.3 Vibración Lateral (Whirl) — Paslay & Dawson
```
Euler-Bernoulli (pinned-pinned):
    ω_n = (π/L_in)² × √(E×I×g / w_lb_in)

RPM Crítico:
    N_crit = (30π / L_in²) × √(E×I×g / w_lb_in)

Severidad de whirl: clearance × (1 + 0.5×sin(inclinación))
Forward whirl: RPM < crítico | Backward whirl: RPM ≥ crítico
```

### 11.4 Stick-Slip
```
Torque por fricción: T_friction = μ × WOB × R_bit / 3
Rigidez torsional: k = G × J / L
    G = 11.5×10⁶ psi (módulo de corte del acero)
    J = π/32 × (OD⁴ − ID⁴)     [momento polar de inercia]

Índice de severidad: severity = Δω / ω_surface
    Leve: < 0.5 | Moderado: 0.5–1.0 | Severo: 1.0–1.5 | Crítico: > 1.5
```

### 11.5 Energía Mecánica Específica — MSE (Teale, 1965)
```
MSE = (480 × T × RPM) / (d² × ROP) + (4 × WOB) / (π × d²)
      ─────────────────────────────    ──────────────────────
         Componente rotacional          Componente de empuje

Founder point: MSE > 3× mínimo teórico (~5,000 psi)
Clasificación:
    < 20,000 psi: Eficiente | 20–50k: Normal | 50–100k: Ineficiente | > 100k: Muy ineficiente
```

### 11.6 Índice de Estabilidad
```
Score ponderado:
    Axial: 0.20 + Lateral: 0.30 + Torsional: 0.35 + MSE: 0.15

Estado: Estable (≥80) | Marginal (60–80) | Inestable (40–60) | Crítico (<40)
```

### 11.7 Matriz de Transferencia (TMM)
```
Matriz 4×4 por segmento: [y, θ, M, V]ᵀ
λ⁴ = m×ω² / EI
Condiciones de frontera: pinned-pinned, fixed-pinned, fixed-free
Eigenvalores: det(boundary_matrix) = 0
```

---

## 12. Cementación

### 12.1 Normas y Referencias

| Referencia | Descripción |
|---|---|
| **Nelson & Guillot** | Well Cementing, 2nd Ed. (Schlumberger) |
| **API Spec 10A** | Cementos y Materiales para Cementación de Pozos |
| **API Spec 10B** | Pruebas de Cementos de Pozos |
| **API RP 65-Part 2** | Aislamiento de Zonas Potenciales de Flujo |
| **Bourgoyne et al.** | Applied Drilling Engineering, Cap. 3 |

### 12.2 Clases de Cemento API
```
Clase A/B: 15–16 ppg, profundidad ≤ 6,000 ft
Clase C:   14–15 ppg, alta resistencia temprana
Clase G:   15.6–16.4 ppg, propósito general (más utilizado)
Clase H:   16–16.5 ppg, alta densidad
```

### 12.3 Fórmulas de Volumen
```
Capacidad Anular: C_ann = (hole_ID² − csg_OD²) / 1029.4     [bbl/ft]
Capacidad de Casing: C_csg = csg_ID² / 1029.4     [bbl/ft]

Volumen de lechada líder:  V_lead = L_lead × C_ann × factor_exceso
Volumen de lechada cola:   V_tail = L_tail × C_ann + L_shoe_track × C_csg
Sacos de cemento: sacos = volumen_bbl × 5.615 / 1.15     [1 saco ≈ 1.15 ft³]
Desplazamiento: V_disp = profundidad_float_collar × C_csg
```

### 12.4 ECD Durante Cementación
```
Hidrostática multi-fluido: P_hydro = Σ(ρ_i × 0.052 × h_i)
Fricción anular (Bingham): ΔP = (PV×v×L)/(1000×Deff²) + (YP×L)/(200×Deff)
ECD = (P_hydro + ΔP_fricción) / (0.052 × TVD)

Velocidad anular: v_ann = 24.5 × Q_gpm / (hole_ID² − csg_OD²)
Margen de fractura: FG_ppg − ECD_ppg     [debe ser > 0]
```

---

## 13. Diseño de Casing

### 13.1 Normas y Referencias

| Referencia | Descripción |
|---|---|
| **API TR 5C3 (ISO 10400)** | Ecuaciones de casing — 4 zonas de colapso |
| **API 5CT** | Especificación para Casing y Tubing |
| **NORSOK D-010** | Integridad de Pozo en Perforación y Producción |
| **Bourgoyne et al.** | Applied Drilling Engineering, Cap. 7 |
| **Fórmula de Barlow** | Resistencia al estallido de tuberías |

### 13.2 Grados de Casing (API 5CT)
```
J55: 55 ksi yield | K55: 55 ksi yield, 95 ksi tensile
L80, N80: 80 ksi yield
C90, T95: 90/95 ksi yield
C110, P110: 110 ksi yield
Q125: 125 ksi yield
```

### 13.3 Perfiles de Carga
```
Burst:
    P_int(z) = P_reservoir − gradiente_gas × (TVD − z)
    P_ext(z) = MW × 0.052 × z
    Carga_burst = P_int − P_ext     [peor caso: gas a superficie]

Colapso:
    P_ext = columna de lodo/cemento exterior
    P_int = escenario de evacuación (vacío hasta nivel de evacuación)
    Carga_colapso = P_ext − P_int
```

### 13.4 Resistencia al Estallido — Fórmula de Barlow
```
P_burst = 0.875 × 2 × Yp × t / OD
    [0.875 = factor por 12.5% de tolerancia de espesor de pared]
```

### 13.5 Resistencia al Colapso — API TR 5C3 (4 Zonas)
```
Zona 1 — Colapso por Yield (bajo D/t):
    Pc = 2 × Yp × [(D/t − 1) / (D/t)²]

Zona 2 — Colapso Plástico:
    Pc = Yp × (A/(D/t) − B) − C

Zona 3 — Colapso de Transición:
    Pc = Yp × (F/(D/t) − G)

Zona 4 — Colapso Elástico (alto D/t):
    Pc = 46.95×10⁶ / [(D/t) × (D/t − 1)²]

Coeficientes A, B, C, F, G derivados empíricamente según yield (tablas API)
```

### 13.6 Tensión y Correcciones
```
Peso al aire: W_air = peso_ppf × longitud
Factor de flotación: BF = 1 − MW / 65.4
Carga de shock (Lubinski): F_shock = 3200 × peso_ppf
Carga por flexión: F_bend = 63 × DLS × OD × peso_ppf
Tensión total: F_total = W_buoyed + F_shock + F_bend + F_overpull

Corrección Biaxial (API 5C3 — Elipse):
    Yp_eff = Yp × [√(1 − 0.75×(σa/Yp)²) − 0.5×(σa/Yp)]
    Factor de reducción: RF = Yp_eff / Yp
    Colapso corregido: Pc_corr = Pc_rating × RF

Triaxial Von Mises:
    σ_vme = √[(σa−σh)² + (σh−σr)² + (σr−σa)² + 6τ²] / √2
    Aceptable si: σ_vme < Yp / FS

Factores de Diseño:
    SF_burst = 1.10 | SF_colapso = 1.00 | SF_tensión = 1.60
```

---

## 14. Reportes Diarios / DDR

### 14.1 Normas y Referencias

| Referencia | Descripción |
|---|---|
| **IADC** | Códigos de operaciones (DR, DV, TT, CS, CM, LG, CT, CP, etc.) |
| **IADC** | Códigos y categorías de Tiempo No Productivo (NPT) |

### 14.2 KPIs Calculados
```
Perforado diario:        footage = depth_end − depth_start
ROP promedio:            ROP = footage / drilling_hours
Porcentaje NPT:          NPT% = (npt_hours / total_hours) × 100
Costo por pie:           CPF = total_cost / footage
Curva tiempo vs. profundidad: acumulativo día a día vs. plan
Costo acumulado vs. AFE: tracking presupuestario en tiempo real
```

### 14.3 Categorías de NPT (IADC)
```
Mecánico | Pozo | Clima | Logística | Humano | Otros

Validaciones automáticas:
    Horas operacionales = 24.0 ± 0.5
    Continuidad de profundidad entre reportes
    Propiedades de lodo dentro de rangos (6–22 ppg)
```

---

## Constantes Físicas Utilizadas

| Constante | Valor | Unidad |
|---|---|---|
| Módulo de Young (acero) | 30 × 10⁶ | psi |
| Módulo de Corte (acero) | 11.5 × 10⁶ | psi |
| Relación de Poisson (acero) | 0.30 | — |
| Coeficiente de expansión térmica (acero) | 6.9 × 10⁻⁶ | 1/°F |
| Densidad del acero | 65.5 | ppg |
| Densidad del acero | 490 | lb/ft³ |
| Constante hidrostática | 0.052 | psi/ft/ppg |
| Gravedad | 32.174 | ft/s² |
| Densidad del agua | 8.34 | ppg |
| 1 barril | 42 gal / 5.615 ft³ / 9,702 in³ | — |
| 1 saco de cemento | 1.15 | ft³ |
| Capacidad de tubería | ID² / 1029.4 | bbl/ft |

---

## Referencias Bibliográficas Completas

### Normas y Estándares Internacionales
1. **API RP 13D** — Rheology and Hydraulics of Oil-Well Drilling Fluids
2. **API RP 19B** — Evaluation of Well Perforators
3. **API RP 19C** — Procedures for Testing Sand Control Screens
4. **API RP 5C7** — Coiled Tubing Low-Cycle Fatigue
5. **API TR 5C3 (ISO 10400)** — Technical Report on Casing Equations and Calculations
6. **API 5CT** — Specification for Casing and Tubing
7. **API Spec 10A** — Cements and Materials for Well Cementing
8. **API Spec 10B** — Testing Well Cements
9. **API RP 65-Part 2** — Isolating Potential Flow Zones During Well Construction
10. **NORSOK D-010** — Well Integrity in Drilling and Well Operations
11. **IWCF/IADC** — Well Control Standards

### Publicaciones Técnicas y Libros
12. **Bourgoyne, A.T. et al.** — Applied Drilling Engineering (SPE Textbook Series)
13. **Nelson, E.B. & Guillot, D.** — Well Cementing, 2nd Edition (Schlumberger)
14. **Penberthy, W.L. & Shaughnessy, C.M.** — Sand Control (SPE Series)
15. **Halliburton Red Book** — Cement Engineering Reference Manual
16. **Baker Hughes Completion Engineering Guide**
17. **ICoTA** — Coiled Tubing Manual

### Artículos SPE y Papers Técnicos
18. **Johancsik, C.A. et al. (1984)** — SPE 11380: Torque & Drag in Directional Wells
19. **Lubinski, A. (1962)** — Helical Buckling of Tubing Sealed in Packers
20. **Mitchell, R. (1999)** — Stiffness Corrections and Post-Buckling Drag
21. **Mitchell, R. & Samuel, R. (2009)** — How Good Is the Thin Shell Approximation
22. **Adams, A.J. & MacEachran, A. (1994)** — Impact on Casing Design of Thermal Expansion
23. **Dranchuk, P.M. & Abou-Kassem, J.H.** — Z-Factor Correlation (DAK, 11 coefficients)
24. **Standing, M.B.** — Pseudo-Critical Property Correlations for Gas
25. **Archie, G.E. (1942)** — The Electrical Resistivity Log as an Aid in Determining Some Reservoir Characteristics
26. **Simandoux, P. (1963)** — Mesures Diélectriques en Milieu Poreux
27. **Poupon, A. & Leveaux, J. (1971)** — Evaluation of Water Saturation in Shaly Formations (Indonesia Equation)
28. **Timur, A. (1968)** — An Investigation of Permeability, Porosity, and Residual Water Saturation Relationships
29. **Coates, G.R. & Dumanoir, J.L. (1974)** — A New Approach to Improved Log-Derived Permeability
30. **Wyllie, M.R.J. et al. (1956)** — Elastic Wave Velocities in Heterogeneous and Porous Media
31. **Raymer, L.L., Hunt, E.R. & Gardner, J.S. (1980)** — An Improved Sonic Transit Time-to-Porosity Transform
32. **Larionov, V.V. (1969)** — Borehole Radiometry (Vshale Correction for Tertiary Rocks)
33. **Karakas, M. & Tariq, S.M. (1991)** — Semi-Analytical Productivity Models for Perforated Completions
34. **Haimson, B. & Fairhurst, C. (1967)** — Initiation and Extension of Hydraulic Fractures in Rocks
35. **Eaton, B.A. (1969)** — Fracture Gradient Prediction and Its Application in Oilfield Operations
36. **Vogel, J.V. (1968)** — Inflow Performance Relationships for Solution-Gas Drive Wells
37. **Fetkovich, M.J. (1973)** — Isochronal Testing of Oil Wells
38. **Joshi, S.D. (1991)** — Horizontal Well Technology
39. **Saucier, R.J. (1974)** — Considerations in Gravel Pack Design
40. **Luo, Y. et al. (1992)** — Hole Cleaning Index (HCI)
41. **Larsen, T.I. et al. (SPE 36383, 1997)** — Slip Velocity in Deviated Wells
42. **Moore, P.L.** — Drilling Practices Manual (Slip Velocity Correlation)
43. **Paslay, P.R. & Dawson, R. (1984)** — Drillstring Lateral Vibrations
44. **Jansen, J.D. & van den Steen, L. (1995)** — Active Damping of Torsional Drillstring Vibrations
45. **Teale, R. (1965)** — The Concept of Specific Energy in Rock Destruction
46. **Dupriest, F.E. (2005)** — MSE-Based Drilling Optimization
47. **Dunayevsky, V.A. (1993)** — BHA Stability in Directional Wells
48. **Mitchell, R.F. (2003)** — Lateral Vibrations and Transfer Matrix Analysis
49. **Miner, M.A. (1945)** — Cumulative Damage in Fatigue
50. **Beggs, H.D. & Brill, J.P. (1973)** — A Study of Two-Phase Flow in Inclined Pipes

---

*Documento generado automáticamente por PetroExpert v1.0 — Sistema Experto de Ingeniería Petrolera con IA*
*Febrero 2026*
