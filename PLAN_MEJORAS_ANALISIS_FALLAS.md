# Plan de Mejoras: Flujo de Analisis de Fallas (Dashboard - Agent Pipeline - RCA Tool)

## Contexto

El flujo de analisis de fallas es la funcionalidad original/fundacional de PetroExpert. Existia antes de los 13 modulos de ingenieria que se han construido. Tras una auditoria completa del codigo frontend y backend, se identificaron **problemas criticos de arquitectura, UX, bugs, y codigo muerto** que impiden que esta seccion alcance el nivel de calidad de los modulos de ingenieria.

**Archivos principales del flujo:**

| Capa | Archivo | Funcion |
|------|---------|---------|
| Frontend | `App.tsx` | Router y orquestador de estado |
| Frontend | `WellSelector.tsx` | Paso 1-2: Crear/Seleccionar Pozo |
| Frontend | `EventWizard.tsx` | Pasos 3-7: Wizard de 3 pasos |
| Frontend | `AnalysisDashboard.tsx` | Pipeline de agentes + RCA |
| Frontend | `PhysicsResults.tsx` | Motor de fisica (ECD/CCI/Riesgo) |
| Frontend | `RCAVisualizer.tsx` | Visualizacion 5-Whys + Ishikawa |
| Backend | `api_main.py` | Endpoints (lineas 155-784) |
| Backend | `orchestrator/api_coordinator.py` | Coordinador de agentes API |
| Backend | `orchestrator/coordinator.py` | Base coordinador (legacy CLI) |
| Backend | `orchestrator/calculation_engine.py` | Motor de fisica simplificado |
| Backend | `agents/base_agent.py` | Agente base |
| Backend | `agents/rca_lead.py` | Agente RCA |
| Backend | `agents/data_extractor.py` | Extractor de datos de archivos |
| Backend | `utils/llm_gateway.py` | Gateway Gemini/Ollama |
| Backend | `models/database.py` | Modelos legacy (Well, Problem, Analysis) |
| Backend | `models/models_v2.py` | Modelos v2 (Event, ParameterSet, RCAReport) |

---

## Flujo Actual (8 Pasos)

```
Paso 1. Crear Pozo              -> WellSelector.tsx
Paso 2. Seleccionar Pozo        -> WellSelector.tsx
Paso 3. Tipo de Operacion       -> EventWizard.tsx (Step 1)
Paso 4. Tipo de Evento          -> NO EXISTE en el wizard (Bug B1)
Paso 5. Cargar Informes         -> EventWizard.tsx (Step 2)
Paso 6. Extraccion automatica   -> DataExtractionAgent + EventWizard.tsx (Step 2)
Paso 7. Seleccionar Especialistas + Lider -> EventWizard.tsx (Step 3)
Paso 8. Tipo de Analisis        -> AnalysisDashboard.tsx (interactivo/automatizado)
```

---

## DIAGNOSTICO: Hallazgos Criticos

---

### BUGS ACTIVOS (13 encontrados)

| # | Bug | Archivo | Linea(s) | Severidad |
|---|-----|---------|----------|-----------|
| **B1** | `event_type` nunca se recolecta en el wizard — siempre `null` en BD y en prompt RCA. El wizard solo tiene `phase` y `family`, falta un selector de tipo de evento especifico | `EventWizard.tsx` | Step 1 | ALTA |
| **B2** | Prompt del agente tiene `select-none` — usuario NO puede copiar el texto en modo interactivo, haciendo ese modo completamente inusable | `AnalysisDashboard.tsx` | :458 | MEDIA |
| **B3** | `conversation_history` en `BaseAgent` se acumula entre TODAS las sesiones. Los agentes son singletons compartidos — un usuario contamina el contexto de otro. Memory leak que crece indefinidamente | `agents/base_agent.py` | :32 | CRITICA |
| **B4** | Archivos temporales se escriben en CWD con nombres predecibles (`temp_{filename}`) — race condition si dos usuarios suben archivo con mismo nombre simultaneamente. Vector de path traversal si filename contiene `../` | `api_main.py` | :576-577 | ALTA |
| **B5** | `gemini_flash` y `gemini_pro` apuntan al MISMO modelo (`gemini-2.5-flash`) — no hay diferenciacion real entre modo "fast" y "reasoning" | `utils/llm_gateway.py` | :24-25 | MEDIA |
| **B6** | `PhysicsResults` usa `POST /calculate` como GET — re-ejecuta calculo fisico en CADA montaje del componente (3x para el mismo evento) | `PhysicsResults.tsx` | :21 | MEDIA |
| **B7** | `calculation_engine.py` usa geometria hardcodeada (`8.5"` hole, `5.0"` pipe) para todos los pozos — los resultados de CCI son ficticios e incorrectos | `calculation_engine.py` | :89-91 | ALTA |
| **B8** | System prompt se concatena como texto en el body del user prompt en vez de usar `system_instruction` de Gemini API — reduce calidad de respuesta del LLM | `utils/llm_gateway.py` | :55 | MEDIA |
| **B9** | `rca_lead` aparece 2 veces en `standard_workflow` (posicion 0 y 6). Cuando el paso 7 se ejecuta, sobreescribe silenciosamente la clasificacion del paso 1. El usuario pierde el output de clasificacion sin explicacion | `coordinator.py` | :49-57 | ALTA |
| **B10** | "Seleccionar Todos" agentes NO asigna lider — `leaderAgent` queda `null`. El analisis arranca sin lider designado | `EventWizard.tsx` | :296-305 | ALTA |
| **B11** | `replace('_', ' ')` solo reemplaza el PRIMER underscore. `"rca_lead_engineer"` se muestra como `"rca lead_engineer"`. Deberia ser `replace(/_/g, ' ')` | `EventWizard.tsx:324`, `AnalysisDashboard.tsx:382` | Varias | BAJA |
| **B12** | Inputs de datos extraidos usan `defaultValue` en vez de `value` — componentes no controlados que pueden quedar stale al re-renderizar | `EventWizard.tsx` | :255 | MEDIA |
| **B13** | `API_BASE_URL` hardcodeado como `'http://localhost:8000'` en `App.tsx` — rompe en produccion/staging. Todos los demas componentes importan correctamente de `config.ts` | `App.tsx` | :26 | ALTA |

