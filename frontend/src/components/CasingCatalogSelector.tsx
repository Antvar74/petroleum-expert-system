import React, { useState, useEffect } from 'react';
import api from '../lib/api';
import { Database, ChevronDown } from 'lucide-react';

interface CatalogEntry {
  weight: number;
  id: number;
  wall: number;
  grade: string;
  burst: number;
  collapse: number;
}

interface CasingCatalogSelectorProps {
  onSelect: (entry: { od: number; id: number; wall: number; weight: number }) => void;
  currentOd: number;
}

const CasingCatalogSelector: React.FC<CasingCatalogSelectorProps> = ({ onSelect, currentOd }) => {
  const [ods, setOds] = useState<number[]>([]);
  const [selectedOd, setSelectedOd] = useState<number>(currentOd || 9.625);
  const [options, setOptions] = useState<CatalogEntry[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.get('/casing-design/catalog').then(r => setOds(r.data.available_ods)).catch(() => {});
  }, []);

  useEffect(() => {
    if (selectedOd > 0) {
      setLoading(true);
      api.get(`/casing-design/catalog/${selectedOd}`)
        .then(r => setOptions(r.data.options || []))
        .catch(() => setOptions([]))
        .finally(() => setLoading(false));
    }
  }, [selectedOd]);

  const handleSelect = (opt: CatalogEntry) => {
    onSelect({ od: selectedOd, id: opt.id, wall: opt.wall, weight: opt.weight });
    setIsOpen(false);
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 mb-1">
        <Database size={14} className="text-indigo-400" />
        <span className="text-xs font-medium text-gray-400">Cat&aacute;logo API 5CT</span>
      </div>
      <div className="flex gap-3 items-end">
        <div className="space-y-1">
          <label className="text-xs text-gray-400">OD (in)</label>
          <select
            value={selectedOd}
            onChange={e => setSelectedOd(Number(e.target.value))}
            className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
          >
            {ods.map(od => (
              <option key={od} value={od}>{od}&quot;</option>
            ))}
          </select>
        </div>
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="flex items-center gap-1 px-3 py-2 text-xs bg-indigo-500/20 text-indigo-400 border border-indigo-500/30 rounded-lg hover:bg-indigo-500/30 transition-colors"
        >
          {isOpen ? 'Cerrar' : 'Ver opciones'}
          <ChevronDown size={14} className={`transition-transform ${isOpen ? 'rotate-180' : ''}`} />
        </button>
      </div>
      {isOpen && (
        <div className="overflow-x-auto rounded-lg border border-white/10 bg-white/5">
          {loading ? (
            <div className="p-4 text-center text-xs text-gray-500">Cargando...</div>
          ) : (
            <table className="w-full text-xs">
              <thead>
                <tr className="text-gray-400 border-b border-white/10">
                  <th className="px-3 py-2 text-left">Peso (ppf)</th>
                  <th className="px-3 py-2 text-left">Grado</th>
                  <th className="px-3 py-2 text-left">ID (in)</th>
                  <th className="px-3 py-2 text-left">Pared (in)</th>
                  <th className="px-3 py-2 text-right">Burst (psi)</th>
                  <th className="px-3 py-2 text-right">Collapse (psi)</th>
                  <th className="px-3 py-2"></th>
                </tr>
              </thead>
              <tbody>
                {options.map((opt, i) => (
                  <tr
                    key={i}
                    onClick={() => handleSelect(opt)}
                    className="border-b border-white/5 hover:bg-indigo-500/10 cursor-pointer transition-colors"
                  >
                    <td className="px-3 py-1.5">{opt.weight}</td>
                    <td className="px-3 py-1.5 font-medium text-indigo-300">{opt.grade}</td>
                    <td className="px-3 py-1.5">{opt.id}&quot;</td>
                    <td className="px-3 py-1.5">{opt.wall}&quot;</td>
                    <td className="px-3 py-1.5 text-right text-green-400">{opt.burst.toLocaleString()}</td>
                    <td className="px-3 py-1.5 text-right text-blue-400">{opt.collapse.toLocaleString()}</td>
                    <td className="px-3 py-1.5 text-right text-indigo-400 text-[10px]">Seleccionar</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
};

export default CasingCatalogSelector;
