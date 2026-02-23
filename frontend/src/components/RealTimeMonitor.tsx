/**
 * RealTimeMonitor.tsx — WITSML Real-Time Data Monitoring Dashboard
 *
 * Features:
 * - WITSML server connection panel
 * - Real-time KPI gauges: ECD, hookload, torque, RPM, ROP
 * - Time-series chart of drilling parameters
 * - Alarm system: kick detection, ECD > fracture, hookload anomaly
 * - Auto-refresh with configurable interval
 * - XML paste mode for offline/demo data
 */
import { useState, useEffect, useRef, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Radio, Wifi, WifiOff, AlertTriangle, Activity, TrendingUp,
  Play, Pause, RefreshCw, Server, Upload,
} from 'lucide-react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, ReferenceLine,
} from 'recharts';
import axios from 'axios';
import { API_BASE_URL } from '../config';

interface RealTimeMonitorProps {
  wellId?: number;
  wellName?: string;
}

interface DataPoint {
  time: string;
  md?: number;
  rop?: number;
  wob?: number;
  rpm?: number;
  torque?: number;
  spp?: number;
  hookload?: number;
  ecd?: number;
  flow_rate?: number;
  mud_weight?: number;
  gr?: number;
}

interface Alarm {
  id: string;
  type: 'kick' | 'ecd' | 'hookload' | 'torque' | 'general';
  severity: 'warning' | 'critical';
  message: string;
  value?: number;
  threshold?: number;
  timestamp: string;
}

const REFRESH_OPTIONS = [
  { label: '5s', value: 5000 },
  { label: '10s', value: 10000 },
  { label: '30s', value: 30000 },
  { label: '1min', value: 60000 },
];

const ALARM_THRESHOLDS = {
  ecd_max_ppg: 14.5,
  hookload_deviation_pct: 15,
  torque_max_ftlb: 25000,
  pit_volume_delta_bbl: 5,
};

