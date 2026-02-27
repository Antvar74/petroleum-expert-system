/**
 * BHAEditor.tsx — Interactive multi-component BHA editor for FEA analysis.
 * Allows adding, removing, reordering BHA components (collar, dp, hwdp, etc.)
 * Tubulars (collar, dp, hwdp) support quantity × joint length.
 */
import React, { useRef } from 'react';
import Papa from 'papaparse';
import * as XLSX from 'xlsx';
import { Plus, Trash2, ChevronUp, ChevronDown, Upload } from 'lucide-react';

export interface BHAComponent {
  type: string;
  od: number;
  id_inner: number;
  length_ft: number;         // Total length (unit_length_ft × quantity) — sent to backend
  weight_ppf: number;
  unit_length_ft?: number;   // Per-joint length
  quantity?: number;          // Number of joints (default 1)
}

interface BHAEditorProps {
  components: BHAComponent[];
  onChange: (components: BHAComponent[]) => void;
  onImportFeedback?: (message: string, type: 'success' | 'error' | 'warning') => void;
}

/** Component types organized by drilling category */
const COMPONENT_GROUPS: { label: string; types: { value: string; label: string }[] }[] = [
  {
    label: 'Combinaciones',
    types: [
      { value: 'collar', label: 'Drill Collar' },
      { value: 'dp', label: 'Drill Pipe' },
      { value: 'hwdp', label: 'Heavy Weight DP' },
    ],
  },
  {
    label: 'Accesorios',
    types: [
      { value: 'crossover', label: 'Crossover Sub' },
      { value: 'sub', label: 'Sub' },
      { value: 'float_sub', label: 'Float Sub' },
      { value: 'bit_sub', label: 'Bit Sub' },
      { value: 'shock_sub', label: 'Shock Sub' },
    ],
  },
  {
    label: 'Herramientas de Fondo',
    types: [
      { value: 'stabilizer', label: 'Stabilizer' },
      { value: 'near_bit_stabilizer', label: 'Near-Bit Stabilizer' },
      { value: 'motor', label: 'Motor (PDM)' },
      { value: 'mwd', label: 'MWD' },
      { value: 'lwd', label: 'LWD' },
      { value: 'jar', label: 'Jar' },
      { value: 'reamer', label: 'Reamer' },
    ],
  },
];

/** Flat list of all valid types (for backward compatibility) */
const COMPONENT_TYPES = COMPONENT_GROUPS.flatMap(g => g.types.map(t => t.value));

/** Tubular types that can have quantity > 1 */
const TUBULAR_TYPES = new Set(['collar', 'dp', 'hwdp']);

const getQty = (c: BHAComponent) => c.quantity ?? 1;
const getUnitLen = (c: BHAComponent) => c.unit_length_ft ?? c.length_ft;

const DEFAULT_BY_TYPE: Record<string, Partial<BHAComponent>> = {
  // Combinaciones
  collar:     { od: 6.75, id_inner: 2.813, weight_ppf: 83.0,  unit_length_ft: 30, quantity: 1, length_ft: 30 },
  dp:         { od: 5.0,  id_inner: 4.276, weight_ppf: 19.5,  unit_length_ft: 30, quantity: 1, length_ft: 30 },
  hwdp:       { od: 5.0,  id_inner: 3.0,   weight_ppf: 49.3,  unit_length_ft: 30, quantity: 1, length_ft: 30 },
  // Accesorios
  crossover:  { od: 6.75, id_inner: 2.813, weight_ppf: 75.0,  unit_length_ft: 3,  quantity: 1, length_ft: 3 },
  sub:        { od: 6.75, id_inner: 2.813, weight_ppf: 75.0,  unit_length_ft: 3,  quantity: 1, length_ft: 3 },
  float_sub:  { od: 6.75, id_inner: 2.813, weight_ppf: 70.0,  unit_length_ft: 4,  quantity: 1, length_ft: 4 },
  bit_sub:    { od: 6.75, id_inner: 2.813, weight_ppf: 75.0,  unit_length_ft: 3,  quantity: 1, length_ft: 3 },
  shock_sub:  { od: 6.75, id_inner: 2.813, weight_ppf: 80.0,  unit_length_ft: 8,  quantity: 1, length_ft: 8 },
  // Herramientas de Fondo
  stabilizer:          { od: 8.25, id_inner: 2.813, weight_ppf: 95.0,  unit_length_ft: 5,  quantity: 1, length_ft: 5 },
  near_bit_stabilizer: { od: 8.25, id_inner: 2.813, weight_ppf: 95.0,  unit_length_ft: 4,  quantity: 1, length_ft: 4 },
  motor:      { od: 6.75, id_inner: 3.5,   weight_ppf: 90.0,  unit_length_ft: 25, quantity: 1, length_ft: 25 },
  mwd:        { od: 6.75, id_inner: 3.25,  weight_ppf: 85.0,  unit_length_ft: 10, quantity: 1, length_ft: 10 },
  lwd:        { od: 6.75, id_inner: 3.25,  weight_ppf: 85.0,  unit_length_ft: 10, quantity: 1, length_ft: 10 },
  jar:        { od: 6.75, id_inner: 2.813, weight_ppf: 85.0,  unit_length_ft: 10, quantity: 1, length_ft: 10 },
  reamer:     { od: 8.5,  id_inner: 3.0,   weight_ppf: 100.0, unit_length_ft: 6,  quantity: 1, length_ft: 6 },
};

