/**
 * GradeSelectionTable.tsx — Table showing evaluated grades and why one was selected.
 * Displays yield, burst/collapse/tension ratings, and pass/fail per grade.
 */
import React from 'react';
import ChartContainer from '../ChartContainer';
import { List } from 'lucide-react';

interface GradeSelectionTableProps {
  gradeSelection: { selected_grade: string; selection_reason?: string; all_candidates?: Array<{ grade: string; yield_psi: number; passes_burst?: boolean; burst_pass?: boolean; passes_collapse?: boolean; collapse_pass?: boolean; passes_tension?: boolean; tension_pass?: boolean; passes_all?: boolean; all_pass?: boolean }>; evaluated_grades?: Array<{ grade: string; yield_psi: number; passes_burst?: boolean; burst_pass?: boolean; passes_collapse?: boolean; collapse_pass?: boolean; passes_tension?: boolean; tension_pass?: boolean; passes_all?: boolean; all_pass?: boolean }>; selected_details?: { yield_psi: number }; yield_strength_psi?: number };
  height?: number;
}

const GRADE_COLORS: Record<string, string> = {
  J55: '#22c55e',
  K55: '#22c55e',
  L80: '#3b82f6',
  N80: '#3b82f6',
  C90: '#8b5cf6',
  T95: '#8b5cf6',
  C110: '#f97316',
  P110: '#f97316',
  Q125: '#ef4444',
};

const GradeSelectionTable: React.FC<GradeSelectionTableProps> = ({ gradeSelection, height = 350 }) => {
  if (!gradeSelection) return null;

  const selected = gradeSelection.selected_grade;
  const evaluated = gradeSelection.all_candidates || gradeSelection.evaluated_grades || [];

  return (
    <ChartContainer title="Selección de Grado" icon={List} height={height} isFluid>
      <div className="flex flex-col h-full overflow-auto">
        {/* Selected grade highlight */}
        <div className="flex items-center gap-3 mb-4 p-3 rounded-xl border border-indigo-500/30 bg-indigo-500/5">
          <div className="w-10 h-10 rounded-lg flex items-center justify-center font-bold text-lg"
            style={{ backgroundColor: (GRADE_COLORS[selected] || '#6366f1') + '20', color: GRADE_COLORS[selected] || '#6366f1' }}>
            {selected?.charAt(0)}
          </div>
          <div>
            <div className="font-bold text-indigo-400">{selected || 'No seleccionado'}</div>
            <div className="text-xs text-gray-500">{gradeSelection.selection_reason || 'Grado óptimo según API 5C3'}</div>
          </div>
        </div>

        {/* Table */}
        {evaluated.length > 0 && (
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-white/10 text-gray-500">
                <th className="text-left py-2 px-2">Grado</th>
                <th className="text-right py-2 px-2">Yield (psi)</th>
                <th className="text-center py-2 px-2">Burst</th>
                <th className="text-center py-2 px-2">Collapse</th>
                <th className="text-center py-2 px-2">Tension</th>
                <th className="text-center py-2 px-2">Status</th>
              </tr>
            </thead>
            <tbody>
              {evaluated.map((g: { grade: string; yield_psi: number; passes_burst?: boolean; burst_pass?: boolean; passes_collapse?: boolean; collapse_pass?: boolean; passes_tension?: boolean; tension_pass?: boolean; passes_all?: boolean; all_pass?: boolean }, i: number) => {
                const isSelected = g.grade === selected;
                return (
                  <tr key={i} className={`border-b border-white/5 ${isSelected ? 'bg-indigo-500/10' : ''}`}>
                    <td className="py-2 px-2 font-bold" style={{ color: GRADE_COLORS[g.grade] || '#fff' }}>
                      {g.grade} {isSelected && '✓'}
                    </td>
                    <td className="text-right py-2 px-2 font-mono text-gray-300">
                      {(g.yield_psi || 0).toLocaleString()}
                    </td>
                    <td className="text-center py-2 px-2">
                      <span className={(g.passes_burst ?? g.burst_pass) ? 'text-green-400' : 'text-red-400'}>
                        {(g.passes_burst ?? g.burst_pass) ? '✓' : '✗'}
                      </span>
                    </td>
                    <td className="text-center py-2 px-2">
                      <span className={(g.passes_collapse ?? g.collapse_pass) ? 'text-green-400' : 'text-red-400'}>
                        {(g.passes_collapse ?? g.collapse_pass) ? '✓' : '✗'}
                      </span>
                    </td>
                    <td className="text-center py-2 px-2">
                      <span className={(g.passes_tension ?? g.tension_pass) ? 'text-green-400' : 'text-red-400'}>
                        {(g.passes_tension ?? g.tension_pass) ? '✓' : '✗'}
                      </span>
                    </td>
                    <td className="text-center py-2 px-2">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        (g.passes_all ?? g.all_pass) ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
                      }`}>
                        {(g.passes_all ?? g.all_pass) ? 'PASS' : 'FAIL'}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}

        {evaluated.length === 0 && (
          <div className="flex-1 flex flex-col items-center justify-center text-gray-500 text-sm">
            <p>Grado: <span className="font-bold text-indigo-400">{selected}</span></p>
            <p className="text-xs mt-1">Yield: {(gradeSelection.selected_details?.yield_psi || gradeSelection.yield_strength_psi || 0).toLocaleString()} psi</p>
          </div>
        )}
      </div>
    </ChartContainer>
  );
};

export default GradeSelectionTable;
