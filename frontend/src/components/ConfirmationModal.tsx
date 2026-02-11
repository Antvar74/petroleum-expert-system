import React from 'react';
import { X, AlertTriangle } from 'lucide-react';

interface ConfirmationModalProps {
    isOpen: boolean;
    onClose: () => void;
    onConfirm: () => void;
    title: string;
    message: string;
    confirmText?: string;
    cancelText?: string;
    variant?: 'danger' | 'warning' | 'info';
}

const ConfirmationModal: React.FC<ConfirmationModalProps> = ({
    isOpen,
    onClose,
    onConfirm,
    title,
    message,
    confirmText = 'Confirm',
    cancelText = 'Cancel',
    variant = 'danger'
}) => {
    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
            <div 
                className="w-full max-w-md bg-[#0c0e12] border border-white/10 rounded-2xl shadow-2xl relative animate-in zoom-in-95 duration-200"
                onClick={(e) => e.stopPropagation()}
            >
                <button 
                    onClick={onClose}
                    className="absolute top-4 right-4 text-white/40 hover:text-white transition-colors"
                >
                    <X size={20} />
                </button>

                <div className="p-6">
                    <div className="w-12 h-12 rounded-full bg-red-500/10 flex items-center justify-center mb-4 text-red-500 mx-auto">
                        <AlertTriangle size={24} />
                    </div>
                    
                    <h3 className="text-xl font-bold text-center mb-2">{title}</h3>
                    <p className="text-white/60 text-center mb-6">{message}</p>

                    <div className="flex gap-3 justify-center">
                        <button 
                            onClick={onClose}
                            className="px-4 py-2 bg-white/5 hover:bg-white/10 text-white rounded-lg transition-colors font-medium border border-white/5"
                        >
                            {cancelText}
                        </button>
                        <button 
                            onClick={onConfirm}
                            className={`px-4 py-2 text-white rounded-lg transition-colors font-medium ${
                                variant === 'danger' 
                                    ? 'bg-red-600 hover:bg-red-500' 
                                    : 'bg-industrial-600 hover:bg-industrial-500'
                            }`}
                        >
                            {confirmText}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ConfirmationModal;
