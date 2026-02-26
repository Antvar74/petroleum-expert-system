/**
 * WellboreSectionEditor.tsx — Wellbore section editor for casing/liner/open hole.
 * Allows defining the wellbore geometry from surface to TD.
 */
import React from 'react';
import { Plus, Trash2 } from 'lucide-react';

export interface WellboreSection {
  section_type: string;
  top_md_ft: number;
  bottom_md_ft: number;
  id_in: number;
}

interface WellboreSectionEditorProps {
  sections: WellboreSection[];
  onChange: (sections: WellboreSection[]) => void;
}

const SECTION_TYPES = [
  'surface_casing',
  'intermediate_casing',
  'production_casing',
  'liner',
  'open_hole',
];

const SECTION_LABELS: Record<string, string> = {
  surface_casing: 'Csg Superficial',
  intermediate_casing: 'Csg Intermedio',
  production_casing: 'Csg Producción',
  liner: 'Liner',
  open_hole: 'Open Hole',
};

const DEFAULT_BY_SECTION: Record<string, Partial<WellboreSection>> = {
  surface_casing:       { id_in: 18.0, top_md_ft: 0, bottom_md_ft: 500 },
  intermediate_casing:  { id_in: 12.347, top_md_ft: 0, bottom_md_ft: 5000 },
  production_casing:    { id_in: 8.681, top_md_ft: 0, bottom_md_ft: 10000 },
  liner:                { id_in: 6.094, top_md_ft: 8000, bottom_md_ft: 12000 },
  open_hole:            { id_in: 8.5, top_md_ft: 10000, bottom_md_ft: 12500 },
};

const TYPE_COLORS: Record<string, string> = {
  surface_casing: 'bg-blue-500/20 text-blue-300',
  intermediate_casing: 'bg-cyan-500/20 text-cyan-300',
  production_casing: 'bg-green-500/20 text-green-300',
  liner: 'bg-amber-500/20 text-amber-300',
  open_hole: 'bg-rose-500/20 text-rose-300',
};

const PRESETS: Record<string, WellboreSection[]> = {
  'Vertical Simple': [
    { section_type: 'surface_casing', top_md_ft: 0, bottom_md_ft: 500, id_in: 18.0 },
    { section_type: 'production_casing', top_md_ft: 0, bottom_md_ft: 8000, id_in: 8.681 },
    { section_type: 'open_hole', top_md_ft: 8000, bottom_md_ft: 10000, id_in: 8.5 },
  ],
  'Direccional con Liner': [
    { section_type: 'surface_casing', top_md_ft: 0, bottom_md_ft: 1000, id_in: 18.0 },
    { section_type: 'intermediate_casing', top_md_ft: 0, bottom_md_ft: 6000, id_in: 12.347 },
    { section_type: 'production_casing', top_md_ft: 0, bottom_md_ft: 10000, id_in: 8.681 },
    { section_type: 'liner', top_md_ft: 9500, bottom_md_ft: 13000, id_in: 6.094 },
    { section_type: 'open_hole', top_md_ft: 13000, bottom_md_ft: 15000, id_in: 6.125 },
  ],
  'Pozo Profundo': [
    { section_type: 'surface_casing', top_md_ft: 0, bottom_md_ft: 2000, id_in: 18.0 },
    { section_type: 'intermediate_casing', top_md_ft: 0, bottom_md_ft: 8000, id_in: 12.347 },
    { section_type: 'production_casing', top_md_ft: 0, bottom_md_ft: 14000, id_in: 8.681 },
    { section_type: 'open_hole', top_md_ft: 14000, bottom_md_ft: 18000, id_in: 8.5 },
  ],
};