---

### CODIGO MUERTO (7 archivos/secciones a eliminar)

| Componente | Archivo | Razon de eliminacion |
|---|---|---|
| `ProblemForm.tsx` | `frontend/src/components/` | Reemplazado por EventWizard. Contiene logica de autofill hardcoded (BAKTE-9). Solo importado por el comentario `// Changed from ProblemForm` en App.tsx |
| `AgentSelector.tsx` | `frontend/src/components/` | Solo importado por `ProblemForm.tsx` (muerto). Ironicamente, tiene funcionalidad de drag-reorder que el wizard actual NO tiene |
| `FishboneEditor.tsx` | `frontend/src/components/` | No importado en ningun componente activo. Tiene editor interactivo funcional de Ishikawa — deberia RECONECTARSE en vez de eliminarse (ver Fase D) |
| `FiveWhysEditor.tsx` | `frontend/src/components/` | No importado. Tiene editor interactivo de 5-Whys — deberia RECONECTARSE (ver Fase D) |
| `ProgramGenerator.tsx` | `frontend/src/components/` | No importado en App.tsx. Boton "Export MD" sin `onClick` — dead button dentro de dead component |
| CLI methods | `orchestrator/coordinator.py` | `analyze_stuck_pipe_interactive()` y `quick_analysis_interactive()` usan `print()`/`input()` — colgarian el server si se invocaran desde la API. ~200 lineas muertas |
| `save_response()`/`load_response()` | `agents/base_agent.py` | Nunca llamados desde ningun endpoint. Permiten escritura arbitraria al filesystem |

---

### DEUDA ARQUITECTONICA (8 items)

| # | Problema | Detalle | Impacto |
|---|----------|---------|---------|
| **A1** | **Modelo dual Problem/Event** | `Problem` (legacy) + `Event` (v2) coexisten. `POST /events` crea AMBOS registros como "bridge". `AnalysisDashboard` busca `event_id` en `problem.additional_data.event_id` (4 niveles de optional chaining). Si la estructura cambia, `eventId` queda `null` silenciosamente | Alto |
| **A2** | **No hay state management** | Todo el estado vive en `App.tsx` con `any` types: `selectedWell: any`, `activeAnalysis: any`, `currentView: string` (sin union type). Prop drilling sin interfaces tipadas | Medio |
| **A3** | **No hay router** | Navegacion por `currentView` string — sin URLs, sin browser back, sin bookmarks, sin deep linking. Un refresh pierde todo el estado | Medio |
| **A4** | **Idioma inconsistente** | EventWizard en espanol, AnalysisDashboard en ingles, RCAVisualizer en ingles, nombres de agentes en snake_case ingles. Mezcla confusa | Medio |
| **A5** | **`RCAReport` duplicable** | No hay upsert — cada llamada a `POST /events/{id}/rca` crea un nuevo registro. Si el usuario reintenta, hay duplicados en BD | Alto |
| **A6** | **`prevention_actions` siempre NULL** | El campo existe en `RCAReport` pero el prompt del LLM no lo genera. Solo se generan `corrective_actions` | Bajo |
| **A7** | **Sidebar con datos hardcoded** | `"Antonio Var."`, `"Operations Dir."`, System Health siempre `"Optimal"` al `80%` — datos falsos | Bajo |
| **A8** | **3 instancias de `LLMGateway`** | Una en `APICoordinator`, una en `DataExtractionAgent`, una en `RCALeadAgent`. Cada una llama `genai.configure(api_key=...)` — la ultima gana. Estado global compartido sin coordinacion | Medio |

