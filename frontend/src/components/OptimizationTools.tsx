import React, { useState } from 'react';
import axios from 'axios';
import { motion } from 'framer-motion';
import {
    Gauge,
    Droplets,
    ArrowUpCircle,
    Calculator,
    RefreshCw,
    CheckCircle2,
    AlertTriangle,
    Upload
} from 'lucide-react';
import { API_BASE_URL } from '../config';



const OptimizationTools: React.FC = () => {
    const [tab, setTab] = useState<'hydraulics' | 'torque' | 'ingestion'>('hydraulics');

    // Hydraulics State
    const [hydData, setHydData] = useState({ flow: 450, mw: 12.5, depth: 10000, pipeId: 4.276 });
    const [hydResult, setHydResult] = useState<any>(null);

    // Torque & Drag State
    const [tdData, setTdData] = useState({ depth: 10000, inclination: 45, mw: 12.5, pipeWeight: 19.5 });
    const [tdResult, setTdResult] = useState<any>(null);

    // Ingestion State
    const [ingestFile, setIngestFile] = useState<File | null>(null);
    const [ingestStatus, setIngestStatus] = useState<any>(null);

    const calculateHydraulics = async () => {
        try {
            const res = await axios.post(`${API_BASE_URL}/optimize/hydraulics?flow_rate=${hydData.flow}&mw=${hydData.mw}&depth=${hydData.depth}&pipe_id=${hydData.pipeId}`);
            setHydResult(res.data);
        } catch (e) {
            console.error(e);
        }
    };

    const calculateTD = async () => {
        try {
            const res = await axios.post(`${API_BASE_URL}/optimize/torque-drag?depth=${tdData.depth}&inclination=${tdData.inclination}&mw=${tdData.mw}&pipe_weight=${tdData.pipeWeight}`);
            setTdResult(res.data);
        } catch (e) {
            console.error(e);
        }
    };

    const handleFileUpload = async () => {
        if (!ingestFile) return;
        const formData = new FormData();
        formData.append('file', ingestFile);
        try {
            const res = await axios.post(`${API_BASE_URL}/ingest/csv?well_id=1`, formData);
            setIngestStatus(res.data);
        } catch (e) {
            console.error(e);
        }
    };

    return (
        <div className="max-w-6xl mx-auto py-8 space-y-8 pb-20">
            <div>
                <h2 className="text-3xl font-bold flex items-center gap-3">
                    <Calculator className="text-industrial-500" />
                    Optimization & Ingestion v3.0
                </h2>
                <p className="text-white/40 mt-1">Perform technical calculations and ingest operational data.</p>
            </div>

            <div className="flex bg-white/5 p-1 rounded-xl border border-white/10 w-fit">
                <button onClick={() => setTab('hydraulics')} className={`px-4 py-2 rounded-lg text-xs font-bold transition-all ${tab === 'hydraulics' ? 'bg-industrial-600 text-white' : 'text-white/40'}`}>
                    Hydraulics
                </button>
                <button onClick={() => setTab('torque')} className={`px-4 py-2 rounded-lg text-xs font-bold transition-all ${tab === 'torque' ? 'bg-industrial-600 text-white' : 'text-white/40'}`}>
                    Torque & Drag
                </button>
                <button onClick={() => setTab('ingestion')} className={`px-4 py-2 rounded-lg text-xs font-bold transition-all ${tab === 'ingestion' ? 'bg-industrial-600 text-white' : 'text-white/40'}`}>
                    Data Ingestion
                </button>
            </div>

            {tab === 'hydraulics' && (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                    <div className="glass-panel p-8 space-y-6">
                        <div className="flex justify-between items-center mb-6">
                            <h3 className="text-lg font-bold flex items-center gap-2"><Droplets size={20} className="text-industrial-500" /> Parameters</h3>
                            <button
                                onClick={() => {
                                    setHydData({ flow: 450, mw: 12.5, depth: 10000, pipeId: 4.276 });
                                    setHydResult(null);
                                }}
                                className="text-[10px] uppercase font-bold text-white/20 hover:text-industrial-500 transition-colors flex items-center gap-1"
                            >
                                <RefreshCw size={10} /> Reset
                            </button>
                        </div>
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className="text-[10px] uppercase text-white/40 font-bold">Flow Rate (GPM)</label>
                                <input type="number" value={hydData.flow} onChange={(e) => setHydData({ ...hydData, flow: Number(e.target.value) })} className="input-field mt-1" />
                            </div>
                            <div>
                                <label className="text-[10px] uppercase text-white/40 font-bold">Mud Weight (PPG)</label>
                                <input type="number" value={hydData.mw} onChange={(e) => setHydData({ ...hydData, mw: Number(e.target.value) })} className="input-field mt-1" />
                            </div>
                            <div>
                                <label className="text-[10px] uppercase text-white/40 font-bold">Total Depth (FT)</label>
                                <input type="number" value={hydData.depth} onChange={(e) => setHydData({ ...hydData, depth: Number(e.target.value) })} className="input-field mt-1" />
                            </div>
                            <div>
                                <label className="text-[10px] uppercase text-white/40 font-bold">Pipe ID (IN)</label>
                                <input type="number" value={hydData.pipeId} onChange={(e) => setHydData({ ...hydData, pipeId: Number(e.target.value) })} className="input-field mt-1" />
                            </div>
                        </div>
                        <button onClick={calculateHydraulics} className="btn-primary w-full py-4 mt-4">Calculate Hydraulics</button>
                    </div>

                    <div className="glass-panel p-8 flex flex-col items-center justify-center text-center">
                        {hydResult ? (
                            <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} className="w-full space-y-8">
                                <div className="relative inline-block">
                                    <div className="w-40 h-40 rounded-full border-4 border-industrial-500/20 flex flex-col items-center justify-center shadow-lg shadow-industrial-900/40 relative">
                                        <Gauge size={48} className="text-industrial-500 mb-1" />
                                        <span className="text-2xl font-black text-white">{hydResult.pressure_drop_psi}</span>
                                        <span className="text-[8px] uppercase tracking-widest font-bold text-white/40">PSI Drop</span>
                                    </div>
                                </div>
                                <div className="grid grid-cols-2 gap-4 text-left">
                                    <div className="bg-white/5 p-4 rounded-xl border border-white/5">
                                        <p className="text-[10px] uppercase font-bold text-white/20 mb-1">Annular Velocity</p>
                                        <p className="text-xl font-bold text-white">{hydResult.annular_velocity_fps} <span className="text-xs text-white/40">fps</span></p>
                                    </div>
                                    <div className="bg-white/5 p-4 rounded-xl border border-white/5">
                                        <p className="text-[10px] uppercase font-bold text-white/20 mb-1">ECD Result</p>
                                        <p className="text-xl font-bold text-industrial-500">{hydResult.ecd_ppg} <span className="text-xs text-white/40">ppg</span></p>
                                    </div>
                                </div>
                                <div className={`p-4 rounded-xl border ${hydResult.status === 'Optimal' ? 'bg-green-500/10 border-green-500/20 text-green-500' : 'bg-amber-500/10 border-amber-500/20 text-amber-500'} flex items-center justify-center gap-2 font-bold text-xs uppercase tracking-widest`}>
                                    {hydResult.status === 'Optimal' ? <CheckCircle2 size={16} /> : <AlertTriangle size={16} />}
                                    Status: {hydResult.status}
                                </div>
                            </motion.div>
                        ) : (
                            <div className="text-white/20">
                                <RefreshCw size={48} className="mx-auto mb-4 opacity-10 animate-spin-slow" />
                                <p>Run calculation to see results</p>
                            </div>
                        )}
                    </div>
                </div>
            )}

            {tab === 'torque' && (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                    <div className="glass-panel p-8 space-y-6">
                        <div className="flex justify-between items-center mb-6">
                            <h3 className="text-lg font-bold flex items-center gap-2"><ArrowUpCircle size={20} className="text-industrial-500" /> T&D Params</h3>
                            <button
                                onClick={() => {
                                    setTdData({ depth: 10000, inclination: 45, mw: 12.5, pipeWeight: 19.5 });
                                    setTdResult(null);
                                }}
                                className="text-[10px] uppercase font-bold text-white/20 hover:text-industrial-500 transition-colors flex items-center gap-1"
                            >
                                <RefreshCw size={10} /> Reset
                            </button>
                        </div>
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className="text-[10px] uppercase text-white/40 font-bold">Measured Depth</label>
                                <input type="number" value={tdData.depth} onChange={(e) => setTdData({ ...tdData, depth: Number(e.target.value) })} className="input-field mt-1" />
                            </div>
                            <div>
                                <label className="text-[10px] uppercase text-white/40 font-bold">Inclination (Deg)</label>
                                <input type="number" value={tdData.inclination} onChange={(e) => setTdData({ ...tdData, inclination: Number(e.target.value) })} className="input-field mt-1" />
                            </div>
                            <div>
                                <label className="text-[10px] uppercase text-white/40 font-bold">Mud Weight</label>
                                <input type="number" value={tdData.mw} onChange={(e) => setTdData({ ...tdData, mw: Number(e.target.value) })} className="input-field mt-1" />
                            </div>
                            <div>
                                <label className="text-[10px] uppercase text-white/40 font-bold">Pipe Weight</label>
                                <input type="number" value={tdData.pipeWeight} onChange={(e) => setTdData({ ...tdData, pipeWeight: Number(e.target.value) })} className="input-field mt-1" />
                            </div>
                        </div>
                        <button onClick={calculateTD} className="btn-primary w-full py-4 mt-4">Run Soft String Model</button>
                    </div>

                    <div className="glass-panel p-8 flex flex-col justify-center">
                        {tdResult ? (
                            <div className="space-y-6">
                                <div className="flex justify-between items-end border-b border-white/5 pb-4">
                                    <p className="text-sm font-bold opacity-60 uppercase">Calculated Hookload</p>
                                    <p className="text-3xl font-black text-industrial-500">{tdResult.hook_load_up_lb.toLocaleString()} <span className="text-xs text-white/40">lb (Up)</span></p>
                                </div>
                                <div className="space-y-4">
                                    <div className="flex justify-between items-center bg-white/5 p-4 rounded-xl">
                                        <span className="text-xs text-white/40">Buoyed Weight</span>
                                        <span className="font-bold">{tdResult.buoyed_weight_lb.toLocaleString()} lb</span>
                                    </div>
                                    <div className="flex justify-between items-center bg-white/5 p-4 rounded-xl font-bold border-l-4 border-industrial-500">
                                        <span className="text-xs text-industrial-500 uppercase tracking-widest">Available Overpull</span>
                                        <span>{tdResult.margin_of_overpull_lb.toLocaleString()} lb</span>
                                    </div>
                                </div>
                            </div>
                        ) : (
                            <div className="text-center text-white/20">Run calculation to see Hookload limits.</div>
                        )}
                    </div>
                </div>
            )}

            {tab === 'ingestion' && (
                <div className="glass-panel p-12 text-center flex flex-col items-center justify-center space-y-8">
                    <div className="w-20 h-20 bg-industrial-600/10 rounded-full flex items-center justify-center text-industrial-500">
                        <Upload size={40} />
                    </div>
                    <div className="max-w-md">
                        <h3 className="text-xl font-bold mb-2">Historical Data Ingestion</h3>
                        <p className="text-white/40 text-sm">Upload CSV or Excel files containing sensor data (ROP, WOB, Torque, Flow) to enhance the agent analysis context.</p>
                    </div>

                    <div className="w-full max-w-sm">
                        <input
                            type="file"
                            onChange={(e) => setIngestFile(e.target.files?.[0] || null)}
                            className="block w-full text-xs text-white/40 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-xs file:font-semibold file:bg-industrial-600 file:text-white hover:file:bg-industrial-500 cursor-pointer"
                        />
                    </div>

                    <button onClick={handleFileUpload} className="btn-primary w-full max-w-sm py-4">Process File</button>

                    {ingestStatus && (
                        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="w-full max-w-md bg-green-500/10 p-6 rounded-2xl border border-green-500/20 text-left">
                            <h4 className="text-green-500 font-bold mb-2">Ingestion Complete</h4>
                            <p className="text-xs text-white/60 mb-4">File processed successfully. Ready for agent context.</p>
                            <div className="grid grid-cols-2 gap-2 text-[10px] font-bold uppercase tracking-widest text-white/20">
                                <span>Rows: {ingestStatus.rows_ingested}</span>
                                <span>Type: CSV</span>
                            </div>
                        </motion.div>
                    )}
                </div>
            )}
        </div>
    );
};

export default OptimizationTools;
