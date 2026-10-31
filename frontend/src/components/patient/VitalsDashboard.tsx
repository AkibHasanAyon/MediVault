import React, { useState, useEffect } from 'react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
  ReferenceLine,
} from 'recharts';
import {
  Activity,
  Plus,
  Heart,
  Scale,
  Layers,
  AlertTriangle,
  AlertCircle,
  CheckCircle2,
  ShieldAlert,
  PhoneCall,
  Info,
} from 'lucide-react';
import { vitalsApi, VitalsSummary, GlucoseLog, BloodPressureLog, WeightLog } from '../../api/vitals';
import { Modal } from '../common/Modal';
import {
  assessGlucose,
  assessBloodPressure,
  ClinicalAssessment,
} from '../../utils/clinicalVitals';

interface VitalsDashboardProps {
  summary: VitalsSummary | null;
  onRefresh: () => void;
}

interface TrendPoint {
  id: string;
  date: string;
  time?: string;
  fullDate: string;
  rawTimestamp: number;
  glucose?: number;
  glucoseContext?: string;
  systolic?: number;
  diastolic?: number;
  pulse?: number;
  weight?: number;
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload || !payload.length) return null;
  const point = payload[0]?.payload as TrendPoint;

  return (
    <div className="bg-slate-900/95 backdrop-blur-xs text-white p-3 rounded-xl shadow-xl border border-slate-700 text-xs min-w-[190px] space-y-1.5">
      <div className="font-bold border-b border-slate-700/80 pb-1 flex items-center justify-between text-slate-300">
        <span>{point?.fullDate || label}</span>
        {point?.time && <span className="text-[10px] text-slate-400 font-normal">{point.time}</span>}
      </div>

      {point?.glucose !== undefined && (
        <div className="flex items-center justify-between text-teal-300">
          <span className="flex items-center space-x-1.5">
            <span className="w-2 h-2 rounded-full bg-teal-400" />
            <span>Glucose{point.glucoseContext ? ` (${point.glucoseContext})` : ''}:</span>
          </span>
          <span className="font-mono font-bold">{point.glucose} mmol/L</span>
        </div>
      )}

      {point?.systolic !== undefined && (
        <div className="flex items-center justify-between text-rose-300">
          <span className="flex items-center space-x-1.5">
            <span className="w-2 h-2 rounded-full bg-rose-400" />
            <span>Blood Pressure:</span>
          </span>
          <span className="font-mono font-bold">
            {point.systolic}/{point.diastolic ?? '--'} mmHg
          </span>
        </div>
      )}

      {point?.pulse !== undefined && (
        <div className="flex items-center justify-between text-pink-300">
          <span className="flex items-center space-x-1.5">
            <span className="w-2 h-2 rounded-full bg-pink-400" />
            <span>Pulse:</span>
          </span>
          <span className="font-mono font-bold">{point.pulse} bpm</span>
        </div>
      )}

      {point?.weight !== undefined && (
        <div className="flex items-center justify-between text-sky-300">
          <span className="flex items-center space-x-1.5">
            <span className="w-2 h-2 rounded-full bg-sky-400" />
            <span>Weight:</span>
          </span>
          <span className="font-mono font-bold">{point.weight} kg</span>
        </div>
      )}
    </div>
  );
};

