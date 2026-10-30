import React, { useState, useEffect } from 'react';
import { Header } from '../../components/common/Header';
import { VitalsDashboard } from '../../components/patient/VitalsDashboard';
import { MedicationTodayCard } from '../../components/patient/MedicationTodayCard';
import { DocumentVault } from '../../components/patient/DocumentVault';
import { EphemeralQrModal } from '../../components/patient/EphemeralQrModal';
import { AskAiDrawer } from '../../components/patient/AskAiDrawer';
import { vitalsApi, VitalsSummary } from '../../api/vitals';
import { documentsApi, MedicalDocument } from '../../api/documents';
import { medicationsApi, TodayMedicationsResponse } from '../../api/medications';
import { QrCode, Bot, Sparkles, Activity } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

export const PatientDashboard: React.FC = () => {
  const { user } = useAuth();
  const [summary, setSummary] = useState<VitalsSummary | null>(null);
  const [documents, setDocuments] = useState<MedicalDocument[]>([]);
  const [schedule, setSchedule] = useState<TodayMedicationsResponse | null>(null);

  // Modals state
  const [isQrOpen, setIsQrOpen] = useState(false);
  const [isAiOpen, setIsAiOpen] = useState(false);

  const loadAllData = async () => {
    try {
      const [sumRes, docsRes, schedRes] = await Promise.all([
        vitalsApi.getSummary().catch(() => null),
        documentsApi.getTimeline().catch(() => []),
        medicationsApi.getTodaySchedule().catch(() => null),
      ]);
      setSummary(sumRes);
      setDocuments(docsRes);
      setSchedule(schedRes);
    } catch {
      // Ignore initial offline load
    }
  };

  useEffect(() => {
    loadAllData();
  }, []);

  return (
    <div className="min-h-screen bg-medivault-bg flex flex-col">
      <Header />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Welcome & Quick Action Bar */}
        <div className="bg-gradient-to-r from-medivault-navy via-slate-800 to-medivault-primary rounded-3xl p-6 sm:p-8 text-white shadow-xl flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-white/20 text-teal-200">
              Patient Portal • Bangladesh
            </span>
            <h1 className="text-2xl sm:text-3xl font-black mt-2">
              Welcome back, {user?.full_name || 'Patient'}
            </h1>
            <p className="text-xs sm:text-sm text-slate-300 mt-1 max-w-lg">
              Manage your vitals, view AI-extracted prescriptions, and share scoped ephemeral records with your doctor.
            </p>
          </div>

          <div className="flex items-center space-x-3">
            <button
              onClick={() => setIsQrOpen(true)}
              className="flex items-center space-x-2 px-5 py-3 bg-white text-medivault-navy rounded-2xl text-xs font-extrabold hover:bg-teal-50 transition shadow-lg"
            >
              <QrCode className="w-4 h-4 text-medivault-primary" />
              <span>Consultation QR Pass</span>
            </button>
          </div>
        </div>

        {/* Top Grid: Vitals & Today's Meds */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2">
            <VitalsDashboard summary={summary} onRefresh={loadAllData} />
          </div>
          <div>
            <MedicationTodayCard scheduleData={schedule} onRefresh={loadAllData} />
          </div>
        </div>

        {/* Medical Document Vault */}
        <div>
          <DocumentVault documents={documents} onRefresh={loadAllData} />
        </div>
      </main>

      {/* Floating Ask AI Button */}
      <button
        onClick={() => setIsAiOpen(true)}
        className="fixed bottom-6 right-6 px-4 py-3 bg-gradient-to-r from-medivault-primary to-medivault-accent text-white rounded-2xl shadow-xl flex items-center space-x-2 text-xs font-bold hover:scale-105 transition z-30"
      >
        <Bot className="w-5 h-5" />
        <span>Ask AI Assistant</span>
        <Sparkles className="w-3.5 h-3.5 text-amber-300" />
      </button>

      {/* Modals & Drawers */}
      <EphemeralQrModal isOpen={isQrOpen} onClose={() => setIsQrOpen(false)} />
      <AskAiDrawer isOpen={isAiOpen} onClose={() => setIsAiOpen(false)} />
    </div>
  );
};

