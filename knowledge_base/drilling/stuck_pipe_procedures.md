# Procedimientos para Tubería Atrapada (Stuck Pipe Procedures)
## Versión: 1.0 | Fecha: 08-Feb-2026 | Basado en API RP 7G-2, IADC Lexicon & SPE-109914[web:21][web:30]

### 1. Definición y Mecanismos
La tubería atrapada ocurre cuando el string no rota, sube o baja libremente, con overpull > peso + fricción esperada o setdown > peso - fricción.[web:6] Categorías principales:
- **Mecánico/Geometría**: Keyseating (surco por tool joints en direccionales), doglegs (>3°/100ft), ledges, undergauge hole (bit desgastado).[web:6]
- **Pack-off/Bridge**: Acúmulo de cuttings, cavings o debris; reduce circulación.[web:6]
- **Diferencial**: Presión hidrostática > presión poro permeable; filter cake grueso.[web:6]
- **Geológicos**: Shale swelling (hidratación bentonita), plastic flow (sal), fractured formations.[web:6]

**Fórmula de sticking**: ( B_F + F_{BHA} > MOP ) donde ( B_F ): fuerza sticking, ( F_{BHA} ): fricción BHA, MOP: max overpull (tensile DP API 5DP).[web:6][web:24]

### 2. Consecuencias (NPT Impacto)
- Tiempo perdido: 20-40% NPT total; fishing hasta sidetrack.[web:6]
- Costo: >$100k/día; BHA perdido ~$500k.[web:14]
- Seguridad: Parting string, kick si pérdida circulación.[web:23]

### 3. Prevención (Normas API/IADC)
- **Planificación**: Análisis estabilidad pozo (API RP 65-2); mud weight ±0.2ppg poro.[web:22]
- **Hole Cleaning**: Q >400gpm, viscosidad 40-60s/qt; sweeps c/100 stands.[web:6]
- **Parámetros**: ROP <30ft/hr shales, WOB <50% neutral point.[web:6]
- **Mud**: Inhibitivo (KCl >5%, pH<10); LCM preventivo.[web:6]

### 4. Diagnóstico Inicial
- **Free Point**: Stretch = (Overpull × L_free) / (2208.5 × peso nominal DP).[web:6]
- **Indicadores**: Torque/drag ↑, pérdida circ, pump pressure ↑.
- **Decision Tree**:
  | Movimiento al stuck? | Hidráulicos? | Mecanismo Probable |
  |----------------------|--------------|-------------------|
  | No                   | Igual        | Diferencial[web:6] |
  | No                   | Cambiado     | Pack-off |
  | Sí (↑)               | -            | Keyseat/Undergauge |

### 5. Procedimientos de Liberación (API RP 54 Seguridad)[web:27]
1. **Inmediato**: Circ bottoms-up @ max rate; work pipe ±5k lb, rotate 20-40rpm.
2. **Spot Pill**: Diesel/acid 50bbls (diferencial); soak 4-6hrs.[web:6]
3. **Jarring**: Jar down si stuck ↑; up si ↓; torque 80% yield. (API 7G-2 jars).[web:6]
4. **Back-ream**: 1-2hr @ low WOB si pack-off.
5. **Fishing**: Back-off (string shot), overshot/jar string.[web:12]
6. **Escalada**: Si >6hrs, free point tool + pipe recovery log.

### 6. Lecciones Aprendidas (Ej. BAKTE-XXX)[cite:1]
- Evitar ROP alta en gumbo; sweeps obligatorios.
- Monitoreo real-time T&D models (Landman/Stiff-string).

## Referencias
- [API RP 7G-2 Drill Stem Design][web:21]
- [DrillingManual Stuck Course][page:0]
- [SPE-109914 Prevention][web:30]