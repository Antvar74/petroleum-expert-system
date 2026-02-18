# PETROEXPERT v5.0 — Sistema Experto de Ingenieria Petrolera

Suite avanzada de ingenieria de pozos que combina agentes especializados de IA con motores de calculo tecnico de clase mundial. Analisis ejecutivo bilingue (EN/ES), 4 modulos de ingenieria, sistema multi-agente con 11 especialistas, y exportacion PDF gerencial.

---

## Inicio Rapido

### Opcion 1: Docker (Recomendado)

```bash
# Clonar y configurar
git clone <repo-url> && cd petroleum-expert-system
cp .env.example .env
# Editar .env con tus API keys (GEMINI_API_KEY, etc.)

# Construir y ejecutar
docker compose up --build

# App disponible en http://localhost:8000
```

### Opcion 2: Desarrollo Local

```bash
# Backend (Puerto 8000)
pip install -r requirements.txt
uvicorn api_main:app --reload --port 8000 --host 0.0.0.0

# Frontend (Puerto 5174)
cd frontend
npm install
npm run dev -- --host --port 5174
```

---

## Configuracion (.env)

| Variable | Requerida | Descripcion |
|----------|-----------|-------------|
| `GEMINI_API_KEY` | Si* | API Key de Google Gemini (LLM primario) |
| `DATABASE_URL` | No | URL de base de datos (default: SQLite local) |
| `API_KEY` | No | Clave para proteger la API (sin configurar = acceso libre) |
| `CORS_ORIGINS` | No | Origenes permitidos separados por coma (default: `*`) |

*Se requiere al menos un proveedor de LLM. Sin API keys, el sistema usa Ollama local como fallback.

---

## Modulos de Ingenieria

### Torque & Drag
- Modelo Soft String (Johancsik et al.)
- Calculo estacion por estacion: hookload, torque, fuerzas laterales
- Deteccion de pandeo sinusoidal y helicoidal
- Comparacion multi-escenario con graficos superpuestos
- Back-calculation de factores de friccion

### Hidraulica / ECD
- Modelos reologicos: Bingham Plastic y Power Law
- Calculo completo del circuito hidraulico (SPP, ECD, HSI)
- Analisis de surgencia/pistoneo (Surge/Swab)
- Hidraulica de barrena: velocidad de chorro, fuerza de impacto
- 8 graficos interactivos con exportacion

### Pega de Tuberia (Stuck Pipe)
- Arbol de decision diagnostico (differential sticking, keyseating, pack-off, etc.)
- Evaluacion de riesgo con puntaje ponderado
- Calculo de punto libre (Free Point)
- Acciones correctivas recomendadas por mecanismo

### Control de Pozo (Well Control)
- Kill Sheet completo: KMW, ICP, FCP, MAASP
- Metodo Driller y Wait & Weight con schedule de presiones
- Metodo Volumetrico con ciclos
- Bullheading con verificacion de integridad de zapata
- Deteccion automatica de tipo de influjo

---

## Sistema Multi-Agente IA

11 agentes especializados orquestados por `APICoordinator`:

| Agente | Especialidad |
|--------|-------------|
| `drilling_engineer` | Stuck Pipe, Well Control, operaciones de perforacion |
| `mud_engineer` | Hidraulica, ECD, reologia, limpieza de hoyo |
| `well_engineer` | Torque & Drag, cargas, pandeo, trayectoria |
| `geologist` | Formaciones, presion de poro, geopresiones |
| `hydrologist` | Presiones, gradientes, balance hidraulico |

### Analisis Ejecutivo IA
- Analisis gerencial automatizado por modulo
- Soporte bilingue completo (EN/ES)
- Exportacion PDF con metricas clave, hallazgos y recomendaciones
- Toggle de idioma en tiempo real

---

## Analisis de Causa Raiz (RCA)

- Metodologia API RP 585
- Diagrama de Ishikawa (Fishbone) interactivo
- Analisis 5-Whys automatizado
- Generacion de reportes estructurados

---

## API

**55+ endpoints RESTful** documentados automaticamente.

```bash
# Swagger UI
http://localhost:8000/docs

# Ejemplo: listar pozos
curl http://localhost:8000/wells

# Con autenticacion (si API_KEY esta configurado)
curl -H "X-API-Key: tu-clave" http://localhost:8000/wells
```

### Endpoints principales

| Grupo | Ruta | Descripcion |
|-------|------|-------------|
| Pozos | `GET/POST /wells` | CRUD de pozos |
| Torque & Drag | `POST /wells/{id}/torque-drag/calculate` | Calculo T&D |
| Hidraulica | `POST /wells/{id}/hydraulics/calculate` | Calculo hidraulico |
| Stuck Pipe | `POST /stuck-pipe/diagnose/start` | Diagnostico de pega |
| Well Control | `POST /wells/{id}/kill-sheet/calculate` | Kill Sheet |
| AI Analysis | `POST /wells/{id}/<module>/analyze` | Analisis ejecutivo IA |

---

## Testing

```bash
# Suite completa (323+ tests)
pytest tests/ -v

# Solo tests unitarios
pytest tests/unit/ -v

# Solo tests de integracion
pytest tests/integration/ -v
```

Cobertura: motores de calculo, API endpoints, configuracion DB, autenticacion, analisis IA.

---

## Despliegue

### Docker (Produccion)
```bash
docker compose up --build -d
```
Datos persistentes via Docker volume `app-data`.

### Vercel (Demo)
Configurado via `vercel.json`. Frontend como sitio estatico, backend como serverless function.

### On-Premise / Futuro SaaS
```bash
# 1. Cambiar a PostgreSQL
DATABASE_URL=postgresql://user:pass@host:5432/petroleum_expert

# 2. Activar autenticacion
API_KEY=tu-clave-secreta

# 3. Restringir CORS
CORS_ORIGINS=https://tu-dominio.com
```

---

## Estructura del Proyecto

```
petroleum-expert-system/
├── agents/              # 11 agentes especializados de IA
├── config/              # Configuracion de agentes (YAML)
├── frontend/            # React 19 + TypeScript + Vite 7
│   ├── src/components/  # 22+ componentes con graficos
│   └── src/translations/# Soporte bilingue EN/ES
├── middleware/           # Autenticacion API Key
├── models/              # SQLAlchemy ORM (database.py + models_v2.py)
├── orchestrator/        # APICoordinator + ModuleAnalysisEngine
├── utils/               # LLM Gateway + motores de calculo
├── tests/               # 323+ tests (unit + integration)
│   ├── unit/            # Tests de motores y configuracion
│   └── integration/     # Tests de API endpoints
├── api_main.py          # FastAPI — 55+ endpoints
├── Dockerfile           # Multi-stage build (Node + Python)
├── docker-compose.yml   # Orquestacion con volumen persistente
├── requirements.txt     # Dependencias Python
└── .env.example         # Template de variables de entorno
```

---

## Tecnologias

| Capa | Stack |
|------|-------|
| **Backend** | FastAPI + SQLAlchemy + Python 3.13 |
| **Frontend** | React 19 + TypeScript 5.9 + Vite 7 + Tailwind CSS 3.4 |
| **Graficos** | Recharts + Framer Motion |
| **IA** | Gemini 2.5 Flash (primario) + Ollama deepseek-r1:14b (fallback local) |
| **PDF** | html2pdf.js v0.14.0 |
| **Base de datos** | SQLite (default) / PostgreSQL (configurable) |
| **Despliegue** | Docker + Vercel |
| **Testing** | pytest 9.0 (323+ tests) |

---

**PETROEXPERT v5.0** | Sistema Experto de Ingenieria Petrolera
