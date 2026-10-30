import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { queueApi, ClinicDisplayResponse } from '../../api/queue';
import { useQueueWebSocket } from '../../hooks/useQueueWebSocket';
import { Shield, Clock, Users, Tv } from 'lucide-react';

export const WaitingRoomTvPage: React.FC = () => {
  const { clinicId = 'popular-dhanmondi-id' } = useParams();
  const [displayData, setDisplayData] = useState<ClinicDisplayResponse | null>(null);
  const [currentTime, setCurrentTime] = useState<string>(new Date().toLocaleTimeString());

  const loadDisplay = async () => {
    try {
      const data = await queueApi.getClinicDisplay(clinicId);
      setDisplayData(data);
    } catch {
      setDisplayData(null);
    }
  };

  useEffect(() => {
    loadDisplay();
    const timer = setInterval(() => {
      setCurrentTime(new Date().toLocaleTimeString());
    }, 1000);
    return () => clearInterval(timer);
  }, [clinicId]);

  // Real-time WebSocket hook to update TV display instantly
  useQueueWebSocket(clinicId, undefined, () => {
    loadDisplay();
  });

  return (
    <div className="min-h-screen bg-slate-950 text-white flex flex-col p-6 sm:p-10 select-none">
      {/* Top TV Header Bar */}
      <header className="flex items-center justify-between pb-6 border-b border-slate-800">
        <div className="flex items-center space-x-4">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-medivault-primary to-medivault-accent flex items-center justify-center text-white shadow-xl">
            <Shield className="w-8 h-8" />
          </div>
          <div>
            <h1 className="text-3xl font-black tracking-tight text-white">
              {displayData?.clinic_name || 'Popular Diagnostic Center'}
            </h1>
            <p className="text-sm font-semibold text-teal-400 mt-0.5">
              {displayData?.branch || 'Dhanmondi Branch'} • Live Chamber Serial Monitor
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-6 text-right">
          <div>
            <span className="text-3xl font-black font-mono text-white tracking-widest block">
              {currentTime}
            </span>
            <span className="text-xs text-slate-400 font-medium">
              {displayData?.date || new Date().toDateString()} (Dhaka)
            </span>
          </div>
          <div className="w-3 h-3 rounded-full bg-emerald-500 animate-ping" title="Live Synced" />
        </div>
      </header>

      {/* Main Display Grid: Large Chamber Cards or Empty Waiting Room */}
      <main className="flex-1 my-8 flex items-center justify-center">
        {!displayData?.chambers || displayData.chambers.length === 0 ? (
          <div className="bg-slate-900/60 rounded-3xl border border-slate-800 p-12 text-center max-w-lg mx-auto">
            <Tv className="w-16 h-16 text-slate-600 mx-auto mb-4 animate-pulse" />
            <h2 className="text-2xl font-bold text-slate-300">No Active Chamber Consultations</h2>
            <p className="text-sm text-slate-500 mt-2">
              There are currently no active consultation queues or doctor sessions registered for this clinic today.
            </p>
            <p className="text-xs text-teal-400 mt-4">
              Waiting room display will update automatically in real-time when a doctor begins consultations.
            </p>
          </div>
        ) : (
          <div className="w-full grid grid-cols-1 md:grid-cols-2 gap-8 items-stretch">
            {displayData.chambers.map((chamber) => (
              <div
                key={chamber.doctor_id}
                className="bg-slate-900/90 rounded-3xl border-2 border-slate-800 p-8 flex flex-col justify-between shadow-2xl relative overflow-hidden"
              >
                {/* Chamber Indicator Bar */}
                <div className="flex items-start justify-between">
                  <div>
                    <span className="text-xs font-bold uppercase tracking-widest text-teal-400 bg-teal-950/80 px-3 py-1 rounded-full border border-teal-800">
                      {chamber.chamber_number}
                    </span>
                    <h2 className="text-2xl font-black text-white mt-3 leading-tight">
                      {chamber.doctor_name}
                    </h2>
                    <p className="text-sm text-slate-400 font-medium">{chamber.specialties}</p>
                  </div>
                </div>

                {/* Huge Serving Token */}
                <div className="my-8 py-8 bg-slate-950/80 rounded-2xl border border-slate-800/80 flex flex-col items-center justify-center text-center">
                  <span className="text-xs font-extrabold uppercase tracking-widest text-slate-400 mb-2">
                    NOW CONSULTING / বর্তমান সিরিয়াল
                  </span>
                  <div className="text-7xl sm:text-8xl font-black font-mono text-emerald-400 tracking-wider animate-pulse">
                    {chamber.current_token}
                  </div>
                  <span className="text-xs font-bold mt-2 text-teal-300 uppercase tracking-widest">
                    {chamber.current_state}
                  </span>
                </div>

                {/* Upcoming Tokens Row */}
                <div className="pt-4 border-t border-slate-800/80">
                  <div className="flex items-center justify-between text-xs text-slate-400 font-bold uppercase tracking-wider mb-3">
                    <span className="flex items-center space-x-1.5">
                      <Clock className="w-4 h-4 text-slate-500" />
                      <span>NEXT IN LINE / পরবর্তী সিরিয়াল:</span>
                    </span>
                    <span className="text-slate-500 font-normal">{chamber.waiting_count} waiting</span>
                  </div>
                  <div className="flex items-center space-x-3">
                    {chamber.upcoming_tokens.map((tok, idx) => (
                      <div
                        key={idx}
                        className="flex-1 py-3 bg-slate-800/60 border border-slate-700/60 rounded-xl text-center font-mono font-bold text-lg text-slate-200"
                      >
                        {tok}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>

      {/* Footer Ticker */}
      <footer className="text-center py-3 bg-slate-900 rounded-2xl border border-slate-800 text-xs text-slate-400 font-medium">
        অনুগ্রহ করে আপনার সিরিয়াল ডাকা হলে চেম্বারে প্রবেশ করুন। তথ্যের জন্য অ্যাসিস্ট্যান্ট ডেস্কে যোগাযোগ করুন।
        (Please proceed to the chamber when your serial is called.)
      </footer>
    </div>
  );
};

