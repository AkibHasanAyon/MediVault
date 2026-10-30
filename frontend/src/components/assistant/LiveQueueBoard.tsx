import React from 'react';
import { QueueEntry, queueApi } from '../../api/queue';
import { Clock, CheckCircle2, PhoneCall, SkipForward, UserCheck } from 'lucide-react';

interface LiveQueueBoardProps {
  entries: QueueEntry[];
  onRefresh: () => void;
}

export const LiveQueueBoard: React.FC<LiveQueueBoardProps> = ({ entries, onRefresh }) => {
  const handleStatusChange = async (entryId: string, newState: QueueEntry['state']) => {
    await queueApi.updateStatus(entryId, newState);
    onRefresh();
  };

  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
      <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
        <div>
          <h3 className="text-base font-bold text-medivault-navy">Today's Chamber Serial Board</h3>
          <p className="text-xs text-slate-500">Live roster with sequential token dispatch</p>
        </div>
        <span className="text-xs font-bold text-teal-800 bg-teal-50 border border-teal-200 px-3 py-1 rounded-full">
          {entries.length} Total Patients
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-50 text-slate-500 uppercase font-semibold border-b border-slate-200 text-[11px]">
            <tr>
              <th className="px-6 py-3">Token</th>
              <th className="px-6 py-3">Patient Name & Phone</th>
              <th className="px-6 py-3">Doctor Chamber</th>
              <th className="px-6 py-3">Est. Wait</th>
              <th className="px-6 py-3">State</th>
              <th className="px-6 py-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {entries.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-6 py-10 text-center text-slate-400">
                  No serial tokens issued today. Use "Issue Serial" to register walk-ins.
                </td>
              </tr>
            ) : (
              entries.map((entry) => (
                <tr
                  key={entry.id}
                  className={`hover:bg-slate-50/70 transition ${
                    entry.state === 'IN_CHAMBER' ? 'bg-teal-50/30' : ''
                  }`}
                >
                  <td className="px-6 py-4 font-mono font-extrabold text-sm text-medivault-navy">
                    {entry.token_display}
                  </td>
                  <td className="px-6 py-4">
                    <p className="font-bold text-slate-900">{entry.patient_name}</p>
                    <p className="text-[11px] text-slate-400">{entry.patient_phone}</p>
                  </td>
                  <td className="px-6 py-4 text-slate-600">
                    {entry.doctor_name}
                  </td>
                  <td className="px-6 py-4 text-slate-500 font-medium">
                    {entry.state === 'DONE' ? '--' : `~${entry.estimated_wait_minutes} mins`}
                  </td>
                  <td className="px-6 py-4">
                    <span
                      className={`inline-flex items-center px-2.5 py-1 rounded-full text-[10px] font-bold ${
                        entry.state === 'WAITING'
                          ? 'bg-slate-100 text-slate-700'
                          : entry.state === 'CALLED_IN'
                          ? 'bg-amber-100 text-amber-800'
                          : entry.state === 'IN_CHAMBER'
                          ? 'bg-teal-100 text-teal-800'
                          : entry.state === 'DONE'
                          ? 'bg-emerald-100 text-emerald-800'
                          : 'bg-rose-100 text-rose-800'
                      }`}
                    >
                      {entry.state}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-right space-x-1">
                    {entry.state === 'WAITING' && (
                      <button
                        onClick={() => handleStatusChange(entry.id, 'CALLED_IN')}
                        className="px-2.5 py-1 rounded bg-amber-500 text-white hover:bg-amber-600 font-bold text-[11px]"
                      >
                        Call
                      </button>
                    )}
                    {entry.state === 'CALLED_IN' && (
                      <button
                        onClick={() => handleStatusChange(entry.id, 'IN_CHAMBER')}
                        className="px-2.5 py-1 rounded bg-teal-600 text-white hover:bg-teal-700 font-bold text-[11px]"
                      >
                        In Chamber
                      </button>
                    )}
                    {entry.state === 'IN_CHAMBER' && (
                      <button
                        onClick={() => handleStatusChange(entry.id, 'DONE')}
                        className="px-2.5 py-1 rounded bg-emerald-600 text-white hover:bg-emerald-700 font-bold text-[11px]"
                      >
                        Done
                      </button>
                    )}
                    {['WAITING', 'CALLED_IN'].includes(entry.state) && (
                      <button
                        onClick={() => handleStatusChange(entry.id, 'SKIPPED')}
                        className="px-2 py-1 rounded border border-slate-200 text-slate-500 hover:bg-slate-100 text-[11px]"
                      >
                        Skip
                      </button>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

