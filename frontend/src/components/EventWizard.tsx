import React, { useState, useRef, useEffect } from 'react';
import { Upload, Check, ArrowRight, ArrowLeft as ArrowLeftIcon, Activity, PenTool, AlertTriangle, FilePlus, Pencil, Play } from 'lucide-react';
import axios from 'axios';
import { useTranslation } from 'react-i18next';
import { API_BASE_URL } from '../config';
import { useToast } from './ui/Toast';

interface EventWizardProps {
    onComplete: (eventData: any) => void;
    onCancel: () => void;
}

const PHASES_CONFIG = [
    { id: 'drilling', icon: Activity },
    { id: 'completion', icon: Check },
    { id: 'workover', icon: PenTool },
];

const EVENT_TYPES_CONFIG: Record<string, { id: string; family: string }[]> = {
    drilling: [
        { id: 'stuck_pipe', family: 'mechanics' },
        { id: 'lost_circulation', family: 'fluids' },
        { id: 'kick', family: 'fluids' },
        { id: 'bha_failure', family: 'mechanics' },
        { id: 'torque_drag', family: 'mechanics' },
        { id: 'severe_vibration', family: 'mechanics' },
        { id: 'wellbore_instability', family: 'well' },
        { id: 'other', family: 'well' },
    ],
    completion: [
        { id: 'perforation_failure', family: 'mechanics' },
        { id: 'formation_damage', family: 'well' },
        { id: 'sand_production', family: 'well' },
        { id: 'packer_failure', family: 'mechanics' },
        { id: 'gravel_pack_failure', family: 'mechanics' },
        { id: 'other', family: 'well' },
    ],
    workover: [
        { id: 'ct_failure', family: 'mechanics' },
        { id: 'bop_failure', family: 'control' },
        { id: 'stuck_string', family: 'mechanics' },
        { id: 'surface_equipment', family: 'mechanics' },
        { id: 'other', family: 'well' },
    ],
};

const FAMILY_IDS = ['well', 'fluids', 'mechanics', 'control', 'human'] as const;

// =====================================================================
// MINIMUM REQUIRED FIELDS PER EVENT TYPE — Nivel Elite
// Basado en investigación de estándares API, SPE, y mejores prácticas
// de ingeniería de perforación, completación y workover.
// =====================================================================
//
// _baseline: campos universales requeridos para CUALQUIER evento
// _baseline_completion: campos base para eventos de completación
// _baseline_workover: campos base para eventos de workover
// Cada evento tiene sus campos específicos adicionales.
// La validación exige: TODOS los baseline + AL MENOS UNO de los específicos.
// =====================================================================

