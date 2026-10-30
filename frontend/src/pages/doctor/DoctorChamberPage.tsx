import React, { useState, useEffect } from 'react';
import { Header } from '../../components/common/Header';
import { DoctorQueueSidebar } from '../../components/doctor/DoctorQueueSidebar';
import { PatientBriefCard } from '../../components/doctor/PatientBriefCard';
import { PrescriptionCanvas } from '../../components/doctor/PrescriptionCanvas';
import { QrScannerModal } from '../../components/doctor/QrScannerModal';
import { queueApi, DoctorLiveQueue, QueueEntry } from '../../api/queue';
import { DoctorScanResult } from '../../api/sharing';
import { useQueueWebSocket } from '../../hooks/useQueueWebSocket';
import { Scan, Stethoscope, Wifi, WifiOff } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

export const DoctorChamberPage: React.FC = () => {
  const { user } = useAuth();
  const [queueData, setQueueData] = useState<DoctorLiveQueue | null>(null);
  const [selectedEntry, setSelectedEntry] = useState<QueueEntry | null>(null);
  const [patientBrief, setPatientBrief] = useState<any>(null);
  const [isScannerOpen, setIsScannerOpen] = useState(false);

  const clinicId = user?.clinic_id || '3d59ae1c-4de1-43df-a4af-45613d8e0ff9';
  const doctorId = user?.doctor_profile_id;

  const loadQueue = async () => {
    try {
      const data = await queueApi.getDoctorLiveQueue();
      setQueueData(data);
      if (data.current_patient) {
        setSelectedEntry(data.current_patient);
      }
    } catch {
      setQueueData(null);
    }
  };

  useEffect(() => {
    loadQueue();
  }, []);

  // Real-time WebSocket hook for chamber queue updates
  const { isConnected } = useQueueWebSocket(clinicId, doctorId, (event) => {
    loadQueue();
  });

  const handleCallNext = async () => {
    await queueApi.doctorCallNext();
    loadQueue();
  };

  const handleStartConsultation = async (entryId: string) => {
    await queueApi.doctorStartConsultation(entryId);
    loadQueue();
  };

  const handleFinishConsultation = async (entryId: string) => {
    await queueApi.doctorFinishConsultation(entryId);
    loadQueue();
  };

  const handleSkipPatient = async (entryId: string) => {
    await queueApi.doctorSkipPatient(entryId);
    loadQueue();
  };

  const handleScanSuccess = (scanResult: DoctorScanResult) => {
    setPatientBrief({
      patient_name: scanResult.patient_name,
      patient_phone: scanResult.patient_phone,
      patient_gender: scanResult.patient_gender,
      patient_age: scanResult.patient_age,
      avg_glucose: scanResult.brief_summary?.avg_glucose,
      avg_bp: scanResult.brief_summary?.avg_bp,
      danger_incidents: scanResult.brief_summary?.danger_incidents || 0,
      active_medications: scanResult.brief_summary?.active_medications || [],
      clinical_summary_bullets: scanResult.brief_summary?.clinical_summary_bullets || [],
    });
  };

  return (
    <div className="min-h-screen bg-medivault-bg flex flex-col">
      <Header />

      {/* Doctor Action Bar */}
      <div className="bg-white border-b border-slate-200 px-6 py-3 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <Stethoscope className="w-5 h-5 text-medivault-primary" />
          <div>
            <h2 className="text-sm font-bold text-medivault-navy">
              Chamber Consultation Desk • {user?.full_name || 'Prof. Dr. Rafiqul Islam'}
            </h2>
            <p className="text-[11px] text-slate-400">BM&DC Reg: A-45678 • Room 304, Dhanmondi Branch</p>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          {/* WebSocket Status */}
          <div className="flex items-center space-x-1.5 text-xs px-2.5 py-1 rounded-full bg-slate-100 font-medium">
            {isConnected ? (
              <>
                <Wifi className="w-3.5 h-3.5 text-emerald-500" />
                <span className="text-emerald-700">Live Queue Synced</span>
              </>
            ) : (
              <>
                <WifiOff className="w-3.5 h-3.5 text-slate-400" />
                <span className="text-slate-500">Connecting...</span>
              </>
            )}
          </div>

          <button
            onClick={() => setIsScannerOpen(true)}
            className="flex items-center space-x-1.5 px-4 py-2 bg-medivault-navy text-white rounded-xl text-xs font-bold hover:bg-slate-800 transition shadow-sm"
          >
            <Scan className="w-4 h-4 text-teal-400" />
            <span>Scan Patient QR Pass</span>
          </button>
        </div>
      </div>

      {/* Main Chamber Layout: Sidebar + Canvas */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left: Queue Sidebar */}
        <DoctorQueueSidebar
          queueData={queueData}
          onCallNext={handleCallNext}
          onStartConsultation={handleStartConsultation}
          onFinishConsultation={handleFinishConsultation}
          onSkipPatient={handleSkipPatient}
          onSelectPatient={(entry) => setSelectedEntry(entry)}
          selectedEntryId={selectedEntry?.id}
        />

        {/* Right: 10-Second Brief + Prescription Canvas */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          <PatientBriefCard brief={patientBrief} />

          {selectedEntry ? (
            <PrescriptionCanvas
              patientId={selectedEntry.patient}
              patientName={selectedEntry.patient_name || patientBrief?.patient_name || 'Patient'}
              onSuccess={() => loadQueue()}
            />
          ) : (
            <div className="bg-white rounded-2xl border border-slate-200 p-8 text-center text-slate-400">
              <p className="text-sm font-semibold text-slate-600">Prescription Canvas Inactive</p>
              <p className="text-xs text-slate-400 mt-1">
                Select or call a patient from the chamber queue to open the digital prescription pad.
              </p>
            </div>
          )}
        </div>
      </div>

      <QrScannerModal
        isOpen={isScannerOpen}
        onClose={() => setIsScannerOpen(false)}
        onScanSuccess={handleScanSuccess}
      />
    </div>
  );
};