const BHA_PRESETS: Record<string, BHAComponent[]> = {
  'Standard Rotary': [
    { type: 'collar', od: 8.0, id_inner: 2.813, unit_length_ft: 30, quantity: 1, length_ft: 30, weight_ppf: 147 },
    { type: 'collar', od: 6.75, id_inner: 2.813, unit_length_ft: 30, quantity: 4, length_ft: 120, weight_ppf: 83 },
    { type: 'hwdp', od: 5.0, id_inner: 3.0, unit_length_ft: 30, quantity: 3, length_ft: 90, weight_ppf: 49.3 },
    { type: 'dp', od: 5.0, id_inner: 4.276, unit_length_ft: 30, quantity: 2, length_ft: 60, weight_ppf: 19.5 },
  ],
  'Motor BHA': [
    { type: 'stabilizer', od: 8.25, id_inner: 2.813, unit_length_ft: 5, quantity: 1, length_ft: 5, weight_ppf: 95 },
    { type: 'motor', od: 6.75, id_inner: 3.5, unit_length_ft: 25, quantity: 1, length_ft: 25, weight_ppf: 90 },
    { type: 'mwd', od: 6.75, id_inner: 3.25, unit_length_ft: 10, quantity: 1, length_ft: 10, weight_ppf: 85 },
    { type: 'collar', od: 6.75, id_inner: 2.813, unit_length_ft: 30, quantity: 3, length_ft: 90, weight_ppf: 83 },
    { type: 'hwdp', od: 5.0, id_inner: 3.0, unit_length_ft: 30, quantity: 3, length_ft: 90, weight_ppf: 49.3 },
    { type: 'dp', od: 5.0, id_inner: 4.276, unit_length_ft: 30, quantity: 2, length_ft: 60, weight_ppf: 19.5 },
  ],
  'RSS BHA': [
    { type: 'stabilizer', od: 8.25, id_inner: 2.813, unit_length_ft: 3, quantity: 1, length_ft: 3, weight_ppf: 95 },
    { type: 'collar', od: 6.75, id_inner: 2.813, unit_length_ft: 15, quantity: 1, length_ft: 15, weight_ppf: 83 },
    { type: 'mwd', od: 6.75, id_inner: 3.25, unit_length_ft: 10, quantity: 1, length_ft: 10, weight_ppf: 85 },
    { type: 'collar', od: 6.75, id_inner: 2.813, unit_length_ft: 30, quantity: 4, length_ft: 120, weight_ppf: 83 },
    { type: 'hwdp', od: 5.0, id_inner: 3.0, unit_length_ft: 30, quantity: 3, length_ft: 90, weight_ppf: 49.3 },
    { type: 'dp', od: 5.0, id_inner: 4.276, unit_length_ft: 30, quantity: 2, length_ft: 60, weight_ppf: 19.5 },
  ],
};

