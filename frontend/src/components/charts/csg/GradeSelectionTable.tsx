/**
 * GradeSelectionTable.tsx — Table showing evaluated grades and why one was selected.
 * Displays yield, burst/collapse/tension ratings, and pass/fail per grade.
 * Rows are clickable to let the user inspect any grade's detailed data.
 */
import React from 'react';
import ChartContainer from '../ChartContainer';
import { List } from 'lucide-react';
import { useTranslation } from 'react-i18next';

interface CandidateRow {
  grade: string;
  yield_psi: number;
  passes_burst?: boolean; burst_pass?: boolean;
  passes_collapse?: boolean; collapse_pass?: boolean;
  passes_tension?: boolean; tension_pass?: boolean;
  passes_all?: boolean; all_pass?: boolean;
}

interface WeightRecommendation {
  ppf: number;
  grade: string;
  burst_rating_psi: number;
  collapse_rating_corrected_psi?: number;
  collapse_rating_psi?: number;
  biaxial_reduction?: number;
  tension_rating_lbs: number;
  description: string;
}

interface GradeSelectionTableProps {
  gradeSelection: {
    selected_grade: string;
    selection_reason?: string;
    weight_recommendation?: WeightRecommendation | null;
    all_candidates?: CandidateRow[];
    evaluated_grades?: CandidateRow[];
    selected_details?: { yield_psi: number };
    yield_strength_psi?: number;
  };
  height?: number;
  onGradeSelect?: (gradeName: string) => void;
  userSelectedGrade?: string | null;
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

const GradeSelectionTable: React.FC<GradeSelectionTableProps> = ({
  gradeSelection, height = 350, onGradeSelect, userSelectedGrade,
}) => {
  const { t } = useTranslation();
  if (!gradeSelection) return null;

  const autoSelected = gradeSelection.selected_grade;
  const activeGrade = userSelectedGrade || autoSelected;
  const isOverride = Boolean(userSelectedGrade && userSelectedGrade !== autoSelected);
  const evaluated = gradeSelection.all_candidates || gradeSelection.evaluated_grades || [];

  return (
    <ChartContainer title={t('casingDesign.chartTitles.gradeSelection')} icon={List} height={height} isFluid>
      <div className="flex flex-col h-full overflow-auto">
        {/* Active grade highlight */}
        <div className={`flex items-center gap-3 mb-4 p-3 rounded-xl border ${
          isOverride ? 'border-yellow-500/30 bg-yellow-500/5' : 'border-indigo-500/30 bg-indigo-500/5'
        }`}>
          <div className="w-10 h-10 rounded-lg flex items-center justify-center font-bold text-lg"
            style={{ backgroundColor: (GRADE_COLORS[activeGrade] || '#6366f1') + '20', color: GRADE_COLORS[activeGrade] || '#6366f1' }}>
            {activeGrade?.charAt(0)}
          </div>
          <div className="flex-1">
            <div className={`font-bold ${isOverride ? 'text-yellow-400' : 'text-indigo-400'}`}>
              {activeGrade || 'No seleccionado'}
            </div>
            <div className="text-xs text-gray-500">
              {isOverride
                ? `Selección manual (auto: ${autoSelected})`
                : gradeSelection.selection_reason || 'Grado óptimo según API 5C3'}
            </div>
          </div>
          {isOverride && (
            <button
              onClick={() => onGradeSelect?.(autoSelected)}
              className="text-xs text-gray-400 hover:text-white px-2 py-1 rounded bg-white/5 hover:bg-white/10 transition-colors"
            >
              Reset
            </button>
          )}
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
                const isActive = g.grade === activeGrade;
                const isAuto = g.grade === autoSelected && !isActive;
                return (
                  <tr key={i}
                    className={`border-b border-white/5 transition-colors ${
                      isActive ? 'bg-indigo-500/10' : ''
                    } ${onGradeSelect ? 'cursor-pointer hover:bg-white/5' : ''}`}
                    onClick={() => onGradeSelect?.(g.grade)}
                  >
                    <td className="py-2 px-2 font-bold" style={{ color: GRADE_COLORS[g.grade] || '#fff' }}>
                      {g.grade} {isActive && '◆'} {isAuto && '✓'}
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
            <p>Grado: <span className="font-bold text-indigo-400">{activeGrade}</span></p>
            <p className="text-xs mt-1">Yield: {(gradeSelection.selected_details?.yield_psi || gradeSelection.yield_strength_psi || 0).toLocaleString()} psi</p>
          </div>
        )}

        {/* Alternative weight section — shown when current weight has no passing grade */}
        {gradeSelection.selected_grade?.startsWith('None') && gradeSelection.weight_recommendation && (
          <div className="mt-4">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-[10px] font-bold text-yellow-400 bg-yellow-500/10 border border-yellow-500/20 px-2 py-0.5 rounded">
                ALTERNATIVA
              </span>
              <span className="text-xs text-yellow-400 font-semibold">
                {gradeSelection.weight_recommendation.ppf} ppf — cumple todos los criterios
              </span>
            </div>
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-yellow-500/20 text-gray-500">
                  <th className="text-left py-1.5 px-2">Grado</th>
                  <th className="text-right py-1.5 px-2">Burst (psi)</th>
                  <th className="text-right py-1.5 px-2">Collapse (psi)</th>
                  <th className="text-right py-1.5 px-2">Tensión (lbs)</th>
                  <th className="text-center py-1.5 px-2">Status</th>
                </tr>
              </thead>
              <tbody>
                <tr className="bg-yellow-500/5 border border-yellow-500/20 rounded">
                  <td className="py-2 px-2 font-bold" style={{ color: GRADE_COLORS[gradeSelection.weight_recommendation.grade] || '#facc15' }}>
                    {gradeSelection.weight_recommendation.grade}
                  </td>
                  <td className="text-right py-2 px-2 font-mono text-gray-300">
                    {(gradeSelection.weight_recommendation.burst_rating_psi || 0).toLocaleString()}
                  </td>
                  <td className="text-right py-2 px-2 font-mono text-gray-300">
                    {(gradeSelection.weight_recommendation.collapse_rating_corrected_psi ?? gradeSelection.weight_recommendation.collapse_rating_psi ?? 0).toLocaleString()}
                    {gradeSelection.weight_recommendation.biaxial_reduction != null && (
                      <span className="text-gray-600 ml-1">
                        ×{gradeSelection.weight_recommendation.biaxial_reduction.toFixed(3)}
                      </span>
                    )}
                  </td>
                  <td className="text-right py-2 px-2 font-mono text-gray-300">
                    {(gradeSelection.weight_recommendation.tension_rating_lbs || 0).toLocaleString()}
                  </td>
                  <td className="text-center py-2 px-2">
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-yellow-500/20 text-yellow-400">
                      PASS
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
            <p className="text-[10px] text-gray-600 mt-1.5 pl-2">
              {gradeSelection.weight_recommendation.description}
            </p>
          </div>
        )}
      </div>
    </ChartContainer>
  );
};

export default GradeSelectionTable;
