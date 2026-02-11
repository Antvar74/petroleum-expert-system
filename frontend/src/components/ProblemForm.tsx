import React, { useState } from 'react';
import { Info, Send } from 'lucide-react';

interface ProblemFormProps {
    onSubmit: (data: any) => void;
}

const ProblemForm: React.FC<ProblemFormProps> = ({ onSubmit }) => {
    const [formData, setFormData] = useState({
        operation: 'drilling',
        depth_md: '',
        depth_tvd: '',
        formation: '',
        description: '',
        mud_weight: '',
        inclination: '',
        torque: '',
        overpull: ''
    });

    // New state for dynamic file list
    const [availableFiles, setAvailableFiles] = useState<string[]>([]);

    React.useEffect(() => {
        // Fetch available PDF files from backend
        fetch('http://localhost:8000/files')
            .then(res => res.json())
            .then(files => setAvailableFiles(files))
            .catch(err => console.error("Error fetching files:", err));
    }, []);

    const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
        setFormData({ ...formData, [e.target.name]: e.target.value });
    };

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        onSubmit({
            ...formData,
            depth_md: parseFloat(formData.depth_md),
            depth_tvd: parseFloat(formData.depth_tvd),
            mud_weight: parseFloat(formData.mud_weight) || null,
            inclination: parseFloat(formData.inclination) || null,
            torque: parseFloat(formData.torque) || null,
            overpull: parseFloat(formData.overpull) || null
        });
    };

    return (
        <form onSubmit={handleSubmit} className="glass-panel p-8 space-y-6">
            <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                    <label className="text-xs font-bold text-white/40 uppercase tracking-wider">Operation Type</label>
                    <select
                        name="operation"
                        value={formData.operation}
                        onChange={handleChange}
                        className="input-field appearance-none cursor-pointer"
                    >
                        <option value="drilling">Drilling</option>
                        <option value="tripping_in">Tripping In</option>
                        <option value="tripping_out">Tripping Out</option>
                        <option value="running_casing">Running Casing</option>
                        <option value="logging">Logging</option>
                    </select>
                </div>

                <div className="col-span-2 flex justify-end items-center gap-2">
                    <label className="text-xs font-bold text-white/40 uppercase tracking-wider">Attach Context Document:</label>
                    <select
                        onChange={(e) => {
                            if (e.target.value) {
                                const filename = e.target.value;
                                setFormData(prev => ({
                                    ...prev,
                                    description: `[REAL_DATA:${filename}] Analyze the attached daily reports regarding the pipe parting event.`,
                                    depth_md: "3450",
                                    depth_tvd: "3400",
                                    // Pre-fil BAKTE-9 specific data if selected
                                    ...(filename.includes("BAKTE-9") ? {
                                        formation: "Shale",
                                        mud_weight: "1.45",
                                        inclination: "45",
                                        torque: "25",
                                        overpull: "50"
                                    } : {})
                                }));
                            }
                        }}
                        className="bg-white/5 border border-white/10 rounded px-2 py-1 text-xs text-ibm-blue-300 focus:outline-none focus:border-ibm-blue-500 cursor-pointer"
                    >
                        <option value="">Select a PDF...</option>
                        {availableFiles.map(file => (
                            <option key={file} value={file}>{file}</option>
                        ))}
                    </select>
                </div>

                <div className="space-y-2">
                    <label className="text-xs font-bold text-white/40 uppercase tracking-wider">Formation</label>
                    <input
                        type="text"
                        name="formation"
                        placeholder="e.g. Naricual"
                        value={formData.formation}
                        onChange={handleChange}
                        className="input-field"
                    />
                </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                    <label className="text-xs font-bold text-white/40 uppercase tracking-wider">Depth MD (ft)</label>
                    <input
                        type="number"
                        name="depth_md"
                        required
                        value={formData.depth_md}
                        onChange={handleChange}
                        className="input-field"
                    />
                </div>
                <div className="space-y-2">
                    <label className="text-xs font-bold text-white/40 uppercase tracking-wider">Depth TVD (ft)</label>
                    <input
                        type="number"
                        name="depth_tvd"
                        required
                        value={formData.depth_tvd}
                        onChange={handleChange}
                        className="input-field"
                    />
                </div>
            </div>

            <div className="space-y-2">
                <label className="text-xs font-bold text-white/40 uppercase tracking-wider">Problem Description</label>
                <textarea
                    name="description"
                    required
                    rows={4}
                    placeholder="Detailed description of symbols, parameters, and events..."
                    value={formData.description}
                    onChange={handleChange}
                    className="input-field resize-none"
                />
                <p className="text-[10px] text-white/20 flex items-center gap-1">
                    <Info size={12} />
                    To use real PDPs/Reports, place the PDF in the 'data/' folder and reference it here (e.g. [REAL_DATA:filename.pdf]).
                </p>
            </div>

            <div className="grid grid-cols-4 gap-4">
                <div className="space-y-2">
                    <label className="text-[10px] font-bold text-white/40 uppercase tracking-tighter">Mud Weight (ppg)</label>
                    <input type="number" step="0.1" name="mud_weight" value={formData.mud_weight} onChange={handleChange} className="input-field" />
                </div>
                <div className="space-y-2">
                    <label className="text-[10px] font-bold text-white/40 uppercase tracking-tighter">Inclination (°)</label>
                    <input type="number" step="0.1" name="inclination" value={formData.inclination} onChange={handleChange} className="input-field" />
                </div>
                <div className="space-y-2">
                    <label className="text-[10px] font-bold text-white/40 uppercase tracking-tighter">Torque (klb-ft)</label>
                    <input type="number" step="0.1" name="torque" value={formData.torque} onChange={handleChange} className="input-field" />
                </div>
                <div className="space-y-2">
                    <label className="text-[10px] font-bold text-white/40 uppercase tracking-tighter">Overpull (lbs)</label>
                    <input type="number" name="overpull" value={formData.overpull} onChange={handleChange} className="input-field" />
                </div>
            </div>

            <button type="submit" className="w-full btn-primary justify-center h-12 text-base shadow-lg shadow-industrial-900/20">
                <Send size={18} />
                Initiate Specialist Analysis
            </button>
        </form>
    );
};

export default ProblemForm;
