import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API_BASE_URL } from '../config';
import { Check, Info } from 'lucide-react';

interface Agent {
    id: string;
    role: string;
    name: string;
}

interface AgentSelectorProps {
    onSelectionChange: (selectedAgentIds: string[]) => void;
}

const AgentSelector: React.FC<AgentSelectorProps> = ({ onSelectionChange }) => {
    const [allAgents, setAllAgents] = useState<Agent[]>([]);
    const [selectedAgents, setSelectedAgents] = useState<string[]>([]);
    const [loading, setLoading] = useState(true);

    // Default workflow order to preset
    const defaultOrder = [
        "rca_lead",
        "drilling_engineer",
        "hydrologist",
        "geologist",
        "mud_engineer",
        "well_engineer"
    ];

    useEffect(() => {
        const fetchAgents = async () => {
            try {
                const res = await axios.get(`${API_BASE_URL}/agents`);
                setAllAgents(res.data);

                // Initialize with default workflow intersection
                // Use defaultOrder but filter by available agents
                const availableIds = res.data.map((a: Agent) => a.id);
                const initial = defaultOrder.filter(id => availableIds.includes(id));

                // Add any missing agents to the end? Or just stick to default?
                // Let's stick to default for now

                setSelectedAgents(initial);
                onSelectionChange(initial);
            } catch (error) {
                console.error("Error fetching agents:", error);
            } finally {
                setLoading(false);
            }
        };

        fetchAgents();
    }, []);

    const toggleAgent = (agentId: string) => {
        let newSelection;
        if (selectedAgents.includes(agentId)) {
            newSelection = selectedAgents.filter(id => id !== agentId);
        } else {
            newSelection = [...selectedAgents, agentId];
        }
        setSelectedAgents(newSelection);
        onSelectionChange(newSelection);
    };

    const moveAgent = (index: number, direction: 'up' | 'down') => {
        if (direction === 'up' && index === 0) return;
        if (direction === 'down' && index === selectedAgents.length - 1) return;

        const newSelection = [...selectedAgents];
        const swapIndex = direction === 'up' ? index - 1 : index + 1;

        [newSelection[index], newSelection[swapIndex]] = [newSelection[swapIndex], newSelection[index]];

        setSelectedAgents(newSelection);
        onSelectionChange(newSelection);
    };

    if (loading) return <div className="text-white/40 text-xs">Loading specialists...</div>;

    return (
        <div className="space-y-4">
            <div className="flex items-center gap-2 mb-2">
                <label className="text-xs font-bold text-white/40 uppercase tracking-wider">Analysis Team & Workflow</label>
                <div className="group relative">
                    <Info size={12} className="text-white/20 cursor-help" />
                    <div className="absolute bottom-full mb-2 left-1/2 -translate-x-1/2 w-64 bg-black/90 p-3 rounded text-[10px] text-white/70 hidden group-hover:block z-10">
                        Customize the team. The order matters: each specialist sees the analysis of those before them.
                    </div>
                </div>
            </div>

            <div className="space-y-2">
                {/* Selected (Active) Agents - Reorderable */}
                {selectedAgents.map((agentId, index) => {
                    const agent = allAgents.find(a => a.id === agentId);
                    if (!agent) return null;

                    return (
                        <div key={agentId} className="flex items-center gap-3 bg-white/5 p-2 rounded-lg border border-white/10 group">
                            <div className="flex flex-col gap-1 text-white/20">
                                <button
                                    type="button"
                                    onClick={() => moveAgent(index, 'up')}
                                    disabled={index === 0}
                                    className="hover:text-white disabled:opacity-20"
                                >
                                    ▲
                                </button>
                                <button
                                    type="button"
                                    onClick={() => moveAgent(index, 'down')}
                                    disabled={index === selectedAgents.length - 1}
                                    className="hover:text-white disabled:opacity-20"
                                >
                                    ▼
                                </button>
                            </div>

                            <div className="w-6 h-6 rounded bg-industrial-500/20 text-industrial-400 flex items-center justify-center text-xs font-bold">
                                {index + 1}
                            </div>

                            <div className="flex-1">
                                <p className="text-sm font-medium text-white">{agent.role}</p>
                                <p className="text-[10px] text-white/40">{agent.name}</p>
                            </div>

                            <button
                                type="button"
                                onClick={() => toggleAgent(agentId)}
                                className="p-1.5 rounded bg-green-500/20 text-green-400 hover:bg-red-500/20 hover:text-red-400 transition-colors"
                                title="Remove from workflow"
                            >
                                <Check size={14} />
                            </button>
                        </div>
                    );
                })}

                {/* Unselected Agents */}
                {allAgents.filter(a => !selectedAgents.includes(a.id)).length > 0 && (
                    <div className="mt-4 pt-4 border-t border-white/5">
                        <p className="text-[10px] font-bold text-white/30 uppercase mb-2">Available Specialists</p>
                        <div className="grid grid-cols-2 gap-2">
                            {allAgents.filter(a => !selectedAgents.includes(a.id)).map(agent => (
                                <button
                                    key={agent.id}
                                    type="button"
                                    onClick={() => toggleAgent(agent.id)}
                                    className="text-left px-3 py-2 rounded bg-white/5 hover:bg-white/10 text-xs text-white/60 transition-colors border border-dashed border-white/10"
                                >
                                    + {agent.role}
                                </button>
                            ))}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

export default AgentSelector;