---

### GAPS DE UX (12 items)

| # | Gap | Ubicacion | Impacto |
|---|-----|-----------|---------|
| **U1** | No hay loading state durante `handleEventSubmit` (3 API calls secuenciales). Usuario puede hacer doble-submit | `App.tsx` | Alto |
| **U2** | Errores se muestran con `alert()` nativo en toda la seccion (5+ ocurrencias). Inconsistente con el diseno glass-panel del resto de la app | Multiples archivos | Medio |
| **U3** | Sin indicador de pasos en el wizard (no hay step dots, progress bar, ni breadcrumb) | `EventWizard.tsx` | Medio |
| **U4** | `RCAVisualizer` recibe `activeAnalysis` (response de init) en vez de un `RCAReport` — vista standalone de RCA esta completamente rota | `App.tsx:120` | Alto |
| **U5** | Al completar sintesis, se oculta TODA la vista previa de agentes sin posibilidad de volver | `AnalysisDashboard.tsx` | Medio |
| **U6** | `completedAnalyses` state se acumula con `{role, confidence}` de cada agente pero NUNCA se renderiza — datos disponibles desperdiciados | `AnalysisDashboard.tsx` | Bajo |
| **U7** | No hay timeout ni boton cancelar en modo automatizado. Si Gemini cuelga, UI permanentemente stuck en `isProcessing=true` | `AnalysisDashboard.tsx` | Alto |
| **U8** | Sin descripcion de que hace cada agente — solo muestra `role` transformado. Usuario no sabe a quien elegir ni por que | `EventWizard.tsx` Step 3 | Medio |
| **U9** | `PhysicsResults` aparece ARRIBA del pipeline de agentes — flujo visual invertido (deberia ser pipeline primero, luego resultados) | `AnalysisDashboard.tsx` | Medio |
| **U10** | No hay back button en step 2 antes de extraer datos. Usuario atrapado sin poder regresar a step 1 | `EventWizard.tsx` | Medio |
| **U11** | Fishbone usa string literal `{"><"}` como icono de diagrama en vez de SVG adecuado | `RCAVisualizer.tsx:62` | Bajo |
| **U12** | `replace('_', ' ')` produce `"rca lead_engineer"` — solo reemplaza primer underscore | `EventWizard.tsx`, `AnalysisDashboard.tsx` | Bajo |

---

### BUGS ADICIONALES DEL BACKEND (encontrados en auditoria profunda)

| # | Bug | Archivo | Detalle |
|---|-----|---------|---------|
| **BE1** | `init_analysis` usa GET y POST con `Body(None)` — Body no es valido en GET requests | `api_main.py:167-227` | FastAPI puede ignorar body en GET silenciosamente |
| **BE2** | `get_synthesis_query` no tiene null check para `analysis_record` — crash con AttributeError en vez de HTTP 404 | `api_main.py:312-313` | Mismo patron en `run_auto_synthesis:423` |
| **BE3** | `event_data.get("family").upper()` lanza AttributeError si `family` es None | `api_main.py:661` | 500 sin mensaje util en vez de 422 validation |
| **BE4** | `json` module referenciado en `api_coordinator.py:get_program_prompt` pero nunca importado en ese archivo | `api_coordinator.py:117` | NameError al generar programas con additional_data |
| **BE5** | `data_extractor.py` incluye comentario Python como texto literal en el prompt del LLM: `# Limit text to avoid context window issues` | `data_extractor.py:61` | Confunde al modelo |
| **BE6** | `_extract_confidence` solo busca terminos en espanol — si LLM responde en ingles, siempre retorna "MEDIUM" | `base_agent.py:120-156` | Confianza incorrecta sistematicamente |
| **BE7** | `[REAL_DATA:filename]` en `problem.description` es un vector de path traversal — `[REAL_DATA:../../../etc/passwd]` intenta cargar archivos del sistema | `api_main.py:383-402` | Vulnerabilidad de seguridad |
| **BE8** | CORS wildcard `*` por defecto con `allow_credentials=True` | `api_main.py:54-61` | Postura de seguridad pobre para produccion |

---

## DECISIONES CONFIRMADAS

| Decision | Respuesta | Justificacion |
|----------|-----------|---------------|
| Modo interactivo (copy/paste a Claude) | **ELIMINAR** | Legacy de cuando no habia API de Gemini. Inusable (bug `select-none`), confuso, duplica codigo |
| `PhysicsResults` (ECD/CCI/Riesgo simplificado) | **ELIMINAR** | Geometria hardcoded (8.5"/5.0"), CCI ficticia, redundante con analisis de agentes IA |
| Alcance | **Implementar las 4 fases completas** | ~6 dias con Claude Opus 4.6 |
| `FishboneEditor` / `FiveWhysEditor` | **NO eliminar — RECONECTAR** | Tienen funcionalidad valiosa, integrar en RCAVisualizer como modo editable |