export const VitalsDashboard: React.FC<VitalsDashboardProps> = ({ summary, onRefresh }) => {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [vitalType, setVitalType] = useState<'GLUCOSE' | 'BP' | 'WEIGHT'>('GLUCOSE');
  const [activeChartTab, setActiveChartTab] = useState<'ALL' | 'GLUCOSE' | 'BP' | 'WEIGHT'>('ALL');
  const [trendData, setTrendData] = useState<TrendPoint[]>([]);

  // Post-submission safety alert dialog state
  const [postSubmitAlert, setPostSubmitAlert] = useState<{
    type: 'GLUCOSE' | 'BP';
    readingLabel: string;
    assessment: ClinicalAssessment;
  } | null>(null);

  // Form states
  const [glucoseVal, setGlucoseVal] = useState('');
  const [context, setContext] = useState('FASTING');
  const [systolic, setSystolic] = useState('');
  const [diastolic, setDiastolic] = useState('');
  const [pulse, setPulse] = useState('');
  const [weightKg, setWeightKg] = useState('');
  const [heightCm, setHeightCm] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Evaluate latest vitals for KPI status indicators
  const latestGlucoseVal = summary?.glucose?.latest?.glucose_value_mmol;
  const latestGlucoseCtx = summary?.glucose?.latest?.context || 'FASTING';
  const latestGlucoseAssess =
    latestGlucoseVal !== undefined && latestGlucoseVal !== null
      ? assessGlucose(Number(latestGlucoseVal), latestGlucoseCtx)
      : null;

  const latestSys = summary?.blood_pressure?.latest?.systolic_mmHg;
  const latestDia = summary?.blood_pressure?.latest?.diastolic_mmHg;
  const latestPulse = summary?.blood_pressure?.latest?.pulse_bpm;
  const latestBpAssess =
    latestSys !== undefined && latestDia !== undefined && latestSys !== null && latestDia !== null
      ? assessBloodPressure(Number(latestSys), Number(latestDia), latestPulse)
      : null;

  // Live real-time evaluations while typing in modal
  const liveGlucoseAssessment =
    vitalType === 'GLUCOSE' && glucoseVal && !isNaN(parseFloat(glucoseVal))
      ? assessGlucose(parseFloat(glucoseVal), context)
      : null;

  const liveBpAssessment =
    vitalType === 'BP' &&
    systolic &&
    diastolic &&
    !isNaN(parseInt(systolic, 10)) &&
    !isNaN(parseInt(diastolic, 10))
      ? assessBloodPressure(
          parseInt(systolic, 10),
          parseInt(diastolic, 10),
          pulse && !isNaN(parseInt(pulse, 10)) ? parseInt(pulse, 10) : undefined
        )
      : null;

  // Fetch real logs to render chronological trend
  const fetchTrendData = async () => {
    try {
      const [glucoseRes, bpRes, weightRes] = await Promise.all([
        vitalsApi.getGlucoseLogs(20).catch(() => [] as GlucoseLog[]),
        vitalsApi.getBPLogs(20).catch(() => [] as BloodPressureLog[]),
        vitalsApi.getWeightLogs(20).catch(() => [] as WeightLog[]),
      ]);

      const timelineMap = new Map<string, TrendPoint>();

      (glucoseRes || []).forEach((g) => {
        const dt = new Date(g.recorded_at);
        const dateKey = dt.toISOString().slice(0, 16);
        const dateLabel = dt.toLocaleDateString(undefined, { month: 'numeric', day: 'numeric' });
        const timeLabel = dt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

        const existing = timelineMap.get(dateKey) || {
          id: dateKey,
          date: dateLabel,
          time: timeLabel,
          fullDate: dt.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' }),
          rawTimestamp: dt.getTime(),
        };
        existing.glucose = typeof g.glucose_value_mmol === 'number' ? g.glucose_value_mmol : parseFloat(String(g.glucose_value_mmol));
        existing.glucoseContext = g.context;
        timelineMap.set(dateKey, existing);
      });

      (bpRes || []).forEach((b) => {
        const dt = new Date(b.recorded_at);
        const dateKey = dt.toISOString().slice(0, 16);
        const dateLabel = dt.toLocaleDateString(undefined, { month: 'numeric', day: 'numeric' });
        const timeLabel = dt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

        const existing = timelineMap.get(dateKey) || {
          id: dateKey,
          date: dateLabel,
          time: timeLabel,
          fullDate: dt.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' }),
          rawTimestamp: dt.getTime(),
        };
        existing.systolic = b.systolic_mmHg;
        existing.diastolic = b.diastolic_mmHg;
        existing.pulse = b.pulse_bpm;
        timelineMap.set(dateKey, existing);
      });

      (weightRes || []).forEach((w) => {
        const dt = new Date(w.recorded_at);
        const dateKey = dt.toISOString().slice(0, 16);
        const dateLabel = dt.toLocaleDateString(undefined, { month: 'numeric', day: 'numeric' });
        const timeLabel = dt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

        const existing = timelineMap.get(dateKey) || {
          id: dateKey,
          date: dateLabel,
          time: timeLabel,
          fullDate: dt.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' }),
          rawTimestamp: dt.getTime(),
        };
        existing.weight = typeof w.weight_kg === 'number' ? w.weight_kg : parseFloat(String(w.weight_kg));
        timelineMap.set(dateKey, existing);
      });

      const points = Array.from(timelineMap.values()).sort((a, b) => a.rawTimestamp - b.rawTimestamp);

      // If multiple readings occur on the same day, append time to date label so X-axis shows distinct ticks
      const dayCounts: Record<string, number> = {};
      points.forEach((p) => {
        dayCounts[p.date] = (dayCounts[p.date] || 0) + 1;
      });
      points.forEach((p) => {
        if (dayCounts[p.date] > 1 && p.time) {
          p.date = `${p.date} ${p.time}`;
        }
      });

      setTrendData(points);
    } catch {
      setTrendData([]);
    }
  };

  useEffect(() => {
    fetchTrendData();
  }, [summary]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      let triggeredAlert: {
        type: 'GLUCOSE' | 'BP';
        readingLabel: string;
        assessment: ClinicalAssessment;
      } | null = null;

      if (vitalType === 'GLUCOSE') {
        const val = parseFloat(glucoseVal);
        const localAssess = assessGlucose(val, context);
        const res: any = await vitalsApi.logGlucose({
          glucose_value: val,
          unit: 'mmol',
          context,
        });

        const isOut = res?.is_out_of_range ?? localAssess?.isOutOfRange;
        if (isOut && localAssess) {
          triggeredAlert = {
            type: 'GLUCOSE',
            readingLabel: `${val} mmol/L (${context === 'FASTING' ? 'Fasting' : context === 'POST_MEAL' ? 'Post Meal 2h' : context})`,
            assessment: {
              ...localAssess,
              warningTitle: res?.clinical_assessment?.warning_title || localAssess.warningTitle,
              warningMessage: res?.warning_message || localAssess.warningMessage,
              recommendation: res?.recommendation || localAssess.recommendation,
              isEmergency: res?.clinical_assessment?.is_emergency ?? localAssess.isEmergency,
            },
          };
        }
      } else if (vitalType === 'BP') {
        const sys = parseInt(systolic, 10);
        const dia = parseInt(diastolic, 10);
        const pls = pulse ? parseInt(pulse, 10) : undefined;
        const localAssess = assessBloodPressure(sys, dia, pls);
        const res: any = await vitalsApi.logBP({
          systolic_mmHg: sys,
          diastolic_mmHg: dia,
          pulse_bpm: pls || 72,
        });

        const isOut = res?.is_out_of_range ?? localAssess?.isOutOfRange;
        if (isOut && localAssess) {
          triggeredAlert = {
            type: 'BP',
            readingLabel: `${sys}/${dia} mmHg${pls ? ` (${pls} bpm)` : ''}`,
            assessment: {
              ...localAssess,
              warningTitle: res?.clinical_assessment?.warning_title || localAssess.warningTitle,
              warningMessage: res?.warning_message || localAssess.warningMessage,
              recommendation: res?.recommendation || localAssess.recommendation,
              isEmergency: res?.clinical_assessment?.is_emergency ?? localAssess.isEmergency,
            },
          };
        }
      } else if (vitalType === 'WEIGHT') {
        await vitalsApi.logWeight({
          weight_kg: parseFloat(weightKg),
          height_cm: heightCm ? parseFloat(heightCm) : undefined,
        });
      }

      setIsModalOpen(false);
      setGlucoseVal('');
      setSystolic('');
      setDiastolic('');
      setPulse('');
      setWeightKg('');
      setHeightCm('');
      onRefresh();
      fetchTrendData();

      if (triggeredAlert) {
        setPostSubmitAlert(triggeredAlert);
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6">
      {/* Top Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-lg font-bold text-medivault-navy flex items-center space-x-2">
            <Activity className="w-5 h-5 text-medivault-primary" />
            <span>Health Vitals & Trends</span>
          </h2>
          <p className="text-xs text-slate-500">90-day physiological monitoring (mmol/L & mmHg)</p>
        </div>
        <div className="flex space-x-2">
          <button
            onClick={() => { setVitalType('GLUCOSE'); setIsModalOpen(true); }}
            className="flex items-center space-x-1.5 px-3 py-1.5 bg-teal-50 text-medivault-primary border border-teal-200 rounded-lg text-xs font-semibold hover:bg-teal-100 transition"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Log Glucose</span>
          </button>
          <button
            onClick={() => { setVitalType('BP'); setIsModalOpen(true); }}
            className="flex items-center space-x-1.5 px-3 py-1.5 bg-rose-50 text-rose-600 border border-rose-200 rounded-lg text-xs font-semibold hover:bg-rose-100 transition"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Log BP</span>
          </button>
          <button
            onClick={() => { setVitalType('WEIGHT'); setIsModalOpen(true); }}
            className="flex items-center space-x-1.5 px-3 py-1.5 bg-slate-50 text-slate-700 border border-slate-200 rounded-lg text-xs font-semibold hover:bg-slate-100 transition"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Log Weight</span>
          </button>
        </div>
      </div>

      {/* Unacknowledged Emergency Danger Alert Banner */}
      {summary?.unacknowledged_danger_alerts_count && summary.unacknowledged_danger_alerts_count > 0 ? (
        <div className="mb-6 p-4 rounded-xl bg-red-50 border border-red-200 text-red-900 flex items-start justify-between space-x-3 animate-pulse">
          <div className="flex items-start space-x-3">
            <ShieldAlert className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
            <div>
              <h4 className="text-xs font-bold uppercase tracking-wider text-red-800">
                Critical Health Danger Alert ({summary.unacknowledged_danger_alerts_count} Active)
              </h4>
              <p className="text-xs text-red-700 mt-1 leading-relaxed">
                {summary.active_danger_alerts?.[0]?.instruction_text ||
                  'An urgent clinical danger alert has been triggered by recent vital readings. Immediate medical review required.'}
              </p>
            </div>
          </div>
          <a
            href="tel:999"
            className="shrink-0 flex items-center space-x-1.5 px-3 py-1.5 bg-red-600 text-white rounded-lg text-xs font-bold hover:bg-red-700 shadow-sm"
          >
            <PhoneCall className="w-3.5 h-3.5" />
            <span>Call 999</span>
          </a>
        </div>
      ) : null}

      {/* Vital KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        {/* Glucose Card */}
        <div className={`rounded-xl p-4 border transition ${
          latestGlucoseAssess?.isOutOfRange
            ? latestGlucoseAssess.severity === 'CRITICAL'
              ? 'bg-red-50/70 border-red-200'
              : 'bg-amber-50/40 border-amber-200/80'
            : 'bg-slate-50 border-slate-100'
        }`}>
          <div className="flex items-center justify-between text-slate-500 text-xs font-medium mb-1">
            <span>Blood Glucose</span>
            <div className="flex items-center space-x-1.5">
              {summary?.glucose?.latest && (
                <span className="text-[10px] bg-slate-200/80 text-slate-700 px-2 py-0.5 rounded-full font-medium">
                  {summary.glucose.latest.context}
                </span>
              )}
              {latestGlucoseAssess && (
                <span
                  className={`text-[10px] px-2 py-0.5 rounded-full font-bold ${
                    !latestGlucoseAssess.isOutOfRange
                      ? 'bg-emerald-100 text-emerald-800'
                      : latestGlucoseAssess.severity === 'CRITICAL'
                      ? 'bg-red-100 text-red-800 animate-pulse'
                      : latestGlucoseAssess.severity === 'HIGH'
                      ? 'bg-rose-100 text-rose-800'
                      : 'bg-amber-100 text-amber-800'
                  }`}
                >
                  {!latestGlucoseAssess.isOutOfRange
                    ? 'Normal'
                    : latestGlucoseAssess.severity === 'CRITICAL'
                    ? 'Critical'
                    : latestGlucoseAssess.severity === 'HIGH'
                    ? 'High'
                    : 'Elevated'}
                </span>
              )}
            </div>
          </div>
          <div className="flex items-baseline space-x-2">
            <span className="text-3xl font-extrabold text-slate-900">
              {summary?.glucose?.latest?.glucose_value_mmol ?? '--'}
            </span>
            <span className="text-xs text-slate-500 font-semibold">mmol/L</span>
          </div>
          <p className="text-[11px] text-slate-500 mt-2">
            90-Day Avg:{' '}
            <strong className="text-slate-700">
              {summary?.glucose?.avg_90_days ? `${summary.glucose.avg_90_days} mmol/L` : 'No logs'}
            </strong>
          </p>

          {/* Out-of-range Warning Notice */}
          {latestGlucoseAssess?.isOutOfRange && (
            <div className="mt-2.5 text-[11px] bg-white/90 rounded-lg p-2.5 border border-amber-300/80 text-amber-950 shadow-xs">
              <div className="font-bold flex items-center space-x-1.5">
                <AlertTriangle className="w-3.5 h-3.5 text-amber-600 shrink-0" />
                <span>{latestGlucoseAssess.warningTitle}</span>
              </div>
              <p className="mt-1 text-slate-600 text-[10px] leading-snug">
                {latestGlucoseAssess.recommendation}
              </p>
            </div>
          )}
        </div>

        {/* BP Card */}
        <div className={`rounded-xl p-4 border transition ${
          latestBpAssess?.isOutOfRange
            ? latestBpAssess.severity === 'CRITICAL'
              ? 'bg-red-50/70 border-red-200'
              : 'bg-rose-50/40 border-rose-200/80'
            : 'bg-slate-50 border-slate-100'
        }`}>
          <div className="flex items-center justify-between text-slate-500 text-xs font-medium mb-1">
            <span className="flex items-center space-x-1">
              <Heart className="w-3.5 h-3.5 text-rose-500" />
              <span>Blood Pressure</span>
            </span>
            <div className="flex items-center space-x-1.5">
              {summary?.blood_pressure?.latest?.pulse_bpm && (
                <span className="text-[10px] bg-slate-200/80 text-slate-700 px-2 py-0.5 rounded-full font-medium">
                  {summary.blood_pressure.latest.pulse_bpm} bpm
                </span>
              )}
              {latestBpAssess && (
                <span
                  className={`text-[10px] px-2 py-0.5 rounded-full font-bold ${
                    !latestBpAssess.isOutOfRange
                      ? 'bg-emerald-100 text-emerald-800'
                      : latestBpAssess.severity === 'CRITICAL'
                      ? 'bg-red-100 text-red-800 animate-pulse'
                      : latestBpAssess.severity === 'HIGH'
                      ? 'bg-rose-100 text-rose-800'
                      : latestBpAssess.status === 'HYPOTENSION'
                      ? 'bg-sky-100 text-sky-800'
                      : 'bg-amber-100 text-amber-800'
                  }`}
                >
                  {!latestBpAssess.isOutOfRange
                    ? 'Normal'
                    : latestBpAssess.severity === 'CRITICAL'
                    ? 'Crisis'
                    : latestBpAssess.severity === 'HIGH'
                    ? 'Stage 2'
                    : latestBpAssess.status === 'HYPOTENSION'
                    ? 'Low BP'
                    : 'Elevated'}
                </span>
              )}
            </div>
          </div>
          <div className="flex items-baseline space-x-2">
            <span className="text-3xl font-extrabold text-slate-900">
              {summary?.blood_pressure?.latest
                ? `${summary.blood_pressure.latest.systolic_mmHg}/${summary.blood_pressure.latest.diastolic_mmHg}`
                : '--/--'}
            </span>
            <span className="text-xs text-slate-500 font-semibold">mmHg</span>
          </div>
          <p className="text-[11px] text-slate-500 mt-2">
            90-Day Avg:{' '}
            <strong className="text-slate-700">
              {summary?.blood_pressure?.avg_systolic_90_days && summary?.blood_pressure?.avg_diastolic_90_days
                ? `${summary.blood_pressure.avg_systolic_90_days}/${summary.blood_pressure.avg_diastolic_90_days}`
                : 'No logs'}
            </strong>
          </p>

          {/* Out-of-range Warning Notice */}
          {latestBpAssess?.isOutOfRange && (
            <div className="mt-2.5 text-[11px] bg-white/90 rounded-lg p-2.5 border border-rose-300/80 text-rose-950 shadow-xs">
              <div className="font-bold flex items-center space-x-1.5">
                <AlertTriangle className="w-3.5 h-3.5 text-rose-600 shrink-0" />
                <span>{latestBpAssess.warningTitle}</span>
              </div>
              <p className="mt-1 text-slate-600 text-[10px] leading-snug">
                {latestBpAssess.recommendation}
              </p>
            </div>
          )}
        </div>

        {/* Weight & BMI Card */}
        <div className="bg-slate-50 rounded-xl p-4 border border-slate-100">
          <div className="flex items-center justify-between text-slate-500 text-xs font-medium mb-1">
            <span className="flex items-center space-x-1">
              <Scale className="w-3.5 h-3.5 text-medivault-primary" />
              <span>Weight & BMI</span>
            </span>
            {summary?.weight?.latest?.bmi_category && (
              <span className="text-[10px] bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded-full">
                {summary.weight.latest.bmi_category}
              </span>
            )}
          </div>
          <div className="flex items-baseline space-x-2">
            <span className="text-3xl font-extrabold text-slate-900">
              {summary?.weight?.latest?.weight_kg ?? '--'}
            </span>
            <span className="text-xs text-slate-500 font-semibold">kg</span>
            {summary?.weight?.current_bmi && (
              <span className="text-xs text-slate-400">| BMI {summary.weight.current_bmi}</span>
            )}
          </div>
          <p className="text-[11px] text-slate-500 mt-2">
            {summary?.weight?.latest?.height_cm
              ? `Height: ${summary.weight.latest.height_cm} cm`
              : 'No weight logged'}
          </p>
        </div>
      </div>

      {/* Chart Filter Tabs & Legend Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 mb-3 pt-2 border-t border-slate-100">
        <div className="flex flex-wrap items-center gap-1.5 bg-slate-100/80 p-1 rounded-xl">
          <button
            type="button"
            onClick={() => setActiveChartTab('ALL')}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition flex items-center space-x-1.5 ${
              activeChartTab === 'ALL'
                ? 'bg-white text-slate-900 shadow-xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Layers className="w-3.5 h-3.5 text-slate-500" />
            <span>All Trends (Dual Axis)</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveChartTab('GLUCOSE')}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition flex items-center space-x-1.5 ${
              activeChartTab === 'GLUCOSE'
                ? 'bg-white text-teal-800 shadow-xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Activity className="w-3.5 h-3.5 text-medivault-primary" />
            <span>Blood Glucose</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveChartTab('BP')}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition flex items-center space-x-1.5 ${
              activeChartTab === 'BP'
                ? 'bg-white text-rose-700 shadow-xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Heart className="w-3.5 h-3.5 text-rose-500" />
            <span>Blood Pressure</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveChartTab('WEIGHT')}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition flex items-center space-x-1.5 ${
              activeChartTab === 'WEIGHT'
                ? 'bg-white text-sky-700 shadow-xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Scale className="w-3.5 h-3.5 text-sky-600" />
            <span>Weight</span>
          </button>
        </div>

        {trendData.length > 0 && (
          <div className="text-[11px] text-slate-400 font-medium flex items-center space-x-2">
            <span>{trendData.length} {trendData.length === 1 ? 'record' : 'records'} logged</span>
            {activeChartTab === 'ALL' && (
              <span className="text-teal-700 font-semibold">• Left: BP & Weight | Right: Glucose</span>
            )}
          </div>
        )}
      </div>

      {/* Trend Graph or Empty State */}
      <div className="h-72 w-full">
        {trendData.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center border border-dashed border-slate-200 rounded-xl text-center p-6 bg-slate-50/50">
            <Activity className="w-8 h-8 text-slate-300 mb-2" />
            <p className="text-sm font-semibold text-slate-600">No Vitals History Yet</p>
            <p className="text-xs text-slate-400 mt-1 max-w-sm">
              Log your blood glucose, blood pressure, or weight above to begin generating your clinical trend chart.
            </p>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={trendData} margin={{ top: 10, right: activeChartTab === 'ALL' ? 25 : 15, left: 10, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
              <XAxis
                dataKey="date"
                stroke="#94A3B8"
                fontSize={11}
                tickLine={false}
                padding={{ left: 35, right: 35 }}
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend
                verticalAlign="top"
                height={32}
                iconType="circle"
                wrapperStyle={{ fontSize: '11px', fontWeight: 600, paddingBottom: '8px' }}
              />

              {activeChartTab === 'ALL' && (
                <>
                  {/* Left Axis for BP & Weight */}
                  <YAxis
                    yAxisId="left"
                    stroke="#94A3B8"
                    fontSize={11}
                    tickLine={false}
                    domain={[40, 'auto']}
                    tickFormatter={(v) => `${v}`}
                    label={{ value: 'BP / Weight (mmHg / kg)', angle: -90, position: 'insideLeft', style: { fontSize: 10, fill: '#94A3B8' } }}
                  />
                  {/* Right Axis for Glucose */}
                  <YAxis
                    yAxisId="right"
                    orientation="right"
                    stroke="#087E8B"
                    fontSize={11}
                    tickLine={false}
                    domain={[0, 16]}
                    tickFormatter={(v) => `${v}`}
                    label={{ value: 'Glucose (mmol/L)', angle: 90, position: 'insideRight', style: { fontSize: 10, fill: '#087E8B' } }}
                  />

                  <Line
                    yAxisId="right"
                    type="monotone"
                    dataKey="glucose"
                    stroke="#087E8B"
                    strokeWidth={3}
                    dot={{ r: 5, fill: '#087E8B', stroke: '#fff', strokeWidth: 2 }}
                    activeDot={{ r: 7 }}
                    name="Blood Glucose (mmol/L)"
                    connectNulls
                  />
                  <Line
                    yAxisId="left"
                    type="monotone"
                    dataKey="systolic"
                    stroke="#E76F51"
                    strokeWidth={2.5}
                    dot={{ r: 4, fill: '#E76F51', stroke: '#fff', strokeWidth: 2 }}
                    activeDot={{ r: 6 }}
                    name="Systolic BP (mmHg)"
                    connectNulls
                  />
                  <Line
                    yAxisId="left"
                    type="monotone"
                    dataKey="diastolic"
                    stroke="#F4A261"
                    strokeWidth={2}
                    strokeDasharray="4 4"
                    dot={{ r: 4, fill: '#F4A261', stroke: '#fff', strokeWidth: 1.5 }}
                    activeDot={{ r: 6 }}
                    name="Diastolic BP (mmHg)"
                    connectNulls
                  />
                  <Line
                    yAxisId="left"
                    type="monotone"
                    dataKey="weight"
                    stroke="#0284C7"
                    strokeWidth={2}
                    dot={{ r: 4, fill: '#0284C7', stroke: '#fff', strokeWidth: 2 }}
                    activeDot={{ r: 6 }}
                    name="Weight (kg)"
                    connectNulls
                  />
                </>
              )}

              {activeChartTab === 'GLUCOSE' && (
                <>
                  <YAxis
                    stroke="#087E8B"
                    fontSize={11}
                    tickLine={false}
                    domain={[0, 16]}
                    tickFormatter={(v) => `${v} mmol`}
                  />
                  <ReferenceLine y={7.0} stroke="#10B981" strokeDasharray="3 3" label={{ value: 'Fasting Upper (7.0)', position: 'insideTopLeft', fill: '#10B981', fontSize: 10 }} />
                  <ReferenceLine y={10.0} stroke="#F59E0B" strokeDasharray="3 3" label={{ value: 'Post-Meal Target (10.0)', position: 'insideTopLeft', fill: '#F59E0B', fontSize: 10 }} />
                  <ReferenceLine y={4.0} stroke="#3B82F6" strokeDasharray="3 3" label={{ value: 'Fasting Lower (4.0)', position: 'insideBottomLeft', fill: '#3B82F6', fontSize: 10 }} />

                  <Line
                    type="monotone"
                    dataKey="glucose"
                    stroke="#087E8B"
                    strokeWidth={3}
                    dot={{ r: 6, fill: '#087E8B', stroke: '#fff', strokeWidth: 2 }}
                    activeDot={{ r: 8 }}
                    name="Blood Glucose (mmol/L)"
                    connectNulls
                  />
                </>
              )}

              {activeChartTab === 'BP' && (
                <>
                  <YAxis
                    stroke="#E76F51"
                    fontSize={11}
                    tickLine={false}
                    domain={[40, 180]}
                    tickFormatter={(v) => `${v} mmHg`}
                  />
                  <ReferenceLine y={120} stroke="#10B981" strokeDasharray="3 3" label={{ value: 'Normal Systolic (120)', position: 'insideTopLeft', fill: '#10B981', fontSize: 10 }} />
                  <ReferenceLine y={80} stroke="#10B981" strokeDasharray="3 3" label={{ value: 'Normal Diastolic (80)', position: 'insideBottomLeft', fill: '#10B981', fontSize: 10 }} />

                  <Line
                    type="monotone"
                    dataKey="systolic"
                    stroke="#E76F51"
                    strokeWidth={3}
                    dot={{ r: 5, fill: '#E76F51', stroke: '#fff', strokeWidth: 2 }}
                    activeDot={{ r: 7 }}
                    name="Systolic (mmHg)"
                    connectNulls
                  />
                  <Line
                    type="monotone"
                    dataKey="diastolic"
                    stroke="#F4A261"
                    strokeWidth={2.5}
                    strokeDasharray="4 4"
                    dot={{ r: 5, fill: '#F4A261', stroke: '#fff', strokeWidth: 1.5 }}
                    activeDot={{ r: 7 }}
                    name="Diastolic (mmHg)"
                    connectNulls
                  />
                  <Line
                    type="monotone"
                    dataKey="pulse"
                    stroke="#EC4899"
                    strokeWidth={2}
                    strokeDasharray="2 2"
                    dot={{ r: 4, fill: '#EC4899', stroke: '#fff', strokeWidth: 1 }}
                    activeDot={{ r: 6 }}
                    name="Pulse (bpm)"
                    connectNulls
                  />
                </>
              )}

              {activeChartTab === 'WEIGHT' && (
                <>
                  <YAxis
                    stroke="#0284C7"
                    fontSize={11}
                    tickLine={false}
                    domain={['dataMin - 5', 'dataMax + 5']}
                    tickFormatter={(v) => `${v} kg`}
                  />
                  <Line
                    type="monotone"
                    dataKey="weight"
                    stroke="#0284C7"
                    strokeWidth={3}
                    dot={{ r: 6, fill: '#0284C7', stroke: '#fff', strokeWidth: 2 }}
                    activeDot={{ r: 8 }}
                    name="Body Weight (kg)"
                    connectNulls
                  />
                </>
              )}
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Log Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title={vitalType === 'GLUCOSE' ? 'Log Blood Glucose' : vitalType === 'BP' ? 'Log Blood Pressure' : 'Log Weight'}
      >
        <form onSubmit={handleSubmit} className="space-y-4">
          {vitalType === 'GLUCOSE' && (
            <>
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Glucose Reading (mmol/L)
                </label>
                <input
                  type="number"
                  step="0.1"
                  required
                  placeholder="e.g. 5.6"
                  value={glucoseVal}
                  onChange={(e) => setGlucoseVal(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:outline-none text-sm"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Measurement Context</label>
                <select
                  value={context}
                  onChange={(e) => setContext(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none"
                >
                  <option value="FASTING">Fasting (খালি পেটে)</option>
                  <option value="POST_MEAL">Post Meal 2h (খাওয়ার ২ ঘণ্টা পর)</option>
                  <option value="BEDTIME">Bedtime (রাতে ঘুমানোর আগে)</option>
                  <option value="RANDOM">Random (যেকোনো সময়)</option>
                </select>
              </div>

              {/* Live Real-Time Clinical Assessment & Recommendations */}
              {liveGlucoseAssessment && (
                <div
                  className={`p-3.5 rounded-xl border text-xs transition-all duration-200 ${
                    !liveGlucoseAssessment.isOutOfRange
                      ? 'bg-emerald-50 border-emerald-200 text-emerald-900'
                      : liveGlucoseAssessment.severity === 'CRITICAL'
                      ? 'bg-red-50 border-red-300 text-red-900 animate-pulse'
                      : liveGlucoseAssessment.severity === 'HIGH'
                      ? 'bg-rose-50 border-rose-200 text-rose-900'
                      : 'bg-amber-50 border-amber-200 text-amber-900'
                  }`}
                >
                  <div className="flex items-center space-x-2 font-bold mb-1">
                    {!liveGlucoseAssessment.isOutOfRange ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                    ) : liveGlucoseAssessment.severity === 'CRITICAL' ? (
                      <ShieldAlert className="w-4 h-4 text-red-600 shrink-0" />
                    ) : (
                      <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
                    )}
                    <span className="font-semibold">{liveGlucoseAssessment.warningTitle}</span>
                    {liveGlucoseAssessment.isOutOfRange && (
                      <span className="ml-auto text-[10px] px-2 py-0.5 rounded-full font-bold uppercase tracking-wider bg-white/80 border border-current">
                        Warning
                      </span>
                    )}
                  </div>
                  <p className="text-slate-700 leading-relaxed mb-2">{liveGlucoseAssessment.warningMessage}</p>
                  <div className="bg-white/85 rounded-lg p-2.5 border border-slate-200/60 shadow-2xs">
                    <span className="font-bold text-slate-800">Recommendation: </span>
                    <span className="text-slate-600">{liveGlucoseAssessment.recommendation}</span>
                  </div>
                </div>
              )}
            </>
          )}

          {vitalType === 'BP' && (
            <>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Systolic (mmHg)</label>
                  <input
                    type="number"
                    required
                    placeholder="e.g. 120"
                    value={systolic}
                    onChange={(e) => setSystolic(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Diastolic (mmHg)</label>
                  <input
                    type="number"
                    required
                    placeholder="e.g. 80"
                    value={diastolic}
                    onChange={(e) => setDiastolic(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                  />
                </div>
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Pulse (BPM)</label>
                <input
                  type="number"
                  placeholder="e.g. 72"
                  value={pulse}
                  onChange={(e) => setPulse(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                />
              </div>

              {/* Live Real-Time Clinical Assessment & Recommendations */}
              {liveBpAssessment && (
                <div
                  className={`p-3.5 rounded-xl border text-xs transition-all duration-200 ${
                    !liveBpAssessment.isOutOfRange
                      ? 'bg-emerald-50 border-emerald-200 text-emerald-900'
                      : liveBpAssessment.severity === 'CRITICAL'
                      ? 'bg-red-50 border-red-300 text-red-900 animate-pulse'
                      : liveBpAssessment.severity === 'HIGH'
                      ? 'bg-rose-50 border-rose-200 text-rose-900'
                      : liveBpAssessment.status === 'HYPOTENSION'
                      ? 'bg-sky-50 border-sky-200 text-sky-900'
                      : 'bg-amber-50 border-amber-200 text-amber-900'
                  }`}
                >
                  <div className="flex items-center space-x-2 font-bold mb-1">
                    {!liveBpAssessment.isOutOfRange ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                    ) : liveBpAssessment.severity === 'CRITICAL' ? (
                      <ShieldAlert className="w-4 h-4 text-red-600 shrink-0" />
                    ) : (
                      <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
                    )}
                    <span className="font-semibold">{liveBpAssessment.warningTitle}</span>
                    {liveBpAssessment.isOutOfRange && (
                      <span className="ml-auto text-[10px] px-2 py-0.5 rounded-full font-bold uppercase tracking-wider bg-white/80 border border-current">
                        Warning
                      </span>
                    )}
                  </div>
                  <p className="text-slate-700 leading-relaxed mb-2">{liveBpAssessment.warningMessage}</p>
                  <div className="bg-white/85 rounded-lg p-2.5 border border-slate-200/60 shadow-2xs">
                    <span className="font-bold text-slate-800">Recommendation: </span>
                    <span className="text-slate-600">{liveBpAssessment.recommendation}</span>
                  </div>
                </div>
              )}
            </>
          )}

          {vitalType === 'WEIGHT' && (
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Body Weight (kg) <span className="text-rose-500">*</span>
                </label>
                <input
                  type="number"
                  step="0.1"
                  min="1"
                  max="400"
                  required
                  placeholder="e.g. 68.5"
                  value={weightKg}
                  onChange={(e) => setWeightKg(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-teal-500 focus:outline-none"
                />
                <p className="text-[11px] text-slate-400 mt-1">Acceptable range: 1.0 – 400.0 kg</p>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Height (cm) <span className="text-slate-400 font-normal">(Optional, for BMI calculation)</span>
                </label>
                <input
                  type="number"
                  step="0.5"
                  min="30"
                  max="300"
                  placeholder={summary?.weight?.latest?.height_cm ? `Current: ${summary.weight.latest.height_cm} cm` : 'e.g. 172'}
                  value={heightCm}
                  onChange={(e) => setHeightCm(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-teal-500 focus:outline-none"
                />
                <p className="text-[11px] text-slate-400 mt-1">
                  Entering height updates your profile and calculates Body Mass Index (BMI).
                </p>
              </div>
            </div>
          )}

          <div className="flex justify-end space-x-2 pt-4">
            <button
              type="button"
              onClick={() => setIsModalOpen(false)}
              className="px-4 py-2 border border-slate-200 rounded-lg text-xs font-medium text-slate-600 hover:bg-slate-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-4 py-2 bg-medivault-primary text-white rounded-lg text-xs font-semibold hover:bg-teal-700 disabled:opacity-50"
            >
              {isSubmitting ? 'Saving...' : 'Save Vital Reading'}
            </button>
          </div>
        </form>
      </Modal>

      {/* Post-Submit Clinical Safety Warning & Recommendation Dialog */}
      <Modal
        isOpen={!!postSubmitAlert}
        onClose={() => setPostSubmitAlert(null)}
        title="Clinical Safety Warning & Guidance"
      >
        {postSubmitAlert && (
          <div className="space-y-4">
            {/* Alert Header Banner */}
            <div
              className={`p-4 rounded-xl border ${
                postSubmitAlert.assessment.severity === 'CRITICAL'
                  ? 'bg-red-50 border-red-200 text-red-900'
                  : postSubmitAlert.assessment.severity === 'HIGH'
                  ? 'bg-rose-50 border-rose-200 text-rose-900'
                  : 'bg-amber-50 border-amber-200 text-amber-900'
              }`}
            >
              <div className="flex items-start space-x-3">
                <div className="p-2 rounded-lg bg-white/90 shadow-xs shrink-0 mt-0.5">
                  {postSubmitAlert.assessment.severity === 'CRITICAL' ? (
                    <ShieldAlert className="w-6 h-6 text-red-600" />
                  ) : (
                    <AlertTriangle className="w-6 h-6 text-amber-600" />
                  )}
                </div>
                <div>
                  <div className="flex items-center space-x-2">
                    <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-white/90 border border-current">
                      {postSubmitAlert.assessment.severity === 'CRITICAL'
                        ? 'Immediate Action Required'
                        : 'Out of Normal Range'}
                    </span>
                  </div>
                  <h4 className="text-sm sm:text-base font-bold mt-1 text-slate-900">
                    {postSubmitAlert.assessment.warningTitle}
                  </h4>
                  <p className="text-xs text-slate-600 mt-0.5">
                    Logged Reading: <strong className="text-slate-900 font-mono">{postSubmitAlert.readingLabel}</strong>
                  </p>
                </div>
              </div>
            </div>

            {/* Clinical Warning Details */}
            <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200 text-xs text-slate-700 space-y-1">
              <h5 className="font-bold text-slate-800 flex items-center space-x-1.5">
                <Info className="w-3.5 h-3.5 text-medivault-primary" />
                <span>Clinical Observation & Risk</span>
              </h5>
              <p className="leading-relaxed">{postSubmitAlert.assessment.warningMessage}</p>
            </div>

            {/* Actionable Recommendations */}
            <div className="bg-emerald-50/70 border border-emerald-200 p-3.5 rounded-xl text-xs space-y-1.5">
              <h5 className="font-bold text-emerald-900 flex items-center space-x-1.5">
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                <span>Doctor-Aligned Recommendations</span>
              </h5>
              <p className="text-slate-700 leading-relaxed font-normal">{postSubmitAlert.assessment.recommendation}</p>
            </div>

            {/* Emergency Action if Critical */}
            {postSubmitAlert.assessment.isEmergency && (
              <div className="p-3 bg-red-100/80 border border-red-300 rounded-xl flex items-center justify-between">
                <div className="text-xs text-red-900">
                  <p className="font-bold">Need Immediate Emergency Assistance?</p>
                  <p className="text-[11px] text-red-700">Bangladesh National Emergency Service</p>
                </div>
                <a
                  href="tel:999"
                  className="flex items-center space-x-1.5 px-3.5 py-1.5 bg-red-600 text-white rounded-lg text-xs font-bold hover:bg-red-700 shadow-sm"
                >
                  <PhoneCall className="w-3.5 h-3.5" />
                  <span>Call 999</span>
                </a>
              </div>
            )}

            {/* Action Buttons */}
            <div className="flex justify-end pt-2">
              <button
                type="button"
                onClick={() => setPostSubmitAlert(null)}
                className="w-full sm:w-auto px-5 py-2.5 bg-slate-900 text-white rounded-xl text-xs font-bold hover:bg-slate-800 transition"
              >
                I Understand & Acknowledge
              </button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
};

