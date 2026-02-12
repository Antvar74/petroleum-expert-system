import React, { useState } from 'react';
import axios from 'axios';
import { motion } from 'framer-motion';
import {
    FilePlus,
    Settings2,
    RotateCcw,
    Download,
    CheckCircle2,
    AlertCircle,
    Loader2,
    ChevronRight,
    HardDrive
} from 'lucide-react';
import { API_BASE_URL } from '../config';

interface ProgramGeneratorProps {
    wellId: number;
}



const ProgramGenerator: React.FC<ProgramGeneratorProps> = ({ wellId }) => {
    const [type, setType] = useState<'drilling' | 'completion' | 'workover'>('drilling');
    const [isGenerating, setIsGenerating] = useState(false);
    const [program, setProgram] = useState<any>(null);
    const [error, setError] = useState<string | null>(null);

    const handleCreate = async () => {
        setIsGenerating(true);
        setError(null);
        try {
            const createRes = await axios.post(`${API_BASE_URL}/wells/${wellId}/programs?type=${type}`);
            const newProgram = createRes.data;

            const genRes = await axios.post(`${API_BASE_URL}/programs/${newProgram.id}/generate`);
            setProgram(genRes.data);
        } catch (err) {
            setError("Error generating program. Ensure Ollama is running or check connection.");
            console.error(err);
        } finally {
            setIsGenerating(false);
        }
    };

    return (
        <div className="max-w-5xl mx-auto py-8 space-y-8">
            <div className="flex justify-between items-end">
                <div>
                    <h2 className="text-3xl font-bold flex items-center gap-3">
                        <Settings2 className="text-industrial-500" />
                        Program Proactive Generator
                    </h2>
                    <p className="text-white/40 mt-1">Generate comprehensive technical programs using industry standards.</p>
                </div>
            </div>

            {!program ? (
                <div className="glass-panel p-10 flex flex-col items-center justify-center text-center space-y-8">
                    <div className="w-20 h-20 bg-industrial-500/10 rounded-full flex items-center justify-center text-industrial-500">
                        <FilePlus size={40} />
                    </div>
                    <div className="max-w-md">
                        <h3 className="text-xl font-bold mb-2">Initialize New Program</h3>
                        <p className="text-white/40 text-sm">Select the type of program you wish to generate. Our specialist agents will draft the complete technical document.</p>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 w-full max-w-2xl">
                        {['drilling', 'completion', 'workover'].map((pType) => (
                            <button
                                key={pType}
                                onClick={() => setType(pType as any)}
                                className={`p-6 rounded-2xl border transition-all flex flex-col items-center gap-4 ${type === pType
                                    ? 'bg-industrial-600/20 border-industrial-500 text-white shadow-lg shadow-industrial-900/40'
                                    : 'bg-white/5 border-white/10 text-white/40 hover:bg-white/10'
                                    }`}
                            >
                                <div className={`p-3 rounded-xl ${type === pType ? 'bg-industrial-500 text-white' : 'bg-white/5'}`}>
                                    <HardDrive size={24} />
                                </div>
                                <span className="font-bold uppercase tracking-widest text-[10px]">{pType} Program</span>
                            </button>
                        ))}
                    </div>

                    <button
                        onClick={handleCreate}
                        disabled={isGenerating}
                        className="btn-primary w-full max-w-sm flex justify-center py-4 bg-industrial-600 hover:bg-industrial-500"
                    >
                        {isGenerating ? (
                            <span className="flex items-center gap-2">
                                <Loader2 className="animate-spin" size={20} />
                                Generating Analysis...
                            </span>
                        ) : (
                            "Generate Full Program v3.0"
                        )}
                    </button>

                    {error && (
                        <div className="flex items-center gap-2 text-red-400 text-sm font-medium bg-red-400/10 px-4 py-2 rounded-lg">
                            <AlertCircle size={16} />
                            {error}
                        </div>
                    )}
                </div>
            ) : (
                <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="space-y-6 pb-20">
                    <div className="flex justify-between items-center">
                        <div className="flex items-center gap-4">
                            <div className="p-3 bg-green-500/10 rounded-2xl text-green-500">
                                <CheckCircle2 size={24} />
                            </div>
                            <div>
                                <h3 className="text-xl font-bold capitalize">{program.type} Program: Generated</h3>
                                <p className="text-white/40 text-xs">Ready for engineering review and export.</p>
                            </div>
                        </div>
                        <div className="flex gap-3">
                            <button onClick={() => setProgram(null)} className="btn-secondary">
                                <RotateCcw size={16} />
                                New Program
                            </button>
                            <button className="btn-primary flex items-center gap-2 bg-industrial-600">
                                <Download size={16} />
                                Export MD
                            </button>
                        </div>
                    </div>

                    <div className="glass-panel p-0 overflow-hidden border-white/10">
                        <div className="bg-white/5 px-8 py-4 border-b border-white/10 flex items-center justify-between">
                            <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-widest text-white/40">
                                <span>View</span>
                                <ChevronRight size={12} />
                                <span className="text-industrial-500">Technical Document</span>
                            </div>
                            <div className="flex gap-2">
                                <div className="w-3 h-3 rounded-full bg-red-500/20" />
                                <div className="w-3 h-3 rounded-full bg-amber-500/20" />
                                <div className="w-3 h-3 rounded-full bg-green-500/20" />
                            </div>
                        </div>
                        <div className="p-10 prose prose-invert max-w-none bg-black/40 min-h-[600px] whitespace-pre-wrap font-sans text-white/80 leading-relaxed custom-scrollbar text-sm">
                            {program.content.markdown}
                        </div>
                    </div>
                </motion.div>
            )}
        </div>
    );
};

export default ProgramGenerator;
