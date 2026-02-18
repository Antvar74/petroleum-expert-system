import React, { useState } from 'react';
import { Upload, Check, ArrowRight, Activity, Droplet, PenTool, Shield, Users, Play } from 'lucide-react';
import axios from 'axios';
import { API_BASE_URL } from '../config';

interface EventWizardProps {
    onComplete: (eventData: any) => void;
    onCancel: () => void;
}

const PHASES = [
    { id: 'drilling', label: 'Perforación', icon: Activity },
    { id: 'completion', label: 'Completación', icon: Check },
    { id: 'workover', label: 'Workover', icon: PenTool },
];

const FAMILIES = [
    { id: 'well', label: 'Pozo / Geomecánica', icon: Activity, description: 'Inestabilidad, Colapso, Pérdidas' },
    { id: 'fluids', label: 'Fluidos / Presión', icon: Droplet, description: 'Kicks, Pérdidas, ECD, Ballooning' },
    { id: 'mechanics', label: 'Sarta / Mecánicos', icon: PenTool, description: 'Pegas, Fallas de BHA, Torque/Drag' },
    { id: 'control', label: 'Control de Pozo', icon: Shield, description: 'BOP, Fallas de Barrera, Brotes' },
    { id: 'human', label: 'Factores Humanos', icon: Users, description: 'Procedimientos, Comunicación, Error' },
];

const EventWizard: React.FC<EventWizardProps> = ({ onComplete, onCancel }) => {
    const [step, setStep] = useState(1);
    const [phase, setPhase] = useState<string | null>(null);
    const [family, setFamily] = useState<string | null>(null);
    const [files, setFiles] = useState<File[]>([]);
    const [isExtracting, setIsExtracting] = useState(false);
    const [extractedData, setExtractedData] = useState<any>(null);
    const [selectedAgents, setSelectedAgents] = useState<string[]>([]);
    const [leaderAgent, setLeaderAgent] = useState<string | null>(null);
    const [availableAgents, setAvailableAgents] = useState<any[]>([]);

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
                alert("Máximo 5 archivos permitidos.");
                return;
            }

            const totalSize = selectedFiles.reduce((acc, file) => acc + file.size, 0);
            if (totalSize > 10 * 1024 * 1024) { // 10MB
                alert("El tamaño total excede los 10MB.");
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
                alert("Error extracting data. Please enter manually.");
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

    const renderStep1 = () => (
        <div className="space-y-6 animate-fadeIn">
            <h3 className="text-xl font-bold text-white mb-4">1. Identificación del Evento</h3>

            <div className="space-y-4">
                <label className="text-sm text-ibm-gray-300">Fase Operativa</label>
                <div className="grid grid-cols-3 gap-4">
                    {PHASES.map((p) => (
                        <button
                            key={p.id}
                            onClick={() => setPhase(p.id)}
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
                    <label className="text-sm text-ibm-gray-300">Familia del Evento</label>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        {FAMILIES.map((f) => (
                            <button
                                key={f.id}
                                onClick={() => setFamily(f.id)}
                                className={`p-4 rounded-lg border text-left flex items-center gap-4 transition-all ${family === f.id
                                    ? 'bg-ibm-blue-600/20 border-ibm-blue-500 text-white'
                                    : 'bg-white/5 border-white/10 text-white/50 hover:bg-white/10'
                                    }`}
                            >
                                <f.icon size={20} className={family === f.id ? 'text-ibm-blue-400' : ''} />
                                <div>
                                    <div className="font-medium">{f.label}</div>
                                    <div className="text-xs text-white/30">{f.description}</div>
                                </div>
                            </button>
                        ))}
                    </div>
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
                    disabled={!phase || !family}
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
                        />
                        <label htmlFor="file-upload" className="cursor-pointer flex flex-col items-center gap-4">
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
                                            ⚠️ Máx 5 archivos o 10MB total. Se procesarán los primeros 15k caracteres.
                                        </div>
                                    </div>
                                </>
                            )}
                        </label>
                    </div>
                    <div className="flex justify-center mt-4">
                        <button
                            onClick={() => {
                                setExtractedData({}); // Set empty data to proceed
                                setStep(3); // Go to agent selection
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
                                    <label className="text-xs text-white/40 uppercase block mb-1">{key.replace('_', ' ')}</label>
                                    <input
                                        type="text"
                                        defaultValue={value as string}
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
                <p className="text-white/60">Selecciona los agentes especialistas que analizarán este evento.</p>
                <button
                    onClick={() => {
                        if (selectedAgents.length === availableAgents.length) {
                            setSelectedAgents([]);
                        } else {
                            setSelectedAgents(availableAgents.map(a => a.id));
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
                            <div className="font-medium">{agent.name.replace('_', ' ').toUpperCase()}</div>
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
                    onClick={() => onComplete({ phase, family, files, parameters: extractedData || {}, workflow: selectedAgents, leader: leaderAgent })}
                    disabled={selectedAgents.length === 0}
                    className="bg-ibm-blue-600 hover:bg-ibm-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white px-6 py-2 rounded flex items-center gap-2"
                >
                    Comenzar Análisis <Play size={16} />
                </button>
            </div>
        </div>
    );

    return (
        <div className="bg-black/40 backdrop-blur-xl border border-white/10 rounded-xl p-8 max-w-4xl mx-auto shadow-2xl">
            <div className="flex items-center justify-between mb-8">
                <h2 className="text-2xl font-bold font-mono">ASISTENTE DE ANÁLISIS DE EVENTOS</h2>
            </div>

            {step === 1 && renderStep1()}
            {step === 2 && renderStep2()}
            {step === 3 && renderStep3()}
        </div>
    );

};

export default EventWizard;
