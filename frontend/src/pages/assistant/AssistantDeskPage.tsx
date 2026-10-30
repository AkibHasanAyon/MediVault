import React, { useState, useEffect } from 'react';
import { Header } from '../../components/common/Header';
import { LiveQueueBoard } from '../../components/assistant/LiveQueueBoard';
import { WalkInRegistrationModal } from '../../components/assistant/WalkInRegistrationModal';
import { queueApi, QueueEntry, DailyQueueSummary } from '../../api/queue';
import { useQueueWebSocket } from '../../hooks/useQueueWebSocket';
import { Users, UserPlus, Tv, TrendingUp, Clock, CheckCircle2, AlertCircle } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

export const AssistantDeskPage: React.FC = () => {
  const { user } = useAuth();
  const [entries, setEntries] = useState<QueueEntry[]>([]);
  const [summary, setSummary] = useState<DailyQueueSummary | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const clinicId = user?.clinic_id || '3d59ae1c-4de1-43df-a4af-45613d8e0ff9';
  const doctorId = '1449b8cf-f904-4867-86f7-b616ace4bda8';

  const loadData = async () => {
    try {
      const [queueRes, sumRes] = await Promise.all([
        queueApi.getTodayQueue(clinicId),
        queueApi.getDailySummary(clinicId),
      ]);
      setEntries(queueRes || []);
      setSummary(sumRes);
    } catch {
      setEntries([]);
      setSummary(null);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // Sync queue in real time via WebSocket
  useQueueWebSocket(clinicId, undefined, () => {
    loadData();
  });

  return (
    <div className="min-h-screen bg-medivault-bg flex flex-col">
      <Header />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {/* Top Header & Actions */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
          <div>
            <h1 className="text-xl font-bold text-medivault-navy flex items-center space-x-2">
              <Users className="w-6 h-6 text-medivault-primary" />
              <span>Clinic Assistant Queue Desk</span>
            </h1>
            <p className="text-xs text-slate-500 mt-1">
              Popular Diagnostic Center • Desk 1 • Walk-in registration & chamber queue dispatch
            </p>
          </div>

          <div className="flex items-center space-x-3">
            <Link
              to={`/display/${clinicId}`}
              target="_blank"
              className="flex items-center space-x-1.5 px-4 py-2 border border-slate-200 rounded-xl text-xs font-bold text-slate-700 hover:bg-slate-50 transition"
            >
              <Tv className="w-4 h-4 text-slate-500" />
              <span>Waiting Room TV Display</span>
            </Link>

            <button
              onClick={() => setIsModalOpen(true)}
              className="flex items-center space-x-1.5 px-5 py-2.5 bg-medivault-primary text-white rounded-xl text-xs font-bold hover:bg-teal-700 transition shadow-sm"
            >
              <UserPlus className="w-4 h-4" />
              <span>Issue Serial Token</span>
            </button>
          </div>
        </div>

        {/* Analytics Summary Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="p-4 bg-white rounded-2xl border border-slate-200 shadow-sm">
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
              Total Registered
            </span>
            <span className="text-2xl font-black text-slate-900 mt-1 block">
              {summary?.metrics?.total_registered ?? entries.length}
            </span>
            <span className="text-[11px] text-teal-600 font-medium">Daily Chamber Intake</span>
          </div>

          <div className="p-4 bg-white rounded-2xl border border-slate-200 shadow-sm">
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
              Completed (Seen)
            </span>
            <span className="text-2xl font-black text-emerald-600 mt-1 block">
              {summary?.metrics?.total_completed ?? 0}
            </span>
            <span className="text-[11px] text-slate-400">Prescriptions Signed</span>
          </div>

          <div className="p-4 bg-white rounded-2xl border border-slate-200 shadow-sm">
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
              Avg. Patient Wait
            </span>
            <span className="text-2xl font-black text-slate-900 mt-1 block">
              {summary?.metrics?.avg_wait_minutes ?? 0} <span className="text-xs font-normal text-slate-400">mins</span>
            </span>
            <span className="text-[11px] text-slate-400">Lobby Arrival to Call</span>
          </div>

          <div className="p-4 bg-white rounded-2xl border border-slate-200 shadow-sm">
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
              No-Show Rate
            </span>
            <span className="text-2xl font-black text-rose-600 mt-1 block">
              {summary?.metrics?.no_show_rate_percent ?? 0}%
            </span>
            <span className="text-[11px] text-slate-400">Absence Rate Today</span>
          </div>
        </div>

        {/* Live Queue Table */}
        <LiveQueueBoard entries={entries} onRefresh={loadData} />
      </main>

      <WalkInRegistrationModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        doctorId={doctorId}
        clinicId={clinicId}
        onSuccess={() => loadData()}
      />
    </div>
  );
};

