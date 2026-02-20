import React, { useState, useEffect } from 'react';
import {
    LayoutDashboard,
    Settings,
    Activity,
    GitBranch,
    Box,
    ChevronRight,
    ArrowUpDown,
    Droplets,
    Lock,
    Shield,
    Waves,
    Anchor,
    Wrench,
    Filter,
    Layers,
    Target,
    Vibrate,
    Cylinder,
    ShieldCheck,
    Wifi,
    WifiOff
} from 'lucide-react';
import axios from 'axios';
import { API_BASE_URL } from '../config';

interface SelectedWell {
    id: number;
    name: string;
    location?: string;
}

interface SidebarProps {
    currentView: string;
    setCurrentView: (view: string) => void;
    selectedWell?: SelectedWell | null;
}

interface SystemHealth {
    api: string;
    llm: { status: string; providers?: any };
    agents: number;
    database: string;
}

const Sidebar: React.FC<SidebarProps> = ({ currentView, setCurrentView, selectedWell }) => {
    const [health, setHealth] = useState<SystemHealth | null>(null);
    const [healthError, setHealthError] = useState(false);

    useEffect(() => {
        const checkHealth = async () => {
            try {
                const res = await axios.get(`${API_BASE_URL}/health`, { timeout: 5000 });
                setHealth(res.data);
                setHealthError(false);
            } catch {
                setHealthError(true);
            }
        };

        checkHealth();
        const interval = setInterval(checkHealth, 30000); // Check every 30s
        return () => clearInterval(interval);
    }, []);

    // Compute health display
    const isHealthy = health && !healthError && health.api === 'ok';
    const llmOk = health?.llm?.status === 'ok';
    const healthLabel = healthError ? 'Offline' : (!llmOk ? 'LLM Error' : 'Operational');
    const healthColor = healthError ? 'text-red-500' : (!llmOk ? 'text-yellow-500' : 'text-green-500');
    const healthBarWidth = healthError ? 'w-1/5' : (!llmOk ? 'w-3/5' : 'w-4/5');
    const healthBarColor = healthError ? 'bg-red-500' : (!llmOk ? 'bg-yellow-500' : 'bg-industrial-500');

    // Well display
    const wellInitials = selectedWell
        ? selectedWell.name.split(/[\s-]+/).map(w => w[0]).join('').slice(0, 2).toUpperCase()
        : 'PE';
    const wellDisplayName = selectedWell?.name || 'PetroExpert';
    const wellSubtitle = selectedWell?.location || 'Sin pozo seleccionado';

    const menuItems = [
        { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
        { id: 'analysis', label: 'Pipeline de Agentes', icon: Activity },
        { id: 'rca', label: 'Herramienta RCA', icon: GitBranch },
        { id: 'torque-drag', label: 'Torque & Drag', icon: ArrowUpDown },
        { id: 'hydraulics', label: 'Hydraulics/ECD', icon: Droplets },
        { id: 'stuck-pipe', label: 'Stuck Pipe', icon: Lock },
        { id: 'well-control', label: 'Well Control', icon: Shield },
        { id: 'wellbore-cleanup', label: 'Wellbore Cleanup', icon: Waves },
        { id: 'packer-forces', label: 'Packer Forces', icon: Anchor },
        { id: 'workover-hydraulics', label: 'Workover Hyd.', icon: Wrench },
        { id: 'sand-control', label: 'Sand Control', icon: Filter },
        { id: 'completion-design', label: 'Completion Design', icon: Layers },
        { id: 'shot-efficiency', label: 'Shot Efficiency', icon: Target },
        { id: 'vibrations', label: 'Vibrations', icon: Vibrate },
        { id: 'cementing', label: 'Cementing', icon: Cylinder },
        { id: 'casing-design', label: 'Casing Design', icon: ShieldCheck },
        { id: 'settings', label: 'Settings', icon: Settings },
    ];

    return (
        <aside className="w-72 bg-black/40 border-r border-white/5 flex flex-col h-screen backdrop-blur-xl z-20">
            <div className="p-8 flex-1 flex flex-col min-h-0">
                <div className="flex items-center gap-3 mb-10 overflow-hidden">
                    <div className="w-10 h-10 bg-industrial-600 rounded-xl flex items-center justify-center shadow-lg shadow-industrial-900/40 flex-shrink-0 animate-pulse">
                        <Box className="text-white" size={24} />
                    </div>
                    <div className="flex flex-col">
                        <h1 className="text-xl font-bold tracking-tighter text-white">PETRO<span className="text-industrial-500">EXPERT</span></h1>
                        <span className="text-[10px] uppercase tracking-[0.2em] font-bold text-white/30">System v3.0 Elite</span>
                    </div>
                </div>

                <nav className="space-y-2 flex-1 overflow-y-auto custom-scrollbar pr-2 -mr-2">
                    {menuItems.map((item) => (
                        <button
                            key={item.id}
                            onClick={() => setCurrentView(item.id)}
                            className={`w-full flex items-center gap-4 px-5 py-4 rounded-2xl transition-all group flex-shrink-0 ${currentView === item.id
                                ? 'bg-industrial-600/10 text-industrial-500 border border-industrial-500/20 shadow-inner'
                                : 'text-white/40 hover:text-white hover:bg-white/5 border border-transparent'
                                } `}
                        >
                            <item.icon size={20} className={currentView === item.id ? 'text-industrial-500' : 'group-hover:scale-110 transition-transform'} />
                            <span className="font-bold text-sm tracking-tight">{item.label}</span>
                            {currentView === item.id && (
                                <div className="ml-auto">
                                    <ChevronRight size={14} />
                                </div>
                            )}
                        </button>
                    ))}
                </nav>
            </div>

            <div className="flex-shrink-0 p-8 border-t border-white/5 bg-white/5">
                <div className="flex items-center gap-4 mb-4">
                    <div className="w-10 h-10 rounded-full bg-industrial-500/20 border border-industrial-500/30 flex items-center justify-center text-industrial-500 font-bold text-xs">
                        {wellInitials}
                    </div>
                    <div className="min-w-0 flex-1">
                        <p className="text-xs font-bold text-white truncate">{wellDisplayName}</p>
                        <p className="text-[10px] text-white/30 uppercase tracking-widest font-bold truncate">{wellSubtitle}</p>
                    </div>
                </div>
                <div className="bg-industrial-950 p-4 rounded-xl border border-white/5">
                    <div className="flex justify-between items-center mb-2">
                        <span className="text-[10px] font-bold text-white/40 uppercase tracking-tighter flex items-center gap-1.5">
                            {isHealthy ? <Wifi size={10} className="text-green-500" /> : <WifiOff size={10} className="text-red-500" />}
                            System Health
                        </span>
                        <span className={`text-[10px] font-bold uppercase tracking-tighter ${healthColor}`}>{healthLabel}</span>
                    </div>
                    <div className="h-1 bg-white/5 rounded-full overflow-hidden">
                        <div className={`h-full ${healthBarWidth} ${healthBarColor} rounded-full shadow-[0_0_8px_rgba(var(--industrial-500-rgb),0.5)] transition-all duration-500`} />
                    </div>
                    {health?.agents && (
                        <div className="mt-2 text-[9px] text-white/20 font-mono">
                            {health.agents} agents | {llmOk ? 'Gemini OK' : 'LLM N/A'}
                        </div>
                    )}
                </div>
            </div>
        </aside>
    );
};

export default Sidebar;
