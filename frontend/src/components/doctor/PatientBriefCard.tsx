import React from 'react';
import { Zap, Heart, Activity, AlertTriangle, Pill, CheckCircle2, ShieldAlert } from 'lucide-react';

interface PatientBriefCardProps {
  brief: {
    patient_name: string;
    patient_phone: string;
    patient_gender?: string;
    patient_age?: number;
    avg_glucose: number | null;
    avg_bp: string | null;
    danger_incidents: number;
    active_medications: Array<{ brand: string; generic: string; schedule: string }>;
    clinical_summary_bullets: string[];
  } | null;
}

export const PatientBriefCard: React.FC<PatientBriefCardProps> = ({ brief }) => {
  if (!brief) {
    return (
      <div className="bg-white rounded-2xl border border-slate-200 p-8 text-center text-slate-400">
        <Zap className="w-8 h-8 mx-auto mb-2 opacity-40 text-teal-600" />
        <h4 className="text-sm font-semibold text-slate-600">No Patient Record Selected</h4>
        <p className="text-xs text-slate-400 mt-1">
          Scan the patient's consultation QR code or call next in line to load the 10-Second Pre-Consultation Brief.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
      {/* Patient Header */}
      <div className="flex items-start justify-between pb-4 border-b border-slate-100 mb-4">
        <div>
          <div className="flex items-center space-x-2">
            <h3 className="text-lg font-bold text-medivault-navy">{brief.patient_name}</h3>
            {(brief.patient_gender || brief.patient_age) && (
              <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">
                {[brief.patient_gender, brief.patient_age ? `${brief.patient_age}y` : null]
                  .filter(Boolean)
                  .join(' • ')}
              </span>
            )}
          </div>
          <p className="text-xs text-slate-400 mt-0.5">{brief.patient_phone}</p>
        </div>

        <div className="flex items-center space-x-1.5 px-3 py-1 bg-amber-50 text-amber-700 rounded-full border border-amber-200 text-xs font-bold">
          <Zap className="w-3.5 h-3.5 text-amber-500 fill-amber-500" />
          <span>10-Second Brief</span>
        </div>
      </div>

      {/* 90-Day Vital Benchmarks */}
      <div className="grid grid-cols-3 gap-3 mb-5">
        <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
          <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block">
            90-Day Glucose Avg
          </span>
          <span className="text-lg font-extrabold text-slate-900 mt-0.5 block">
            {brief.avg_glucose ? `${brief.avg_glucose} mmol/L` : '--'}
          </span>
        </div>
        <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
          <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block">
            90-Day BP Avg
          </span>
          <span className="text-lg font-extrabold text-slate-900 mt-0.5 block">
            {brief.avg_bp || '--'}
          </span>
        </div>
        <div className={`p-3 rounded-xl border ${brief.danger_incidents > 0 ? 'bg-rose-50 border-rose-200 text-rose-700' : 'bg-slate-50 border-slate-100 text-slate-800'}`}>
          <span className="text-[10px] font-bold uppercase tracking-wider block">
            Danger Incidents (30d)
          </span>
          <span className="text-lg font-extrabold mt-0.5 block">
            {brief.danger_incidents} alerts
          </span>
        </div>
      </div>

      {/* AI Clinical Summary (3-Bullet Synthesis) */}
      <div className="mb-5 bg-teal-50/50 border border-teal-100 rounded-xl p-4">
        <h4 className="text-xs font-bold text-teal-900 uppercase tracking-wider mb-2 flex items-center space-x-1">
          <Activity className="w-3.5 h-3.5 text-medivault-primary" />
          <span>Clinical Trajectory & Observations</span>
        </h4>
        <ul className="space-y-1.5 text-xs text-slate-700">
          {brief.clinical_summary_bullets && brief.clinical_summary_bullets.length > 0 ? (
            brief.clinical_summary_bullets.map((bullet, idx) => (
              <li key={idx} className="flex items-start space-x-2">
                <span className="w-1.5 h-1.5 rounded-full bg-teal-600 mt-1.5 shrink-0" />
                <span>{bullet}</span>
              </li>
            ))
          ) : (
            <li className="text-xs text-slate-400 italic">
              No historical trajectory notes synthesized yet for this patient.
            </li>
          )}
        </ul>
      </div>

      {/* Active Medications */}
      <div>
        <h4 className="text-xs font-bold text-slate-600 uppercase tracking-wider mb-2 flex items-center space-x-1">
          <Pill className="w-3.5 h-3.5 text-slate-500" />
          <span>Active Medications Roster</span>
        </h4>
        <div className="grid grid-cols-2 gap-2">
          {brief.active_medications && brief.active_medications.length > 0 ? (
            brief.active_medications.map((med, idx) => (
              <div key={idx} className="p-2 bg-slate-50 border border-slate-200/60 rounded-lg text-xs">
                <span className="font-bold text-slate-800">{med.brand}</span>
                <span className="text-[11px] text-slate-500 block">Generic: {med.generic}</span>
                <span className="text-[10px] text-teal-700 font-mono font-medium">{med.schedule}</span>
              </div>
            ))
          ) : (
            <p className="text-xs text-slate-400 col-span-2">No active medications recorded</p>
          )}
        </div>
      </div>
    </div>
  );
};

