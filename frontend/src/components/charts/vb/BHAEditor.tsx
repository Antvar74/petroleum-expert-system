/**
 * BHAEditor.tsx — Interactive multi-component BHA editor for FEA analysis.
 * Allows adding, removing, reordering BHA components (collar, dp, hwdp, etc.)
 */
import React, { useRef } from 'react';
import Papa from 'papaparse';
import * as XLSX from 'xlsx';
import { Plus, Trash2, ChevronUp, ChevronDown, Upload } from 'lucide-react';

export interface BHAComponent {
  type: string;
  od: number;
  id_inner: number;
  length_ft: number;
  weight_ppf: number;
}

interface BHAEditorProps {
  components: BHAComponent[];
  onChange: (components: BHAComponent[]) => void;
}

const COMPONENT_TYPES = ['collar', 'dp', 'hwdp', 'stabilizer', 'motor', 'MWD'];

const DEFAULT_BY_TYPE: Record<string, Partial<BHAComponent>> = {
  collar:     { od: 6.75, id_inner: 2.813, weight_ppf: 83.0, length_ft: 30 },
  dp:         { od: 5.0,  id_inner: 4.276, weight_ppf: 19.5, length_ft: 30 },
  hwdp:       { od: 5.0,  id_inner: 3.0,   weight_ppf: 49.3, length_ft: 30 },
  stabilizer: { od: 8.25, id_inner: 2.813, weight_ppf: 95.0, length_ft: 5 },
  motor:      { od: 6.75, id_inner: 3.5,   weight_ppf: 90.0, length_ft: 25 },
  MWD:        { od: 6.75, id_inner: 3.25,  weight_ppf: 85.0, length_ft: 10 },
};

const BHA_PRESETS: Record<string, BHAComponent[]> = {
  'Standard Rotary': [
    { type: 'collar', od: 8.0, id_inner: 2.813, length_ft: 30, weight_ppf: 147 },
    { type: 'collar', od: 6.75, id_inner: 2.813, length_ft: 60, weight_ppf: 83 },
    { type: 'collar', od: 6.75, id_inner: 2.813, length_ft: 60, weight_ppf: 83 },
    { type: 'hwdp', od: 5.0, id_inner: 3.0, length_ft: 90, weight_ppf: 49.3 },
    { type: 'dp', od: 5.0, id_inner: 4.276, length_ft: 60, weight_ppf: 19.5 },
  ],
  'Motor BHA': [
    { type: 'stabilizer', od: 8.25, id_inner: 2.813, length_ft: 5, weight_ppf: 95 },
    { type: 'motor', od: 6.75, id_inner: 3.5, length_ft: 25, weight_ppf: 90 },
    { type: 'MWD', od: 6.75, id_inner: 3.25, length_ft: 10, weight_ppf: 85 },
    { type: 'collar', od: 6.75, id_inner: 2.813, length_ft: 90, weight_ppf: 83 },
    { type: 'hwdp', od: 5.0, id_inner: 3.0, length_ft: 90, weight_ppf: 49.3 },
    { type: 'dp', od: 5.0, id_inner: 4.276, length_ft: 60, weight_ppf: 19.5 },
  ],
  'RSS BHA': [
    { type: 'stabilizer', od: 8.25, id_inner: 2.813, length_ft: 3, weight_ppf: 95 },
    { type: 'collar', od: 6.75, id_inner: 2.813, length_ft: 15, weight_ppf: 83 },
    { type: 'MWD', od: 6.75, id_inner: 3.25, length_ft: 10, weight_ppf: 85 },
    { type: 'collar', od: 6.75, id_inner: 2.813, length_ft: 120, weight_ppf: 83 },
    { type: 'hwdp', od: 5.0, id_inner: 3.0, length_ft: 90, weight_ppf: 49.3 },
    { type: 'dp', od: 5.0, id_inner: 4.276, length_ft: 60, weight_ppf: 19.5 },
  ],
};

const TYPE_COLORS: Record<string, string> = {
  collar: 'bg-rose-500/20 text-rose-300',
  dp: 'bg-blue-500/20 text-blue-300',
  hwdp: 'bg-amber-500/20 text-amber-300',
  stabilizer: 'bg-green-500/20 text-green-300',
  motor: 'bg-purple-500/20 text-purple-300',
  MWD: 'bg-cyan-500/20 text-cyan-300',
};