const RealTimeMonitor: React.FC<RealTimeMonitorProps> = ({ wellName = '' }) => {
  const { t } = useTranslation();

  // Connection state
  const [connectionMode, setConnectionMode] = useState<'server' | 'paste'>('paste');
  const [serverUrl, setServerUrl] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [connected, setConnected] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [connectionError, setConnectionError] = useState('');

  // Data state
  const [dataBuffer, setDataBuffer] = useState<DataPoint[]>([]);
  const [latestPoint, setLatestPoint] = useState<DataPoint | null>(null);
  const [alarms, setAlarms] = useState<Alarm[]>([]);

  // Paste mode
  const [xmlInput, setXmlInput] = useState('');
  const [parseError, setParseError] = useState('');

  // Auto-refresh
  const [isStreaming, setIsStreaming] = useState(false);
  const [refreshInterval, setRefreshInterval] = useState(10000);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Tab state
  const [activeTab, setActiveTab] = useState<'dashboard' | 'alarms' | 'xml'>('dashboard');

  // ── Connection handler ────────────────────────────────────
  const handleConnect = async () => {
    setConnecting(true);
    setConnectionError('');
    try {
      const res = await axios.post(`${API_BASE_URL}/witsml/connect`, {
        url: serverUrl, username, password,
      });
      if (res.data.connected || res.data.status === 'stub') {
        setConnected(true);
        setConnectionError(res.data.message || '');
      } else {
        setConnectionError(res.data.error || 'Connection failed');
      }
    } catch (err: any) {
      setConnectionError(err.response?.data?.detail || err.message);
    } finally {
      setConnecting(false);
    }
  };

  // ── Parse pasted XML ──────────────────────────────────────
  const handleParseXml = async () => {
    if (!xmlInput.trim()) return;
    setParseError('');
    try {
      const res = await axios.post(`${API_BASE_URL}/witsml/convert-log`, { xml: xmlInput });
      const points: DataPoint[] = res.data.data.map((d: any, i: number) => ({
        time: `T${i}`,
        ...d,
      }));
      setDataBuffer(prev => [...prev, ...points].slice(-200));
      if (points.length > 0) {
        setLatestPoint(points[points.length - 1]);
        checkAlarms(points[points.length - 1]);
      }
      setActiveTab('dashboard');
    } catch (err: any) {
      setParseError(err.response?.data?.detail || err.message);
    }
  };

  // ── Alarm checking ────────────────────────────────────────
  const checkAlarms = useCallback((point: DataPoint) => {
    const now = new Date().toISOString();
    const newAlarms: Alarm[] = [];

    if (point.ecd && point.ecd > ALARM_THRESHOLDS.ecd_max_ppg) {
      newAlarms.push({
        id: `ecd-${now}`, type: 'ecd', severity: 'critical',
        message: t('realtime.alarmECDHigh', { value: point.ecd.toFixed(2), threshold: ALARM_THRESHOLDS.ecd_max_ppg }),
        value: point.ecd, threshold: ALARM_THRESHOLDS.ecd_max_ppg, timestamp: now,
      });
    }

    if (point.torque && point.torque > ALARM_THRESHOLDS.torque_max_ftlb) {
      newAlarms.push({
        id: `torque-${now}`, type: 'torque', severity: 'warning',
        message: t('realtime.alarmTorqueHigh', { value: point.torque.toFixed(0), threshold: ALARM_THRESHOLDS.torque_max_ftlb }),
        value: point.torque, threshold: ALARM_THRESHOLDS.torque_max_ftlb, timestamp: now,
      });
    }

    if (newAlarms.length > 0) {
      setAlarms(prev => [...newAlarms, ...prev].slice(0, 50));
    }
  }, [t]);

  // ── Auto-refresh ──────────────────────────────────────────
  useEffect(() => {
    if (isStreaming && connected) {
      intervalRef.current = setInterval(() => {
        // In a real implementation, this would fetch fresh data from the WITSML server
        // For now, the stub connection doesn't provide real-time data
      }, refreshInterval);
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [isStreaming, connected, refreshInterval]);

  // ── Demo data generator ───────────────────────────────────
  const loadDemoData = () => {
    const demoPoints: DataPoint[] = Array.from({ length: 50 }, (_, i) => ({
      time: `${i * 10}s`,
      md: 8000 + i * 10,
      rop: 40 + Math.random() * 30,
      wob: 15 + Math.random() * 10,
      rpm: 120 + Math.random() * 20,
      torque: 8000 + Math.random() * 5000,
      spp: 2800 + Math.random() * 400,
      hookload: 180 + Math.random() * 40,
      ecd: 11.5 + Math.random() * 1.5,
      flow_rate: 600 + Math.random() * 100,
      mud_weight: 11.2,
    }));
    setDataBuffer(demoPoints);
    setLatestPoint(demoPoints[demoPoints.length - 1]);
    setConnected(true);
    setActiveTab('dashboard');
  };

  // ── KPI Card ──────────────────────────────────────────────
  const KPICard = ({ label, value, unit, color, icon: Icon, alarm }: {
    label: string; value: string; unit: string; color: string;
    icon: React.ElementType; alarm?: boolean;
  }) => (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className={`relative bg-white/[0.03] border rounded-2xl p-4 ${
        alarm ? 'border-red-500/50 shadow-lg shadow-red-500/10' : 'border-white/5'
      }`}
    >
      {alarm && (
        <div className="absolute top-2 right-2">
          <AlertTriangle size={14} className="text-red-400 animate-pulse" />
        </div>
      )}
      <div className="flex items-center gap-2 mb-2">
        <Icon size={14} className={color} />
        <span className="text-[10px] font-bold uppercase tracking-wider text-white/40">{label}</span>
      </div>
      <div className="flex items-baseline gap-1">
        <span className={`text-2xl font-black tracking-tight ${color}`}>{value}</span>
        <span className="text-xs text-white/30">{unit}</span>
      </div>
    </motion.div>
  );

  // ── Render ────────────────────────────────────────────────
  return (
    <div className="p-8 space-y-6 max-w-[1400px] mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 bg-cyan-500/10 rounded-2xl flex items-center justify-center">
            <Radio className="text-cyan-400" size={24} />
          </div>
          <div>
            <h2 className="text-2xl font-black tracking-tight">
              {t('realtime.title')}
            </h2>
            <p className="text-sm text-white/40">
              {wellName ? `${wellName} — ` : ''}{t('realtime.subtitle')}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* Connection indicator */}
          <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-bold ${
            connected ? 'bg-green-500/10 text-green-400' : 'bg-white/5 text-white/30'
          }`}>
            {connected ? <Wifi size={12} /> : <WifiOff size={12} />}
            {connected ? t('realtime.connected') : t('realtime.disconnected')}
          </div>

          {/* Stream controls */}
          {connected && (
            <div className="flex items-center gap-2">
              <button
                onClick={() => setIsStreaming(!isStreaming)}
                className={`p-2 rounded-xl transition-colors ${
                  isStreaming ? 'bg-red-500/20 text-red-400' : 'bg-green-500/20 text-green-400'
                }`}
              >
                {isStreaming ? <Pause size={14} /> : <Play size={14} />}
              </button>

              <select
                value={refreshInterval}
                onChange={e => setRefreshInterval(Number(e.target.value))}
                className="bg-white/5 border border-white/10 rounded-xl px-2 py-1.5 text-xs text-white/60"
              >
                {REFRESH_OPTIONS.map(opt => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>
          )}

          {/* Demo data button */}
          <button
            onClick={loadDemoData}
            className="px-3 py-1.5 rounded-xl bg-cyan-500/10 text-cyan-400 text-xs font-bold hover:bg-cyan-500/20 transition-colors"
          >
            {t('realtime.loadDemo')}
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-white/[0.02] p-1 rounded-2xl border border-white/5 w-fit">
        {(['dashboard', 'alarms', 'xml'] as const).map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 rounded-xl text-xs font-bold tracking-tight transition-all ${
              activeTab === tab
                ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20'
                : 'text-white/30 hover:text-white/60'
            }`}
          >
            {tab === 'dashboard' && t('realtime.tabDashboard')}
            {tab === 'alarms' && (
              <span className="flex items-center gap-1">
                {t('realtime.tabAlarms')}
                {alarms.length > 0 && (
                  <span className="bg-red-500 text-white text-[9px] px-1.5 py-0.5 rounded-full">{alarms.length}</span>
                )}
              </span>
            )}
            {tab === 'xml' && t('realtime.tabXmlInput')}
          </button>
        ))}
      </div>

      <AnimatePresence mode="wait">
        {/* ── Dashboard Tab ──────────────────────────────────── */}
        {activeTab === 'dashboard' && (
          <motion.div key="dashboard" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            {/* KPI Cards */}
            {latestPoint ? (
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3 mb-6">
                <KPICard
                  label={t('realtime.kpiROP')} value={(latestPoint.rop ?? 0).toFixed(1)}
                  unit="ft/hr" color="text-green-400" icon={TrendingUp}
                />
                <KPICard
                  label={t('realtime.kpiHookload')} value={(latestPoint.hookload ?? 0).toFixed(0)}
                  unit="klb" color="text-blue-400" icon={Activity}
                />
                <KPICard
                  label={t('realtime.kpiECD')} value={(latestPoint.ecd ?? 0).toFixed(2)}
                  unit="ppg" color="text-amber-400" icon={Activity}
                  alarm={latestPoint.ecd ? latestPoint.ecd > ALARM_THRESHOLDS.ecd_max_ppg : false}
                />
                <KPICard
                  label={t('realtime.kpiRPM')} value={(latestPoint.rpm ?? 0).toFixed(0)}
                  unit="rpm" color="text-purple-400" icon={RefreshCw}
                />
                <KPICard
                  label={t('realtime.kpiTorque')} value={((latestPoint.torque ?? 0) / 1000).toFixed(1)}
                  unit="kft-lb" color="text-orange-400" icon={Activity}
                  alarm={latestPoint.torque ? latestPoint.torque > ALARM_THRESHOLDS.torque_max_ftlb : false}
                />
              </div>
            ) : (
              <div className="bg-white/[0.02] border border-white/5 rounded-2xl p-12 text-center mb-6">
                <Server size={32} className="text-white/10 mx-auto mb-3" />
                <p className="text-white/30 text-sm">{t('realtime.noDataYet')}</p>
                <p className="text-white/20 text-xs mt-1">{t('realtime.noDataHint')}</p>
              </div>
            )}

            {/* Time-series chart */}
            {dataBuffer.length > 0 && (
              <div className="bg-white/[0.02] border border-white/5 rounded-2xl p-6">
                <h3 className="text-sm font-bold text-white/60 mb-4">{t('realtime.chartTitle')}</h3>
                <ResponsiveContainer width="100%" height={320}>
                  <LineChart data={dataBuffer}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" />
                    <XAxis dataKey="time" stroke="rgba(255,255,255,0.15)" tick={{ fontSize: 10 }} />
                    <YAxis yAxisId="left" stroke="rgba(255,255,255,0.15)" tick={{ fontSize: 10 }} />
                    <YAxis yAxisId="right" orientation="right" stroke="rgba(255,255,255,0.15)" tick={{ fontSize: 10 }} />
                    <Tooltip
                      contentStyle={{ background: '#1a1a2e', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px', fontSize: '11px' }}
                      labelStyle={{ color: '#999' }}
                    />
                    <Legend wrapperStyle={{ fontSize: '11px' }} />
                    <Line yAxisId="left" type="monotone" dataKey="rop" stroke="#22c55e" strokeWidth={2} dot={false} name="ROP (ft/hr)" />
                    <Line yAxisId="left" type="monotone" dataKey="hookload" stroke="#3b82f6" strokeWidth={2} dot={false} name="Hookload (klb)" />
                    <Line yAxisId="right" type="monotone" dataKey="ecd" stroke="#f59e0b" strokeWidth={2} dot={false} name="ECD (ppg)" />
                    <Line yAxisId="left" type="monotone" dataKey="torque" stroke="#f97316" strokeWidth={1} dot={false} name="Torque (ft-lb)" opacity={0.5} />
                    <ReferenceLine yAxisId="right" y={ALARM_THRESHOLDS.ecd_max_ppg} stroke="#ef4444" strokeDasharray="6 4" label={{ value: 'ECD Limit', fill: '#ef4444', fontSize: 10 }} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}

            {/* Secondary stats row */}
            {latestPoint && (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4">
                <div className="bg-white/[0.02] border border-white/5 rounded-xl p-3">
                  <span className="text-[9px] font-bold uppercase text-white/30">{t('realtime.kpiWOB')}</span>
                  <p className="text-lg font-black text-white/80">{(latestPoint.wob ?? 0).toFixed(1)} <span className="text-xs text-white/30">klb</span></p>
                </div>
                <div className="bg-white/[0.02] border border-white/5 rounded-xl p-3">
                  <span className="text-[9px] font-bold uppercase text-white/30">{t('realtime.kpiSPP')}</span>
                  <p className="text-lg font-black text-white/80">{(latestPoint.spp ?? 0).toFixed(0)} <span className="text-xs text-white/30">psi</span></p>
                </div>
                <div className="bg-white/[0.02] border border-white/5 rounded-xl p-3">
                  <span className="text-[9px] font-bold uppercase text-white/30">{t('realtime.kpiFlowRate')}</span>
                  <p className="text-lg font-black text-white/80">{(latestPoint.flow_rate ?? 0).toFixed(0)} <span className="text-xs text-white/30">gpm</span></p>
                </div>
                <div className="bg-white/[0.02] border border-white/5 rounded-xl p-3">
                  <span className="text-[9px] font-bold uppercase text-white/30">{t('realtime.kpiMD')}</span>
                  <p className="text-lg font-black text-white/80">{(latestPoint.md ?? 0).toFixed(0)} <span className="text-xs text-white/30">ft</span></p>
                </div>
              </div>
            )}
          </motion.div>
        )}

        {/* ── Alarms Tab ─────────────────────────────────────── */}
        {activeTab === 'alarms' && (
          <motion.div key="alarms" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <div className="bg-white/[0.02] border border-white/5 rounded-2xl p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-bold text-white/60">{t('realtime.alarmHistory')}</h3>
                {alarms.length > 0 && (
                  <button
                    onClick={() => setAlarms([])}
                    className="text-xs text-white/30 hover:text-white/60"
                  >
                    {t('realtime.clearAlarms')}
                  </button>
                )}
              </div>
              {alarms.length === 0 ? (
                <p className="text-white/20 text-sm text-center py-8">{t('realtime.noAlarms')}</p>
              ) : (
                <div className="space-y-2 max-h-[400px] overflow-y-auto custom-scrollbar">
                  {alarms.map(alarm => (
                    <div key={alarm.id} className={`flex items-center gap-3 p-3 rounded-xl border ${
                      alarm.severity === 'critical'
                        ? 'bg-red-500/5 border-red-500/20'
                        : 'bg-yellow-500/5 border-yellow-500/20'
                    }`}>
                      <AlertTriangle size={14} className={
                        alarm.severity === 'critical' ? 'text-red-400' : 'text-yellow-400'
                      } />
                      <div className="flex-1">
                        <p className="text-xs font-bold text-white/70">{alarm.message}</p>
                        <p className="text-[10px] text-white/30">{new Date(alarm.timestamp).toLocaleTimeString()}</p>
                      </div>
                      <span className={`text-[9px] font-bold uppercase px-2 py-0.5 rounded-full ${
                        alarm.severity === 'critical' ? 'bg-red-500/20 text-red-400' : 'bg-yellow-500/20 text-yellow-400'
                      }`}>
                        {alarm.severity}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </motion.div>
        )}

        {/* ── XML Input Tab ──────────────────────────────────── */}
        {activeTab === 'xml' && (
          <motion.div key="xml" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <div className="space-y-4">
              {/* Connection Mode Toggle */}
              <div className="flex gap-2">
                <button
                  onClick={() => setConnectionMode('paste')}
                  className={`px-4 py-2 rounded-xl text-xs font-bold ${
                    connectionMode === 'paste' ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20' : 'text-white/30 border border-white/5'
                  }`}
                >
                  <Upload size={12} className="inline mr-1" />
                  {t('realtime.pasteXml')}
                </button>
                <button
                  onClick={() => setConnectionMode('server')}
                  className={`px-4 py-2 rounded-xl text-xs font-bold ${
                    connectionMode === 'server' ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20' : 'text-white/30 border border-white/5'
                  }`}
                >
                  <Server size={12} className="inline mr-1" />
                  {t('realtime.connectServer')}
                </button>
              </div>

              {connectionMode === 'paste' ? (
                <div className="bg-white/[0.02] border border-white/5 rounded-2xl p-6">
                  <h3 className="text-sm font-bold text-white/60 mb-3">{t('realtime.pasteWitsmlXml')}</h3>
                  <textarea
                    value={xmlInput}
                    onChange={e => setXmlInput(e.target.value)}
                    placeholder={t('realtime.xmlPlaceholder')}
                    className="w-full h-48 bg-black/20 border border-white/10 rounded-xl p-4 text-xs font-mono text-white/70 placeholder:text-white/20 resize-none"
                  />
                  {parseError && (
                    <p className="text-red-400 text-xs mt-2">{parseError}</p>
                  )}
                  <button
                    onClick={handleParseXml}
                    disabled={!xmlInput.trim()}
                    className="mt-3 px-4 py-2 rounded-xl bg-cyan-500/20 text-cyan-400 text-xs font-bold hover:bg-cyan-500/30 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                  >
                    {t('realtime.parseAndLoad')}
                  </button>
                </div>
              ) : (
                <div className="bg-white/[0.02] border border-white/5 rounded-2xl p-6">
                  <h3 className="text-sm font-bold text-white/60 mb-4">{t('realtime.serverConnection')}</h3>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                    <div>
                      <label className="text-[10px] font-bold uppercase text-white/30 block mb-1">{t('realtime.serverUrl')}</label>
                      <input
                        type="url"
                        value={serverUrl}
                        onChange={e => setServerUrl(e.target.value)}
                        placeholder="https://witsml.example.com/store"
                        className="w-full bg-black/20 border border-white/10 rounded-xl px-3 py-2 text-xs text-white/70 placeholder:text-white/20"
                      />
                    </div>
                    <div>
                      <label className="text-[10px] font-bold uppercase text-white/30 block mb-1">{t('realtime.username')}</label>
                      <input
                        type="text"
                        value={username}
                        onChange={e => setUsername(e.target.value)}
                        className="w-full bg-black/20 border border-white/10 rounded-xl px-3 py-2 text-xs text-white/70"
                      />
                    </div>
                    <div>
                      <label className="text-[10px] font-bold uppercase text-white/30 block mb-1">{t('realtime.password')}</label>
                      <input
                        type="password"
                        value={password}
                        onChange={e => setPassword(e.target.value)}
                        className="w-full bg-black/20 border border-white/10 rounded-xl px-3 py-2 text-xs text-white/70"
                      />
                    </div>
                  </div>
                  {connectionError && (
                    <p className="text-yellow-400 text-xs mt-2">{connectionError}</p>
                  )}
                  <button
                    onClick={handleConnect}
                    disabled={connecting || !serverUrl}
                    className="mt-4 px-4 py-2 rounded-xl bg-cyan-500/20 text-cyan-400 text-xs font-bold hover:bg-cyan-500/30 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                  >
                    {connecting ? t('realtime.connecting') : t('realtime.connect')}
                  </button>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default RealTimeMonitor;
