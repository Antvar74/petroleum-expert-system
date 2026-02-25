import { useState } from 'react';
import type { Well } from './types/api';
import { useTranslation } from 'react-i18next';
import { ArrowLeft, Activity, GitBranch, Loader2, Database } from 'lucide-react';
import LanguageSelector from './components/LanguageSelector';
import api from './lib/api';
import { ToastProvider, useToast } from './components/ui/Toast';
import { AuthProvider, useAuth } from './context/AuthContext';
import LoginPage from './components/LoginPage';
import Sidebar from './components/Sidebar';
import WellSelector from './components/WellSelector';
import EventWizard from './components/EventWizard';
import AnalysisDashboard from './components/AnalysisDashboard';
import RCAVisualizer from './components/RCAVisualizer';
import TorqueDragModule from './components/TorqueDragModule';
import HydraulicsModule from './components/HydraulicsModule';
import StuckPipeAnalyzer from './components/StuckPipeAnalyzer';
import WellControlModule from './components/WellControlModule';
import WellboreCleanupModule from './components/WellboreCleanupModule';
import PackerForcesModule from './components/PackerForcesModule';
import WorkoverHydraulicsModule from './components/WorkoverHydraulicsModule';
import SandControlModule from './components/SandControlModule';
import CompletionDesignModule from './components/CompletionDesignModule';
import ShotEfficiencyModule from './components/ShotEfficiencyModule';
import VibrationsModule from './components/VibrationsModule';
import CementingModule from './components/CementingModule';
import CasingDesignModule from './components/CasingDesignModule';
import DailyReportsModule from './components/DailyReportsModule';
import PetrophysicsModule from './components/PetrophysicsModule';
import ModuleDashboard from './components/charts/dashboard/ModuleDashboard';

