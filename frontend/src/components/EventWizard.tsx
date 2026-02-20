import React, { useState } from 'react';
import { Upload, Check, ArrowRight, ArrowLeft as ArrowLeftIcon, Activity, PenTool, Play, AlertTriangle } from 'lucide-react';
import axios from 'axios';
import { API_BASE_URL } from '../config';
import { useToast } from './ui/Toast';

interface EventWizardProps {
    onComplete: (eventData: any) => void;
    onCancel: () => void;
}

const PHASES = [
    { id: 'drilling', label: 'Perforación', icon: Activity },
    { id: 'completion', label: 'Completación', icon: Check },
    { id: 'workover', label: 'Workover', icon: PenTool },
];

const EVENT_TYPES: Record<string, { id: string; label: string; family: string }[]> = {
    drilling: [
        { id: 'stuck_pipe', label: 'Pega de Tubería', family: 'mechanics' },
        { id: 'lost_circulation', label: 'Pérdida de Circulación', family: 'fluids' },
        { id: 'kick', label: 'Kick / Influjo', family: 'fluids' },
        { id: 'bha_failure', label: 'Falla de BHA', family: 'mechanics' },
        { id: 'torque_drag', label: 'Torque/Drag Excesivo', family: 'mechanics' },
        { id: 'severe_vibration', label: 'Vibración Severa', family: 'mechanics' },
        { id: 'wellbore_instability', label: 'Inestabilidad del Hoyo', family: 'well' },
        { id: 'other', label: 'Otro', family: 'well' },
    ],
    completion: [
        { id: 'perforation_failure', label: 'Falla de Cañoneo', family: 'mechanics' },
        { id: 'formation_damage', label: 'Daño de Formación', family: 'well' },
        { id: 'sand_production', label: 'Producción de Arena', family: 'well' },
        { id: 'packer_failure', label: 'Falla de Packer', family: 'mechanics' },
        { id: 'gravel_pack_failure', label: 'Falla de Empaque', family: 'mechanics' },
        { id: 'other', label: 'Otro', family: 'well' },
    ],
    workover: [
        { id: 'ct_failure', label: 'Falla de Coiled Tubing', family: 'mechanics' },
        { id: 'bop_failure', label: 'Falla de BOP', family: 'control' },
        { id: 'stuck_string', label: 'Atascamiento', family: 'mechanics' },
        { id: 'surface_equipment', label: 'Falla de Equipo Superficie', family: 'mechanics' },
        { id: 'other', label: 'Otro', family: 'well' },
    ],
};

// Family labels for display (auto-inferred, not manually selected)
const FAMILY_LABELS: Record<string, string> = {
    well: 'Pozo / Geomecánica',
    fluids: 'Fluidos / Presión',
    mechanics: 'Sarta / Mecánicos',
    control: 'Control de Pozo',
    human: 'Factores Humanos',
};