---

## PLAN DE IMPLEMENTACION

---

### FASE A — Correcciones Criticas (Bugs + Limpieza)

**Duracion estimada: ~1 dia (4-6 horas con Claude Opus 4.6)**

#### A.1 — Agregar `event_type` al wizard (Bug B1 + Gap U8)

**Archivos:** `EventWizard.tsx`, `api_main.py`

En `EventWizard.tsx` Step 1, agregar sub-selector dependiente de la fase seleccionada:

```
Si phase = "drilling":
  - Pega de Tuberia
  - Perdida de Circulacion
  - Kick / Influjo
  - Falla de BHA
  - Torque/Drag Excesivo
  - Vibracion Severa
  - Otro

Si phase = "completion":
  - Falla de Canoneo
  - Dano de Formacion
  - Produccion de Arena
  - Falla de Packer
  - Falla de Empaque
  - Otro

Si phase = "workover":
  - Falla de Coiled Tubing
  - Falla de BOP
  - Atascamiento
  - Falla de Equipo Superficie
  - Otro
```

En `api_main.py:661`, leer `event_data.get("event_type")` y pasarlo al modelo `Event`.

#### A.2 — Eliminar modo interactivo completo

**Archivo:** `AnalysisDashboard.tsx`

Eliminar:
- Toggle interactivo/automatizado (`isAutomated` state)
- Textarea de paste de prompts
- Panel de instrucciones "How to proceed"
- Logica de `select-none` en prompts
- Todo el branch condicional de modo interactivo

Dejar SOLO el flujo automatizado con Gemini como modo unico. Actualizar labels de "Ollama" a "IA Automatizada (Gemini)".

#### A.3 — Limpiar estado de agentes entre sesiones (Bug B3 — CRITICO)

**Archivo:** `agents/base_agent.py`

Opcion A (rapida): Resetear `conversation_history = []` al inicio de cada `analyze_interactive()`.

Opcion B (correcta): No acumular history en el singleton — crear history por request pasando un `session_context` dict desde el endpoint.

Implementar Opcion A como fix inmediato, evaluar Opcion B en Fase C.

#### A.4 — Fix archivos temporales (Bug B4 + Bug BE7)

**Archivo:** `api_main.py:576-589`

```python
# ANTES (inseguro):
temp_filename = f"temp_{file.filename}"
with open(temp_filename, "wb") as buffer: ...

# DESPUES (seguro):
import tempfile
suffix = os.path.splitext(file.filename)[1] if file.filename else ".tmp"
# Sanitizar: solo permitir extensiones conocidas
allowed_exts = {".pdf", ".csv", ".txt", ".xlsx", ".docx", ".las"}
if suffix.lower() not in allowed_exts:
    suffix = ".tmp"
with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
    tmp.write(await file.read())
    temp_path = tmp.name
try:
    # ... procesar archivo ...
finally:
    os.unlink(temp_path)
```

Tambien sanitizar `[REAL_DATA:filename]` validando que el path no salga de `data/`:
```python
import os
safe_path = os.path.realpath(os.path.join("data", filename))
if not safe_path.startswith(os.path.realpath("data")):
    raise HTTPException(400, "Invalid file path")
```

#### A.5 — Usar `system_instruction` de Gemini API (Bug B8)

**Archivo:** `utils/llm_gateway.py`

```python
# ANTES:
full_prompt = f"System: {system_prompt}\n\nUser: {prompt}" if system_prompt else prompt
model = self.gemini_pro if mode == "reasoning" else self.gemini_flash
response = await model.generate_content_async(full_prompt)

# DESPUES:
model = self.gemini_pro if mode == "reasoning" else self.gemini_flash
if system_prompt:
    # Crear modelo con system_instruction para esta llamada
    model = genai.GenerativeModel(
        model_name=model.model_name,
        system_instruction=system_prompt
    )
response = await model.generate_content_async(prompt)
```

#### A.6 — Eliminar codigo muerto (7 items)

**Archivos a BORRAR:**
- `frontend/src/components/ProblemForm.tsx`
- `frontend/src/components/AgentSelector.tsx`
- `frontend/src/components/ProgramGenerator.tsx`

**Archivos a MOVER (no borrar — se reconectan en Fase D):**
- `FishboneEditor.tsx` — conservar para Fase D.4
- `FiveWhysEditor.tsx` — conservar para Fase D.4

**Limpiar en `coordinator.py`:**
- Eliminar `analyze_stuck_pipe_interactive()` (~97 lineas)
- Eliminar `quick_analysis_interactive()` (~57 lineas)

**Limpiar en `base_agent.py`:**
- Eliminar `save_response()` (lineas 158-168)
- Eliminar `load_response()` (lineas 170-181)

