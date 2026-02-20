import { useState } from 'react';
import axios from 'axios';
import { ArrowLeft, Activity, GitBranch, Loader2 } from 'lucide-react';
import { API_BASE_URL } from './config';
import { ToastProvider, useToast } from './components/ui/Toast';
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
import ModuleDashboard from './components/charts/dashboard/ModuleDashboard';

function AppContent() {
  const [currentView, setCurrentView] = useState('dashboard');
  const [selectedWell, setSelectedWell] = useState<any>(null);
  const [activeAnalysis, setActiveAnalysis] = useState<any>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitStep, setSubmitStep] = useState('');
  const { addToast } = useToast();

  const handleWellSelect = (well: any) => {
    setSelectedWell(well);
    setCurrentView('dashboard');
  };

  const handleEventSubmit = async (eventData: any) => {
    setIsSubmitting(true);
    try {
      // 1. Create the Structured Event record
      setSubmitStep('Creando registro del evento...');
      const payload = {
        ...eventData,
        well_id: selectedWell.id
      };

      const response = await axios.post(`${API_BASE_URL}/events`, payload);
      const { id: eventId } = response.data;

      // 2. Trigger Physics Calculation (Async)
      setSubmitStep('Ejecutando cálculos de física...');
      try {
        await axios.post(`${API_BASE_URL}/events/${eventId}/calculate`);
      } catch (calcError) {
        console.warn("Physics calculation failed:", calcError);
      }

      // 3. Initialize analysis directly from Event (no legacy Problem bridge)
      setSubmitStep('Inicializando pipeline de agentes...');
      const analysisResponse = await axios.post(`${API_BASE_URL}/events/${eventId}/analysis/init`, {
        workflow: eventData.workflow || "standard",
        leader: eventData.leader
      });

      setActiveAnalysis(analysisResponse.data);
      setCurrentView('analysis');
      addToast('Pipeline de análisis iniciado correctamente', 'success');
    } catch (error) {
      console.error("Error creating event/analysis:", error);
      addToast(`Error al iniciar análisis: ${error instanceof Error ? error.message : String(error)}`, 'error', 8000);
    } finally {
      setIsSubmitting(false);
      setSubmitStep('');
    }
  };

  const renderContent = () => {
    if (!selectedWell && currentView !== 'settings') {
      return <WellSelector onSelect={handleWellSelect} />;
    }

    switch (currentView) {
      case 'dashboard':
        return (
          <div className="w-full mx-auto py-12">
            <div className="mb-12">
              <h2 className="text-3xl font-bold mb-2">Nuevo Análisis de Evento: {selectedWell?.name}</h2>
              <p className="text-white/40">Usa el Asistente IA para identificar el evento y extraer parámetros técnicos.</p>
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
              onComplete={() => setCurrentView('rca')}
              onBack={() => setCurrentView('dashboard')}
            />
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-center p-12 animate-fadeIn">
            <div className="w-16 h-16 bg-white/5 rounded-full flex items-center justify-center mb-4">
              <Activity className="text-white/20" size={32} />
            </div>
            <h3 className="text-xl font-bold text-white mb-2">Sin Análisis en Progreso</h3>
            <p className="text-white/40 mb-6 max-w-md">
              Inicia un nuevo análisis de evento desde el Dashboard para ver el Pipeline de Agentes en acción.
            </p>
            <button
              onClick={() => setCurrentView('dashboard')}
              className="px-6 py-2 bg-industrial-600 hover:bg-industrial-700 text-white rounded-lg transition-colors font-medium"
            >
              Ir al Dashboard
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
            <h3 className="text-xl font-bold text-white mb-2">Sin Análisis de Causa Raíz</h3>
            <p className="text-white/40 mb-6 max-w-md">
              Completa un análisis de evento para generar un reporte RCA.
            </p>
            <button
              onClick={() => setCurrentView('dashboard')}
              className="px-6 py-2 bg-industrial-600 hover:bg-industrial-700 text-white rounded-lg transition-colors font-medium"
            >
              Iniciar Nuevo Análisis
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
      case 'settings':
        return <div className="p-12 text-center text-white/40 italic">Settings module coming soon in v3.1</div>;
      default:
        return <div className="p-12 text-center text-white/40">Select a module from the sidebar</div>;
    }
  };

  return (
    <div className="w-full flex h-screen overflow-hidden bg-industrial-950 text-white selection:bg-industrial-500/30">
      <Sidebar currentView={currentView} setCurrentView={setCurrentView} selectedWell={selectedWell} />

      <main className="flex-1 flex flex-col h-screen overflow-hidden">
        <header className="h-20 border-b border-white/5 bg-black/20 backdrop-blur-md flex items-center justify-between px-12 z-10">
          <div className="flex items-center gap-4">
            {selectedWell && (
              <button
                onClick={() => {
                  if (currentView === 'analysis' || currentView === 'rca') {
                    setCurrentView('dashboard');
                  } else if (currentView === 'dashboard') {
                    setSelectedWell(null);
                  } else {
                    setCurrentView('dashboard');
                  }
                }}
                className="p-2 mr-2 text-white/50 hover:text-white hover:bg-white/10 rounded-lg transition-colors"
                title={currentView === 'dashboard' ? 'Volver a Proyectos' : 'Volver'}
              >
                <ArrowLeft size={20} />
              </button>
            )}
            <div className="p-2 bg-industrial-600/10 rounded-lg text-industrial-500">
              {currentView === 'dashboard' && <span className="font-bold">Reporte de Problema Operacional</span>}
              {currentView === 'analysis' && <span className="font-bold">Pipeline Multi-Agente Especialista</span>}
              {currentView === 'rca' && <span className="font-bold">Análisis de Causa Raíz (RCA)</span>}
              {currentView === 'module-dashboard' && <span className="font-bold">Dashboard de Ingeniería</span>}
              {currentView === 'torque-drag' && <span className="font-bold">Torque & Drag Real-Time</span>}
              {currentView === 'hydraulics' && <span className="font-bold">Hidráulica / ECD Dinámico</span>}
              {currentView === 'stuck-pipe' && <span className="font-bold">Analizador de Pega de Tubería</span>}
              {currentView === 'well-control' && <span className="font-bold">Control de Pozo / Kill Sheet</span>}
              {currentView === 'wellbore-cleanup' && <span className="font-bold">Limpieza de Hoyo</span>}
              {currentView === 'packer-forces' && <span className="font-bold">Fuerzas de Packer / Análisis de Tubing</span>}
              {currentView === 'workover-hydraulics' && <span className="font-bold">Hidráulica de Workover / CT</span>}
              {currentView === 'sand-control' && <span className="font-bold">Control de Arena / Gravel Pack</span>}
              {currentView === 'completion-design' && <span className="font-bold">Diseño de Completación / Cañoneo & Fractura</span>}
              {currentView === 'shot-efficiency' && <span className="font-bold">Eficiencia de Disparo / Petrofísica</span>}
              {currentView === 'vibrations' && <span className="font-bold">Vibraciones & Estabilidad / Dinámica de Sarta</span>}
              {currentView === 'cementing' && <span className="font-bold">Simulación de Cementación / Desplazamiento & ECD</span>}
              {currentView === 'casing-design' && <span className="font-bold">Diseño de Casing / API 5C3 Burst-Collapse-Tension</span>}
            </div>
          </div>
          <div className="flex items-center gap-6">
            <div className="text-right">
              <p className="text-xs font-bold uppercase tracking-widest text-white/20">Estado del Activo</p>
              <p className="text-sm font-semibold text-green-500 flex items-center gap-2">
                <span className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse" />
                Activo: {selectedWell?.name || 'Sin pozo seleccionado'}
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
              <h3 className="text-lg font-bold text-white mb-1">Inicializando Análisis</h3>
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
    <ToastProvider>
      <AppContent />
    </ToastProvider>
  );
}

export default App;