const BHAEditor: React.FC<BHAEditorProps> = ({ components, onChange }) => {

  const addComponent = () => {
    const defaults = DEFAULT_BY_TYPE['collar'];
    onChange([...components, { type: 'collar', ...defaults } as BHAComponent]);
  };

  const removeComponent = (index: number) => {
    onChange(components.filter((_, i) => i !== index));
  };

  const updateComponent = (index: number, field: keyof BHAComponent, value: string | number) => {
    const updated = [...components];
    if (field === 'type') {
      const newType = value as string;
      const defaults = DEFAULT_BY_TYPE[newType] || {};
      updated[index] = { ...updated[index], ...defaults, type: newType };
    } else {
      updated[index] = { ...updated[index], [field]: typeof value === 'string' ? parseFloat(value) || 0 : value };
    }
    onChange(updated);
  };

  const moveComponent = (index: number, direction: 'up' | 'down') => {
    const newIdx = direction === 'up' ? index - 1 : index + 1;
    if (newIdx < 0 || newIdx >= components.length) return;
    const updated = [...components];
    [updated[index], updated[newIdx]] = [updated[newIdx], updated[index]];
    onChange(updated);
  };

  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileImport = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    const ext = file.name.split('.').pop()?.toLowerCase();

    const parseRows = (rows: Record<string, string>[]) => {
      const mapped: BHAComponent[] = rows
        .filter(r => r.type || r.Type || r.component)
        .map(r => ({
          type: (r.type || r.Type || r.component || 'collar').toLowerCase(),
          od: parseFloat(r.od || r.OD || r.od_in || '6.75') || 6.75,
          id_inner: parseFloat(r.id_inner || r.ID || r.id_in || r.id || '2.813') || 2.813,
          length_ft: parseFloat(r.length_ft || r.length || r.Length || '30') || 30,
          weight_ppf: parseFloat(r.weight_ppf || r.weight || r.Weight || r.weight_lbft || '83') || 83,
        }));
      if (mapped.length > 0) onChange(mapped);
    };

    if (ext === 'csv') {
      Papa.parse<Record<string, string>>(file, {
        header: true,
        skipEmptyLines: true,
        complete: (result) => parseRows(result.data),
      });
    } else if (ext === 'xlsx' || ext === 'xls') {
      const reader = new FileReader();
      reader.onload = (e) => {
        const wb = XLSX.read(e.target?.result, { type: 'array' });
        const ws = wb.Sheets[wb.SheetNames[0]];
        const rows = XLSX.utils.sheet_to_json<Record<string, string>>(ws);
        parseRows(rows);
      };
      reader.readAsArrayBuffer(file);
    }
    // Reset input so same file can be re-imported
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const totalLength = components.reduce((sum, c) => sum + c.length_ft, 0);

  return (
    <div className="space-y-3">
      {/* Presets */}
      <div className="flex flex-wrap gap-2">
        {Object.keys(BHA_PRESETS).map(name => (
          <button key={name} type="button"
            onClick={() => onChange([...BHA_PRESETS[name]])}
            className="px-3 py-1 text-xs rounded-md border bg-white/5 border-white/10 text-gray-400 hover:border-rose-500/40 hover:text-rose-300 transition-colors"
          >
            {name}
          </button>
        ))}
      </div>

      {/* Component Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-gray-500 text-xs border-b border-white/10">
              <th className="text-left py-2 px-1 w-8">#</th>
              <th className="text-left py-2 px-1">Type</th>
              <th className="text-right py-2 px-1">OD (in)</th>
              <th className="text-right py-2 px-1">ID (in)</th>
              <th className="text-right py-2 px-1">Length (ft)</th>
              <th className="text-right py-2 px-1">Weight (lb/ft)</th>
              <th className="py-2 px-1 w-24"></th>
            </tr>
          </thead>
          <tbody>
            {components.map((comp, i) => (
              <tr key={i} className="border-b border-white/5 hover:bg-white/[0.02]">
                <td className="py-1 px-1 text-gray-600">{i + 1}</td>
                <td className="py-1 px-1">
                  <select value={comp.type}
                    onChange={e => updateComponent(i, 'type', e.target.value)}
                    className={`bg-transparent border border-white/10 rounded px-2 py-1 text-xs ${TYPE_COLORS[comp.type] || 'text-gray-300'}`}>
                    {COMPONENT_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                  </select>
                </td>
                {(['od', 'id_inner', 'length_ft', 'weight_ppf'] as const).map(field => (
                  <td key={field} className="py-1 px-1">
                    <input type="number"
                      value={comp[field]}
                      step={field === 'length_ft' ? '5' : '0.125'}
                      onChange={e => updateComponent(i, field, e.target.value)}
                      className="w-full text-right bg-white/5 border border-white/10 rounded px-2 py-1 text-xs focus:border-rose-500 focus:outline-none"
                    />
                  </td>
                ))}
                <td className="py-1 px-1">
                  <div className="flex gap-1 justify-end">
                    <button onClick={() => moveComponent(i, 'up')} disabled={i === 0}
                      className="p-1 text-gray-500 hover:text-gray-300 disabled:opacity-20"><ChevronUp size={14} /></button>
                    <button onClick={() => moveComponent(i, 'down')} disabled={i === components.length - 1}
                      className="p-1 text-gray-500 hover:text-gray-300 disabled:opacity-20"><ChevronDown size={14} /></button>
                    <button onClick={() => removeComponent(i)}
                      className="p-1 text-gray-500 hover:text-red-400"><Trash2 size={14} /></button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Footer */}
      <div className="flex justify-between items-center">
        <div className="flex gap-2">
          <button onClick={addComponent} type="button"
            className="flex items-center gap-1 px-3 py-1.5 text-xs rounded-lg border border-dashed border-white/20 text-gray-400 hover:border-rose-500/40 hover:text-rose-300 transition-colors">
            <Plus size={14} /> Add Component
          </button>
          <button onClick={() => fileInputRef.current?.click()} type="button"
            className="flex items-center gap-1 px-3 py-1.5 text-xs rounded-lg border border-dashed border-white/20 text-gray-400 hover:border-cyan-500/40 hover:text-cyan-300 transition-colors">
            <Upload size={14} /> Import CSV/Excel
          </button>
          <input ref={fileInputRef} type="file" accept=".csv,.xlsx,.xls" onChange={handleFileImport} className="hidden" />
        </div>
        <span className="text-xs text-gray-500">
          {components.length} components &middot; Total: {totalLength.toFixed(0)} ft
        </span>
      </div>
    </div>
  );
};

export default BHAEditor;