#### A.7 — Eliminar PhysicsResults (redundante)

**Archivos:**
- `AnalysisDashboard.tsx`: Eliminar import y renderizado de `<PhysicsResults>`
- `PhysicsResults.tsx`: Eliminar archivo completo
- `calculation_engine.py`: Agregar comentario `# DEPRECATED — usar HydraulicsEngine/WellboreCleanupEngine`

#### A.8 — Fix `API_BASE_URL` hardcoded (Bug B13)

**Archivo:** `App.tsx`

```typescript
// ANTES (linea 26):
const API_BASE_URL = 'http://localhost:8000';

// DESPUES:
import { API_BASE_URL } from './config';
// (eliminar la linea 26 hardcoded)
```

#### A.9 — Fix `rca_lead` duplicado en workflow (Bug B9)

**Archivo:** `coordinator.py`

```python
# ANTES:
self.standard_workflow = [
    "rca_lead",           # 1. Incident Classification
    "drilling_engineer",
    "hydrologist",
    "geologist",
    "mud_engineer",
    "well_engineer",
    "rca_lead"            # 7. Final Report Synthesis (SOBREESCRIBE paso 1!)
]

# DESPUES: Usar etiquetas de rol para distinguir las 2 apariciones
self.standard_workflow = [
    "rca_lead",           # 1. Incident Classification (Level 1-3)
    "drilling_engineer",
    "hydrologist",
    "geologist",
    "mud_engineer",
    "well_engineer",
    "rca_lead:synthesis"  # 7. Final Report Synthesis (rol distinto)
]
```

El backend debe parsear `agent_id:role` y usar el mismo agente pero con contexto de sintesis. Alternativamente, crear `rca_synthesizer` como agente separado (ver Fase D.1).

Fix inmediato en Fase A: usar key compuesto `"rca_lead_synthesis"` en `individual_analyses` para no sobreescribir el paso 1.

#### A.10 — Fix "Seleccionar Todos" sin lider (Bug B10)

**Archivo:** `EventWizard.tsx`

```typescript
// ANTES (linea 296-305):
// Select-all solo setea selectedAgents, NO toca leaderAgent

// DESPUES:
const handleSelectAll = () => {
  if (selectedAgents.length === availableAgents.length) {
    setSelectedAgents([]);
    setLeaderAgent(null);
  } else {
    const allIds = availableAgents.map(a => a.id);
    setSelectedAgents(allIds);
    // Auto-asignar primer agente del workflow como lider
    if (!leaderAgent) {
      setLeaderAgent(allIds.includes('drilling_engineer') ? 'drilling_engineer' : allIds[0]);
    }
  }
};
```

#### A.11 — Fix `json` import faltante (Bug BE4)

**Archivo:** `orchestrator/api_coordinator.py`

Agregar `import json` en los imports del archivo.

#### A.12 — Fix null guards faltantes (Bugs BE2, BE3)

**Archivo:** `api_main.py`

```python
# Fix BE2 — null check en get_synthesis_query y run_auto_synthesis:
analysis_record = db.query(Analysis).filter(Analysis.id == analysis_id).first()
if not analysis_record:
    raise HTTPException(404, f"Analysis {analysis_id} not found")

# Fix BE3 — null guard en family.upper():
family = event_data.get("family", "unknown")
description = f"[{family.upper()}] {params.get('operation_summary', '')}"
```

---

### FASE B — Mejoras de UX del Flujo

**Duracion estimada: ~2 dias (2 sesiones de 4-6 horas con Claude Opus 4.6)**

#### B.1 — Loading states y notificaciones (reemplazar `alert()`)

**Archivos:** `App.tsx`, `AnalysisDashboard.tsx`, `EventWizard.tsx`, `WellSelector.tsx`

1. **`App.tsx` - `handleEventSubmit`**: Agregar overlay de progreso con stepper visual:
   ```
   [*] Creando evento...  ->  [ ] Inicializando pipeline...  ->  [ ] Listo
   ```
   Agregar `isSubmitting` state para deshabilitar boton y prevenir doble-submit.

2. **Sistema de notificaciones**: Instalar `sonner` (toast library) y reemplazar TODOS los `alert()`:
   - `EventWizard.tsx`: 3 alert() (validacion archivos, error extraccion)
   - `AnalysisDashboard.tsx`: 5 alert() (errores de agentes, RCA, PDF)
   - `WellSelector.tsx`: 1 alert() (error delete)
   - `App.tsx`: 1 alert() (error event creation)

3. **Error inline**: Mostrar mensajes de error dentro del panel cuando agentes fallan, no en popups.

#### B.2 — Mejorar Step 2: Carga de archivos

**Archivo:** `EventWizard.tsx`

1. Drag-and-drop visual mejorado:
   - Borde animado al arrastrar archivo sobre la zona
   - Preview de archivos subidos con icono por tipo (PDF, CSV, TXT)
   - Indicador de tamano del archivo

