import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Activity, AlertTriangle, Droplet } from 'lucide-react';
import { API_BASE_URL } from '../config';

interface PhysicsResultsProps {
    eventId: number;
}

const PhysicsResults: React.FC<PhysicsResultsProps> = ({ eventId }) => {
    const [results, setResults] = useState<any>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchResults = async () => {
            try {
                // In a real app, maybe poll or use websockets? 
                // For now, we assume calc was triggered on creation.
                // We'll call the calc endpoint again which is idempotent-ish (re-runs calc)
                // creating a specific GET endpoint would be better but POST /calculate returns results too.
                const response = await axios.post(`${API_BASE_URL}/events/${eventId}/calculate`);
                setResults(response.data.physics_results);
            } catch (error) {
                console.error("Failed to load physics:", error);
            } finally {
                setLoading(false);
            }
        };

        fetchResults();
    }, [eventId]);

    if (loading) return <div className="text-white/40 text-sm animate-pulse">Running Physics Engine...</div>;
    if (!results) return null;

    return (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6 animate-fadeIn">
            {/* ECD Card */}
            <div className={`p-4 rounded-lg border ${results.ecd.status.includes("High") ? 'bg-red-500/10 border-red-500/30' :
                    results.ecd.status.includes("Low") ? 'bg-yellow-500/10 border-yellow-500/30' :
                        'bg-green-500/10 border-green-500/30'
                }`}>
                <div className="flex items-center gap-2 mb-2">
                    <Droplet size={18} className={results.ecd.status.includes("Normal") ? "text-green-400" : "text-yellow-400"} />
                    <h4 className="font-bold text-white/80">ECD (Densidad Eq.)</h4>
                </div>
                <div className="text-2xl font-mono font-bold text-white">{results.ecd.value || "--"} <span className="text-sm text-white/50">ppg</span></div>
                <div className="text-xs text-white/60 mt-1">{results.ecd.status}</div>
            </div>

            {/* CCI Card */}
            <div className={`p-4 rounded-lg border ${results.cci.status.includes("Poor") ? 'bg-yellow-500/10 border-yellow-500/30' :
                    'bg-green-500/10 border-green-500/30'
                }`}>
                <div className="flex items-center gap-2 mb-2">
                    <Activity size={18} className={results.cci.status.includes("Poor") ? "text-yellow-400" : "text-green-400"} />
                    <h4 className="font-bold text-white/80">Indice Limpieza (CCI)</h4>
                </div>
                <div className="text-2xl font-mono font-bold text-white">{results.cci.value || "--"}</div>
                <div className="text-xs text-white/60 mt-1">Target &gt; {results.cci.target} ({results.cci.status})</div>
            </div>

            {/* Risk Card */}
            <div className={`p-4 rounded-lg border ${results.mechanical_risk.risk_level === "High" ? 'bg-red-500/10 border-red-500/30' :
                    results.mechanical_risk.risk_level === "Medium" ? 'bg-orange-500/10 border-orange-500/30' :
                        'bg-blue-500/10 border-blue-500/30'
                }`}>
                <div className="flex items-center gap-2 mb-2">
                    <AlertTriangle size={18} className={results.mechanical_risk.risk_level === "Low" ? "text-blue-400" : "text-red-400"} />
                    <h4 className="font-bold text-white/80">Riesgo Mecánico</h4>
                </div>
                <div className="text-2xl font-mono font-bold text-white">{results.mechanical_risk.risk_level}</div>
                <div className="text-xs text-white/60 mt-1">
                    {results.mechanical_risk.alerts.length > 0 ? results.mechanical_risk.alerts.join(", ") : "Operating within limits"}
                </div>
            </div>
        </div>
    );
};

export default PhysicsResults;
