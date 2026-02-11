import React, { useState } from 'react';
import { Plus, X, CheckCircle2 } from 'lucide-react';

interface FishboneData {
    man: string[];
    machine: string[];
    method: string[];
    material: string[];
    measurement: string[];
    environment: string[];
}

interface FishboneEditorProps {
    initialData?: FishboneData;
    onComplete: (data: FishboneData) => void;
}

const FishboneEditor: React.FC<FishboneEditorProps> = ({ initialData, onComplete }) => {
    const [data, setData] = useState<FishboneData>(initialData || {
        man: [], machine: [], method: [],
        material: [], measurement: [], environment: []
    });

    const [activeInput, setActiveInput] = useState<{ category: keyof FishboneData, value: string } | null>(null);

    const categories: { key: keyof FishboneData, label: string }[] = [
        { key: 'man', label: 'Manpower' },
        { key: 'method', label: 'Method' },
        { key: 'machine', label: 'Machine' },
        { key: 'material', label: 'Material' },
        { key: 'measurement', label: 'Measurement' },
        { key: 'environment', label: 'Environment' },
    ];

    const addFactor = (category: keyof FishboneData) => {
        if (activeInput && activeInput.value.trim()) {
            const newData = { ...data };
            newData[activeInput.category] = [...newData[activeInput.category], activeInput.value];
            setData(newData);
            setActiveInput(null);
        } else {
            setActiveInput({ category, value: '' });
        }
    };

    const removeFactor = (category: keyof FishboneData, index: number) => {
        const newData = { ...data };
        newData[category] = newData[category].filter((_, i) => i !== index);
        setData(newData);
    };

    const handleInputChange = (value: string) => {
        if (activeInput) {
            setActiveInput({ ...activeInput, value });
        }
    };

    const handleInputSubmit = () => {
        if (activeInput && activeInput.value.trim()) {
            const newData = { ...data };
            newData[activeInput.category] = [...newData[activeInput.category], activeInput.value];
            setData(newData);
            setActiveInput(null);
        }
    };

    const hasData = Object.values(data).some(arr => arr.length > 0);

    return (
        <div className="space-y-8">
            <div className="bg-white/5 p-6 rounded-xl border border-white/10">
                <h3 className="text-xl font-bold mb-2 text-industrial-500">Fishbone (Ishikawa) Analysis</h3>
                <p className="text-white/40 text-sm">
                    Map contributing factors across the 6M categories. This helps identify latent systemic causes beyond the immediate symptoms.
                </p>
            </div>

            <div className="relative overflow-x-auto pb-10 min-h-[500px]">
                <div className="min-w-[800px] h-[400px] relative">
                    {/* Main Spine */}
                    <div className="absolute top-1/2 left-0 right-10 h-1 bg-white/20 rounded-full" />
                    <div className="absolute top-1/2 -mt-4 right-0 w-8 h-8 rotate-45 border-t-4 border-r-4 border-white/20" />

                    <div className="absolute top-1/2 -mt-10 right-[-60px] w-20 flex items-center">
                        <span className="text-white font-bold text-xs uppercase bg-industrial-900 border border-industrial-500 px-2 py-1 rounded">Problem</span>
                    </div>

                    {/* Categories Grid */}
                    <div className="grid grid-cols-3 gap-y-48 h-full">
                        {categories.map((cat, i) => (
                            <div key={cat.key} className="relative group">
                                <div className={`absolute ${i < 3 ? 'bottom-1/2 mb-4' : 'top-1/2 mt-4'} left-4 w-48`}>
                                    <div className="flex justify-between items-center mb-2">
                                        <h4 className="text-xs font-bold text-industrial-500 uppercase tracking-widest bg-industrial-500/10 inline-block px-2 py-1 rounded">
                                            {cat.label}
                                        </h4>
                                        <button
                                            onClick={() => addFactor(cat.key)}
                                            className="text-white/20 hover:text-industrial-500 transition-colors"
                                        >
                                            <Plus size={14} />
                                        </button>
                                    </div>

                                    <div className="space-y-1">
                                        {data[cat.key].map((item, j) => (
                                            <div key={j} className="flex items-center gap-2 group/item">
                                                <div className="w-1.5 h-1.5 rounded-full bg-white/20 flex-shrink-0" />
                                                <span className="text-[11px] text-white/70 truncate">{item}</span>
                                                <button
                                                    onClick={() => removeFactor(cat.key, j)}
                                                    className="ml-auto text-white/10 hover:text-red-500 opacity-0 group-hover/item:opacity-100"
                                                >
                                                    <X size={10} />
                                                </button>
                                            </div>
                                        ))}

                                        {activeInput?.category === cat.key && (
                                            <div className="flex items-center gap-2 animate-in fade-in slide-in-from-left-2">
                                                <div className="w-1.5 h-1.5 rounded-full bg-industrial-500 flex-shrink-0" />
                                                <input
                                                    type="text"
                                                    value={activeInput.value}
                                                    onChange={(e) => handleInputChange(e.target.value)}
                                                    onKeyDown={(e) => e.key === 'Enter' && handleInputSubmit()}
                                                    onBlur={handleInputSubmit}
                                                    autoFocus
                                                    className="bg-transparent border-b border-industrial-500 text-[11px] text-white focus:outline-none w-full"
                                                    placeholder="Add factor..."
                                                />
                                            </div>
                                        )}
                                    </div>
                                </div>

                                {/* Bone */}
                                <div className={`absolute left-10 w-0.5 ${i < 3 ? 'bottom-1/2 h-24' : 'top-1/2 h-24'} bg-white/10 ${i < 3 ? 'rotate-[30deg]' : '-rotate-[30deg]'} origin-bottom`} />
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            <div className="flex justify-end pt-4 border-t border-white/5">
                <button
                    onClick={() => onComplete(data)}
                    disabled={!hasData}
                    className={`btn-primary flex items-center gap-2 ${!hasData ? 'opacity-50 cursor-not-allowed' : ''}`}
                >
                    <CheckCircle2 size={18} />
                    Submit Analysis
                </button>
            </div>
        </div>
    );
};

export default FishboneEditor;