2. Barra de progreso durante extraccion IA (en vez de solo spinner generico)

3. Cambiar de `defaultValue` a `value` en inputs de datos extraidos (Bug B12):
   ```typescript
   // ANTES: <input defaultValue={value as string} onChange={...} />
   // DESPUES: <input value={value as string} onChange={...} />
   ```

4. Agregar boton "Atras" en step 2 ANTES de extraer datos (Bug U10):
   ```typescript
   <button onClick={() => setStep(1)}>Atras</button>
   ```

5. Si extraccion parcialmente falla, mostrar que campos se extrajeron y cuales quedaron vacios con indicador visual.

#### B.3 — Mejorar Step 3: Seleccion de especialistas

**Archivo:** `EventWizard.tsx`

1. **Descripcion de cada agente**: Mostrar tooltip o subtexto con la especialidad:
   ```
   [x] DRILLING ENGINEER
       Evalua mecanica de perforacion, parametros operacionales y BHA

   [x] MUD ENGINEER
       Analiza propiedades del fluido, reologia y estabilidad del pozo
   ```

2. **Validar lider obligatorio**: Si no hay lider al hacer click en "Comenzar Analisis", mostrar warning inline.

3. **Sugerencia automatica**: Al seleccionar `phase` + `event_type`, pre-seleccionar agentes relevantes:
   - "Pega de Tuberia" -> drilling, mud, geologist, well, rca_lead
   - "Kick" -> drilling, hydrologist, well, hse, rca_lead
   - "Vibracion Severa" -> drilling, geomechanic, directional, rca_lead

4. **Fix `replace('_', ' ')`** (Bug B11):
   ```typescript
   // ANTES:  agent.name.replace('_', ' ')
   // DESPUES: agent.name.replace(/_/g, ' ')
   ```

#### B.4 — Mejorar AnalysisDashboard (Pipeline)

**Archivo:** `AnalysisDashboard.tsx`

1. **Eliminar sintesis que oculta todo** (Bug U5): La sintesis se muestra como panel expandible al final, SIN reemplazar la vista de agentes completados.

2. **Mostrar `completedAnalyses` visualmente** (Bug U6): Badge de confianza (HIGH verde / MEDIUM amarillo / LOW rojo) junto a cada agente completado.

3. **Indicador de LIDER**: Estrella dorada al lado del agente designado como lider en el pipeline tracker.

4. **Auto-run secuencial**: Opcion de ejecutar todos los agentes en secuencia automatica sin click por paso. Boton "Ejecutar Todos" con progreso visual.

5. **Barra de progreso general**: `"Agente 3 de 7 completados"` con barra visual.

6. **Timeout + cancelar** (Bug U7): Timeout de 60s por agente con opcion de cancelar y continuar al siguiente.

#### B.5 — Mejorar RCAVisualizer

**Archivo:** `RCAVisualizer.tsx`

1. Agregar TypeScript interface `RCAReport` con todos los campos tipados (no `any`)

2. Guards para campos vacios/faltantes con mensajes informativos:
   ```typescript
   {report.five_whys?.length > 0 ? (
     // Renderizar 5-Whys
   ) : (
     <p className="text-gray-500">No se generaron los 5 Por Ques para este evento.</p>
   )}
   ```

3. Reemplazar `{"><"}` por icono SVG Ishikawa adecuado (Bug U11)

4. Agregar `prevention_actions` al prompt RCA y mostrarlas separadas de `corrective_actions` (Bug A6)

5. **Boton "Exportar RCA a PDF"**: Usar el mismo patron de `html2pdf` que ya existe en AnalysisDashboard

#### B.6 — Step indicator en el wizard (Bug U3)

**Archivo:** `EventWizard.tsx`

Agregar componente de progress stepper en la parte superior:

```
  [1]----[2]----[3]
  Identificacion  Datos  Especialistas
       *
```

Paso activo resaltado, pasos completados con checkmark, pasos futuros en gris.

---

### FASE C — Mejoras Arquitectonicas

**Duracion estimada: ~2 dias (2 sesiones de 4-6 horas con Claude Opus 4.6)**

#### C.1 — Unificar modelo de datos (eliminar bridge Problem - Event)

**Archivos:** `api_main.py`, `database.py`, `models_v2.py`, `AnalysisDashboard.tsx`

1. Agregar `event_id` como FK en tabla `Analysis`:
   ```python
   # models/database.py - Analysis model:
   event_id = Column(Integer, ForeignKey("events.id"), nullable=True)
   ```
   Migration: `ALTER TABLE analyses ADD COLUMN event_id INTEGER REFERENCES events(id);`

2. Eliminar creacion de `Problem` legacy en `POST /events` — crear solo `Event` + `ParameterSet`

