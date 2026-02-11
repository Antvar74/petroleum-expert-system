# PETROEXPERT v3.0 - Elite Industrial

Sistema integral de ingeniería y análisis multi-agente para la industria petrolera. De la resolución reactiva de problemas a la generación proactiva de programas técnicos.

## 🎯 Descripción
PETROEXPERT v3.0 "Elite Industrial" es una suite avanzada de ingeniería de pozos que combina el poder de agentes especializados de IA con motores de cálculo técnico. El sistema permite analizar fallas operacionales, visualizar causas raíz y generar programas de perforación y completación de nivel experto, todo operando de manera privada y local.

## 🚀 Características de Clase Mundial (v3.0)

### 1. Inteligencia Artificial de Élite
- **Multi-Agent Specialist Pipeline**: 5 agentes expertos (Perforación, Fluidos, Geología, Trayectoria, Presiones) analizando cada caso.
- **Local LLM First**: Integración nativa con **Ollama** para usar modelos como DeepSeek y Llama 3 localmente, garantizando privacidad de datos y cero costos de API.
- **Modo Automatizado**: Ejecución completa del flujo de análisis con un solo clic.

### 2. Módulo de Análisis de Causa Raíz (RCA)
- **Visualizador Avanzado**: Diagramas de **Ishikawa (Fishbone)** y **5-Whys** dinámicos generados automáticamente a partir del análisis.
- **Reportes Gerenciales**: Exportación de hallazgos en formatos técnicos estructurados.

### 3. Generación Proactiva de Programas
- **DDP (Digital Drilling Program)**: Generación completa de planes de perforación.
- **CP (Completion Program)**: Diseño detallado de terminación de pozos.
- **Workover & Intervention**: Programas detallados para reparaciones mayores.

### 4. Motor de Optimización Técnica
- **Cálculos de Hidráulica**: ECD, caídas de presión y velocidades anulares.
- **Torque & Drag**: Análisis de Hookload y márgenes de sobre-tensión (Soft String Model).
- **Ingesta de Datos**: Soporte para archivos CSV con datos históricos de sensores.

## 🛠️ Arquitectura
- **Backend**: FastAPI (Python) + SQLAlchemy + SQLite.
- **Frontend**: React + Vite + Tailwind CSS + Lucide + Framer Motion.
- **Orquestación**: Sistema de agentes asíncrono con conectores locales y remotos.

## 📋 Requisitos
- Python 3.10+
- Node.js 18+
- [Ollama](https://ollama.com/) (Instalado y ejecutándose con el modelo `deepseek-v2` o `llama3`)

## 🔧 Instalación y Setup

### 1. Backend
```bash
# Instalar dependencias
pip install -r requirements.txt

# Iniciar el servidor API (Puerto 8000)
python api_main.py
```

### 2. Frontend
```bash
cd frontend

# Instalar dependencias
npm installBase

# Iniciar servidor de desarrollo (Puerto 5173)
npm run dev
```

## 📁 Estructura del Proyecto (v3.0)
```
petroleum-expert-system/
├── agents/             # Lógica de agentes especializados
├── orchestrator/       # Coordinación de pipelines e IA
├── models/             # Esquemas de DB (SQLAlchemy) y Pydantic
├── utils/              # Motores de cálculo y conectores LLM
├── analysis_results/   # Exportaciones Markdown/JSON
├── frontend/           # Aplicación React v3.0
├── api_main.py         # Punto de entrada de la API FastAPI
└── README.md           # Este archivo
```

## 🔄 Flujo de Trabajo
1. **Selección de Pozo**: Define el entorno operacional.
2. **Reporte de Problema**: Ingresa parámetros o carga un CSV.
3. **Pipeline de Agentes**: Los expertos analizan y sintetizan una solución.
4. **Visualización RCA**: Genera y revisa diagramas de causa raíz.
5. **Generación Proactiva**: Crea el programa técnico para prevenir futuras fallas.
6. **Optimización**: Valida límites hidráulicos y mecánicos.

## 🔐 Privacidad y Seguridad
- El sistema prioriza el uso de LLMs locales para proteger la propiedad intelectual de los datos operativos.
- No se requiere envío de datos a nubes externas.

---
**PETROEXPERT v3.0 Elite Industrial** | Desarrollado para operaciones de alta complejidad.