const EventWizard: React.FC<EventWizardProps> = ({ onComplete, onCancel }) => {
    const { addToast } = useToast();
    const [step, setStep] = useState(1);
    const [phase, setPhase] = useState<string | null>(null);
    const [eventType, setEventType] = useState<string | null>(null);
    const [files, setFiles] = useState<File[]>([]);
    const [isExtracting, setIsExtracting] = useState(false);
    const [extractedData, setExtractedData] = useState<any>(null);
    const [selectedAgents, setSelectedAgents] = useState<string[]>([]);
    const [leaderAgent, setLeaderAgent] = useState<string | null>(null);
    const [availableAgents, setAvailableAgents] = useState<any[]>([]);

    // Auto-infer family from event type selection
    const inferredFamily = React.useMemo(() => {
        if (!phase || !eventType) return null;
        const types = EVENT_TYPES[phase] || [];
        const match = types.find(t => t.id === eventType);
        return match?.family || 'well';
    }, [phase, eventType]);

    React.useEffect(() => {
        // Fetch agents on mount
        axios.get(`${API_BASE_URL}/agents`)
            .then(res => {
                setAvailableAgents(res.data);
                // Default to empty selection (User request)
                setSelectedAgents([]);
            })
            .catch(err => console.error("Failed to fetch agents:", err));
    }, []);

    const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files.length > 0) {
            const selectedFiles = Array.from(e.target.files);

            // Validation
            if (selectedFiles.length > 5) {
                addToast("Máximo 5 archivos permitidos.", 'warning');
                return;
            }

            const totalSize = selectedFiles.reduce((acc, file) => acc + file.size, 0);
            if (totalSize > 10 * 1024 * 1024) { // 10MB
                addToast("El tamaño total excede los 10MB.", 'warning');
                return;
            }

            setFiles(selectedFiles);
            setIsExtracting(true);

            const formData = new FormData();
            selectedFiles.forEach(file => {
                formData.append('files', file); // Note: Backend expects 'files' list
            });

            try {
                // Call Extraction Endpoint
                const response = await axios.post(`${API_BASE_URL}/events/extract`, formData, {
                    headers: { 'Content-Type': 'multipart/form-data' }
                });
                setExtractedData(response.data);
            } catch (error) {
                console.error("Extraction error:", error);
                addToast("Error al extraer datos. Ingrese los parámetros manualmente.", 'error');
            } finally {
                setIsExtracting(false);
            }
        }
    };

    const handleConfirm = () => {
        // Move to Agent Selection Step instead of completing immediately
        setStep(3);
    };

    const handleAgentToggle = (agentId: string) => {
        const isSelected = selectedAgents.includes(agentId);
        let newSelection;

        if (isSelected) {
            newSelection = selectedAgents.filter(id => id !== agentId);
            if (leaderAgent === agentId) setLeaderAgent(null);
        } else {
            newSelection = [...selectedAgents, agentId];
            if (newSelection.length === 1) setLeaderAgent(agentId);
        }

        setSelectedAgents(newSelection);
    };

    const renderStepIndicator = () => (
        <div className="flex items-center justify-center gap-2 mb-8">
            {[
                { num: 1, label: 'Identificación' },
                { num: 2, label: 'Datos' },
                { num: 3, label: 'Especialistas' },
            ].map((s, i) => (
                <React.Fragment key={s.num}>
                    <div className="flex flex-col items-center gap-1">
                        <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold border-2 transition-all ${
                            step === s.num ? 'border-ibm-blue-500 bg-ibm-blue-500/20 text-ibm-blue-400' :
                            step > s.num ? 'border-green-500 bg-green-500/20 text-green-400' :
                            'border-white/20 bg-white/5 text-white/30'
                        }`}>
                            {step > s.num ? <Check size={14} /> : s.num}
                        </div>
                        <span className={`text-xs ${step === s.num ? 'text-ibm-blue-400' : step > s.num ? 'text-green-400' : 'text-white/30'}`}>
                            {s.label}
                        </span>
                    </div>
                    {i < 2 && <div className={`w-16 h-0.5 mb-5 ${step > s.num ? 'bg-green-500' : 'bg-white/10'}`} />}
                </React.Fragment>
            ))}
        </div>
    );

    const renderStep1 = () => (
        <div className="space-y-6 animate-fadeIn">
            <h3 className="text-xl font-bold text-white mb-4">1. Identificación del Evento</h3>

            <div className="space-y-4">
                <label className="text-sm text-ibm-gray-300">Fase Operativa</label>
                <div className="grid grid-cols-3 gap-4">
                    {PHASES.map((p) => (
                        <button
                            key={p.id}
                            onClick={() => { setPhase(p.id); setEventType(null); }}
                            className={`p-4 rounded-lg border flex flex-col items-center gap-2 transition-all ${phase === p.id
                                ? 'bg-ibm-blue-600/20 border-ibm-blue-500 text-white'
                                : 'bg-white/5 border-white/10 text-white/50 hover:bg-white/10'
                                }`}
                        >
                            <p.icon size={24} />
                            <span className="font-medium">{p.label}</span>
                        </button>
                    ))}
                </div>
            </div>

            {phase && (
                <div className="space-y-4 animate-fadeIn">
                    <label className="text-sm text-ibm-gray-300">Tipo de Evento</label>
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                        {(EVENT_TYPES[phase] || []).map((et) => (
                            <button
                                key={et.id}
                                onClick={() => setEventType(et.id)}
                                className={`p-3 rounded-lg border text-left transition-all ${eventType === et.id
                                    ? 'bg-ibm-blue-600/20 border-ibm-blue-500 text-white'
                                    : 'bg-white/5 border-white/10 text-white/50 hover:bg-white/10'
                                    }`}
                            >
                                <div className="font-medium text-sm">{et.label}</div>
                            </button>
                        ))}
                    </div>
                </div>
            )}

            {/* Auto-inferred family shown as read-only chip */}
            {phase && eventType && inferredFamily && (
                <div className="animate-fadeIn flex items-center gap-3 px-4 py-3 rounded-lg bg-white/5 border border-white/10">
                    <span className="text-xs text-white/40 uppercase tracking-wider">Familia:</span>
                    <span className="text-sm text-ibm-blue-400 font-medium">{FAMILY_LABELS[inferredFamily] || inferredFamily}</span>
                    <span className="text-[10px] text-white/20 ml-auto italic">auto-clasificado</span>
                </div>
            )}

            <div className="flex justify-end pt-6">
                <button
                    onClick={onCancel}
                    className="mr-auto text-white/50 hover:text-white px-4 py-2"
                >
                    Cancelar
                </button>

                <button
                    disabled={!phase || !eventType}
                    onClick={() => setStep(2)}
                    className="bg-ibm-blue-600 hover:bg-ibm-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white px-6 py-2 rounded flex items-center gap-2 transition-colors"
                >
                    Siguiente <ArrowRight size={16} />
                </button>
            </div>
        </div>
    );

    const renderStep2 = () => (
        <div className="space-y-6 animate-fadeIn">
            <h3 className="text-xl font-bold text-white mb-4">2. Captura de Datos Inteligente</h3>

            {!extractedData ? (
                <>
                    <div className="border-2 border-dashed border-white/20 rounded-xl p-12 text-center hover:border-ibm-blue-500/50 transition-colors bg-white/5">
                        <input
                            type="file"
                            id="file-upload"
                            className="hidden"
                            accept=".pdf,.csv,.txt,.md"
                            multiple
                            onChange={handleFileUpload}
                            disabled={isExtracting}
                        />
                        <label htmlFor="file-upload" className={`flex flex-col items-center gap-4 ${isExtracting ? 'pointer-events-none' : 'cursor-pointer'}`}>
                            {isExtracting ? (
                                <>
                                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-ibm-blue-500"></div>
                                    <div className="text-ibm-blue-300 animate-pulse">Analizando documentos con IA...</div>
                                </>
                            ) : (
                                <>
                                    <div className="p-4 bg-ibm-blue-500/10 rounded-full text-ibm-blue-400">
                                        <Upload size={32} />
                                    </div>
                                    <div>
                                        <div className="text-lg font-medium text-white">Sube Reportes Diarios (DDR) o PDFs</div>
                                        <div className="text-sm text-white/40 mt-1">Soporta PDF, CSV, TXT, MD</div>
                                        <div className="text-xs text-yellow-500/80 mt-2 font-mono border border-yellow-500/20 bg-yellow-500/5 px-2 py-1 rounded inline-block">
                                            Max 5 archivos o 10MB total. Se procesaran los primeros 15k caracteres.
                                        </div>
                                    </div>
                                </>
                            )}
                        </label>
                    </div>
                    <div className="flex justify-between mt-4">
                        <button
                            onClick={() => setStep(1)}
                            className="text-white/50 hover:text-white px-4 py-2 flex items-center gap-2"
                        >
                            <ArrowLeftIcon size={16} /> Atrás
                        </button>
                        <button
                            onClick={() => {
                                setExtractedData({});
                                setStep(3);
                            }}
                            className="text-sm text-white/40 hover:text-white transition-colors"
                        >
                            Omitir (Continuar sin datos)
                        </button>
                    </div>
                </>
            ) : (
                <div className="space-y-6">
                    <div className="bg-green-500/10 border border-green-500/20 p-4 rounded-lg flex items-center gap-3 text-green-400">
                        <Check size={20} />
                        <div className="flex-1">
                            <div className="font-bold">Datos Extraídos Exitosamente</div>
                            <div className="text-xs opacity-80 mb-1">Por favor verifica los valores detectados automáticamente.</div>
                            <div className="flex flex-wrap gap-2">
                                {files.map((f, i) => (
                                    <span key={i} className="text-xs bg-green-500/20 px-2 py-0.5 rounded text-green-300 border border-green-500/30">
                                        {f.name} ({(f.size / 1024).toFixed(1)} KB)
                                    </span>
                                ))}
                            </div>
                        </div>
                        <button
                            onClick={() => {
                                setExtractedData(null);
                                setFiles([]);
                            }}
                            className="ml-auto text-xs underline hover:text-green-300 whitespace-nowrap"
                        >
                            Re-subir
                        </button>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        {Object.entries(extractedData).map(([key, value]) => {
                            if (key === 'operation_summary') return null;
                            return (
                                <div key={key} className="bg-white/5 p-3 rounded border border-white/10">
                                    <label className="text-xs text-white/40 uppercase block mb-1">{key.replace(/_/g, ' ')}</label>
                                    <input
                                        type="text"
                                        value={(value as string) || ''}
                                        onChange={(e) => setExtractedData({ ...extractedData, [key]: e.target.value })}
                                        className="bg-transparent text-white font-mono w-full focus:outline-none"
                                    />
                                </div>
                            );
                        })}
                    </div>

                    {extractedData.operation_summary && (
                        <div className="bg-white/5 p-4 rounded border border-white/10">
                            <label className="text-xs text-white/40 uppercase block mb-1">Resumen Operacional</label>
                            <p className="text-white/80 text-sm">{extractedData.operation_summary}</p>
                        </div>
                    )}

                    <div className="flex justify-between pt-6">
                        <button
                            onClick={() => setStep(1)}
                            className="text-white/50 hover:text-white px-4 py-2"
                        >
                            Atrás
                        </button>
                        <button
                            onClick={handleConfirm}
                            className="bg-ibm-blue-600 hover:bg-ibm-blue-700 text-white px-6 py-2 rounded flex items-center gap-2"
                        >
                            Confirmar y Analizar <ArrowRight size={16} />
                        </button>
                    </div>
                </div>
            )}
        </div>
    );

    const renderStep3 = () => (
        <div className="space-y-6 animate-fadeIn">
            <h3 className="text-xl font-bold text-white mb-4">3. Selección del Equipo de Investigación (IA)</h3>
            <div className="flex justify-between items-center mb-4">
                <p className="text-white/60">Selecciona los agentes especialistas que analizarán este evento.
                    {selectedAgents.length > 0 && !leaderAgent && (
                        <span className="block text-yellow-400 text-xs mt-1 flex items-center gap-1">
                            <AlertTriangle size={12} /> Designa un líder para el análisis
                        </span>
                    )}
                </p>
                <button
                    onClick={() => {
                        if (selectedAgents.length === availableAgents.length) {
                            setSelectedAgents([]);
                            setLeaderAgent(null);
                        } else {
                            const allIds = availableAgents.map(a => a.id);
                            setSelectedAgents(allIds);
                            if (!leaderAgent) {
                                setLeaderAgent(allIds.includes('drilling_engineer') ? 'drilling_engineer' : allIds[0]);
                            }
                        }
                    }}
                    className="text-ibm-blue-400 text-sm hover:text-ibm-blue-300 font-medium"
                >
                    {selectedAgents.length === availableAgents.length ? 'Deseleccionar Todos' : 'Seleccionar Todos'}
                </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-h-60 overflow-y-auto custom-scrollbar p-1">
                {availableAgents.map(agent => (
                    <div
                        key={agent.id}
                        onClick={() => handleAgentToggle(agent.id)}
                        className={`p-3 rounded-lg border cursor-pointer transition-all flex items-center gap-3 ${selectedAgents.includes(agent.id)
                            ? 'bg-ibm-blue-500/20 border-ibm-blue-500 text-white'
                            : 'bg-white/5 border-white/10 text-white/50 hover:bg-white/10'
                            }`}
                    >
                        <div className={`w-4 h-4 rounded border flex items-center justify-center ${selectedAgents.includes(agent.id) ? 'bg-ibm-blue-500 border-ibm-blue-500' : 'border-white/30'
                            }`}>
                            {selectedAgents.includes(agent.id) && <Check size={12} className="text-white" />}
                        </div>
                        <div>
                            <div className="font-medium">{agent.name.replace(/_/g, ' ').toUpperCase()}</div>
                            <div className="text-xs opacity-70">{agent.role}</div>
                        </div>
                        {selectedAgents.includes(agent.id) && (
                            <div
                                onClick={(e) => {
                                    e.stopPropagation();
                                    setLeaderAgent(agent.id);
                                }}
                                className={`ml-auto px-2 py-1 rounded text-xs font-bold border transition-colors ${leaderAgent === agent.id
                                    ? 'bg-yellow-500/20 border-yellow-500 text-yellow-500 shadow-[0_0_10px_rgba(234,179,8,0.2)]'
                                    : 'border-white/20 text-white/40 hover:border-white/60 hover:text-white'
                                    }`}
                            >
                                {leaderAgent === agent.id ? '★ LÍDER' : 'Designar Líder'}
                            </div>
                        )}
                    </div>
                ))}
            </div>

            <div className="flex justify-between pt-6">
                <button
                    onClick={() => setStep(2)}
                    className="text-white/50 hover:text-white px-4 py-2"
                >
                    Atrás
                </button>
                <button
                    onClick={() => onComplete({
                        phase,
                        family: inferredFamily,
                        event_type: eventType,
                        parameters: extractedData || {},
                        workflow: selectedAgents,
                        leader: leaderAgent
                    })}
                    disabled={selectedAgents.length === 0}
                    className="bg-ibm-blue-600 hover:bg-ibm-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white px-6 py-2 rounded flex items-center gap-2"
                >
                    Comenzar Análisis <Play size={16} />
                </button>
            </div>
        </div>
    );

    return (
        <div className="bg-black/40 backdrop-blur-xl border border-white/10 rounded-xl p-8 w-full max-w-7xl mx-auto shadow-2xl">
            <div className="flex items-center justify-between mb-4">
                <h2 className="text-2xl font-bold font-mono">ASISTENTE DE ANÁLISIS DE EVENTOS</h2>
            </div>

            {renderStepIndicator()}

            {step === 1 && renderStep1()}
            {step === 2 && renderStep2()}
            {step === 3 && renderStep3()}
        </div>
    );

};

export default EventWizard;
