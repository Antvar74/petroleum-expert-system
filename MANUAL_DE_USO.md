# 📖 Manual de Uso: Sistema Experto Petrolero (Versión 3.0)

Bienvenido. Esta guía te llevará paso a paso por el flujo de trabajo para analizar el caso real **BAKTE-9**.

---

## 🚀 Paso 1: Iniciar la Aplicación
Asegúrate de tener las terminales corriendo (Backend y Frontend).
1.  Abre tu navegador (Chrome recomendado).
2.  Ve a la dirección: `http://localhost:5173`

---

## 📝 Paso 2: Configurar el Caso (Datos Reales)
Verás una pantalla de bienvenida con un formulario técnico. No necesitas llenarlo manualmente.

1.  Busca el enlace pequeño en la esquina inferior derecha del formulario que dice:
    **"Load Real Data (BAKTE-9)"**
2.  **Haz clic en él**.
    *   *Verás cómo el formulario se llena automáticamente:* "Tripping Out", Profundidad 3450 ft, y la descripción clave: `[REAL_DATA:BAKTE-9]`.
    *   Esta "etiqueta" especial le dice al cerebro del sistema que lea el PDF real.
3.  Presiona el botón grande **"INITIATE SPECIALIST ANALYSIS"**.

---

## 🎛️ Paso 3: El Panel de Control (Analysis Dashboard)
Ahora estás en el centro de mando. A la izquierda ves la "Tubería de Especialistas" (Drilling, Mud, Geologist...).

**⚠️ CONFIGURACIÓN CLAVE:**
1.  Mira la esquina superior derecha del panel central.
2.  Busca el interruptor que dice **"Analysis Mode"**.
3.  **ACTÍVALO** (Click para que se ponga Verde/Industrial).
    *   Debe decir: **"Automated (Local LLM via Ollama)"** (Nota: Aunque dice Ollama, en realidad está conectado a **Gemini Cloud** ahora).
    *   *Si lo dejas apagado, tendrás que copiar y pegar manualmente a ChatGPT/Claude.*

---

## 🧠 Paso 4: Consultar a los Expertos
Ahora vamos a interrogar a los agentes uno por uno.

1.  **Agente 1: Drilling Engineer**
    *   El sistema te mostrará "Ready to Consult Drilling Engineer".
    *   Haz clic en el botón **"Run Automated Analysis"**.
    *   *Espera unos segundos...* Verás aparecer el análisis técnico. Lee sus hallazgos iniciales.
    *   Haz clic en "Next Step".

2.  **Agente 2: Mud Engineer (Fluidos)**
    *   Repite el proceso: **"Run Automated Analysis"**.
    *   Este agente leerá el PDF y criticará las propiedades del lodo vs. la formación.

3.  **Agente 3: Geologist (Geólogo)**
    *   Ejecuta el análisis.
    *   Este es crítico: Buscará "shale instability" (inestabilidad de lutitas) en el reporte.

**💡 CONSEJO PRO:** Como estamos usando una cuenta gratuita de Gemini, espera **10-15 segundos** entre cada agente para no saturar el límite de velocidad.

---

## 🏁 Paso 5: Síntesis Final (RCA)
Una vez que todos los especialistas hayan hablado:

1.  Llegarás al paso **"Final Synthesis"**.
2.  Dale clic a **"Run Synthesis"**.
3.  El **RCA Lead Agent** tomará todos los reportes anteriores, los cruzará con la norma **API RP 585**, y escribirá el **Reporte de Investigación de Incidente**.

### Resultado Final
Verás un documento formal con:
*   **Executive Summary**: Qué pasó.
*   **Root Cause**: Por qué pasó (Causa Raíz).
*   **Action Plan**: Qué hacer para que no se repita.

¡Felicidades! Has completado una investigación forense digital completa.