const TYPE_COLORS: Record<string, string> = {
  // Combinaciones
  collar: 'bg-rose-500/20 text-rose-300',
  dp: 'bg-blue-500/20 text-blue-300',
  hwdp: 'bg-amber-500/20 text-amber-300',
  // Accesorios
  crossover: 'bg-gray-500/20 text-gray-300',
  sub: 'bg-gray-500/20 text-gray-300',
  float_sub: 'bg-teal-500/20 text-teal-300',
  bit_sub: 'bg-gray-500/20 text-gray-300',
  shock_sub: 'bg-orange-500/20 text-orange-300',
  // Herramientas de Fondo
  stabilizer: 'bg-green-500/20 text-green-300',
  near_bit_stabilizer: 'bg-emerald-500/20 text-emerald-300',
  motor: 'bg-purple-500/20 text-purple-300',
  mwd: 'bg-cyan-500/20 text-cyan-300',
  lwd: 'bg-sky-500/20 text-sky-300',
  jar: 'bg-yellow-500/20 text-yellow-300',
  reamer: 'bg-red-500/20 text-red-300',
};

const INPUT_CLASS = 'w-full text-right bg-white/5 border border-white/10 rounded px-2 py-1 text-xs focus:border-rose-500 focus:outline-none';

const BHAEditor: React.FC<BHAEditorProps> = ({ components, onChange, onImportFeedback }) => {
  const fileInputRef = useRef<HTMLInputElement>(null);

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
    } else if (field === 'unit_length_ft') {
      const unitLen = typeof value === 'string' ? parseFloat(value) || 0 : value;
      const qty = getQty(updated[index]);
      updated[index] = { ...updated[index], unit_length_ft: unitLen, length_ft: unitLen * qty };
    } else if (field === 'quantity') {
      const qty = Math.max(1, Math.round(typeof value === 'string' ? parseFloat(value) || 1 : value));
      const unitLen = getUnitLen(updated[index]);
      updated[index] = { ...updated[index], quantity: qty, length_ft: unitLen * qty };
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

  const handleFileImport = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    const ext = file.name.split('.').pop()?.toLowerCase();

    const parseRows = (rows: Record<string, string>[]) => {
      // Collect all valid COMPONENT_TYPES + extras recognized by backend
      const VALID_TYPES = new Set([
        ...COMPONENT_TYPES.map(t => t.toLowerCase()),
        'string_stabilizer',  // backend-only type not in UI groups
      ]);

      let skipped = 0;
      const warnings: string[] = [];

      const mapped: BHAComponent[] = rows
        .filter(r => {
          const hasType = !!(r.type || r.Type || r.component);
          if (!hasType) { skipped++; return false; }
          return true;
        })
        .map(r => {
          const rawType = (r.type || r.Type || r.component || 'collar').toLowerCase();
          const type = VALID_TYPES.has(rawType) ? rawType : 'collar';
          if (!VALID_TYPES.has(rawType)) {
            warnings.push(`Unknown type "${rawType}" → defaulted to collar`);
          }

          const od = parseFloat(r.od || r.OD || r.od_in || '6.75') || 6.75;
          const id_inner = parseFloat(r.id_inner || r.ID || r.id_in || r.id || '2.813') || 2.813;
          if (id_inner >= od) {
            warnings.push(`Row "${rawType}": ID (${id_inner}) >= OD (${od}) — check dimensions`);
          }

          const qty = Math.max(1, parseInt(r.quantity || r.qty || r.Qty || '1') || 1);
          const unitLen = parseFloat(r.unit_length_ft || r.joint_length || r.jt_len || '0');
          const totalLen = parseFloat(r.length_ft || r.length || r.Length || '30') || 30;
          const resolvedUnitLen = unitLen > 0 ? unitLen : (qty > 1 ? totalLen / qty : totalLen);

          return {
            type,
            od,
            id_inner,
            unit_length_ft: resolvedUnitLen,
            quantity: qty,
            length_ft: resolvedUnitLen * qty,
            weight_ppf: parseFloat(r.weight_ppf || r.weight || r.Weight || r.weight_lbft || '83') || 83,
          };
        });

      if (mapped.length > 0) {
        onChange(mapped);
        const msg = `Imported ${mapped.length} components` +
          (skipped > 0 ? `, ${skipped} rows skipped (no type)` : '') +
          (warnings.length > 0 ? `. Warnings: ${warnings.join('; ')}` : '');
        onImportFeedback?.(msg, warnings.length > 0 ? 'warning' : 'success');
      } else {
        onImportFeedback?.('No valid components found in file. Ensure column "type" exists.', 'error');
      }
    };

    const resetInput = () => { if (fileInputRef.current) fileInputRef.current.value = ''; };

    if (ext === 'csv') {
      Papa.parse<Record<string, string>>(file, {
        header: true,
        skipEmptyLines: true,
        complete: (result) => { parseRows(result.data); resetInput(); },
        error: (err) => { onImportFeedback?.(`CSV parse error: ${err.message}`, 'error'); resetInput(); },
      });
    } else if (ext === 'xlsx' || ext === 'xls') {
      const reader = new FileReader();
      reader.onload = (e) => {
        try {
          const wb = XLSX.read(e.target?.result, { type: 'array' });
          const ws = wb.Sheets[wb.SheetNames[0]];
          const rows = XLSX.utils.sheet_to_json<Record<string, string>>(ws);
          parseRows(rows);
        } catch (err) {
          onImportFeedback?.(`Excel parse error: ${(err as Error).message}`, 'error');
        }
        resetInput();
      };
      reader.onerror = () => { onImportFeedback?.('Failed to read file', 'error'); resetInput(); };
      reader.readAsArrayBuffer(file);
    }
  };

  const totalLength = components.reduce((sum, c) => sum + c.length_ft, 0);
  const totalJoints = components.reduce((sum, c) => sum + getQty(c), 0);
  const totalConnections = totalJoints > 0 ? totalJoints - 1 : 0;

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
              <th className="text-right py-2 px-1 w-16">Qty</th>
              <th className="text-right py-2 px-1 w-20">Total (ft)</th>
              <th className="text-right py-2 px-1">Wt (lb/ft)</th>
              <th className="py-2 px-1 w-24"></th>
            </tr>
          </thead>
          <tbody>
            {components.map((comp, i) => {
              const isTubular = TUBULAR_TYPES.has(comp.type);
              return (
                <tr key={i} className="border-b border-white/5 hover:bg-white/[0.02]">
                  <td className="py-1 px-1 text-gray-600">{i + 1}</td>
                  <td className="py-1 px-1">
                    <select value={comp.type}
                      onChange={e => updateComponent(i, 'type', e.target.value)}
                      className={`bg-transparent border border-white/10 rounded px-2 py-1 text-xs ${TYPE_COLORS[comp.type] || 'text-gray-300'}`}>
                      {COMPONENT_GROUPS.map(group => (
                        <optgroup key={group.label} label={group.label}>
                          {group.types.map(t => (
                            <option key={t.value} value={t.value}>{t.label}</option>
                          ))}
                        </optgroup>
                      ))}
                    </select>
                  </td>
                  {/* OD */}
                  <td className="py-1 px-1">
                    <input type="number" value={comp.od} step="0.125"
                      onChange={e => updateComponent(i, 'od', e.target.value)}
                      className={INPUT_CLASS} />
                  </td>
                  {/* ID */}
                  <td className="py-1 px-1">
                    <input type="number" value={comp.id_inner} step="0.125"
                      onChange={e => updateComponent(i, 'id_inner', e.target.value)}
                      className={INPUT_CLASS} />
                  </td>
                  {/* Per-joint length */}
                  <td className="py-1 px-1">
                    <input type="number" value={getUnitLen(comp)} step="5"
                      onChange={e => updateComponent(i, 'unit_length_ft', e.target.value)}
                      className={INPUT_CLASS} />
                  </td>
                  {/* Quantity */}
                  <td className="py-1 px-1">
                    {isTubular ? (
                      <input type="number" value={getQty(comp)} min={1} step={1}
                        onChange={e => updateComponent(i, 'quantity', e.target.value)}
                        className={INPUT_CLASS} />
                    ) : (
                      <span className="block text-right text-xs text-gray-600 px-2 py-1">1</span>
                    )}
                  </td>
                  {/* Total length (computed) */}
                  <td className="py-1 px-1 text-right text-xs text-gray-400 tabular-nums">
                    {comp.length_ft.toFixed(0)}
                  </td>
                  {/* Weight */}
                  <td className="py-1 px-1">
                    <input type="number" value={comp.weight_ppf} step="0.1"
                      onChange={e => updateComponent(i, 'weight_ppf', e.target.value)}
                      className={INPUT_CLASS} />
                  </td>
                  {/* Actions */}
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
              );
            })}
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
          {totalJoints} joints &middot; {totalConnections} connections &middot; Total: {totalLength.toFixed(0)} ft
        </span>
      </div>
    </div>
  );
};

export default BHAEditor;
