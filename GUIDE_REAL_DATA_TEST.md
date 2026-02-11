# 🧪 Cómo Probar con Datos Reales (BAKTE-9)

El sistema ha sido actualizado para permitir una prueba completa de "Datos Reales" desde la interfaz gráfica.

## Pasos para la Prueba

1.  **Abre la Aplicación Web**:
    Ve a `http://localhost:5173` en tu navegador.

2.  **Carga los Datos de BAKTE-9**:
    En el formulario principal ("Describe the Operational Problem"), busca el nuevo enlace pequeño en la parte inferior derecha que dice:
    `Load Real Data (BAKTE-9)`
    
    *Al hacer clic, el formulario se llenará automáticamente con:*
    *   **Description**: `[REAL_DATA:BAKTE-9] Analyze the attached daily reports...`
    *   **Depth**: 3450 ft
    *   **Operation**: Tripping Out

3.  **Inicia el Análisis**:
    Haz clic en el botón grande **"Initiate Specialist Analysis"**.

4.  **Activa el Modo Automático (Cloud AI)**:
    En el Dashboard de Análisis:
    1.  Busca el interruptor en la parte superior derecha que dice **"Analysis Mode"**.
    2.  Actívalo (se pondrá verde/industrial). Ahora usará **Gemini 2.5 Flash** (Nube) en lugar de copiar/pegar manual.

5.  **Ejecuta los Agentes**:
    Haz clic en **"Run Automated Analysis"** para cada especialista (Drilling, Mud, Geologist, etc.).
    
    *Observa cómo cada agente genera un análisis profundo basado en el PDF "BAKTE-9 ETAPA 18.5" que el sistema inyecta en segundo plano.*

## ¿Qué está pasando "bajo el capó"?
*   El backend detecta la etiqueta `[REAL_DATA:BAKTE-9]`.
*   Lee el archivo `data/BAKTE-9_ETAPA_18.5.pdf`.
*   Extrae el texto y se lo envía a Gemini junto con tu solicitud.
*   Gemini actúa como el experto (Geólogo, Loderos, etc.) leyendo el reporte real.

¡Disfruta la demostración! 🚀
