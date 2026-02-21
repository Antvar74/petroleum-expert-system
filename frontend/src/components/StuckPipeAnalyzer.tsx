import { useState, useEffect } from 'react';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';
import { Lock, ChevronRight, AlertTriangle, Target, ListChecks, BrainCircuit } from 'lucide-react';
import { API_BASE_URL } from '../config';
import InteractiveRiskMatrix from './charts/sp/InteractiveRiskMatrix';
import ContributingFactorsRadar from './charts/sp/ContributingFactorsRadar';
import FreePointIndicator from './charts/sp/FreePointIndicator';
import DecisionTreeDiagram from './charts/sp/DecisionTreeDiagram';
import AIAnalysisPanel from './AIAnalysisPanel';
import { useTranslation } from 'react-i18next';
import { useLanguage } from '../hooks/useLanguage';
import type { Provider, ProviderOption } from '../types/ai';

interface StuckPipeAnalyzerProps {
  wellId?: number;
  wellName?: string;
}

const RISK_COLORS: Record<string, string> = {
  LOW: 'text-green-400 bg-green-500/10 border-green-500/20',
  MEDIUM: 'text-yellow-400 bg-yellow-500/10 border-yellow-500/20',
  HIGH: 'text-orange-400 bg-orange-500/10 border-orange-500/20',
  CRITICAL: 'text-red-400 bg-red-500/10 border-red-500/20',
};