const MINIMUM_REQUIRED_FIELDS: Record<string, string[]> = {
    // ── PERFORACIÓN: Baseline ──
    _baseline: ['depth_md', 'depth_tvd', 'mud_weight'],

    // ── PERFORACIÓN: Eventos ──
    // Pega de Tubería (Stuck Pipe) — Familia: Sarta/Mecánicos
    // Ref: SPE Stuck Pipe Manual, Aramco Early Warning System
    // Requiere: torque (tendencia), overpull (vs drag normal), hook_load (MOP),
    // differential_pressure (overbalance), friction_factor (para T&D model)
    stuck_pipe: ['torque', 'overpull', 'hook_load', 'differential_pressure', 'friction_factor'],

    // Pérdida de Circulación (Lost Circulation) — Familia: Fluidos/Presión
    // Ref: SPE Lost Circulation Classification, ECD Management
    // Requiere: flow_rate (caudal), ecd (densidad circulante equivalente),
    // fracture_gradient (gradiente de fractura), loss_rate (tasa de pérdida),
    // pore_pressure (presión de poro)
    lost_circulation: ['flow_rate', 'ecd', 'fracture_gradient', 'loss_rate', 'pore_pressure'],

    // Kick / Influjo — Familia: Fluidos/Presión
    // Ref: API RP 59, Well Control Formulas (Driller's / Wait & Weight)
    // Requiere: pit_gain (volumen kick), sidpp/sicp (presiones shut-in),
    // kill_mud_weight (peso lodo matar), bht (temp fondo)
    kick: ['pit_gain', 'sidpp', 'sicp', 'kill_mud_weight', 'bht'],

    // Falla de BHA — Familia: Sarta/Mecánicos
    // Ref: SPE Drillstring Vibration Analysis, BHA Fatigue Models
    // Requiere: torque, wob, rpm, lateral_vibration (g), mse (energía específica)
    bha_failure: ['torque', 'wob', 'rpm', 'lateral_vibration', 'mse'],

    // Torque/Drag Excesivo — Familia: Sarta/Mecánicos
    // Ref: Innova T&D, PVI TADPRO, Broomstick/Hookload Plots
    // Requiere: torque, overpull, hook_load, friction_factor, rop
    torque_drag: ['torque', 'overpull', 'hook_load', 'friction_factor', 'rop'],

    // Vibración Severa — Familia: Sarta/Mecánicos
    // Ref: SPE/IADC Drilling Vibration Monitoring, MSE Optimization
    // Requiere: torque, wob, rpm, lateral_vibration, mse, spp
    severe_vibration: ['torque', 'wob', 'rpm', 'lateral_vibration', 'mse', 'spp'],

    // Inestabilidad del Hoyo — Familia: Pozo/Geomecánica
    // Ref: Oilfield Geomechanics, Wellbore Stability Evaluations
    // Requiere: pore_pressure, ucs, hole_diameter, inclination, azimuth
    wellbore_instability: ['pore_pressure', 'ucs', 'hole_diameter', 'inclination', 'azimuth'],

    // ── COMPLETACIÓN: Baseline ──
    _baseline_completion: ['depth_md', 'depth_tvd', 'reservoir_pressure'],

    // Falla de Cañoneo — Familia: Sarta/Mecánicos
    // Ref: AAPG Perforation Design, SPE Underbalance Criteria
    // Requiere: shot_density, penetration_depth, skin_factor,
    // underbalance_pressure, perforation_diameter
    perforation_failure: ['shot_density', 'penetration_depth', 'skin_factor', 'underbalance_pressure', 'perforation_diameter'],

    // Daño de Formación — Familia: Pozo/Geomecánica
    // Ref: ScienceDirect Skin Factor & Well Test Analysis
    // Requiere: skin_factor, permeability, flow_rate, pressure_drawdown, porosity
    formation_damage: ['skin_factor', 'permeability', 'flow_rate', 'pressure_drawdown', 'porosity'],

    // Producción de Arena — Familia: Pozo/Geomecánica
    // Ref: SPE Sanding Prediction, Critical Drawdown Pressure
    // Requiere: ucs, pressure_drawdown, flow_rate, grain_size, shmin
    sand_production: ['ucs', 'pressure_drawdown', 'flow_rate', 'grain_size', 'shmin'],

    // Falla de Packer — Familia: Sarta/Mecánicos
    // Ref: SPE HTHP Packer Analysis, Tubing Movement Studies
    // Requiere: differential_pressure, bht, setting_depth,
    // tubing_pressure, annular_pressure
    packer_failure: ['differential_pressure', 'bht', 'setting_depth', 'tubing_pressure', 'annular_pressure'],

    // Falla de Empaque (Gravel Pack) — Familia: Sarta/Mecánicos
    // Ref: SPE Gravel Pack Fluidization, Sand Screen Selection
    // Requiere: flow_rate, pressure_drawdown, gravel_permeability,
    // screen_slot_size, skin_factor
    gravel_pack_failure: ['flow_rate', 'pressure_drawdown', 'gravel_permeability', 'screen_slot_size', 'skin_factor'],

    // ── WORKOVER: Baseline ──
    _baseline_workover: ['depth_md', 'depth_tvd', 'fluid_density'],

    // Falla de Coiled Tubing — Familia: Sarta/Mecánicos
    // Ref: SPE CT Fatigue Models, BSEE CT Stress Analysis
    // Requiere: ct_od, ct_wall_thickness, internal_pressure,
    // reel_radius, tensile_load
    ct_failure: ['ct_od', 'ct_wall_thickness', 'internal_pressure', 'reel_radius', 'tensile_load'],

    // Falla de BOP — Familia: Control de Pozo
    // Ref: API Standard 53, 30 CFR § 250.737
    // Requiere: bop_pressure_rating, test_pressure, wellhead_pressure,
    // last_test_date, bop_type
    bop_failure: ['bop_pressure_rating', 'test_pressure', 'wellhead_pressure', 'last_test_date', 'bop_type'],

    // Atascamiento (Stuck String Workover) — Familia: Sarta/Mecánicos
    // Ref: SPE Stuck Pipe Manual, Differential Sticking Guide
    // Requiere: overpull, torque, hook_load, differential_pressure,
    // stuck_point_depth
    stuck_string: ['overpull', 'torque', 'hook_load', 'differential_pressure', 'stuck_point_depth'],

    // Falla de Equipo Superficie — Familia: Sarta/Mecánicos
    // Requiere: equipment_type, operating_pressure, operating_temperature,
    // failure_mode, hours_in_service
    surface_equipment: ['equipment_type', 'operating_pressure', 'operating_temperature', 'failure_mode', 'hours_in_service'],
};

