import type { Well } from '../types/api';
import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useToast } from './ui/Toast';
import api from '../lib/api';
import { Database, Plus, ChevronRight, Trash2 } from 'lucide-react';
import ConfirmationModal from './ConfirmationModal';

interface WellSelectorProps {
    onSelect: (well: Well) => void;
}



const WellSelector: React.FC<WellSelectorProps> = ({ onSelect }) => {
    const { t } = useTranslation();
    const { addToast } = useToast();
    const [wells, setWells] = useState<Well[]>([]);
    const [loading, setLoading] = useState(true);
    const [newWellName, setNewWellName] = useState('');
    const [isAdding, setIsAdding] = useState(false);

    const [wellToDelete, setWellToDelete] = useState<number | null>(null);

    useEffect(() => {
        fetchWells();
    }, []);

    const fetchWells = async () => {
        try {
            const response = await api.get(`/wells`);
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
            const response = await api.post(`/wells?name=${encodeURIComponent(newWellName)}`);
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
            await api.delete(`/wells/${wellToDelete}`);
            setWells(wells.filter(w => w.id !== wellToDelete));
            setWellToDelete(null);
        } catch (error) {
            console.error("Error deleting well:", error);
            addToast(t('well.deleteError'), 'error');
            setWellToDelete(null);
        }
    };

    if (loading) return <div className="animate-pulse flex justify-center p-20">{t('well.loadingData')}</div>;

    return (
        <div className="max-w-4xl mx-auto py-12">
            <div className="flex justify-between items-end mb-8">
                <div>
                    <h2 className="text-3xl font-bold mb-2">{t('well.welcomeBack')}</h2>
                    <p className="text-white/40">{t('well.selectWellDescription')}</p>
                </div>
                <button
                    onClick={() => setIsAdding(!isAdding)}
                    className="btn-primary"
                >
                    <Plus size={18} />
                    {isAdding ? t('well.cancel') : t('well.newWellProject')}
                </button>
            </div>

            {isAdding && (
                <form onSubmit={handleAddWell} className="glass-panel p-6 mb-8 animate-in fade-in slide-in-from-top-4">
                    <h3 className="text-lg font-bold mb-4">{t('well.registerNewWell')}</h3>
                    <div className="flex gap-4">
                        <input
                            type="text"
                            value={newWellName}
                            onChange={(e) => setNewWellName(e.target.value)}
                            placeholder="e.g. WELL-X106-OFFSHORE"
                            className="input-field flex-1"
                            autoFocus
                        />
                        <button type="submit" className="btn-primary">{t('well.createProject')}</button>
                    </div>
                </form>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {wells.length === 0 ? (
                    <div className="col-span-2 glass-panel p-12 text-center text-white/20 italic">
                        {t('well.noWellsYet')}
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
                                    <p className="text-xs text-white/40">{well.location || t('well.locationNotSpecified')}</p>
                                </div>
                            </div>
                            <div className="flex items-center gap-4">
                                <button
                                    onClick={(e) => initiateDelete(e, well.id)}
                                    className="text-white/20 hover:text-red-500 transition-colors p-2 rounded-full hover:bg-white/5 z-20"
                                    title={t('well.deleteWellTitle')}
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
                title={t('well.deleteWellTitle')}
                message={t('well.deleteWellMessage')}
                confirmText={t('well.deleteProject')}
                variant="danger"
            />
        </div>
    );
};

export default WellSelector;
