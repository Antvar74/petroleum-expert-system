# 🚀 Inicio Rápido - Petroleum Expert System

## ⚡ Configuración en 3 pasos

### 1️⃣ Instalar dependencias

```bash
cd /Users/antvar/Downloads/petroleum-expert-system
pip install -r requirements.txt
```

### 2️⃣ Configurar API Key

```bash
# Copia el archivo de ejemplo
cp .env.example .env

# Edita .env y agrega tu API key
nano .env
```

Agrega tu API key:
```
ANTHROPIC_API_KEY=sk-ant-api03-tu-key-aqui
```

### 3️⃣ Ejecutar

```bash
python main.py
```

## 📝 Uso Básico

### Menú Interactivo
```bash
python main.py
```

Te mostrará:
```
1. Differential Sticking en Zona Permeable
2. Pack-off por Limpieza Deficiente
3. Keyseat Mecánico
```

### Ejecución Directa
```bash
python main.py 1  # Analiza caso 1
python main.py 2  # Analiza caso 2
python main.py 3  # Analiza caso 3
```

## 📊 Resultados

Los resultados se guardan automáticamente en:
```
analysis_results/
├── WELL-A-001_20250208_143022.json
└── WELL-A-001_20250208_143022.md
```

- **JSON**: Datos estructurados para integración
- **Markdown**: Reporte técnico legible

## 🔍 ¿Qué hace el sistema?

1. **Analiza el problema** con 5 especialistas de IA
2. **Genera síntesis integrada** unificando todos los hallazgos
3. **Calcula niveles de confianza** por especialista y global
4. **Exporta reportes** en JSON y Markdown

## 🎯 Especialistas Disponibles

- 🔧 **Drilling Engineer**: Liderazgo operacional
- 💧 **Mud Engineer**: Fluidos e hidráulica
- 🪨 **Geologist**: Formaciones y estabilidad
- 📐 **Well Engineer**: Trayectorias y diseño
- 💦 **Hydrologist**: Presiones y ventana operativa

## ⚙️ Workflows

- **standard**: Análisis completo (5 agentes)
- **quick_differential**: Rápido para differential sticking
- **quick_mechanical**: Rápido para problemas mecánicos

## 🆘 Troubleshooting

### Error: "ANTHROPIC_API_KEY no está configurada"
✅ Revisa que el archivo `.env` existe y contiene tu API key

### Error: "Module not found"
✅ Ejecuta: `pip install -r requirements.txt`

### Los resultados no aparecen
✅ Revisa la carpeta `analysis_results/`

## 📞 Siguientes Pasos

1. ✅ Prueba los 3 casos de ejemplo
2. 📖 Lee el `README.md` completo
3. 🔧 Personaliza workflows en `config/agents_config.yaml`
4. 💡 Crea tus propios casos de análisis

---

**¿Listo?** → `python main.py` 🚀
