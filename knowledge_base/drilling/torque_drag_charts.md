# Gráficos de Torque y Drag (Torque Drag Charts)
## Versión: 1.0 | Fecha: 08-Feb-2026 | API RP 7G-2, SPE-11380-PA[web:26][web:18]

### 1. Fundamentos
Modelos predicen fuerzas axiales/torsionales: Soft-string (fricción cte), Stiff-string (contactos puntuales).[web:18] Factor fricción μ=0.15-0.35 (lube mud).[web:26]

**Ecuaciones**:
[ T = T_0 e^{mu \theta / r} ]
[ Drag = W_{fluid} (1 - cos alpha) + mu N ]

Donde T: torque, θ: contacto arco, r: radio pozo.

### 2. Construcción de Charts (Excel)
- Ejes: Profundidad vs. Hookload/Torque.
- Curvas: Predicted (buoyed weight ±fricción), Actual.
- Normalizado: Actual/Predicted >1.2 = alerta.[web:11]

| Condición | Ratio HL | Acción |
|-----------|----------|--------|
| Free     | 0.9-1.1 | OK |
| Tight    | >1.2    | Ream/Work |

### 3. Normas y Aplicación
- **API 7G-2**: Drift specs para rigidez BHA.
- **Monitoreo**: Cada 90ft surveyed; update μ real-time.[web:26]
- **Direccionales**: Torque ↑ en doglegs >6°/30m; lubricantes.[web:18]

### 4. Prevención NPT
- Validar pre-trip: Torque sin rotación <50%.
- Post-job: Calibrar model con logs.

### 5. Ejemplo BHA Slim-Hole (6.5" Liner)[cite:3]
| Componente | Peso (klb) | Torque Max (ft-lb) |
|------------|------------|-------------------|
| PDC 6.25" | 0.2       | 1000             |
| Motor     | 10        | 1200             |
| DC        | 30×8      | -                |

## Referencias
- [TorqueDrag ReadTheDocs][web:26]
- [ACS Omega Model][web:18]