const WellboreSectionEditor: React.FC<WellboreSectionEditorProps> = ({ sections, onChange }) => {

  const addSection = () => {
    const defaults = DEFAULT_BY_SECTION['open_hole'];
    onChange([...sections, { section_type: 'open_hole', ...defaults } as WellboreSection]);
  };

  const removeSection = (index: number) => {
    onChange(sections.filter((_, i) => i !== index));
  };

  const updateSection = (index: number, field: keyof WellboreSection, value: string | number) => {
    const updated = [...sections];
    if (field === 'section_type') {
      const newType = value as string;
      const defaults = DEFAULT_BY_SECTION[newType] || {};
      updated[index] = { ...updated[index], ...defaults, section_type: newType };
    } else {
      updated[index] = { ...updated[index], [field]: typeof value === 'string' ? parseFloat(value) || 0 : value };
    }
    onChange(updated);
  };

  const lastShoe = sections
    .filter(s => s.section_type !== 'open_hole')
    .reduce((max, s) => Math.max(max, s.bottom_md_ft), 0);
  const td = sections.reduce((max, s) => Math.max(max, s.bottom_md_ft), 0);
  const openHoleLength = td - lastShoe;

  return (
    <div className="space-y-3">
      {/* Presets */}
      <div className="flex flex-wrap gap-2">
        {Object.keys(PRESETS).map(name => (
          <button key={name} type="button"
            onClick={() => onChange([...PRESETS[name]])}
            className="px-3 py-1 text-xs rounded-md border bg-white/5 border-white/10 text-gray-400 hover:border-rose-500/40 hover:text-rose-300 transition-colors"
          >
            {name}
          </button>
        ))}
      </div>

      {/* Section Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-gray-500 text-xs border-b border-white/10">
              <th className="text-left py-2 px-1">Tipo</th>
              <th className="text-right py-2 px-1">Top MD (ft)</th>
              <th className="text-right py-2 px-1">Bottom MD (ft)</th>
              <th className="text-right py-2 px-1">ID (in)</th>
              <th className="py-2 px-1 w-10"></th>
            </tr>
          </thead>
          <tbody>
            {sections.map((sec, i) => (
              <tr key={i} className="border-b border-white/5 hover:bg-white/[0.02]">
                <td className="py-1 px-1">
                  <select value={sec.section_type}
                    onChange={e => updateSection(i, 'section_type', e.target.value)}
                    className={`bg-transparent border border-white/10 rounded px-2 py-1 text-xs ${TYPE_COLORS[sec.section_type] || 'text-gray-300'}`}>
                    {SECTION_TYPES.map(t => <option key={t} value={t}>{SECTION_LABELS[t]}</option>)}
                  </select>
                </td>
                {(['top_md_ft', 'bottom_md_ft', 'id_in'] as const).map(field => (
                  <td key={field} className="py-1 px-1">
                    <input type="number"
                      value={sec[field]}
                      step={field === 'id_in' ? '0.125' : '100'}
                      onChange={e => updateSection(i, field, e.target.value)}
                      className="w-full text-right bg-white/5 border border-white/10 rounded px-2 py-1 text-xs focus:border-rose-500 focus:outline-none"
                    />
                  </td>
                ))}
                <td className="py-1 px-1">
                  <button onClick={() => removeSection(i)}
                    className="p-1 text-gray-500 hover:text-red-400"><Trash2 size={14} /></button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Footer */}
      <div className="flex justify-between items-center">
        <button onClick={addSection} type="button"
          className="flex items-center gap-1 px-3 py-1.5 text-xs rounded-lg border border-dashed border-white/20 text-gray-400 hover:border-rose-500/40 hover:text-rose-300 transition-colors">
          <Plus size={14} /> Add Section
        </button>
        <div className="text-xs text-gray-500 space-x-3">
          {lastShoe > 0 && <span>Shoe: {lastShoe.toLocaleString()} ft</span>}
          {openHoleLength > 0 && <span>OH: {openHoleLength.toLocaleString()} ft</span>}
          {td > 0 && <span>TD: {td.toLocaleString()} ft</span>}
        </div>
      </div>
    </div>
  );
};

export default WellboreSectionEditor;