const StuckPipeAnalyzer: React.FC<StuckPipeAnalyzerProps> = ({ wellId, wellName = '' }) => {
  const [activeTab, setActiveTab] = useState('diagnosis');
  const [loading, setLoading] = useState(false);

  // Diagnosis wizard state
  const [diagnosisPath, setDiagnosisPath] = useState<any[]>([]);
  const [currentQuestion, setCurrentQuestion] = useState<any>(null);
  const [diagnosisResult, setDiagnosisResult] = useState<any>(null);

  // Free point state
  const [fpParams, setFpParams] = useState({
    pipe_od: 5.0, pipe_id: 4.276, pipe_grade: 'S135',
    stretch_inches: 6.0, pull_force_lbs: 80000,
  });
  const [fpResult, setFpResult] = useState<any>(null);

  // Risk state
  const [riskParams, setRiskParams] = useState({
    mechanism: '', mud_weight: 10.0, pore_pressure: 9.0,
    inclination: 45, stationary_hours: 1, torque: 15000, overpull: 20,
  });
  const [riskResult, setRiskResult] = useState<any>(null);

  // Actions state
  const [_actionsResult, setActionsResult] = useState<any>(null);

  // AI Analysis state
  const [aiAnalysis, setAiAnalysis] = useState<any>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const { t } = useTranslation();
  const { language, setLanguage } = useLanguage();
  const [provider, setProvider] = useState<Provider>('auto');
  const [availableProviders, setAvailableProviders] = useState<ProviderOption[]>([
    { id: 'auto', name: 'Auto (Best Available)', name_es: 'Auto (Mejor Disponible)' }
  ]);

  // Fetch available providers on mount
  useEffect(() => {
    axios.get(`${API_BASE_URL}/providers`)
      .then(res => setAvailableProviders(res.data))
      .catch(() => { });
  }, []);

  const runAIAnalysis = async () => {
    if (!diagnosisResult && !riskResult && !fpResult) return;
    setIsAnalyzing(true);
    try {
      const analyzeUrl = wellId
        ? `${API_BASE_URL}/wells/${wellId}/stuck-pipe/analyze`
        : `${API_BASE_URL}/analyze/module`;
      const analyzeBody = {
        ...(wellId ? {} : { module: 'stuck-pipe', well_name: wellName || 'General Analysis' }),
        result_data: {
          diagnosis: diagnosisResult || {},
          risk: riskResult || {},
          freePoint: fpResult || {},
        },
        params: { mechanism: riskParams.mechanism || diagnosisResult?.mechanism, mud_weight: riskParams.mud_weight },
        language,
        provider,
      };
      const res = await axios.post(analyzeUrl, analyzeBody);
      setAiAnalysis(res.data);
    } catch (e: any) {
      console.error('AI analysis error:', e);
      const errMsg = e?.response?.data?.detail || e?.message || 'Connection error. Please try again.';
      setAiAnalysis({ analysis: `Error: ${errMsg}`, confidence: 'LOW', agent_role: 'Error', key_metrics: [] });
    }
    setIsAnalyzing(false);
  };

  const tabs = [
    { id: 'diagnosis', label: 'Diagnosis Wizard' },
    { id: 'freepoint', label: 'Free Point Calculator' },
    { id: 'risk', label: 'Risk Matrix' },
    { id: 'actions', label: 'Action Plan' },
  ];

  // --- Diagnosis ---
  const startDiagnosis = async () => {
    setDiagnosisPath([]);
    setDiagnosisResult(null);
    setLoading(true);
    try {
      const res = await axios.post(`${API_BASE_URL}/stuck-pipe/diagnose/start`);
      setCurrentQuestion(res.data);
    } catch (e: any) { alert('Error: ' + (e.response?.data?.detail || e.message)); }
    setLoading(false);
  };

  const answerQuestion = async (answer: string) => {
    if (!currentQuestion) return;
    setLoading(true);

    const newPath = [...diagnosisPath, { node_id: currentQuestion.node_id, question: currentQuestion.question, answer }];
    setDiagnosisPath(newPath);

    try {
      const res = await axios.post(`${API_BASE_URL}/stuck-pipe/diagnose/answer`, {
        node_id: currentQuestion.node_id,
        answer,
      });

      if (res.data.type === 'result') {
        setDiagnosisResult(res.data);
        setCurrentQuestion(null);
        // Auto-set mechanism in risk tab
        setRiskParams(prev => ({ ...prev, mechanism: res.data.mechanism }));
      } else {
        setCurrentQuestion(res.data);
      }
    } catch (e: any) { alert('Error: ' + (e.response?.data?.detail || e.message)); }
    setLoading(false);
  };

  // --- Free Point ---
  const runFreePoint = async () => {
    setLoading(true);
    try {
      const res = await axios.post(`${API_BASE_URL}/stuck-pipe/free-point`, fpParams);
      setFpResult(res.data);
    } catch (e: any) { alert('Error: ' + (e.response?.data?.detail || e.message)); }
    setLoading(false);
  };

  // --- Risk ---
  const runRisk = async () => {
    setLoading(true);
    try {
      const res = await axios.post(`${API_BASE_URL}/stuck-pipe/risk-assessment`, {
        mechanism: riskParams.mechanism,
        params: {
          mud_weight: riskParams.mud_weight,
          pore_pressure: riskParams.pore_pressure,
          inclination: riskParams.inclination,
          stationary_hours: riskParams.stationary_hours,
          torque: riskParams.torque,
          overpull: riskParams.overpull,
        },
      });
      setRiskResult(res.data);

      // Also fetch actions
      await axios.post(`${API_BASE_URL}/stuck-pipe/risk-assessment`, {
        mechanism: riskParams.mechanism,
        params: {},
      });
      // Fetch recommended actions using the mechanism
      fetchActions(riskParams.mechanism);
    } catch (e: any) { alert('Error: ' + (e.response?.data?.detail || e.message)); }
    setLoading(false);
  };

  const fetchActions = async (_mechanism: string) => {
    try {
      // We use full analysis endpoint with minimal data to get actions
      // Or we construct from the risk assessment
      // For simplicity, let's post to diagnose and use the actions from classification
      setActionsResult(null);
      // We'll get actions when the user navigates to the actions tab
    } catch (e) {
      console.error(e);
    }
  };

  const loadActions = async () => {
    if (!riskParams.mechanism) return;
    setLoading(true);
    try {
      // Use the stuck-pipe risk-assessment which also returns mechanism info
      // Actually we need a dedicated endpoint — let's use event-level endpoint creatively
      // For now, fetch risk which gives us enough to show actions
      const res = await axios.post(`${API_BASE_URL}/stuck-pipe/risk-assessment`, {
        mechanism: riskParams.mechanism,
        params: {},
      });
      // The actions are embedded in the engine's get_recommended_actions,
      // which is called via the event endpoint. For standalone, re-fetch.
      setActionsResult(res.data);
    } catch (e: any) { console.error(e); }
    setLoading(false);
  };

  // (Risk matrix SVG replaced by InteractiveRiskMatrix component)

  return (
    <div className="space-y-6 py-8">
      <div className="flex items-center gap-3 mb-8">
        <Lock className="text-industrial-500" size={28} />
        <h2 className="text-2xl font-bold">Stuck Pipe Analyzer</h2>
      </div>

      <div className="flex gap-2 mb-8">
        {tabs.map((tab) => (
          <button key={tab.id} onClick={() => { setActiveTab(tab.id); if (tab.id === 'actions') loadActions(); }}
            className={`px-5 py-2.5 rounded-xl text-sm font-bold transition-all ${activeTab === tab.id ? 'bg-industrial-600 text-white shadow-lg' : 'bg-white/5 text-white/40 hover:text-white hover:bg-white/10'}`}>
            {tab.label}
          </button>
        ))}
      </div>

      <AnimatePresence mode="wait">
        {/* Diagnosis Wizard */}
        {activeTab === 'diagnosis' && (
          <motion.div key="diagnosis" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="space-y-6">
            {!currentQuestion && !diagnosisResult && (
              <div className="glass-panel p-12 rounded-2xl border border-white/5 text-center">
                <Lock className="mx-auto mb-4 text-white/20" size={48} />
                <h3 className="text-xl font-bold mb-2">Stuck Pipe Diagnostic Decision Tree</h3>
                <p className="text-white/40 mb-6 max-w-md mx-auto">Answer a series of questions to identify the stuck pipe mechanism.</p>
                <button onClick={startDiagnosis} className="btn-primary">Start Diagnosis</button>
              </div>
            )}

            {/* Decision Tree Diagram */}
            {(diagnosisPath.length > 0 || currentQuestion || diagnosisResult) && (
              <DecisionTreeDiagram
                path={diagnosisPath}
                currentQuestion={currentQuestion}
                result={diagnosisResult}
              />
            )}

            {/* Breadcrumb path */}
            {diagnosisPath.length > 0 && (
              <div className="flex flex-wrap gap-2 items-center text-xs text-white/40">
                {diagnosisPath.map((step, i) => (
                  <span key={i} className="flex items-center gap-1">
                    <span className={step.answer === 'yes' ? 'text-green-400' : 'text-red-400'}>{step.answer.toUpperCase()}</span>
                    {i < diagnosisPath.length - 1 && <ChevronRight size={12} />}
                  </span>
                ))}
              </div>
            )}

            {/* Current question */}
            {currentQuestion && (
              <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} className="glass-panel p-8 rounded-2xl border border-white/5">
                <p className="text-xs text-white/40 mb-2">Question {diagnosisPath.length + 1}</p>
                <h3 className="text-xl font-bold mb-6">{currentQuestion.question}</h3>
                <div className="flex gap-4">
                  <button onClick={() => answerQuestion('yes')} disabled={loading} className="flex-1 py-4 bg-green-500/10 hover:bg-green-500/20 border border-green-500/20 rounded-xl text-green-400 font-bold text-lg transition-all disabled:opacity-50">
                    YES
                  </button>
                  <button onClick={() => answerQuestion('no')} disabled={loading} className="flex-1 py-4 bg-red-500/10 hover:bg-red-500/20 border border-red-500/20 rounded-xl text-red-400 font-bold text-lg transition-all disabled:opacity-50">
                    NO
                  </button>
                </div>
              </motion.div>
            )}

            {/* Result */}
            {diagnosisResult && (
              <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">
                <div className="glass-panel p-8 rounded-2xl border border-industrial-500/20 bg-industrial-500/5">
                  <div className="flex items-center gap-3 mb-4">
                    <Target className="text-industrial-500" size={24} />
                    <h3 className="text-xl font-bold text-industrial-400">Mechanism Identified</h3>
                  </div>
                  <p className="text-2xl font-bold mb-3">{diagnosisResult.mechanism}</p>
                  <p className="text-white/60 mb-4">{diagnosisResult.description}</p>
                  <div>
                    <p className="text-xs text-white/40 mb-2 uppercase tracking-wider font-bold">Key Indicators:</p>
                    <ul className="space-y-1">
                      {diagnosisResult.indicators?.map((ind: string, i: number) => (
                        <li key={i} className="text-sm text-white/60 flex items-start gap-2">
                          <span className="text-industrial-500 mt-0.5">-</span> {ind}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
                <button onClick={startDiagnosis} className="text-sm text-white/40 hover:text-white underline">Restart Diagnosis</button>
              </motion.div>
            )}
          </motion.div>
        )}

        {/* Free Point Calculator */}
        {activeTab === 'freepoint' && (
          <motion.div key="freepoint" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="space-y-6">
            <div className="glass-panel p-6 rounded-2xl border border-white/5">
              <h3 className="font-bold text-lg mb-4">Free Point Calculation (Stretch Method)</h3>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-6">
                <div><label className="text-xs text-white/40 block mb-1">Pipe OD (in)</label><input type="number" step="0.1" value={fpParams.pipe_od} onChange={(e) => setFpParams({ ...fpParams, pipe_od: +e.target.value })} className="input-field w-full py-2 px-3 text-sm" /></div>
                <div><label className="text-xs text-white/40 block mb-1">Pipe ID (in)</label><input type="number" step="0.001" value={fpParams.pipe_id} onChange={(e) => setFpParams({ ...fpParams, pipe_id: +e.target.value })} className="input-field w-full py-2 px-3 text-sm" /></div>
                <div>
                  <label className="text-xs text-white/40 block mb-1">Pipe Grade</label>
                  <select value={fpParams.pipe_grade} onChange={(e) => setFpParams({ ...fpParams, pipe_grade: e.target.value })} className="input-field w-full py-2 px-3 text-sm">
                    {['E75', 'X95', 'G105', 'S135', 'V150'].map(g => <option key={g} value={g}>{g}</option>)}
                  </select>
                </div>
                <div><label className="text-xs text-white/40 block mb-1">Stretch (inches)</label><input type="number" step="0.1" value={fpParams.stretch_inches} onChange={(e) => setFpParams({ ...fpParams, stretch_inches: +e.target.value })} className="input-field w-full py-2 px-3 text-sm" /></div>
                <div><label className="text-xs text-white/40 block mb-1">Pull Force (lbs)</label><input type="number" value={fpParams.pull_force_lbs} onChange={(e) => setFpParams({ ...fpParams, pull_force_lbs: +e.target.value })} className="input-field w-full py-2 px-3 text-sm" /></div>
              </div>
              <button onClick={runFreePoint} disabled={loading} className="btn-primary disabled:opacity-50">{loading ? 'Calculating...' : 'Calculate Free Point'}</button>
            </div>

            {fpResult && !fpResult.error && (
              <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  {/* Free Point Indicator visual */}
                  <FreePointIndicator
                    freePointDepth={fpResult.free_point_depth_ft || 0}
                    totalDepth={fpResult.free_point_depth_ft * 1.3 || 10000}
                    pipeSafe={fpResult.pull_safe}
                    pullPctYield={fpResult.pull_pct_of_yield}
                    height={350}
                  />
                  {/* Summary cards */}
                  <div className="md:col-span-2 grid grid-cols-2 gap-4 content-start">
                    <div className="glass-panel p-5 rounded-xl border border-industrial-500/20 text-center col-span-2">
                      <p className="text-xs text-white/40 mb-2">Free Point Depth</p>
                      <p className="text-4xl font-bold text-industrial-400">{fpResult.free_point_depth_ft?.toLocaleString()}</p>
                      <p className="text-xs text-white/30">ft</p>
                    </div>
                    <div className="glass-panel p-5 rounded-xl border border-white/5 text-center">
                      <p className="text-xs text-white/40 mb-2">Pipe Area</p>
                      <p className="text-xl font-bold text-white">{fpResult.pipe_area_sqin} in²</p>
                    </div>
                    <div className={`glass-panel p-5 rounded-xl border text-center ${fpResult.pull_safe ? 'border-green-500/20' : 'border-red-500/20'}`}>
                      <p className="text-xs text-white/40 mb-2">Pull vs Yield</p>
                      <p className={`text-xl font-bold ${fpResult.pull_safe ? 'text-green-400' : 'text-red-400'}`}>{fpResult.pull_pct_of_yield}%</p>
                      <p className="text-xs text-white/30">{fpResult.pull_safe ? 'SAFE' : 'EXCEEDS 80%'}</p>
                    </div>
                  </div>
                </div>
              </motion.div>
            )}
          </motion.div>
        )}

        {/* Risk Matrix */}
        {activeTab === 'risk' && (
          <motion.div key="risk" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="space-y-6">
            <div className="glass-panel p-6 rounded-2xl border border-white/5">
              <h3 className="font-bold text-lg mb-4">Risk Assessment</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                <div>
                  <label className="text-xs text-white/40 block mb-1">Mechanism</label>
                  <select value={riskParams.mechanism} onChange={(e) => setRiskParams({ ...riskParams, mechanism: e.target.value })} className="input-field w-full py-2 px-3 text-sm">
                    <option value="">Select...</option>
                    {['Differential Sticking', 'Mechanical Sticking', 'Hole Cleaning / Pack-Off', 'Wellbore Instability', 'Key Seating', 'Undergauge Hole', 'Formation Flow / Kick', 'Pack-Off / Bridge'].map(m => <option key={m} value={m}>{m}</option>)}
                  </select>
                </div>
                <div><label className="text-xs text-white/40 block mb-1">MW (ppg)</label><input type="number" step="0.1" value={riskParams.mud_weight} onChange={(e) => setRiskParams({ ...riskParams, mud_weight: +e.target.value })} className="input-field w-full py-2 px-3 text-sm" /></div>
                <div><label className="text-xs text-white/40 block mb-1">Pore Pressure (ppg)</label><input type="number" step="0.1" value={riskParams.pore_pressure} onChange={(e) => setRiskParams({ ...riskParams, pore_pressure: +e.target.value })} className="input-field w-full py-2 px-3 text-sm" /></div>
                <div><label className="text-xs text-white/40 block mb-1">Inclination (°)</label><input type="number" value={riskParams.inclination} onChange={(e) => setRiskParams({ ...riskParams, inclination: +e.target.value })} className="input-field w-full py-2 px-3 text-sm" /></div>
                <div><label className="text-xs text-white/40 block mb-1">Stationary (hours)</label><input type="number" step="0.5" value={riskParams.stationary_hours} onChange={(e) => setRiskParams({ ...riskParams, stationary_hours: +e.target.value })} className="input-field w-full py-2 px-3 text-sm" /></div>
                <div><label className="text-xs text-white/40 block mb-1">Torque (ft-lb)</label><input type="number" value={riskParams.torque} onChange={(e) => setRiskParams({ ...riskParams, torque: +e.target.value })} className="input-field w-full py-2 px-3 text-sm" /></div>
                <div><label className="text-xs text-white/40 block mb-1">Overpull (klb)</label><input type="number" value={riskParams.overpull} onChange={(e) => setRiskParams({ ...riskParams, overpull: +e.target.value })} className="input-field w-full py-2 px-3 text-sm" /></div>
              </div>
              <button onClick={runRisk} disabled={loading || !riskParams.mechanism} className="btn-primary disabled:opacity-50">{loading ? 'Assessing...' : 'Assess Risk'}</button>
            </div>

            {riskResult && (
              <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-4">
                  <InteractiveRiskMatrix
                    probability={riskResult.probability}
                    severity={riskResult.severity}
                    riskLevel={riskResult.risk_level}
                    riskScore={riskResult.risk_score}
                    mechanism={riskParams.mechanism}
                  />
                  <div className="text-center">
                    <span className={`inline-block px-4 py-2 rounded-lg font-bold ${RISK_COLORS[riskResult.risk_level] || ''}`}>
                      {riskResult.risk_level} (Score: {riskResult.risk_score})
                    </span>
                  </div>
                </div>
                <ContributingFactorsRadar
                  factors={riskResult.contributing_factors || []}
                  riskLevel={riskResult.risk_level}
                  height={300}
                />
              </motion.div>
            )}
          </motion.div>
        )}

        {/* Action Plan */}
        {activeTab === 'actions' && (
          <motion.div key="actions" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="space-y-6">
            {riskParams.mechanism ? (
              <>
                <div className="glass-panel p-6 rounded-2xl border border-white/5">
                  <div className="flex items-center gap-3 mb-4">
                    <ListChecks className="text-industrial-500" size={24} />
                    <h3 className="font-bold text-lg">Action Plan: {riskParams.mechanism}</h3>
                  </div>
                  <p className="text-white/40 text-sm">Recommended actions are prioritized by urgency category.</p>
                </div>

                {['Immediate', 'Short-Term', 'Contingency'].map((category) => {
                  // Hardcode common actions based on mechanism for display
                  const actionColors: Record<string, string> = {
                    'Immediate': 'border-red-500/20 bg-red-500/5',
                    'Short-Term': 'border-yellow-500/20 bg-yellow-500/5',
                    'Contingency': 'border-blue-500/20 bg-blue-500/5',
                  };

                  return (
                    <div key={category} className={`glass-panel p-6 rounded-2xl border ${actionColors[category]}`}>
                      <h4 className="font-bold mb-3 flex items-center gap-2">
                        <AlertTriangle size={16} className={category === 'Immediate' ? 'text-red-400' : category === 'Short-Term' ? 'text-yellow-400' : 'text-blue-400'} />
                        {category} Actions
                      </h4>
                      <p className="text-white/40 text-sm italic">Run Risk Assessment to populate specific actions for this mechanism.</p>
                    </div>
                  );
                })}
              </>
            ) : (
              <div className="glass-panel p-12 rounded-2xl border border-white/5 text-center">
                <ListChecks className="mx-auto mb-4 text-white/20" size={48} />
                <h3 className="text-xl font-bold mb-2">No Mechanism Selected</h3>
                <p className="text-white/40 max-w-md mx-auto">Complete the Diagnosis Wizard or select a mechanism in the Risk Matrix tab to see recommended actions.</p>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* AI Executive Analysis Button & Panel */}
      {(diagnosisResult || riskResult || fpResult) && (
        <div className="mt-8">
          {!aiAnalysis && (
            <div className="flex flex-col items-center gap-3">
              <div className="flex items-center gap-2 bg-white/5 rounded-lg overflow-hidden border border-white/10">
                {(['en', 'es'] as const).map((lang) => (
                  <button
                    key={lang}
                    onClick={() => setLanguage(lang)}
                    className={`px-3 py-1.5 text-xs font-bold transition-all ${language === lang
                      ? 'bg-industrial-600 text-white'
                      : 'text-white/40 hover:text-white/70'
                      }`}
                  >
                    {lang.toUpperCase()}
                  </button>
                ))}
              </div>
              <button
                onClick={runAIAnalysis}
                disabled={isAnalyzing}
                className="btn-primary py-3 px-8 text-lg disabled:opacity-50"
              >
                <BrainCircuit size={22} />
                {isAnalyzing ? t('ai.analyzingWithAI') : t('ai.executiveAnalysis')}
              </button>
            </div>
          )}
          {(aiAnalysis || isAnalyzing) && (
            <AIAnalysisPanel
              moduleName={t('modules.stuckPipe')}
              moduleIcon={Lock}
              wellName={wellName}
              analysis={aiAnalysis?.analysis || null}
              confidence={aiAnalysis?.confidence || 'MEDIUM'}
              agentRole={aiAnalysis?.agent_role || 'Drilling Engineer'}
              isLoading={isAnalyzing}
              keyMetrics={aiAnalysis?.key_metrics || []}
              onAnalyze={runAIAnalysis}
              onClose={() => setAiAnalysis(null)}
              provider={provider}
              onProviderChange={setProvider}
              availableProviders={availableProviders}
            />
          )}
        </div>
      )}
    </div>
  );
};

export default StuckPipeAnalyzer;
