export type Language = 'en' | 'es';
export type Provider = 'auto' | 'gemini' | 'ollama';
export interface ProviderOption { id: Provider; name: string; name_es: string; }

export const LOCALE_MAP: Record<Language, string> = {
  en: 'en-US',
  es: 'es-MX',
};

export const t = {
  en: {
    // AIAnalysisPanel
    aiExecutiveAnalysis: 'AI Executive Analysis',
    analyzingWithAI: 'Analyzing with AI...',
    analyzingWithAgent: 'Analyzing with AI agent',
    noAnalysis: 'No analysis available.',
    exportPdf: 'PDF',
    generatingPdf: 'Generating...',
    share: 'Share',
    regenerate: 'Regenerate analysis',
    sharingNotSupported: 'Sharing is not supported on this device/browser.',
    filesNotSupported: 'System does not support sharing files.',
    reportFor: 'Executive analysis report for',
    // ExecutiveReport
    executiveReport: 'Executive Report',
    well: 'Well',
    date: 'Date',
    analyst: 'Analyst',
    confidence: 'Confidence',
    kpiTitle: 'Key Performance Indicators',
    confidential: 'Confidential',
    generatedBy: 'Generated automatically by AI Agent',
    expertSystem: 'PETROEXPERT Expert System',
    // Language selector
    language: 'Language',
    // Provider selector
    provider: 'Provider',
    providerAuto: 'Auto (Best Available)',
    providerGemini: 'Google Gemini',
    providerOllama: 'Ollama (Local)',
    // Module names
    torqueDrag: 'Torque & Drag',
    hydraulicsECD: 'Hydraulics / ECD',
    stuckPipe: 'Stuck Pipe',
    wellControl: 'Well Control',
  },
  es: {
    aiExecutiveAnalysis: 'Análisis Ejecutivo IA',
    analyzingWithAI: 'Analizando con IA...',
    analyzingWithAgent: 'Analizando con agente IA',
    noAnalysis: 'No hay análisis disponible.',
    exportPdf: 'PDF',
    generatingPdf: 'Generando...',
    share: 'Compartir',
    regenerate: 'Regenerar análisis',
    sharingNotSupported: 'Compartir no está soportado en este dispositivo/navegador.',
    filesNotSupported: 'El sistema no soporta compartir archivos.',
    reportFor: 'Reporte ejecutivo de análisis para',
    executiveReport: 'Reporte Ejecutivo',
    well: 'Pozo',
    date: 'Fecha',
    analyst: 'Analista',
    confidence: 'Confianza',
    kpiTitle: 'Indicadores Clave de Desempeño',
    confidential: 'Confidencial',
    generatedBy: 'Generado automáticamente por Agente IA',
    expertSystem: 'PETROEXPERT Sistema Experto',
    language: 'Idioma',
    // Provider selector
    provider: 'Proveedor',
    providerAuto: 'Auto (Mejor Disponible)',
    providerGemini: 'Google Gemini',
    providerOllama: 'Ollama (Local)',
    // Module names
    torqueDrag: 'Torque y Arrastre',
    hydraulicsECD: 'Hidráulica / ECD',
    stuckPipe: 'Tubería Pegada',
    wellControl: 'Control de Pozo',
  },
} as const;
