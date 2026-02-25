import { useState, useEffect, useCallback } from 'react';
import api from '../lib/api';
import { useLanguage } from './useLanguage';
import type { Provider, ProviderOption } from '../types/ai';
import type { AIAnalysisResponse, APIError } from '../types/api';

interface UseAIAnalysisOptions {
  module: string;
  wellId?: number;
  wellName?: string;
}

export function useAIAnalysis({ module, wellId, wellName }: UseAIAnalysisOptions) {
  const [aiAnalysis, setAiAnalysis] = useState<AIAnalysisResponse | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const { language } = useLanguage();
  const [provider, setProvider] = useState<Provider>('auto');
  const [availableProviders, setAvailableProviders] = useState<ProviderOption[]>([
    { id: 'auto', name: 'Auto (Best Available)', name_es: 'Auto (Mejor Disponible)' },
  ]);

  useEffect(() => {
    api.get('/providers')
      .then(res => setAvailableProviders(res.data))
      .catch(() => {});
  }, []);

  const runAnalysis = useCallback(async (resultData: Record<string, unknown>, params: Record<string, unknown>) => {
    setIsAnalyzing(true);
    try {
      const url = wellId
        ? `/wells/${wellId}/${module}/analyze`
        : '/analyze/module';
      const res = await api.post(url, {
        ...(wellId ? {} : { module, well_name: wellName || 'General Analysis' }),
        result_data: resultData,
        params,
        language,
        provider,
      });
      setAiAnalysis(res.data);
    } catch (e: unknown) {
      const err = e as APIError;
      const errMsg = err.response?.data?.detail || err.message || 'Connection error';
      setAiAnalysis({ analysis: `Error: ${errMsg}`, confidence: 'LOW', agent: 'Error', role: 'Error' });
    }
    setIsAnalyzing(false);
  }, [wellId, wellName, module, language, provider]);

  return { aiAnalysis, isAnalyzing, runAnalysis, provider, setProvider, availableProviders, setAiAnalysis };
}