// =====================================================================
// FIELD LABELS — Etiquetas legibles para cada campo con unidades
// =====================================================================
const FIELD_LABELS_KEYS: Record<string, string> = {
    // ── Universales / Baseline ──
    depth_md:               'Profundidad MD (ft)',
    depth_tvd:              'Profundidad TVD (ft)',
    mud_weight:             'Peso del Lodo (ppg)',
    fluid_density:          'Densidad del Fluido (ppg)',
    reservoir_pressure:     'Presión de Reservorio (psi)',

    // ── Perforación: Mecánicos ──
    torque:                 'Torque (ft-lb)',
    overpull:               'Overpull (klb)',
    hook_load:              'Carga del Gancho (klb)',
    wob:                    'WOB (klb)',
    rpm:                    'RPM',
    rop:                    'ROP (ft/hr)',
    friction_factor:        'Factor de Fricción (adim.)',
    differential_pressure:  'Presión Diferencial (psi)',
    spp:                    'Presión de Standpipe (psi)',
    mse:                    'MSE — Energía Específica (psi)',
    lateral_vibration:      'Vibración Lateral (g)',

    // ── Perforación: Fluidos / Presión ──
    flow_rate:              'Caudal (gpm)',
    ecd:                    'ECD (ppg)',
    fracture_gradient:      'Gradiente de Fractura (ppg)',
    loss_rate:              'Tasa de Pérdida (bbl/hr)',
    pore_pressure:          'Presión de Poro (ppg)',
    pit_gain:               'Ganancia de Pileta (bbl)',
    sidpp:                  'SIDPP (psi)',
    sicp:                   'SICP (psi)',
    kill_mud_weight:        'Peso Lodo de Matar (ppg)',
    bht:                    'Temperatura de Fondo (°F)',

    // ── Perforación: Geomecánica ──
    ucs:                    'UCS — Resist. Compresión (psi)',
    hole_diameter:          'Diámetro del Hoyo (in)',
    inclination:            'Inclinación (°)',
    azimuth:                'Azimut (°)',

    // ── Completación: Cañoneo ──
    shot_density:           'Densidad de Disparos (SPF)',
    penetration_depth:      'Profundidad de Penetración (in)',
    skin_factor:            'Factor de Daño / Skin (adim.)',
    underbalance_pressure:  'Presión Underbalance (psi)',
    perforation_diameter:   'Diámetro de Perforación (in)',

    // ── Completación: Formación / Arena ──
    permeability:           'Permeabilidad (mD)',
    pressure_drawdown:      'Drawdown de Presión (psi)',
    porosity:               'Porosidad (%)',
    grain_size:             'Tamaño de Grano (mm)',
    shmin:                  'Esfuerzo Horizontal Mín. (psi)',

    // ── Completación: Packer ──
    setting_depth:          'Profundidad de Asentamiento (ft)',
    tubing_pressure:        'Presión de Tubing (psi)',
    annular_pressure:       'Presión Anular (psi)',

    // ── Completación: Gravel Pack ──
    gravel_permeability:    'Permeabilidad del Gravel (D)',
    screen_slot_size:       'Apertura de Screen (in)',

    // ── Workover: Coiled Tubing ──
    ct_od:                  'OD del CT (in)',
    ct_wall_thickness:      'Espesor Pared CT (in)',
    internal_pressure:      'Presión Interna CT (psi)',
    reel_radius:            'Radio del Carrete (ft)',
    tensile_load:           'Carga Tensil (klb)',

    // ── Workover: BOP ──
    bop_pressure_rating:    'Presión Nominal BOP (psi)',
    test_pressure:          'Presión de Prueba (psi)',
    wellhead_pressure:      'Presión de Cabezal (psi)',
    last_test_date:         'Fecha Última Prueba',
    bop_type:               'Tipo de BOP',

    // ── Workover: Stuck String ──
    stuck_point_depth:      'Profundidad Pto. Pegado (ft)',

    // ── Workover: Equipo Superficie ──
    equipment_type:         'Tipo de Equipo',
    operating_pressure:     'Presión de Operación (psi)',
    operating_temperature:  'Temperatura de Operación (°F)',
    failure_mode:           'Modo de Falla',
    hours_in_service:       'Horas en Servicio',
};

