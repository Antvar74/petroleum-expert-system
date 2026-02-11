import { useState } from 'react';
import axios from 'axios';
import { ArrowLeft } from 'lucide-react';
import Sidebar from './components/Sidebar';
import WellSelector from './components/WellSelector';
import ProblemForm from './components/ProblemForm';
import AnalysisDashboard from './components/AnalysisDashboard';
import RCAVisualizer from './components/RCAVisualizer';

import OptimizationTools from './components/OptimizationTools';

const API_BASE_URL = 'http://localhost:8000';

function App() {
  const [currentView, setCurrentView] = useState('dashboard');
  const [selectedWell, setSelectedWell] = useState<any>(null);
  const [activeAnalysis, setActiveAnalysis] = useState<any>(null);

  const handleWellSelect = (well: any) => {
    setSelectedWell(well);
    setCurrentView('dashboard');
  };

  const handleProblemSubmit = async (problemData: any) => {
    try {
      const response = await axios.post(`${API_BASE_URL}/wells/${selectedWell.id}/problems`, problemData);

      const analysisResponse = await axios.post(`${API_BASE_URL}/problems/${response.data.id}/analysis/init`);
      setActiveAnalysis(analysisResponse.data);
      setCurrentView('analysis');
    } catch (error) {
      console.error("Error creating analysis:", error);
    }
  };

  const renderContent = () => {
    if (!selectedWell && currentView !== 'settings') {
      return <WellSelector onSelect={handleWellSelect} />;
    }

    switch (currentView) {
      case 'dashboard':
        return (
          <div className="max-w-4xl mx-auto py-12">
            <div className="mb-12">
              <h2 className="text-3xl font-bold mb-2">Well Operation: {selectedWell?.name}</h2>
              <p className="text-white/40">Enter the operational parameters to initiate the specialist agent pipeline.</p>
            </div>
            <ProblemForm onSubmit={handleProblemSubmit} />
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
          <div className="text-center py-20 text-white/20">No active analysis. Go to Dashboard to start.</div>
        );
      case 'optimization':
        return <div className="py-12"><OptimizationTools /></div>;
      case 'rca':
        return <div className="py-12"><RCAVisualizer analysisData={activeAnalysis} analysisId={activeAnalysis?.id} /></div>;
      case 'settings':
        return <div className="p-12 text-center text-white/40 italic">Settings module coming soon in v3.1</div>;
      default:
        return <div className="p-12 text-center text-white/40">Select a module from the sidebar</div>;
    }
  };

  return (
    <div className="flex min-h-screen bg-industrial-950 text-white selection:bg-industrial-500/30">
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
              {currentView === 'optimization' && <span className="font-bold">Technical Optimization Engine</span>}
              {currentView === 'rca' && <span className="font-bold">Elite Root Cause Analysis</span>}
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
