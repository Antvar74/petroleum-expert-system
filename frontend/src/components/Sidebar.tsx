import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import {
    LayoutDashboard,
    Settings,
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
    ClipboardList,
    Wifi,
    WifiOff,
    Database,
    Search,
    LogOut,
    User,
} from 'lucide-react';
import api from '../lib/api';
import { useAuth, type AuthUser } from '../context/AuthContext';

interface SelectedWell {
    id: number;
    name: string;
    location?: string;
}

interface SidebarProps {
    currentView: string;
    setCurrentView: (view: string) => void;
    selectedWell?: SelectedWell | null;
    user?: AuthUser | null;
}

interface SystemHealth {
    api: string;
    llm: { status: string; providers?: Record<string, unknown> };
    agents: number;
    database: string;
}

const Sidebar: React.FC<SidebarProps> = ({ currentView, setCurrentView, selectedWell, user }) => {
    const { t } = useTranslation();
    const { logout } = useAuth();
    const [health, setHealth] = useState<SystemHealth | null>(null);
    const [healthError, setHealthError] = useState(false);

    useEffect(() => {
        const checkHealth = async () => {
            try {
                const res = await api.get(`/health`, { timeout: 5000 });
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
    const healthLabel = healthError ? t('sidebar.offline') : (!llmOk ? t('sidebar.llmError') : t('sidebar.operational'));
    const healthColor = healthError ? 'text-red-500' : (!llmOk ? 'text-yellow-500' : 'text-green-500');
    const healthBarWidth = healthError ? 'w-1/5' : (!llmOk ? 'w-3/5' : 'w-4/5');
    const healthBarColor = healthError ? 'bg-red-500' : (!llmOk ? 'bg-yellow-500' : 'bg-industrial-500');

    // Well display
    const wellInitials = selectedWell
        ? selectedWell.name.split(/[\s-]+/).map(w => w[0]).join('').slice(0, 2).toUpperCase()
        : 'PE';
    const wellDisplayName = selectedWell?.name || 'PetroExpert';
    const wellSubtitle = selectedWell?.location || t('sidebar.noWellSelected');

    // Engineering modules — work without a well selected
    const engineeringModules = [
        { id: 'module-dashboard', label: t('sidebar.engineeringDashboard'), icon: LayoutDashboard },
        { id: 'torque-drag', label: t('sidebar.torqueDrag'), icon: ArrowUpDown },
        { id: 'hydraulics', label: t('sidebar.hydraulicsECD'), icon: Droplets },
        { id: 'stuck-pipe', label: t('sidebar.stuckPipe'), icon: Lock },
        { id: 'well-control', label: t('sidebar.wellControl'), icon: Shield },
        { id: 'wellbore-cleanup', label: t('sidebar.wellboreCleanup'), icon: Waves },
        { id: 'packer-forces', label: t('sidebar.packerForces'), icon: Anchor },
        { id: 'workover-hydraulics', label: t('sidebar.workoverHydraulics'), icon: Wrench },
        { id: 'sand-control', label: t('sidebar.sandControl'), icon: Filter },
        { id: 'completion-design', label: t('sidebar.completionDesign'), icon: Layers },
        { id: 'shot-efficiency', label: t('sidebar.shotEfficiency'), icon: Target },
        { id: 'vibrations', label: t('sidebar.vibrations'), icon: Vibrate },
        { id: 'cementing', label: t('sidebar.cementing'), icon: Cylinder },
        { id: 'casing-design', label: t('sidebar.casingDesign'), icon: ShieldCheck },
    ];

    // Reporting — independent, manages its own well selection
    const reportingItems = [
        { id: 'daily-reports', label: t('sidebar.dailyReports'), icon: ClipboardList },
    ];

    // Well-dependent views — require a well to be selected
    const wellDependentItems = [
        { id: 'well-selector', label: t('sidebar.selectWell'), icon: Search },
        { id: 'dashboard', label: t('sidebar.eventAnalysis'), icon: Database },
    ];

    const bottomItems = [
        { id: 'settings', label: t('sidebar.settings'), icon: Settings },
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

                <nav className="space-y-1 flex-1 overflow-y-auto custom-scrollbar pr-2 -mr-2">
                    {/* Engineering Modules */}
                    <p className="text-[9px] font-bold uppercase tracking-[0.15em] text-white/20 px-5 pt-2 pb-1">{t('sidebar.engineeringModules')}</p>
                    {engineeringModules.map((item) => (
                        <button
                            key={item.id}
                            onClick={() => setCurrentView(item.id)}
                            className={`w-full flex items-center gap-4 px-5 py-3 rounded-2xl transition-all group flex-shrink-0 ${currentView === item.id
                                ? 'bg-industrial-600/10 text-industrial-500 border border-industrial-500/20 shadow-inner'
                                : 'text-white/40 hover:text-white hover:bg-white/5 border border-transparent'
                                } `}
                        >
                            <item.icon size={18} className={currentView === item.id ? 'text-industrial-500' : 'group-hover:scale-110 transition-transform'} />
                            <span className="font-bold text-xs tracking-tight">{item.label}</span>
                            {currentView === item.id && (
                                <div className="ml-auto">
                                    <ChevronRight size={14} />
                                </div>
                            )}
                        </button>
                    ))}

                    {/* Divider */}
                    <div className="my-3 border-t border-white/5" />

                    {/* Reporting — independent module */}
                    <p className="text-[9px] font-bold uppercase tracking-[0.15em] text-white/20 px-5 pt-1 pb-1">{t('sidebar.reporting')}</p>
                    {reportingItems.map((item) => (
                        <button
                            key={item.id}
                            onClick={() => setCurrentView(item.id)}
                            className={`w-full flex items-center gap-4 px-5 py-3 rounded-2xl transition-all group flex-shrink-0 ${currentView === item.id
                                ? 'bg-blue-600/10 text-blue-500 border border-blue-500/20 shadow-inner'
                                : 'text-white/40 hover:text-white hover:bg-white/5 border border-transparent'
                                } `}
                        >
                            <item.icon size={18} className={currentView === item.id ? 'text-blue-500' : 'group-hover:scale-110 transition-transform'} />
                            <span className="font-bold text-xs tracking-tight">{item.label}</span>
                            {currentView === item.id && (
                                <div className="ml-auto">
                                    <ChevronRight size={14} />
                                </div>
                            )}
                        </button>
                    ))}

                    {/* Divider */}
                    <div className="my-3 border-t border-white/5" />

                    {/* Well-dependent views */}
                    <p className="text-[9px] font-bold uppercase tracking-[0.15em] text-white/20 px-5 pt-1 pb-1">{t('sidebar.wellOperations')}</p>
                    {wellDependentItems.map((item) => (
                        <button
                            key={item.id}
                            onClick={() => setCurrentView(item.id)}
                            className={`w-full flex items-center gap-4 px-5 py-3 rounded-2xl transition-all group flex-shrink-0 ${currentView === item.id
                                ? 'bg-industrial-600/10 text-industrial-500 border border-industrial-500/20 shadow-inner'
                                : 'text-white/40 hover:text-white hover:bg-white/5 border border-transparent'
                                } `}
                        >
                            <item.icon size={18} className={currentView === item.id ? 'text-industrial-500' : 'group-hover:scale-110 transition-transform'} />
                            <span className="font-bold text-xs tracking-tight">{item.label}</span>
                            {currentView === item.id && (
                                <div className="ml-auto">
                                    <ChevronRight size={14} />
                                </div>
                            )}
                        </button>
                    ))}

                    {/* Divider */}
                    <div className="my-3 border-t border-white/5" />

                    {/* Settings */}
                    {bottomItems.map((item) => (
                        <button
                            key={item.id}
                            onClick={() => setCurrentView(item.id)}
                            className={`w-full flex items-center gap-4 px-5 py-3 rounded-2xl transition-all group flex-shrink-0 ${currentView === item.id
                                ? 'bg-industrial-600/10 text-industrial-500 border border-industrial-500/20 shadow-inner'
                                : 'text-white/40 hover:text-white hover:bg-white/5 border border-transparent'
                                } `}
                        >
                            <item.icon size={18} className={currentView === item.id ? 'text-industrial-500' : 'group-hover:scale-110 transition-transform'} />
                            <span className="font-bold text-xs tracking-tight">{item.label}</span>
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
                {/* User card */}
                {user && (
                    <div className="flex items-center gap-3 mb-4">
                        <div className="w-10 h-10 rounded-full bg-industrial-500/20 border border-industrial-500/30 flex items-center justify-center text-industrial-500 font-bold text-xs">
                            <User size={18} />
                        </div>
                        <div className="min-w-0 flex-1">
                            <p className="text-xs font-bold text-white truncate">{user.full_name || user.username}</p>
                            <p className="text-[10px] text-white/30 uppercase tracking-widest font-bold truncate">{user.role}</p>
                        </div>
                        <button
                            onClick={logout}
                            className="p-2 text-white/30 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
                            title={t('auth.logout')}
                        >
                            <LogOut size={16} />
                        </button>
                    </div>
                )}

                {/* Well info */}
                <div className="flex items-center gap-3 mb-4">
                    <div className="w-8 h-8 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center text-white/40 font-bold text-[10px]">
                        {wellInitials}
                    </div>
                    <div className="min-w-0 flex-1">
                        <p className="text-[11px] font-bold text-white/60 truncate">{wellDisplayName}</p>
                        <p className="text-[9px] text-white/20 uppercase tracking-widest font-bold truncate">{wellSubtitle}</p>
                    </div>
                </div>

                {/* Health bar */}
                <div className="bg-industrial-950 p-4 rounded-xl border border-white/5">
                    <div className="flex justify-between items-center mb-2">
                        <span className="text-[10px] font-bold text-white/40 uppercase tracking-tighter flex items-center gap-1.5">
                            {isHealthy ? <Wifi size={10} className="text-green-500" /> : <WifiOff size={10} className="text-red-500" />}
                            {t('sidebar.systemHealth')}
                        </span>
                        <span className={`text-[10px] font-bold uppercase tracking-tighter ${healthColor}`}>{healthLabel}</span>
                    </div>
                    <div className="h-1 bg-white/5 rounded-full overflow-hidden">
                        <div className={`h-full ${healthBarWidth} ${healthBarColor} rounded-full shadow-[0_0_8px_rgba(var(--industrial-500-rgb),0.5)] transition-all duration-500`} />
                    </div>
                    {health?.agents && (
                        <div className="mt-2 text-[9px] text-white/20 font-mono">
                            {health.agents} {t('sidebar.agents')} | {llmOk ? 'Gemini OK' : 'LLM N/A'}
                        </div>
                    )}
                </div>
            </div>
        </aside>
    );
};

export default Sidebar;
