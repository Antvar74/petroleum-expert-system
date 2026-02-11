import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Database, Plus, ChevronRight, Trash2 } from 'lucide-react';
import ConfirmationModal from './ConfirmationModal';

interface WellSelectorProps {
    onSelect: (well: any) => void;
}

const API_BASE_URL = 'http://localhost:8000';

const WellSelector: React.FC<WellSelectorProps> = ({ onSelect }) => {
    const [wells, setWells] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [newWellName, setNewWellName] = useState('');
    const [isAdding, setIsAdding] = useState(false);

    const [wellToDelete, setWellToDelete] = useState<number | null>(null);

    useEffect(() => {
        fetchWells();
    }, []);

    const fetchWells = async () => {
        try {
            const response = await axios.get(`${API_BASE_URL}/wells`);
            setWells(response.data);
            setLoading(false);
        } catch (error) {
            console.error("Error fetching wells:", error);
            setLoading(false);
        }
    };

    const handleAddWell = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!newWellName.trim()) return;

        try {
            const response = await axios.post(`${API_BASE_URL}/wells?name=${encodeURIComponent(newWellName)}`);
            setWells([...wells, response.data]);
            setNewWellName('');
            setIsAdding(false);
        } catch (error) {
            console.error("Error adding well:", error);
        }
    };

    const initiateDelete = (e: React.MouseEvent, wellId: number) => {
        e.stopPropagation();
        setWellToDelete(wellId);
    };

    const confirmDelete = async () => {
        if (!wellToDelete) return;

        try {
            await axios.delete(`${API_BASE_URL}/wells/${wellToDelete}`);
            setWells(wells.filter(w => w.id !== wellToDelete));
            setWellToDelete(null);
        } catch (error) {
            console.error("Error deleting well:", error);
            alert("Failed to delete well. Please try again.");
            setWellToDelete(null);
        }
    };

    if (loading) return <div className="animate-pulse flex justify-center p-20">Loading exploration data...</div>;

    return (
        <div className="max-w-4xl mx-auto py-12">
            <div className="flex justify-between items-end mb-8">
                <div>
                    <h2 className="text-3xl font-bold mb-2">Welcome Back</h2>
                    <p className="text-white/40">Select an existing well project or create a new one to start analysis.</p>
                </div>
                <button
                    onClick={() => setIsAdding(!isAdding)}
                    className="btn-primary"
                >
                    <Plus size={18} />
                    {isAdding ? 'Cancel' : 'New Well Project'}
                </button>
            </div>

            {isAdding && (
                <form onSubmit={handleAddWell} className="glass-panel p-6 mb-8 animate-in fade-in slide-in-from-top-4">
                    <h3 className="text-lg font-bold mb-4">Register New Well</h3>
                    <div className="flex gap-4">
                        <input
                            type="text"
                            value={newWellName}
                            onChange={(e) => setNewWellName(e.target.value)}
                            placeholder="e.g. WELL-X106-OFFSHORE"
                            className="input-field flex-1"
                            autoFocus
                        />
                        <button type="submit" className="btn-primary">Create Project</button>
                    </div>
                </form>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {wells.length === 0 ? (
                    <div className="col-span-2 glass-panel p-12 text-center text-white/20 italic">
                        No wells registered yet. Click "New Well Project" to start.
                    </div>
                ) : (
                    wells.map((well) => (
                        <div
                            key={well.id}
                            className="glass-card p-6 flex items-center justify-between text-left group cursor-pointer hover:border-industrial-500/50 transition-colors"
                            onClick={() => onSelect(well)}
                        >
                            <div className="flex items-center gap-4">
                                <div className="w-12 h-12 bg-white/5 border border-white/10 rounded-xl flex items-center justify-center text-industrial-500 group-hover:scale-110 transition-transform">
                                    <Database size={24} />
                                </div>
                                <div>
                                    <h4 className="font-bold text-lg">{well.name}</h4>
                                    <p className="text-xs text-white/40">{well.location || 'Location not specified'}</p>
                                </div>
                            </div>
                            <div className="flex items-center gap-4">
                                <button
                                    onClick={(e) => initiateDelete(e, well.id)}
                                    className="text-white/20 hover:text-red-500 transition-colors p-2 rounded-full hover:bg-white/5 z-20"
                                    title="Delete Well Project"
                                >
                                    <Trash2 size={18} />
                                </button>
                                <ChevronRight className="text-white/20 group-hover:text-industrial-500 transition-colors" />
                            </div>
                        </div>
                    ))
                )}
            </div>

            <ConfirmationModal
                isOpen={!!wellToDelete}
                onClose={() => setWellToDelete(null)}
                onConfirm={confirmDelete}
                title="Delete Well Project"
                message="Are you sure you want to delete this well project? This action cannot be undone and all associated data will be lost."
                confirmText="Delete Project"
                variant="danger"
            />
        </div>
    );
};

export default WellSelector;