3. Migrar `POST /problems/{id}/analysis/init` a `POST /events/{id}/analysis/init`

4. Actualizar `AnalysisDashboard` para obtener `eventId` directamente del `Analysis` record (sin el bridge de 4 niveles `problem.additional_data.event_id`)

5. Mantener endpoints legacy (`/problems/...`) como redirects temporales para no romper nada

#### C.2 — Consolidar LLMGateway (Bug A8)

**Archivos:** `api_main.py`, `api_coordinator.py`, `data_extractor.py`, `rca_lead.py`

1. Crear UNA SOLA instancia de `LLMGateway` en `api_main.py`
2. Pasarla como parametro al constructor de `APICoordinator`, `DataExtractionAgent`, `RCALeadAgent`
3. Eliminar `self.gateway = LLMGateway()` de cada clase individual

```python
# api_main.py
gateway = LLMGateway()
coordinator = APICoordinator(gateway=gateway)
data_extractor = DataExtractionAgent(gateway=gateway)
rca_agent = RCALeadAgent(gateway=gateway)
```

#### C.3 — Evitar duplicacion de RCA (Bug A5)

**Archivo:** `api_main.py`

```python
# POST /events/{id}/rca — verificar existente:
existing = db.query(RCAReport).filter(RCAReport.event_id == event_id).first()
if existing:
    return existing  # Retornar sin recalcular

# Agregar endpoints nuevos:
# GET  /events/{id}/rca  -> recuperar sin recalcular
# DELETE /events/{id}/rca -> eliminar para permitir regeneracion
```

#### C.4 — Internacionalizacion consistente

**Archivos:** `EventWizard.tsx`, `AnalysisDashboard.tsx`, `RCAVisualizer.tsx`, `translations/`

1. Mover cadenas hardcoded al sistema de traducciones existente (`translations/aiAnalysis.ts`)
2. Agregar toggle ES/EN que aplique a toda la seccion de analisis de fallas
3. Incluir terminos en ingles en `_extract_confidence` de `base_agent.py` (Bug BE6):
   ```python
   high_terms_en = ["definitely", "clearly", "high confidence", "certain"]
   high_terms_es = ["definitivamente", "claramente", "sin duda", "alta confianza"]
   high_confidence_terms = high_terms_en + high_terms_es
   ```

#### C.5 — Tipar estado de App.tsx (Bug A2)

**Archivo:** `App.tsx`

```typescript
// Definir tipos:
interface Well {
  id: number;
  name: string;
  location?: string;
}

type ViewName = 'dashboard' | 'analysis' | 'rca' | 'settings' | 'module-dashboard'
  | 'hydraulics' | 'torque-drag' | 'vibrations' | 'well-control'
  | 'stuck-pipe' | 'wellbore-cleanup' | 'cementing' | 'casing-design'
  | 'completion-design' | 'shot-efficiency' | 'sand-control'
  | 'packer-forces' | 'workover-hydraulics';

interface AnalysisSession {
  id: number;
  eventId: number;
  workflow: string[];
  leader: string | null;
}

// Usar:
const [selectedWell, setSelectedWell] = useState<Well | null>(null);
const [currentView, setCurrentView] = useState<ViewName>('dashboard');
const [activeAnalysis, setActiveAnalysis] = useState<AnalysisSession | null>(null);
```

---

### FASE D — Sintetizar y Pulir

**Duracion estimada: ~1 dia (4-6 horas con Claude Opus 4.6)**

#### D.1 — Separar `rca_lead` en 2 agentes distintos

**Archivos:** `coordinator.py`, `agents/rca_lead.py`, `api_coordinator.py`

Crear dos roles funcionales:
- **`rca_classifier`**: Paso 1 del workflow — Clasificacion de incidente API RP 585 (Level 1-3)
- **`rca_synthesizer`**: Paso final — Sintesis ejecutiva integrando hallazgos de todos los especialistas

```python
self.standard_workflow = [
    "rca_classifier",     # 1. Clasificacion (usa RCALeadAgent con rol de clasificacion)
    "drilling_engineer",
    "hydrologist",
    "geologist",
    "mud_engineer",
    "well_engineer",
    "rca_synthesizer"     # 7. Sintesis (usa RCALeadAgent con rol de sintesis)
]
```

Ambos pueden usar la misma clase `RCALeadAgent` pero con `system_prompt` diferente y guardando resultados con keys distintos.

#### D.2 — Sidebar dinamico

**Archivo:** `Sidebar.tsx`

```typescript
// ANTES (hardcoded):
<p>Antonio Var.</p>
<p>Operations Dir.</p>
<span>System Health: Optimal 80%</span>

// DESPUES (dinamico):
<p>{selectedWell?.name || 'Sin pozo seleccionado'}</p>
<p>{selectedWell?.location || 'Sin ubicacion'}</p>
<span>Gemini: {geminiStatus}</span> // OK, Error, Checking...
```