const EventWizard: React.FC<EventWizardProps> = ({ onComplete, onCancel }) => {
    const { t } = useTranslation();
    const { addToast } = useToast();

    // Translated constants (resolved inside component)
    const PHASES = PHASES_CONFIG.map(p => ({ ...p, label: t(`eventWizard.phases.${p.id}`) }));
    const EVENT_TYPES: Record<string, { id: string; label: string; family: string }[]> = Object.fromEntries(
        Object.entries(EVENT_TYPES_CONFIG).map(([phase, types]) => [
            phase,
            types.map(et => ({ ...et, label: t(`eventWizard.eventTypes.${et.id}`) }))
        ])
    );
    const FAMILY_LABELS: Record<string, string> = Object.fromEntries(
        FAMILY_IDS.map(id => [id, t(`eventWizard.families.${id}`)])
    );
    const FIELD_LABELS: Record<string, string> = Object.fromEntries(
        Object.keys(FIELD_LABELS_KEYS).map(key => [key, t(`eventWizard.fields.${key}`)])
    );
    const [step, setStep] = useState(1);
    const [phase, setPhase] = useState<string | null>(null);
    const [eventType, setEventType] = useState<string | null>(null);
    const [files, setFiles] = useState<File[]>([]);
    const [isExtracting, setIsExtracting] = useState(false);
    const [extractedData, setExtractedData] = useState<any>(null);
    const [manualOverrides, setManualOverrides] = useState<Record<string, string>>({});
    const [showManualInputs, setShowManualInputs] = useState(false);
    const [manualFieldsSnapshot, setManualFieldsSnapshot] = useState<string[]>([]);
    const additionalFileRef = useRef<HTMLInputElement>(null);

    // Step 3 state: Agent selection
    const [availableAgents, setAvailableAgents] = useState<any[]>([]);
    const [selectedAgents, setSelectedAgents] = useState<string[]>([]);
    const [leaderAgent, setLeaderAgent] = useState<string | null>(null);

    // Auto-infer family from event type selection
    const inferredFamily = React.useMemo(() => {
        if (!phase || !eventType) return null;
        const types = EVENT_TYPES[phase] || [];
        const match = types.find(t => t.id === eventType);
        return match?.family || 'well';
    }, [phase, eventType]);

    // Merge extracted data + manual overrides
    const mergedData = React.useMemo(() => {
        if (!extractedData) return null;
        const merged = { ...extractedData };
        for (const [key, value] of Object.entries(manualOverrides)) {
            if (value !== '') {
                merged[key] = parseFloat(value) || value;
            }
        }
        return merged;
    }, [extractedData, manualOverrides]);

    // Fetch agents when reaching Step 3
    useEffect(() => {
        if (step === 3 && availableAgents.length === 0) {
            axios.get(`${API_BASE_URL}/agents`)
                .then(res => {
                    setAvailableAgents(res.data);
                    // Pre-select all agents and set drilling_engineer as leader
                    const allIds = res.data.map((a: any) => a.id);
                    setSelectedAgents(allIds);
                    setLeaderAgent(allIds.includes('drilling_engineer') ? 'drilling_engineer' : allIds[0]);
                })
                .catch(err => console.error("Failed to fetch agents:", err));
        }
    }, [step, availableAgents.length]);

    // ----- Validation -----
    // Determine which baseline fields apply based on the selected phase
    const getBaselineKey = (): string => {
        if (phase === 'completion') return '_baseline_completion';
        if (phase === 'workover') return '_baseline_workover';
        return '_baseline'; // drilling default
    };

    const validateMinimumData = (data: any): { valid: boolean; missingBaseline: string[]; missingSpecific: string[]; } => {
        const baselineKey = getBaselineKey();
        const baselineFields = MINIMUM_REQUIRED_FIELDS[baselineKey] || MINIMUM_REQUIRED_FIELDS._baseline;

        if (!data || Object.keys(data).length === 0) {
            return { valid: false, missingBaseline: baselineFields, missingSpecific: [] };
        }

        const hasValue = (key: string) => {
            const val = data[key];
            return val !== null && val !== undefined && val !== '' && val !== 0 && val !== '0';
        };

        const missingBaseline = baselineFields.filter(f => !hasValue(f));
        const specificFields = MINIMUM_REQUIRED_FIELDS[eventType || ''] || [];
        const hasAnySpecific = specificFields.length === 0 || specificFields.some(f => hasValue(f));
        const missingSpecific = hasAnySpecific ? [] : specificFields;

        return { valid: missingBaseline.length === 0 && hasAnySpecific, missingBaseline, missingSpecific };
    };

    const getMissingFields = (data: any): string[] => {
        const validation = validateMinimumData(data);
        const missing: string[] = [...validation.missingBaseline];
        if (validation.missingSpecific.length > 0) {
            for (const f of validation.missingSpecific) {
                if (!missing.includes(f)) missing.push(f);
            }
        }
        return missing;
    };

    // ----- File Upload -----
    const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>, isAdditional: boolean = false) => {
        if (e.target.files && e.target.files.length > 0) {
            const selectedFiles = Array.from(e.target.files);
            const allFiles = isAdditional ? [...files, ...selectedFiles] : selectedFiles;

            if (allFiles.length > 5) {
                addToast(t('eventWizard.maxFilesWarning'), 'warning');
                return;
            }

            const totalSize = allFiles.reduce((acc, file) => acc + file.size, 0);
            if (totalSize > 10 * 1024 * 1024) {
                addToast(t('eventWizard.maxSizeWarning'), 'warning');
                return;
            }

            setFiles(allFiles);
            setIsExtracting(true);

            const formData = new FormData();
            selectedFiles.forEach(file => { formData.append('files', file); });

            try {
                const response = await axios.post(`${API_BASE_URL}/events/extract`, formData, {
                    headers: { 'Content-Type': 'multipart/form-data' }
                });
                const newData = response.data;

                if (isAdditional && extractedData) {
                    const merged = { ...extractedData };
                    for (const [key, value] of Object.entries(newData)) {
                        if (value !== null && value !== undefined && value !== '' && value !== 0) {
                            merged[key] = value;
                        }
                    }
                    setExtractedData(merged);
                    addToast(t('eventWizard.additionalDataMerged', { files: selectedFiles.map(f => f.name).join(', ') }), 'success');
                } else {
                    setExtractedData(newData);
                }
            } catch (error) {
                console.error("Extraction error:", error);
                addToast(t('eventWizard.extractionError'), 'error');
            } finally {
                setIsExtracting(false);
                if (e.target) e.target.value = '';
            }
        }
    };

    const handleManualChange = (field: string, value: string) => {
        setManualOverrides(prev => ({ ...prev, [field]: value }));
    };

    // ----- Agent toggle -----
    const handleAgentToggle = (agentId: string) => {
        const isSelected = selectedAgents.includes(agentId);
        let newSelection: string[];

        if (isSelected) {
            newSelection = selectedAgents.filter(id => id !== agentId);
            if (leaderAgent === agentId) setLeaderAgent(null);
        } else {
            newSelection = [...selectedAgents, agentId];
            if (newSelection.length === 1) setLeaderAgent(agentId);
        }

        setSelectedAgents(newSelection);
    };

    // ----- Final Submit -----
    const handleFinalSubmit = () => {
        onComplete({
            phase,
            family: inferredFamily,
            event_type: eventType,
            parameters: mergedData || {},
            workflow: selectedAgents,
            leader: leaderAgent
        });
    };

    // ----- Skip data and go to step 3 -----
    const handleSkipData = () => {
        setExtractedData({});
        setStep(3);
    };

    // ----- Step Indicator (3 steps) -----
    const renderStepIndicator = () => (
        <div className="flex items-center justify-center gap-2 mb-8">
            {[
                { num: 1, label: t('eventWizard.steps.identification') },
                { num: 2, label: t('eventWizard.steps.data') },
                { num: 3, label: t('eventWizard.steps.specialists') },
            ].map((s, i) => (
                <React.Fragment key={s.num}>
                    <div className="flex flex-col items-center gap-1">
                        <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold border-2 transition-all ${
                            step === s.num ? 'border-ibm-blue-500 bg-ibm-blue-500/20 text-ibm-blue-400' :
                            step > s.num ? 'border-green-500 bg-green-500/20 text-green-400' :
                            'border-white/20 bg-white/5 text-white/30'
                        }`}>
                            {step > s.num ? <Check size={14} /> : s.num}
                        </div>
                        <span className={`text-xs ${step === s.num ? 'text-ibm-blue-400' : step > s.num ? 'text-green-400' : 'text-white/30'}`}>
                            {s.label}
                        </span>
                    </div>
                    {i < 2 && <div className={`w-16 h-0.5 mb-5 ${step > s.num ? 'bg-green-500' : 'bg-white/10'}`} />}
                </React.Fragment>
            ))}
        </div>
    );

    // ===== Step 1: Identification =====
    const renderStep1 = () => (
        <div className="space-y-6 animate-fadeIn">
            <h3 className="text-xl font-bold text-white mb-4">{t('eventWizard.step1Title')}</h3>

            <div className="space-y-4">
                <label className="text-sm text-ibm-gray-300">{t('eventWizard.operationalPhase')}</label>
                <div className="grid grid-cols-3 gap-4">
                    {PHASES.map((p) => (
                        <button
                            key={p.id}
                            onClick={() => { setPhase(p.id); setEventType(null); }}
                            className={`p-4 rounded-lg border flex flex-col items-center gap-2 transition-all ${phase === p.id
                                ? 'bg-ibm-blue-600/20 border-ibm-blue-500 text-white'
                                : 'bg-white/5 border-white/10 text-white/50 hover:bg-white/10'
                                }`}
                        >
                            <p.icon size={24} />
                            <span className="font-medium">{p.label}</span>
                        </button>
                    ))}
                </div>
            </div>

            {phase && (
                <div className="space-y-4 animate-fadeIn">
                    <label className="text-sm text-ibm-gray-300">{t('eventWizard.eventType')}</label>
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                        {(EVENT_TYPES[phase] || []).map((et) => (
                            <button
                                key={et.id}
                                onClick={() => setEventType(et.id)}
                                className={`p-3 rounded-lg border text-left transition-all ${eventType === et.id
                                    ? 'bg-ibm-blue-600/20 border-ibm-blue-500 text-white'
                                    : 'bg-white/5 border-white/10 text-white/50 hover:bg-white/10'
                                    }`}
                            >
                                <div className="font-medium text-sm">{et.label}</div>
                            </button>
                        ))}
                    </div>
                </div>
            )}

            {phase && eventType && inferredFamily && (
                <div className="animate-fadeIn flex items-center gap-3 px-4 py-3 rounded-lg bg-white/5 border border-white/10">
                    <span className="text-xs text-white/40 uppercase tracking-wider">{t('eventWizard.family')}:</span>
                    <span className="text-sm text-ibm-blue-400 font-medium">{FAMILY_LABELS[inferredFamily] || inferredFamily}</span>
                    <span className="text-[10px] text-white/20 ml-auto italic">{t('eventWizard.autoClassified')}</span>
                </div>
            )}

            <div className="flex justify-end pt-6">
                <button onClick={onCancel} className="mr-auto text-white/50 hover:text-white px-4 py-2">
                    {t('common.cancel')}
                </button>
                <button
                    disabled={!phase || !eventType}
                    onClick={() => setStep(2)}
                    className="bg-ibm-blue-600 hover:bg-ibm-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white px-6 py-2 rounded flex items-center gap-2 transition-colors"
                >
                    {t('common.next')} <ArrowRight size={16} />
                </button>
            </div>
        </div>
    );

    // ===== Step 2: Data Capture =====
    const renderStep2 = () => {
        const validation = mergedData && Object.keys(mergedData).length > 0
            ? validateMinimumData(mergedData)
            : null;

        const extractedFieldCount = mergedData
            ? Object.entries(mergedData).filter(([k, v]) => k !== 'operation_summary' && v !== null && v !== '' && v !== undefined).length
            : 0;

        const missingFields = mergedData ? getMissingFields(mergedData) : [];
        const specificFields = MINIMUM_REQUIRED_FIELDS[eventType || ''] || [];
        const baselineFields = MINIMUM_REQUIRED_FIELDS[getBaselineKey()] || MINIMUM_REQUIRED_FIELDS._baseline;

        return (
            <div className="space-y-6 animate-fadeIn">
                <h3 className="text-xl font-bold text-white mb-4">{t('eventWizard.step2Title')}</h3>

                {!extractedData ? (
                    <>
                        <div className="border-2 border-dashed border-white/20 rounded-xl p-12 text-center hover:border-ibm-blue-500/50 transition-colors bg-white/5">
                            <input type="file" id="file-upload" className="hidden" accept=".pdf,.csv,.txt,.md" multiple
                                onChange={(e) => handleFileUpload(e, false)} disabled={isExtracting} />
                            <label htmlFor="file-upload" className={`flex flex-col items-center gap-4 ${isExtracting ? 'pointer-events-none' : 'cursor-pointer'}`}>
                                {isExtracting ? (
                                    <>
                                        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-ibm-blue-500"></div>
                                        <div className="text-ibm-blue-300 animate-pulse">{t('eventWizard.analyzingDocs')}</div>
                                    </>
                                ) : (
                                    <>
                                        <div className="p-4 bg-ibm-blue-500/10 rounded-full text-ibm-blue-400"><Upload size={32} /></div>
                                        <div>
                                            <div className="text-lg font-medium text-white">{t('eventWizard.uploadDDR')}</div>
                                            <div className="text-sm text-white/40 mt-1">{t('eventWizard.supportedFormats')}</div>
                                            <div className="text-xs text-yellow-500/80 mt-2 font-mono border border-yellow-500/20 bg-yellow-500/5 px-2 py-1 rounded inline-block">
                                                {t('eventWizard.maxFiles')}
                                            </div>
                                        </div>
                                    </>
                                )}
                            </label>
                        </div>
                        <div className="flex justify-between mt-4">
                            <button onClick={() => setStep(1)} className="text-white/50 hover:text-white px-4 py-2 flex items-center gap-2">
                                <ArrowLeftIcon size={16} /> {t('common.back')}
                            </button>
                            <button onClick={handleSkipData} className="text-sm text-white/40 hover:text-white transition-colors">
                                {t('eventWizard.skipData')}
                            </button>
                        </div>
                    </>
                ) : (
                    <div className="space-y-5">
                        {/* Success Banner */}
                        <div className="bg-green-500/10 border border-green-500/20 p-4 rounded-lg flex items-center gap-3 text-green-400">
                            <Check size={20} className="flex-shrink-0" />
                            <div className="flex-1 min-w-0">
                                <div className="font-bold">{t('eventWizard.extractionSuccess')}</div>
                                <div className="text-xs opacity-80 mb-1">{t('eventWizard.detectedCount', { count: extractedFieldCount, files: files.length })}</div>
                                <div className="flex flex-wrap gap-2">
                                    {files.map((f, i) => (
                                        <span key={i} className="text-xs bg-green-500/20 px-2 py-0.5 rounded text-green-300 border border-green-500/30">
                                            {f.name} ({(f.size / 1024).toFixed(1)} KB)
                                        </span>
                                    ))}
                                </div>
                            </div>
                            <button onClick={() => { setExtractedData(null); setFiles([]); setManualOverrides({}); setShowManualInputs(false); setManualFieldsSnapshot([]); }}
                                className="ml-auto text-xs underline hover:text-green-300 whitespace-nowrap flex-shrink-0">
                                {t('eventWizard.reset')}
                            </button>
                        </div>

                        {/* Extracted Data Summary */}
                        <div className="bg-white/5 border border-white/10 rounded-lg p-4">
                            <div className="flex items-center justify-between mb-3">
                                <span className="text-sm text-white/60 font-medium">{t('eventWizard.detectedParams')}</span>
                                <span className="text-xs text-ibm-blue-400 font-mono">{extractedFieldCount} {t('eventWizard.fieldsLabel')}</span>
                            </div>
                            <div className="flex flex-wrap gap-2">
                                {Object.entries(mergedData || {})
                                    .filter(([k, v]) => k !== 'operation_summary' && v !== null && v !== '' && v !== undefined)
                                    .map(([key, value]) => {
                                        const isManual = manualOverrides[key] !== undefined && manualOverrides[key] !== '';
                                        return (
                                            <span key={key} className={`text-xs px-2.5 py-1.5 rounded-lg font-mono border ${isManual ? 'bg-ibm-blue-500/10 border-ibm-blue-500/30 text-ibm-blue-300' : 'bg-white/10 border-white/5 text-white/70'}`}>
                                                <span className="text-white/40">{FIELD_LABELS[key]?.split(' (')[0] || key.replace(/_/g, ' ')}:</span>{' '}
                                                <span className="text-ibm-blue-400">{String(value)}</span>
                                                {isManual && <span className="ml-1 text-[9px] text-ibm-blue-500/60">(manual)</span>}
                                            </span>
                                        );
                                    })}
                                {extractedFieldCount === 0 && <span className="text-xs text-white/30 italic">{t('eventWizard.noParamsDetected')}</span>}
                            </div>
                        </div>

                        {/* Operation Summary */}
                        {(mergedData as any)?.operation_summary && (
                            <div className="bg-white/5 p-4 rounded border border-white/10">
                                <label className="text-xs text-white/40 uppercase block mb-1">{t('eventWizard.operationSummary')}</label>
                                <p className="text-white/80 text-sm">{(mergedData as any).operation_summary}</p>
                            </div>
                        )}

                        {/* Validation Warning */}
                        {validation && !validation.valid && (
                            <div className="bg-yellow-500/10 border border-yellow-500/20 p-4 rounded-lg space-y-3">
                                <div className="flex items-center gap-2 text-yellow-400">
                                    <AlertTriangle size={16} />
                                    <span className="font-bold text-sm">{t('eventWizard.insufficientData')}</span>
                                </div>
                                {validation.missingBaseline.length > 0 && (
                                    <div className="text-xs text-yellow-300/80">
                                        {t('eventWizard.missingRequired')}: <span className="font-medium">{validation.missingBaseline.map(f => FIELD_LABELS[f]?.split(' (')[0] || f).join(', ')}</span>
                                    </div>
                                )}
                                {validation.missingSpecific.length > 0 && (
                                    <div className="text-xs text-yellow-300/80">
                                        {t('eventWizard.requiresAtLeastOne', { eventType: eventType?.replace(/_/g, ' ') })}: <span className="font-medium">{validation.missingSpecific.map(f => FIELD_LABELS[f]?.split(' (')[0] || f).join(', ')}</span>
                                    </div>
                                )}
                                <div className="flex flex-wrap gap-2 pt-1">
                                    {files.length < 5 && (
                                        <button onClick={() => additionalFileRef.current?.click()} disabled={isExtracting}
                                            className="flex items-center gap-1.5 text-xs bg-yellow-500/10 hover:bg-yellow-500/20 border border-yellow-500/30 text-yellow-400 px-3 py-1.5 rounded-lg transition-colors disabled:opacity-50">
                                            <FilePlus size={13} /> {isExtracting ? t('eventWizard.extracting') : t('eventWizard.uploadAnother')}
                                        </button>
                                    )}
                                    <button onClick={() => { setManualFieldsSnapshot(missingFields); setShowManualInputs(true); }}
                                        className="flex items-center gap-1.5 text-xs bg-ibm-blue-500/10 hover:bg-ibm-blue-500/20 border border-ibm-blue-500/30 text-ibm-blue-400 px-3 py-1.5 rounded-lg transition-colors">
                                        <Pencil size={13} /> {t('eventWizard.completeManually')}
                                    </button>
                                </div>
                            </div>
                        )}

                        <input ref={additionalFileRef} type="file" className="hidden" accept=".pdf,.csv,.txt,.md" multiple
                            onChange={(e) => handleFileUpload(e, true)} disabled={isExtracting} />

                        {isExtracting && extractedData && (
                            <div className="flex items-center gap-3 p-4 bg-ibm-blue-500/5 border border-ibm-blue-500/20 rounded-lg animate-pulse">
                                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-ibm-blue-500"></div>
                                <span className="text-sm text-ibm-blue-300">{t('eventWizard.extractingNew')}</span>
                            </div>
                        )}

                        {/* Manual Input — uses snapshot of missing fields so inputs don't vanish mid-typing */}
                        {showManualInputs && manualFieldsSnapshot.length > 0 && (
                            <div className="bg-ibm-blue-500/5 border border-ibm-blue-500/20 rounded-lg p-4 space-y-4 animate-fadeIn">
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-2">
                                        <Pencil size={14} className="text-ibm-blue-400" />
                                        <span className="text-sm font-medium text-white">{t('eventWizard.completeMissing')}</span>
                                    </div>
                                    <button onClick={() => setShowManualInputs(false)} className="text-xs text-white/30 hover:text-white/60 transition-colors">{t('eventWizard.hide')}</button>
                                </div>
                                {specificFields.length > 0 && validation && validation.missingSpecific.length > 0 && (
                                    <div className="text-[11px] text-ibm-blue-400/70 bg-ibm-blue-500/10 px-3 py-1.5 rounded">
                                        {t('eventWizard.fillAtLeastOneStarred')}
                                    </div>
                                )}
                                <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                                    {manualFieldsSnapshot.map(field => {
                                        const isSpecificOnly = !baselineFields.includes(field) && specificFields.includes(field);
                                        const isFilled = manualOverrides[field] !== undefined && manualOverrides[field] !== '';
                                        return (
                                            <div key={field} className="space-y-1">
                                                <label className="text-xs text-white/50 flex items-center gap-1">
                                                    {FIELD_LABELS[field] || field.replace(/_/g, ' ')}
                                                    {isSpecificOnly && <span className="text-yellow-400" title="Al menos uno requerido">★</span>}
                                                    {isFilled && <Check size={10} className="text-green-400 ml-1" />}
                                                </label>
                                                <input type="number" step="any" placeholder={t('eventWizard.enterValue')}
                                                    value={manualOverrides[field] || ''}
                                                    onChange={(e) => handleManualChange(field, e.target.value)}
                                                    className={`w-full bg-white/5 border rounded px-3 py-2 text-sm text-white font-mono focus:outline-none focus:border-ibm-blue-500 focus:ring-1 focus:ring-ibm-blue-500/30 placeholder:text-white/20 ${isFilled ? 'border-green-500/30' : 'border-white/10'}`} />
                                            </div>
                                        );
                                    })}
                                </div>
                            </div>
                        )}

                        {validation && validation.valid && (
                            <div className="bg-green-500/5 border border-green-500/20 p-3 rounded-lg flex items-center gap-2 text-green-400">
                                <Check size={16} />
                                <span className="text-sm font-medium">{t('eventWizard.dataComplete')}</span>
                            </div>
                        )}

                        {validation && validation.valid && files.length < 5 && (
                            <button onClick={() => additionalFileRef.current?.click()} disabled={isExtracting}
                                className="flex items-center gap-2 text-xs text-white/30 hover:text-white/60 transition-colors disabled:opacity-50">
                                <FilePlus size={13} /> {t('eventWizard.addMoreDocs')} ({files.length}/5)
                            </button>
                        )}

                        {/* Navigation */}
                        <div className="flex justify-between pt-4">
                            <button onClick={() => { setExtractedData(null); setFiles([]); setManualOverrides({}); setShowManualInputs(false); setManualFieldsSnapshot([]); }}
                                className="text-white/50 hover:text-white px-4 py-2 flex items-center gap-2">
                                <ArrowLeftIcon size={16} /> {t('common.back')}
                            </button>
                            <div className="flex items-center gap-4">
                                <button onClick={handleSkipData} className="text-sm text-white/40 hover:text-white transition-colors">
                                    {t('eventWizard.skipData')}
                                </button>
                                <button
                                    onClick={() => setStep(3)}
                                    disabled={validation ? !validation.valid : true}
                                    className="bg-ibm-blue-600 hover:bg-ibm-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white px-6 py-2 rounded flex items-center gap-2 transition-colors"
                                >
                                    {t('common.next')} <ArrowRight size={16} />
                                </button>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        );
    };

    // ===== Step 3: Agent Selection =====
    const renderStep3 = () => (
        <div className="space-y-6 animate-fadeIn">
            <h3 className="text-xl font-bold text-white mb-4">{t('eventWizard.step3Title')}</h3>
            <div className="flex justify-between items-center mb-4">
                <p className="text-white/60 text-sm">
                    {t('eventWizard.selectAgents')}
                    {selectedAgents.length > 0 && !leaderAgent && (
                        <span className="block text-yellow-400 text-xs mt-1 flex items-center gap-1">
                            <AlertTriangle size={12} /> {t('eventWizard.designateLeader')}
                        </span>
                    )}
                </p>
                <button
                    onClick={() => {
                        if (selectedAgents.length === availableAgents.length) {
                            setSelectedAgents([]);
                            setLeaderAgent(null);
                        } else {
                            const allIds = availableAgents.map(a => a.id);
                            setSelectedAgents(allIds);
                            if (!leaderAgent) {
                                setLeaderAgent(allIds.includes('drilling_engineer') ? 'drilling_engineer' : allIds[0]);
                            }
                        }
                    }}
                    className="text-ibm-blue-400 text-sm hover:text-ibm-blue-300 font-medium whitespace-nowrap"
                >
                    {selectedAgents.length === availableAgents.length ? t('eventWizard.deselectAll') : t('eventWizard.selectAll')}
                </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-h-64 overflow-y-auto custom-scrollbar p-1">
                {availableAgents.map(agent => (
                    <div
                        key={agent.id}
                        onClick={() => handleAgentToggle(agent.id)}
                        className={`p-3 rounded-lg border cursor-pointer transition-all flex items-center gap-3 ${selectedAgents.includes(agent.id)
                            ? 'bg-ibm-blue-500/20 border-ibm-blue-500 text-white'
                            : 'bg-white/5 border-white/10 text-white/50 hover:bg-white/10'
                            }`}
                    >
                        <div className={`w-4 h-4 rounded border flex items-center justify-center ${selectedAgents.includes(agent.id) ? 'bg-ibm-blue-500 border-ibm-blue-500' : 'border-white/30'}`}>
                            {selectedAgents.includes(agent.id) && <Check size={12} className="text-white" />}
                        </div>
                        <div className="flex-1 min-w-0">
                            <div className="font-medium text-sm truncate">{agent.name.replace(/_/g, ' ').toUpperCase()}</div>
                            <div className="text-xs opacity-70 truncate">{agent.role}</div>
                        </div>
                        {selectedAgents.includes(agent.id) && (
                            <div
                                onClick={(e) => { e.stopPropagation(); setLeaderAgent(agent.id); }}
                                className={`flex-shrink-0 px-2 py-1 rounded text-xs font-bold border transition-colors ${leaderAgent === agent.id
                                    ? 'bg-yellow-500/20 border-yellow-500 text-yellow-500 shadow-[0_0_10px_rgba(234,179,8,0.2)]'
                                    : 'border-white/20 text-white/40 hover:border-white/60 hover:text-white'
                                    }`}
                            >
                                {leaderAgent === agent.id ? `★ ${t('eventWizard.leader')}` : t('eventWizard.designateLeaderBtn')}
                            </div>
                        )}
                    </div>
                ))}
            </div>

            <div className="flex justify-between pt-6">
                <button onClick={() => setStep(2)} className="text-white/50 hover:text-white px-4 py-2 flex items-center gap-2">
                    <ArrowLeftIcon size={16} /> {t('common.back')}
                </button>
                <button
                    onClick={handleFinalSubmit}
                    disabled={selectedAgents.length === 0 || !leaderAgent}
                    className="bg-ibm-blue-600 hover:bg-ibm-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white px-6 py-2 rounded flex items-center gap-2 transition-colors"
                >
                    {t('eventWizard.startAnalysis')} <Play size={16} />
                </button>
            </div>
        </div>
    );

    return (
        <div className="bg-black/40 backdrop-blur-xl border border-white/10 rounded-xl p-8 w-full max-w-7xl mx-auto shadow-2xl">
            <div className="flex items-center justify-between mb-4">
                <h2 className="text-2xl font-bold font-mono">{t('eventWizard.title')}</h2>
            </div>

            {renderStepIndicator()}

            {step === 1 && renderStep1()}
            {step === 2 && renderStep2()}
            {step === 3 && renderStep3()}
        </div>
    );
};

export default EventWizard;
