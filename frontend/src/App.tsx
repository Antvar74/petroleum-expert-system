import { useState } from 'react';
import axios from 'axios';
import { ArrowLeft, Activity, GitBranch } from 'lucide-react';
import Sidebar from './components/Sidebar';
import WellSelector from './components/WellSelector';
import EventWizard from './components/EventWizard'; // Changed from ProblemForm
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
import ModuleDashboard from './components/charts/dashboard/ModuleDashboard';



const API_BASE_URL = 'http://localhost:8000';

function App() {
  const [currentView, setCurrentView] = useState('dashboard');
  const [selectedWell, setSelectedWell] = useState<any>(null);
  const [activeAnalysis, setActiveAnalysis] = useState<any>(null);

  const handleWellSelect = (well: any) => {
    setSelectedWell(well);
    setCurrentView('dashboard');
  };

  const handleEventSubmit = async (eventData: any) => {
    try {
      // 1. Create the Structured Event record
      const payload = {
        ...eventData,
        well_id: selectedWell.id
      };

      const response = await axios.post(`${API_BASE_URL}/events`, payload);
      const { id: eventId, problem_id: legacyProblemId } = response.data;

      // 2. Trigger Physics Calculation (Async)
      // We don't block the UI for this, but we fire it off.
      try {
        await axios.post(`${API_BASE_URL}/events/${eventId}/calculate`);
      } catch (calcError) {
        console.warn("Physics calculation failed:", calcError);
      }

      // 3. Initialize analysis using legacy pipeline (for now)
      // We use the legacy_problem_id to bridge to the existing Agents
      const analysisResponse = await axios.post(`${API_BASE_URL}/problems/${legacyProblemId}/analysis/init`, {
        workflow: eventData.workflow || "standard",
        leader: eventData.leader
      });

      setActiveAnalysis(analysisResponse.data);
      setCurrentView('analysis');
    } catch (error) {
      console.error("Error creating event/analysis:", error);
      alert(`Failed to start analysis: ${error instanceof Error ? error.message : String(error)}`);
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
              <h2 className="text-3xl font-bold mb-2">New Event Analysis: {selectedWell?.name}</h2>
              <p className="text-white/40">Use the AI Wizard to identify the event and extract technical parameters.</p>
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
            />
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-center p-12 animate-fadeIn">
            <div className="w-16 h-16 bg-white/5 rounded-full flex items-center justify-center mb-4">
              <Activity className="text-white/20" size={32} />
            </div>
            <h3 className="text-xl font-bold text-white mb-2">No Analysis in Progress</h3>
            <p className="text-white/40 mb-6 max-w-md">
              Start a new event analysis from the Dashboard to see the Agent Pipeline in action.
            </p>
            <button
              onClick={() => setCurrentView('dashboard')}
              className="px-6 py-2 bg-industrial-600 hover:bg-industrial-700 text-white rounded-lg transition-colors font-medium"
            >
              Go to Dashboard
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
            <h3 className="text-xl font-bold text-white mb-2">No Root Cause Analysis</h3>
            <p className="text-white/40 mb-6 max-w-md">
              Complete an event analysis to generate an RCA report.
            </p>
            <button
              onClick={() => setCurrentView('dashboard')}
              className="px-6 py-2 bg-industrial-600 hover:bg-industrial-700 text-white rounded-lg transition-colors font-medium"
            >
              Start New Analysis
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
      case 'settings':
        return <div className="p-12 text-center text-white/40 italic">Settings module coming soon in v3.1</div>;
      default:
        return <div className="p-12 text-center text-white/40">Select a module from the sidebar</div>;
    }
  };

  return (
    <div className="w-full flex h-screen overflow-hidden bg-industrial-950 text-white selection:bg-industrial-500/30">
      <Sidebar currentView={currentView} setCurrentView={setCurrentView} />

      <main className="flex-1 flex flex-col h-screen overflow-hidden">
        <header className="h-20 border-b border-white/5 bg-black/20 backdrop-blur-md flex items-center justify-between px-12 z-10">
          <div className="flex items-center gap-4">
            {selectedWell && (
              <button
                onClick={() => setSelectedWell(null)}
                className="p-2 mr-2 text-white/50 hover:text-white hover:bg-white/10 rounded-lg transition-colors"
                title="Back to Projects"
              >
                <ArrowLeft size={20} />
              </button>
            )}
            <div className="p-2 bg-industrial-600/10 rounded-lg text-industrial-500">
              {currentView === 'dashboard' && <span className="font-bold">Operational Problem Report</span>}
              {currentView === 'analysis' && <span className="font-bold">Multi-Agent Specialist Pipeline</span>}
              {currentView === 'rca' && <span className="font-bold">Elite Root Cause Analysis</span>}
              {currentView === 'module-dashboard' && <span className="font-bold">Engineering Dashboard</span>}
              {currentView === 'torque-drag' && <span className="font-bold">Torque & Drag Real-Time</span>}
              {currentView === 'hydraulics' && <span className="font-bold">Hydraulics / ECD Dynamic</span>}
              {currentView === 'stuck-pipe' && <span className="font-bold">Stuck Pipe Analyzer</span>}
              {currentView === 'well-control' && <span className="font-bold">Well Control / Kill Sheet</span>}
              {currentView === 'wellbore-cleanup' && <span className="font-bold">Wellbore Cleanup / Hole Cleaning</span>}
              {currentView === 'packer-forces' && <span className="font-bold">Packer Forces / Tubing Analysis</span>}
              {currentView === 'workover-hydraulics' && <span className="font-bold">Workover Hydraulics / CT Operations</span>}
              {currentView === 'sand-control' && <span className="font-bold">Sand Control / Gravel Pack Design</span>}
              {currentView === 'completion-design' && <span className="font-bold">Completion Design / Perforating & Fracture</span>}
              {currentView === 'shot-efficiency' && <span className="font-bold">Shot Efficiency / Petrophysics & Intervals</span>}
              {currentView === 'vibrations' && <span className="font-bold">Vibrations & Stability / Drillstring Dynamics</span>}
            </div>
          </div>
          <div className="flex items-center gap-6">
            <div className="text-right">
              <p className="text-xs font-bold uppercase tracking-widest text-white/20">Asset Status</p>
              <p className="text-sm font-semibold text-green-500 flex items-center gap-2">
                <span className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse" />
                Live: {selectedWell?.name || 'No well selected'}
              </p>
            </div>
          </div>
        </header>

        <section className="flex-1 overflow-y-auto px-12 custom-scrollbar">
          {renderContent()}
        </section>
      </main>
    </div>
  );
}

export default App;
