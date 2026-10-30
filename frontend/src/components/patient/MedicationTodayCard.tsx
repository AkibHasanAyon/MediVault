import React from 'react';
import { Pill, Check, X, Clock, AlertTriangle, ShieldCheck } from 'lucide-react';
import { TodayMedicationsResponse, medicationsApi } from '../../api/medications';

interface MedicationTodayCardProps {
  scheduleData: TodayMedicationsResponse | null;
  onRefresh: () => void;
}

export const MedicationTodayCard: React.FC<MedicationTodayCardProps> = ({ scheduleData, onRefresh }) => {
  const handleAction = async (reminderId: string, action: 'TAKEN' | 'SKIPPED') => {
    await medicationsApi.logDoseStatus(reminderId, action);
    onRefresh();
  };

  const allDoses: any[] = (scheduleData?.doses && scheduleData.doses.length > 0)
    ? scheduleData.doses
    : [
        ...(scheduleData?.schedule?.morning || []),
        ...(scheduleData?.schedule?.noon || []),
        ...(scheduleData?.schedule?.night || []),
      ];

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-lg font-bold text-medivault-navy flex items-center space-x-2">
            <Pill className="w-5 h-5 text-medivault-primary" />
            <span>Today's Medication Doses</span>
          </h2>
          <p className="text-xs text-slate-500">Scheduled times and daily adherence tracking</p>
        </div>
        <div className="flex items-center space-x-2 bg-teal-50 px-3 py-1.5 rounded-xl border border-teal-100">
          <ShieldCheck className="w-4 h-4 text-medivault-primary" />
          <span className="text-xs font-bold text-medivault-primary">
            {scheduleData?.adherence_percentage !== undefined ? `${scheduleData.adherence_percentage}% Adherence` : '--% Adherence'}
          </span>
        </div>
      </div>

      {/* Safety Notice */}
      <div className="bg-amber-50 border border-amber-200 rounded-xl p-3 mb-4 flex items-start space-x-2.5 text-xs text-amber-800">
        <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
        <p>
          <strong>Clinical Safety Guideline:</strong> If you miss a scheduled dose, take it as soon as remembered unless it is almost time for your next dose. <em>Never take a double dose to make up for a missed pill.</em>
        </p>
      </div>

      {/* Doses List */}
      <div className="space-y-3">
        {allDoses.length === 0 ? (
          <p className="text-sm text-slate-400 py-6 text-center">No medications scheduled for today</p>
        ) : (
          allDoses.map((dose, idx) => {
            const doseId = dose.id || dose.reminder_id || `dose-${idx}`;
            const timeDisplay = dose.dose_time ? dose.dose_time.slice(0, 5) : dose.reminder_time || '';
            const brand = dose.brand_name || dose.medication_name || 'Medication';
            const generic = dose.generic_name || dose.medication_name || '';
            const slot = dose.time_slot || dose.label || 'Daily';

            return (
              <div
                key={doseId}
                className={`p-3.5 rounded-xl border transition flex items-center justify-between ${
                  dose.status === 'TAKEN'
                    ? 'bg-emerald-50/50 border-emerald-200'
                    : dose.status === 'SKIPPED'
                    ? 'bg-rose-50/40 border-rose-200 opacity-60'
                    : 'bg-white border-slate-200 hover:border-slate-300'
                }`}
              >
                <div className="flex items-center space-x-3">
                  <div
                    className={`w-10 h-10 rounded-lg flex items-center justify-center font-bold text-xs ${
                      dose.status === 'TAKEN'
                        ? 'bg-emerald-100 text-emerald-700'
                        : 'bg-slate-100 text-slate-700'
                    }`}
                  >
                    <Clock className="w-4 h-4" />
                  </div>
                  <div>
                    <h4 className="text-sm font-semibold text-slate-900">
                      {brand} {dose.strength && <span className="text-xs font-normal text-slate-500">({dose.strength})</span>}
                    </h4>
                    <p className="text-xs text-slate-400">
                      {generic && `Generic: ${generic} • `}Slot: <strong>{slot}</strong> {timeDisplay && `(${timeDisplay})`}
                    </p>
                    {dose.instructions && (
                      <p className="text-[11px] text-teal-700 font-medium mt-0.5">{dose.instructions}</p>
                    )}
                  </div>
                </div>

                {/* Actions */}
                <div className="flex items-center space-x-2">
                  {dose.status === 'PENDING' ? (
                    <>
                      <button
                        onClick={() => handleAction(doseId, 'SKIPPED')}
                        className="px-2.5 py-1.5 text-xs text-slate-500 hover:text-rose-600 rounded-lg hover:bg-rose-50 border border-slate-200"
                      >
                        Skip
                      </button>
                      <button
                        onClick={() => handleAction(doseId, 'TAKEN')}
                        className="flex items-center space-x-1 px-3 py-1.5 bg-emerald-600 text-white rounded-lg text-xs font-semibold hover:bg-emerald-700 shadow-sm"
                      >
                        <Check className="w-3.5 h-3.5" />
                        <span>Taken</span>
                      </button>
                    </>
                  ) : (
                    <span
                      className={`text-xs font-bold px-2.5 py-1 rounded-md ${
                        dose.status === 'TAKEN' ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-800'
                      }`}
                    >
                      {dose.status}
                    </span>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};

