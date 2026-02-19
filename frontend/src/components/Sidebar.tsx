import React from 'react';
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
    Vibrate
} from 'lucide-react';

interface SidebarProps {
    currentView: string;
    setCurrentView: (view: string) => void;
}

const Sidebar: React.FC<SidebarProps> = ({ currentView, setCurrentView }) => {
    const menuItems = [
        { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
        { id: 'analysis', label: 'Agent Pipeline', icon: Activity },
        { id: 'rca', label: 'RCA Tool', icon: GitBranch },
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
                    <div className="w-10 h-10 rounded-full bg-industrial-500/20 border border-industrial-500/30 flex items-center justify-center text-industrial-500 font-bold">
                        AV
                    </div>
                    <div>
                        <p className="text-xs font-bold text-white">Antonio Var.</p>
                        <p className="text-[10px] text-white/30 uppercase tracking-widest font-bold">Operations Dir.</p>
                    </div>
                </div>
                <div className="bg-industrial-950 p-4 rounded-xl border border-white/5">
                    <div className="flex justify-between items-center mb-2">
                        <span className="text-[10px] font-bold text-white/40 uppercase tracking-tighter">System Health</span>
                        <span className="text-[10px] font-bold text-green-500 uppercase tracking-tighter">Optimal</span>
                    </div>
                    <div className="h-1 bg-white/5 rounded-full overflow-hidden">
                        <div className="h-full w-4/5 bg-industrial-500 rounded-full shadow-[0_0_8px_rgba(var(--industrial-500-rgb),0.5)]" />
                    </div>
                </div>
            </div>
        </aside>
    );
};

export default Sidebar;
