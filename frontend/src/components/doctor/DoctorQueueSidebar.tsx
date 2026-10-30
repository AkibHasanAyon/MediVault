import React from 'react';
import { Users, PhoneCall, Play, CheckCircle, SkipForward, Clock } from 'lucide-react';
import { QueueEntry, DoctorLiveQueue } from '../../api/queue';

interface DoctorQueueSidebarProps {
  queueData: DoctorLiveQueue | null;
  onCallNext: () => void;
  onStartConsultation: (entryId: string) => void;
  onFinishConsultation: (entryId: string) => void;
  onSkipPatient: (entryId: string) => void;
  onSelectPatient: (entry: QueueEntry) => void;
  selectedEntryId?: string;
}

export const DoctorQueueSidebar: React.FC<DoctorQueueSidebarProps> = ({
  queueData,
  onCallNext,
  onStartConsultation,
  onFinishConsultation,
  onSkipPatient,
  onSelectPatient,
  selectedEntryId,
}) => {
  const currentInChamber = queueData?.current_patient;
  const calledPatient = queueData?.called_patient;
  const nextWaiting = queueData?.next_waiting || [];

  return (
    <div className="w-80 bg-white border-r border-slate-200 flex flex-col h-[calc(100vh-4rem)]">
      {/* Top Header */}
      <div className="p-4 border-b border-slate-200">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center space-x-2">
            <Users className="w-5 h-5 text-medivault-primary" />
            <h3 className="font-bold text-medivault-navy text-sm">Chamber Queue</h3>
          </div>
          <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-teal-50 text-medivault-primary border border-teal-100">
            {queueData?.stats?.waiting_count ?? 0} Waiting
          </span>
        </div>

        {/* Big Action: Call Next Patient */}
        <button
          onClick={onCallNext}
          className="w-full py-2.5 px-4 bg-gradient-to-r from-medivault-primary to-teal-600 text-white rounded-xl text-xs font-bold hover:shadow-md hover:from-teal-700 hover:to-teal-700 transition flex items-center justify-center space-x-2"
        >
          <PhoneCall className="w-4 h-4" />
          <span>Call Next Serial</span>
        </button>
      </div>

      {/* Roster Sections */}
      <div className="flex-1 overflow-y-auto p-3 space-y-4">
        {/* Active In-Chamber Patient */}
        {currentInChamber && (
          <div className="bg-teal-50/70 border-2 border-teal-500 rounded-xl p-3 shadow-sm">
            <div className="flex items-center justify-between text-xs font-bold text-teal-900 mb-1">
              <span>IN CONSULTATION</span>
              <span className="text-teal-700 font-mono text-sm">{currentInChamber.token_display}</span>
            </div>
            <p className="text-sm font-semibold text-slate-900">{currentInChamber.patient_name}</p>
            <p className="text-[11px] text-slate-500">{currentInChamber.patient_phone}</p>

            <div className="mt-3 flex space-x-1.5">
              <button
                onClick={() => onFinishConsultation(currentInChamber.id)}
                className="flex-1 py-1.5 bg-medivault-primary text-white text-[11px] font-bold rounded-lg hover:bg-teal-700 transition flex items-center justify-center space-x-1"
              >
                <CheckCircle className="w-3.5 h-3.5" />
                <span>Finish (Rx)</span>
              </button>
            </div>
          </div>
        )}

        {/* Called Patient Arriving */}
        {calledPatient && !currentInChamber && (
          <div className="bg-amber-50 border border-amber-300 rounded-xl p-3 animate-pulse">
            <div className="flex items-center justify-between text-xs font-bold text-amber-900 mb-1">
              <span>CALLED TO CHAMBER</span>
              <span className="text-amber-800 font-mono text-sm">{calledPatient.token_display}</span>
            </div>
            <p className="text-sm font-semibold text-slate-900">{calledPatient.patient_name}</p>
            <div className="mt-3 flex space-x-1.5">
              <button
                onClick={() => onStartConsultation(calledPatient.id)}
                className="flex-1 py-1.5 bg-amber-600 text-white text-[11px] font-bold rounded-lg hover:bg-amber-700 transition flex items-center justify-center space-x-1"
              >
                <Play className="w-3.5 h-3.5" />
                <span>Patient Entered</span>
              </button>
              <button
                onClick={() => onSkipPatient(calledPatient.id)}
                className="px-2.5 py-1.5 border border-amber-300 text-amber-700 text-[11px] font-semibold rounded-lg hover:bg-amber-100"
              >
                <SkipForward className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        )}

        {/* Next Waiting Patients */}
        <div>
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block px-1 mb-2">
            Upcoming In Line
          </span>
          <div className="space-y-1.5">
            {nextWaiting.length === 0 ? (
              <p className="text-xs text-slate-400 py-4 text-center">No more waiting patients</p>
            ) : (
              nextWaiting.map((entry) => (
                <div
                  key={entry.id}
                  onClick={() => onSelectPatient(entry)}
                  className={`p-2.5 rounded-lg border text-xs cursor-pointer transition flex items-center justify-between ${
                    selectedEntryId === entry.id
                      ? 'bg-slate-100 border-teal-500'
                      : 'bg-white border-slate-100 hover:border-slate-300'
                  }`}
                >
                  <div className="flex items-center space-x-2">
                    <span className="font-mono font-bold text-medivault-navy bg-slate-100 px-1.5 py-0.5 rounded text-[11px]">
                      {entry.token_display}
                    </span>
                    <div>
                      <p className="font-semibold text-slate-800 leading-tight">{entry.patient_name}</p>
                      <p className="text-[10px] text-slate-400 flex items-center space-x-1 mt-0.5">
                        <Clock className="w-2.5 h-2.5" />
                        <span>~{entry.estimated_wait_minutes}m wait</span>
                      </p>
                    </div>
                  </div>
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-50 text-slate-500 font-medium">
                    {entry.state}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