Donde `geminiStatus` se obtiene de `GET /providers` (ya existe el endpoint).

#### D.3 — Simplificar Step 1 del wizard

**Archivo:** `EventWizard.tsx`

Con `event_type` agregado en Fase A.1, evaluar si las 5 familias (`well/fluids/mechanics/control/human`) aportan valor adicional o son redundantes.

**Recomendacion:** Simplificar a `Phase -> Event Type` directamente. Las familias fueron un intento de clasificacion intermedia que `event_type` reemplaza de forma mas intuitiva para el usuario.

Si se elimina `family`:
1. Quitar selector de familia del wizard
2. Actualizar `POST /events` para hacer `family` opcional
3. El `event_type` provee suficiente contexto para la seleccion automatica de agentes (Fase B.3)

#### D.4 — Conectar editores de 5-Whys y Fishbone

**Archivos:** `RCAVisualizer.tsx`, `FiveWhysEditor.tsx`, `FishboneEditor.tsx`

Integrar los editores existentes (actualmente codigo muerto) en `RCAVisualizer` como modo editable:

```typescript
// RCAVisualizer.tsx
const [isEditing, setIsEditing] = useState(false);

// Modo lectura (actual):
{!isEditing && <FiveWhysDisplay data={report.five_whys} />}

// Modo edicion (nuevo):
{isEditing && <FiveWhysEditor
  initial={report.five_whys}
  onChange={(updated) => setEditedWhys(updated)}
/>}

// Boton toggle:
<button onClick={() => setIsEditing(!isEditing)}>
  {isEditing ? 'Guardar' : 'Editar RCA'}
</button>
```

Esto permite al usuario refinar/corregir los hallazgos del RCA generado por la IA, agregando valor de supervision humana al proceso automatizado.

**Nota:** Antes de reconectar `FishboneEditor`, corregir el bug existente donde `addFactor` agrega al `activeInput.category` en vez de la categoria clickeada.

---

## Resumen de Esfuerzo Total

| Fase | Contenido | Duracion (Claude Opus 4.6) | Archivos Principales |
|------|-----------|---------------------------|---------------------|
| **A** | Bugs criticos + Limpieza de codigo muerto | **1 dia** | `EventWizard.tsx`, `AnalysisDashboard.tsx`, `base_agent.py`, `api_main.py`, `llm_gateway.py`, `coordinator.py`, eliminar 3 archivos |
| **B** | Mejoras de UX del flujo completo | **2 dias** | `EventWizard.tsx`, `AnalysisDashboard.tsx`, `RCAVisualizer.tsx`, `App.tsx`, `WellSelector.tsx` |
| **C** | Mejoras arquitectonicas + unificacion modelos | **2 dias** | `api_main.py`, `database.py`, `models_v2.py`, `api_coordinator.py`, `translations/`, `App.tsx` |
| **D** | Sintetizar, simplificar y reconectar editores | **1 dia** | `coordinator.py`, `Sidebar.tsx`, `agents/rca_lead.py`, `EventWizard.tsx`, `RCAVisualizer.tsx` |
| | **TOTAL** | **~6 dias** | |

---

## Verificacion Post-Implementacion

1. **Test end-to-end del flujo completo:**
   ```
   Crear pozo -> Seleccionar -> Tipo operacion -> Tipo evento -> Upload PDF
   -> Verificar extraccion -> Seleccionar agentes + lider -> Ejecutar pipeline
   -> Generar RCA -> Verificar 5-Whys + Ishikawa + CAPA + Prevention Actions
   ```

2. **Test de regresion:** Correr los 1105 tests existentes + nuevos tests para endpoints modificados

3. **Test visual:** Verificar loading states, toast notifications, feedback correcto en cada paso

4. **Build de produccion:** `npm run build` sin errores TypeScript

5. **Test de endpoints:** Verificar todos los endpoints del flujo RCA devuelven HTTP 200 con datos validos

6. **Test de seguridad:** Verificar que `[REAL_DATA:../../../etc/passwd]` es rechazado correctamente

---

## Impacto Esperado

| Metrica | Antes | Despues |
|---------|-------|---------|
| Bugs activos en el flujo | 13+ | 0 |
| Codigo muerto | ~500 lineas en 7 archivos | Eliminado |
| Paso 4 (Tipo de Evento) | No existe | Funcional con tipos por fase |
| Modo de analisis | 2 modos (interactivo roto + automatizado) | 1 modo automatizado funcional |
| Seguridad (temp files, path traversal) | Vulnerable | Corregido |
| Memory leak (conversation_history) | Activo | Eliminado |
| UX (loading, errores, navegacion) | alert() + sin feedback | Toast notifications + progress |
| RCA duplicados en BD | Ilimitados | Controlado (upsert) |
| Editabilidad del RCA | Solo lectura | Editable (5-Whys + Fishbone) |
