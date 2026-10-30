import React, { useState, useEffect } from 'react';
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts';
import { Activity, Plus, Heart, Scale } from 'lucide-react';
import { vitalsApi, VitalsSummary, GlucoseLog, BloodPressureLog } from '../../api/vitals';
import { Modal } from '../common/Modal';

interface VitalsDashboardProps {
  summary: VitalsSummary | null;
  onRefresh: () => void;
}

interface TrendPoint {
  date: string;
  glucose?: number;
  systolic?: number;
  diastolic?: number;
}

export const VitalsDashboard: React.FC<VitalsDashboardProps> = ({ summary, onRefresh }) => {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [vitalType, setVitalType] = useState<'GLUCOSE' | 'BP' | 'WEIGHT'>('GLUCOSE');
  const [trendData, setTrendData] = useState<TrendPoint[]>([]);

  // Form states
  const [glucoseVal, setGlucoseVal] = useState('');
  const [context, setContext] = useState('FASTING');
  const [systolic, setSystolic] = useState('');
  const [diastolic, setDiastolic] = useState('');
  const [pulse, setPulse] = useState('');
  const [weightKg, setWeightKg] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Fetch real logs to render chronological trend
  const fetchTrendData = async () => {
    try {
      const [glucoseRes, bpRes] = await Promise.all([
        vitalsApi.getGlucoseLogs(10).catch(() => [] as GlucoseLog[]),
        vitalsApi.getBPLogs(10).catch(() => [] as BloodPressureLog[]),
      ]);

      const dateMap = new Map<string, TrendPoint>();

      (glucoseRes || []).forEach((g) => {
        const d = new Date(g.recorded_at).toLocaleDateString(undefined, { month: 'numeric', day: 'numeric' });
        const existing = dateMap.get(d) || { date: d };
        existing.glucose = g.glucose_value_mmol;
        dateMap.set(d, existing);
      });

      (bpRes || []).forEach((b) => {
        const d = new Date(b.recorded_at).toLocaleDateString(undefined, { month: 'numeric', day: 'numeric' });
        const existing = dateMap.get(d) || { date: d };
        existing.systolic = b.systolic_mmHg;
        existing.diastolic = b.diastolic_mmHg;
        dateMap.set(d, existing);
      });

      const points = Array.from(dateMap.values());
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
      if (vitalType === 'GLUCOSE') {
        await vitalsApi.logGlucose({
          glucose_value: parseFloat(glucoseVal),
          unit: 'mmol',
          context,
        });
      } else if (vitalType === 'BP') {
        await vitalsApi.logBP({
          systolic_mmHg: parseInt(systolic, 10),
          diastolic_mmHg: parseInt(diastolic, 10),
          pulse_bpm: parseInt(pulse, 10),
        });
      } else if (vitalType === 'WEIGHT') {
        await vitalsApi.logWeight({
          weight_kg: parseFloat(weightKg),
        });
      }
      setIsModalOpen(false);
      setGlucoseVal('');
      setSystolic('');
      setDiastolic('');
      setPulse('');
      setWeightKg('');
      onRefresh();
      fetchTrendData();
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

      {/* Vital KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        {/* Glucose Card */}
        <div className="bg-slate-50 rounded-xl p-4 border border-slate-100">
          <div className="flex items-center justify-between text-slate-500 text-xs font-medium mb-1">
            <span>Blood Glucose</span>
            {summary?.glucose?.latest && (
              <span className="text-[10px] bg-teal-100 text-teal-800 px-2 py-0.5 rounded-full">
                {summary.glucose.latest.context}
              </span>
            )}
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
        </div>

        {/* BP Card */}
        <div className="bg-slate-50 rounded-xl p-4 border border-slate-100">
          <div className="flex items-center justify-between text-slate-500 text-xs font-medium mb-1">
            <span className="flex items-center space-x-1">
              <Heart className="w-3.5 h-3.5 text-rose-500" />
              <span>Blood Pressure</span>
            </span>
            {summary?.blood_pressure?.latest?.pulse_bpm && (
              <span className="text-[10px] bg-slate-200 text-slate-700 px-2 py-0.5 rounded-full">
                {summary.blood_pressure.latest.pulse_bpm} bpm
              </span>
            )}
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

      {/* Trend Graph or Empty State */}
      <div className="h-64 w-full">
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
            <LineChart data={trendData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
              <XAxis dataKey="date" stroke="#94A3B8" fontSize={12} tickLine={false} />
              <YAxis stroke="#94A3B8" fontSize={12} tickLine={false} domain={[0, 'auto']} />
              <Tooltip
                contentStyle={{ backgroundColor: '#1E293B', borderRadius: '8px', color: '#FFF', border: 'none' }}
                labelStyle={{ fontWeight: 'bold', marginBottom: '4px' }}
              />
              <Line
                type="monotone"
                dataKey="glucose"
                stroke="#087E8B"
                strokeWidth={3}
                dot={{ r: 4 }}
                name="Glucose (mmol/L)"
                connectNulls
              />
              <Line
                type="monotone"
                dataKey="systolic"
                stroke="#E76F51"
                strokeWidth={2}
                dot={{ r: 3 }}
                name="Systolic (mmHg)"
                connectNulls
              />
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
                  required
                  placeholder="e.g. 72"
                  value={pulse}
                  onChange={(e) => setPulse(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                />
              </div>
            </>
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
    </div>
  );
};