function AppContent() {
  const { t } = useTranslation();
  const { user, isLoading } = useAuth();
  const [currentView, setCurrentView] = useState('module-dashboard');
  const [selectedWell, setSelectedWell] = useState<Well | null>(null);
  const [activeAnalysis, setActiveAnalysis] = useState<{id: number; analysis_id: number; workflow: string[]} | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitStep, setSubmitStep] = useState('');
  const { addToast } = useToast();

  // Auth loading spinner
  if (isLoading) {
    return (
      <div className="min-h-screen bg-industrial-950 flex items-center justify-center">
        <Loader2 size={40} className="text-industrial-500 animate-spin" />
      </div>
    );
  }

  // Not authenticated — show login page
  if (!user) {
    return <LoginPage />;
  }

  const handleWellSelect = (well: Well) => {
    setSelectedWell(well);
    setCurrentView('dashboard');
  };

  const handleEventSubmit = async (eventData: Record<string, unknown>) => {
    setIsSubmitting(true);
    try {
      // 1. Create the Structured Event record
      setSubmitStep(t('app.creatingEvent'));
      const payload = {
        ...eventData,
        well_id: selectedWell.id
      };

      const response = await api.post(`/events`, payload);
      const { id: eventId } = response.data;

      // 2. Trigger Physics Calculation (Async)
      setSubmitStep(t('app.runningPhysics'));
      try {
        await api.post(`/events/${eventId}/calculate`);
      } catch (calcError) {
        console.warn("Physics calculation failed:", calcError);
      }

      // 3. Initialize analysis directly from Event (no legacy Problem bridge)
      setSubmitStep(t('app.initializingPipeline'));
      const analysisResponse = await api.post(`/events/${eventId}/analysis/init`, {
        workflow: eventData.workflow || "standard",
        leader: eventData.leader
      });

      setActiveAnalysis(analysisResponse.data);
      setCurrentView('analysis');
      addToast(t('app.pipelineStarted'), 'success');
    } catch (error) {
      console.error("Error creating event/analysis:", error);
      addToast(`${t('app.errorStartingAnalysis')} ${error instanceof Error ? error.message : String(error)}`, 'error', 8000);
    } finally {
      setIsSubmitting(false);
      setSubmitStep('');
    }
  };

  // Views that REQUIRE a well to be selected (event-based workflow)
  const WELL_REQUIRED_VIEWS = new Set(['dashboard', 'analysis', 'rca']);

  const renderContent = () => {
    // Only gate well-dependent views — calculators work without a well
    if (!selectedWell && WELL_REQUIRED_VIEWS.has(currentView)) {
      return (
        <div className="flex flex-col items-center justify-center h-full text-center p-12 animate-fadeIn">
          <div className="w-20 h-20 bg-industrial-600/10 rounded-2xl flex items-center justify-center mb-6 border border-industrial-500/20">
            <Database className="text-industrial-500" size={36} />
          </div>
          <h3 className="text-2xl font-bold text-white mb-3">{t('app.wellRequired')}</h3>
          <p className="text-white/40 mb-8 max-w-md">{t('app.wellRequiredDescription')}</p>
          <button
            onClick={() => setCurrentView('well-selector')}
            className="px-8 py-3 bg-industrial-600 hover:bg-industrial-700 text-white rounded-xl transition-colors font-bold text-sm tracking-tight"
          >
            {t('app.selectWell')}
          </button>
        </div>
      );
    }

    switch (currentView) {
      case 'well-selector':
        return <WellSelector onSelect={handleWellSelect} />;
      case 'dashboard':
        return (
          <div className="w-full mx-auto py-12">
            <div className="mb-12">
              <h2 className="text-3xl font-bold mb-2">{t('app.newEventAnalysis')} {selectedWell?.name}</h2>
              <p className="text-white/40">{t('app.eventWizardSubtitle')}</p>
            </div>
            <EventWizard
              onComplete={handleEventSubmit}
              onCancel={() => setSelectedWell(null)}
            />
          </div>
        );
      case 'analysis':
        return activeAnalysis ? (
          <div className="py-12">
            <AnalysisDashboard
              analysisId={activeAnalysis.id}
              workflow={activeAnalysis.workflow || activeAnalysis.workflow_used || []}
              onBack={() => setCurrentView('dashboard')}
            />
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-center p-12 animate-fadeIn">
            <div className="w-16 h-16 bg-white/5 rounded-full flex items-center justify-center mb-4">
              <Activity className="text-white/20" size={32} />
            </div>
            <h3 className="text-xl font-bold text-white mb-2">{t('app.noAnalysisInProgress')}</h3>
            <p className="text-white/40 mb-6 max-w-md">
              {t('app.noAnalysisDescription')}
            </p>
            <button
              onClick={() => setCurrentView('dashboard')}
              className="px-6 py-2 bg-industrial-600 hover:bg-industrial-700 text-white rounded-lg transition-colors font-medium"
            >
              {t('app.goToDashboard')}
            </button>
          </div>
        );

      case 'rca':
        return activeAnalysis ? (
          <div className="py-12"><RCAVisualizer report={activeAnalysis} /></div>
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-center p-12 animate-fadeIn">
            <div className="w-16 h-16 bg-white/5 rounded-full flex items-center justify-center mb-4">
              <GitBranch className="text-white/20" size={32} />
            </div>
            <h3 className="text-xl font-bold text-white mb-2">{t('app.noRCA')}</h3>
            <p className="text-white/40 mb-6 max-w-md">
              {t('app.noRCADescription')}
            </p>
            <button
              onClick={() => setCurrentView('dashboard')}
              className="px-6 py-2 bg-industrial-600 hover:bg-industrial-700 text-white rounded-lg transition-colors font-medium"
            >
              {t('app.startNewAnalysis')}
            </button>
          </div>
        );
      case 'module-dashboard':
        return <ModuleDashboard onNavigate={setCurrentView} wellId={selectedWell?.id} />;
      case 'torque-drag':
        return <TorqueDragModule wellId={selectedWell?.id} wellName={selectedWell?.name || ''} />;
      case 'hydraulics':
        return <HydraulicsModule wellId={selectedWell?.id} wellName={selectedWell?.name || ''} />;
      case 'stuck-pipe':
        return <StuckPipeAnalyzer wellId={selectedWell?.id} wellName={selectedWell?.name || ''} />;
      case 'well-control':
        return <WellControlModule wellId={selectedWell?.id} wellName={selectedWell?.name || ''} />;
      case 'wellbore-cleanup':
        return <WellboreCleanupModule wellId={selectedWell?.id} wellName={selectedWell?.name || ''} />;
      case 'packer-forces':
        return <PackerForcesModule wellId={selectedWell?.id} wellName={selectedWell?.name || ''} />;
      case 'workover-hydraulics':
        return <WorkoverHydraulicsModule wellId={selectedWell?.id} wellName={selectedWell?.name || ''} />;
      case 'sand-control':
        return <SandControlModule wellId={selectedWell?.id} wellName={selectedWell?.name || ''} />;
      case 'completion-design':
        return <CompletionDesignModule wellId={selectedWell?.id} wellName={selectedWell?.name || ''} />;
      case 'shot-efficiency':
        return <ShotEfficiencyModule wellId={selectedWell?.id} wellName={selectedWell?.name || ''} />;
      case 'vibrations':
        return <VibrationsModule wellId={selectedWell?.id} wellName={selectedWell?.name || ''} />;
      case 'cementing':
        return <CementingModule wellId={selectedWell?.id} wellName={selectedWell?.name || ''} />;
      case 'casing-design':
        return <CasingDesignModule wellId={selectedWell?.id} wellName={selectedWell?.name || ''} />;
      case 'daily-reports':
        return <DailyReportsModule />;
      case 'petrophysics':
        return <PetrophysicsModule wellId={selectedWell?.id} wellName={selectedWell?.name || ''} />;
      case 'settings':
        return <div className="p-12 text-center text-white/40 italic">{t('app.settingsComingSoon')}</div>;
      default:
        return <div className="p-12 text-center text-white/40">{t('app.selectModule')}</div>;
    }
  };

  return (
    <div className="w-full flex h-screen overflow-hidden bg-industrial-950 text-white selection:bg-industrial-500/30">
      <Sidebar currentView={currentView} setCurrentView={setCurrentView} selectedWell={selectedWell} user={user} />

      <main className="flex-1 flex flex-col h-screen overflow-hidden">
        <header className="h-20 border-b border-white/5 bg-black/20 backdrop-blur-md flex items-center justify-between px-12 z-10">
          <div className="flex items-center gap-4">
            {currentView !== 'module-dashboard' && (
              <button
                onClick={() => {
                  if (currentView === 'analysis' || currentView === 'rca') {
                    setCurrentView('dashboard');
                  } else if (currentView === 'dashboard') {
                    setSelectedWell(null);
                    setCurrentView('module-dashboard');
                  } else if (currentView === 'well-selector') {
                    setCurrentView('module-dashboard');
                  } else {
                    setCurrentView('module-dashboard');
                  }
                }}
                className="p-2 mr-2 text-white/50 hover:text-white hover:bg-white/10 rounded-lg transition-colors"
                title={t('app.back')}
              >
                <ArrowLeft size={20} />
              </button>
            )}
            <div className="p-2 bg-industrial-600/10 rounded-lg text-industrial-500">
              {currentView === 'well-selector' && <span className="font-bold">{t('app.selectWell')}</span>}
              {currentView === 'dashboard' && <span className="font-bold">{t('app.operationalReport')}</span>}
              {currentView === 'analysis' && <span className="font-bold">{t('app.multiAgentPipeline')}</span>}
              {currentView === 'rca' && <span className="font-bold">{t('app.rootCauseAnalysis')}</span>}
              {currentView === 'module-dashboard' && <span className="font-bold">{t('app.engineeringDashboard')}</span>}
              {currentView === 'torque-drag' && <span className="font-bold">{t('app.torqueDragTitle')}</span>}
              {currentView === 'hydraulics' && <span className="font-bold">{t('app.hydraulicsECD')}</span>}
              {currentView === 'stuck-pipe' && <span className="font-bold">{t('app.stuckPipeAnalyzer')}</span>}
              {currentView === 'well-control' && <span className="font-bold">{t('app.wellControlKillSheet')}</span>}
              {currentView === 'wellbore-cleanup' && <span className="font-bold">{t('app.wellboreCleanup')}</span>}
              {currentView === 'packer-forces' && <span className="font-bold">{t('app.packerForcesTubing')}</span>}
              {currentView === 'workover-hydraulics' && <span className="font-bold">{t('app.workoverCT')}</span>}
              {currentView === 'sand-control' && <span className="font-bold">{t('app.sandControlGP')}</span>}
              {currentView === 'completion-design' && <span className="font-bold">{t('app.completionDesignFrac')}</span>}
              {currentView === 'shot-efficiency' && <span className="font-bold">{t('app.shotEfficiencyPetro')}</span>}
              {currentView === 'vibrations' && <span className="font-bold">{t('app.vibrationsDynamics')}</span>}
              {currentView === 'cementing' && <span className="font-bold">{t('app.cementingSimulation')}</span>}
              {currentView === 'casing-design' && <span className="font-bold">{t('app.casingDesignAPI')}</span>}
            </div>
          </div>
          <div className="flex items-center gap-6">
            <LanguageSelector />
            <div className="text-right">
              <p className="text-xs font-bold uppercase tracking-widest text-white/20">{t('app.assetStatus')}</p>
              <p className="text-sm font-semibold text-green-500 flex items-center gap-2">
                <span className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse" />
                {t('app.active')} {selectedWell?.name || t('app.noWellSelected')}
              </p>
            </div>
          </div>
        </header>

        <section className="flex-1 overflow-y-auto px-12 custom-scrollbar">
          {renderContent()}
        </section>
      </main>

      {/* Loading Overlay */}
      {isSubmitting && (
        <div className="fixed inset-0 z-[9998] bg-black/60 backdrop-blur-sm flex items-center justify-center">
          <div className="bg-industrial-950 border border-white/10 rounded-2xl p-10 flex flex-col items-center gap-5 shadow-2xl max-w-sm">
            <Loader2 size={40} className="text-industrial-500 animate-spin" />
            <div className="text-center">
              <h3 className="text-lg font-bold text-white mb-1">{t('app.initializingAnalysis')}</h3>
              <p className="text-sm text-white/50 animate-pulse">{submitStep}</p>
            </div>
            <div className="w-full h-1 bg-white/5 rounded-full overflow-hidden">
              <div className="h-full bg-industrial-500 rounded-full animate-[loading_2s_ease-in-out_infinite]" style={{ width: '60%' }} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function App() {
  return (
    <AuthProvider>
      <ToastProvider>
        <AppContent />
      </ToastProvider>
    </AuthProvider>
  );
}

export default App;
