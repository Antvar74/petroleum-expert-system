import React, { useState, useEffect } from 'react';
import { Plus, Trash2, ArrowDown, CheckCircle2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface FiveWhysEditorProps {
    initialData?: string[];
    onComplete: (data: string[]) => void;
}

const FiveWhysEditor: React.FC<FiveWhysEditorProps> = ({ initialData, onComplete }) => {
    const [whys, setWhys] = useState<string[]>(initialData || ['', '', '', '', '']);

    useEffect(() => {
        if (initialData) {
            setWhys(initialData);
        }
    }, [initialData]);

    const handleChange = (index: number, value: string) => {
        const newWhys = [...whys];
        newWhys[index] = value;
        setWhys(newWhys);
    };

    const addLevel = () => {
        setWhys([...whys, '']);
    };

    const removeLevel = (index: number) => {
        if (whys.length <= 1) return;
        const newWhys = whys.filter((_, i) => i !== index);
        setWhys(newWhys);
    };

    const isValid = whys.filter(w => w.trim().length > 0).length >= 3;

    return (
        <div className="space-y-6 max-w-2xl mx-auto">
            <div className="bg-white/5 p-6 rounded-xl border border-white/10 mb-8">
                <h3 className="text-xl font-bold mb-2 text-industrial-500">5-Whys Analysis</h3>
                <p className="text-white/40 text-sm">
                    Drill down to the root cause by asking "Why?" at least 5 times.
                    The final answer should point to a systemic or procedural failure.
                </p>
            </div>

            <div className="space-y-2">
                <AnimatePresence>
                    {whys.map((why, index) => (
                        <motion.div
                            key={index}
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, height: 0 }}
                            className="relative"
                        >
                            {index > 0 && (
                                <div className="flex justify-center py-2 text-white/20">
                                    <ArrowDown size={20} />
                                </div>
                            )}

                            <div className="glass-panel p-4 flex gap-4 items-start group">
                                <div className={`w-12 h-12 rounded-lg flex-shrink-0 flex items-center justify-center font-bold border ${index === whys.length - 1 ? 'bg-green-500/20 border-green-500/50 text-green-500' : 'bg-white/5 border-white/10 text-white/40'}`}>
                                    {index + 1}
                                </div>
                                <div className="flex-1">
                                    <label className="text-xs text-white/30 uppercase font-bold mb-1 block">
                                        {index === 0 ? "The Problem (Incident)" : index === whys.length - 1 ? "Root Cause" : `Why did this happen?`}
                                    </label>
                                    <textarea
                                        value={why}
                                        onChange={(e) => handleChange(index, e.target.value)}
                                        placeholder={index === 0 ? "Describe the incident..." : "Because..."}
                                        className="w-full bg-transparent border-none focus:ring-0 text-white placeholder-white/20 resize-none"
                                        rows={2}
                                        autoFocus={index === whys.length - 1 && index > 0}
                                    />
                                </div>
                                <button
                                    onClick={() => removeLevel(index)}
                                    className="p-2 text-white/20 hover:text-red-500 transition-colors opacity-0 group-hover:opacity-100"
                                >
                                    <Trash2 size={16} />
                                </button>
                            </div>
                        </motion.div>
                    ))}
                </AnimatePresence>
            </div>

            <div className="flex justify-between items-center pt-8">
                <button
                    onClick={addLevel}
                    className="flex items-center gap-2 text-industrial-500 hover:text-industrial-400 font-bold text-sm px-4 py-2 hover:bg-industrial-500/10 rounded-lg transition-colors"
                >
                    <Plus size={16} />
                    Add Another Level
                </button>

                <button
                    onClick={() => onComplete(whys)}
                    disabled={!isValid}
                    className={`btn-primary flex items-center gap-2 ${!isValid ? 'opacity-50 cursor-not-allowed' : ''}`}
                >
                    <CheckCircle2 size={18} />
                    Submit Analysis
                </button>
            </div>
        </div>
    );
};

export default FiveWhysEditor;
