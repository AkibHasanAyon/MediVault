import React, { useState } from 'react';
import { Plus, Trash2, AlertTriangle, FileDown, ShieldCheck, Sparkles, Check } from 'lucide-react';
import { PrescribedMedicine, DrugInteractionResult, prescriptionsApi } from '../../api/prescriptions';

interface PrescriptionCanvasProps {
  patientId: string;
  patientName: string;
  onSuccess: (rxId: string) => void;
}

export const PrescriptionCanvas: React.FC<PrescriptionCanvasProps> = ({
  patientId,
  patientName,
  onSuccess,
}) => {
  const [complaints, setComplaints] = useState('Fever for 3 days, mild dry cough');
  const [findings, setFindings] = useState('BP: 120/80 mmHg, Chest: Clear, Temp: 99.4 F');
  const [diagnoses, setDiagnoses] = useState('Viral Upper Respiratory Infection, Type-2 Diabetes');
  const [advice, setAdvice] = useState('Drink plenty of warm fluids. Continue current diabetic meds. Rest for 3 days.');
  const [followUpDays, setFollowUpDays] = useState(7);
  const [overrideNotes, setOverrideNotes] = useState('');

  // Medicines List
  const [medications, setMedications] = useState<PrescribedMedicine[]>([
    {
      brand_name: 'Napa Extend',
      generic_name: 'Paracetamol',
      strength: '665mg',
      dosage_form: 'Tablet',
      schedule_pattern: '1+0+1',
      instructions: 'After meal for fever',
      duration_days: 5,
    },
  ]);

  // Drug Interaction State
  const [interactionResult, setInteractionResult] = useState<DrugInteractionResult | null>(null);
  const [isCheckingInteractions, setIsCheckingInteractions] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [createdRxId, setCreatedRxId] = useState<string | null>(null);

  const addMedicine = () => {
    setMedications((prev) => [
      ...prev,
      {
        brand_name: '',
        generic_name: '',
        strength: '',
        dosage_form: 'Tablet',
        schedule_pattern: '1+0+1',
        instructions: 'After meal',
        duration_days: 7,
      },
    ]);
  };

  const removeMedicine = (index: number) => {
    setMedications((prev) => prev.filter((_, i) => i !== index));
  };

  const updateMedicine = (index: number, field: keyof PrescribedMedicine, value: any) => {
    setMedications((prev) => {
      const copy = [...prev];
      copy[index] = { ...copy[index], [field]: value };
      return copy;
    });
  };

  // Trigger real-time drug interaction check
  const handleCheckInteractions = async () => {
    const validDrugs = medications
      .filter((m) => m.brand_name && m.generic_name)
      .map((m) => ({ brand_name: m.brand_name, generic_name: m.generic_name }));

    if (validDrugs.length === 0) return;

    setIsCheckingInteractions(true);
    try {
      const res = await prescriptionsApi.checkInteractions({
        patient_id: patientId,
        drugs: validDrugs,
      });
      setInteractionResult(res);
    } finally {
      setIsCheckingInteractions(false);
    }
  };

  const handleSavePrescription = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      const res = await prescriptionsApi.createPrescription({
        patient_id: patientId,
        chief_complaints: complaints,
        clinical_findings: findings,
        diagnoses: diagnoses.split(',').map((d) => d.trim()),
        medications,
        general_advice: advice,
        next_follow_up_days: followUpDays,
        clinical_override_notes: overrideNotes,
      });

      const rxId = res.id;
      setCreatedRxId(rxId);
      onSuccess(rxId);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
      {/* Header */}
      <div className="flex items-center justify-between pb-4 border-b border-slate-200 mb-6">
        <div>
          <h3 className="text-lg font-bold text-medivault-navy">Digital Prescription Writer</h3>
          <p className="text-xs text-slate-500">
            Composing digital prescription for <strong>{patientName}</strong>
          </p>
        </div>
        <div className="flex space-x-2">
          <button
            type="button"
            onClick={handleCheckInteractions}
            disabled={isCheckingInteractions}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border border-teal-200 bg-teal-50 text-teal-800 text-xs font-semibold hover:bg-teal-100 transition"
          >
            <Sparkles className="w-3.5 h-3.5 text-medivault-primary" />
            <span>{isCheckingInteractions ? 'Checking...' : 'Check Drug Interactions'}</span>
          </button>
        </div>
      </div>

      {/* Drug Interactions Banner if detected */}
      {interactionResult?.interactions && interactionResult.interactions.length > 0 && (
        <div className={`p-4 rounded-xl border mb-6 ${interactionResult.has_contraindications ? 'bg-rose-50 border-rose-300 text-rose-900' : 'bg-amber-50 border-amber-300 text-amber-900'}`}>
          <div className="flex items-center space-x-2 font-bold text-xs mb-1">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            <span>Drug-Drug Interaction Alert: {interactionResult.highest_severity}</span>
          </div>
          <div className="space-y-1.5 text-xs">
            {interactionResult.interactions.map((int, idx) => (
              <div key={idx} className="p-2 rounded bg-white/70 border border-slate-200/50">
                <span className="font-semibold">{int.drug_a} + {int.drug_b} ({int.severity})</span>: {int.description}
              </div>
            ))}
          </div>

          {interactionResult.requires_clinical_override && (
            <div className="mt-3 pt-3 border-t border-rose-200">
              <label className="block text-xs font-bold text-rose-800 mb-1">
                Mandatory Clinical Override Note (Reason for prescribing contraindicated combination):
              </label>
              <textarea
                required
                rows={2}
                placeholder="State clinical rationale (e.g. Benefits outweigh risks under strict outpatient monitoring)..."
                value={overrideNotes}
                onChange={(e) => setOverrideNotes(e.target.value)}
                className="w-full p-2 text-xs border border-rose-300 rounded-lg focus:outline-none focus:ring-1 focus:ring-rose-500"
              />
            </div>
          )}
        </div>
      )}

      {/* Bangladesh Standard 2-Column Canvas */}
      <form onSubmit={handleSavePrescription}>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
          {/* Left Column: Complaints, O/E, Diagnoses */}
          <div className="space-y-4 lg:border-r lg:border-slate-100 lg:pr-6">
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Chief Complaints (C/C)</label>
              <textarea
                rows={3}
                value={complaints}
                onChange={(e) => setComplaints(e.target.value)}
                className="w-full p-2.5 text-xs border border-slate-300 rounded-lg focus:ring-1 focus:ring-teal-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">On Examination (O/E)</label>
              <textarea
                rows={2}
                value={findings}
                onChange={(e) => setFindings(e.target.value)}
                className="w-full p-2.5 text-xs border border-slate-300 rounded-lg focus:ring-1 focus:ring-teal-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Diagnoses (Dx)</label>
              <input
                type="text"
                value={diagnoses}
                onChange={(e) => setDiagnoses(e.target.value)}
                className="w-full p-2.5 text-xs border border-slate-300 rounded-lg focus:ring-1 focus:ring-teal-500 focus:outline-none"
              />
            </div>
          </div>

          {/* Right Column: Rx Medications Table */}
          <div className="lg:col-span-2 space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-2xl font-serif font-black text-medivault-navy">℞</span>
              <button
                type="button"
                onClick={addMedicine}
                className="flex items-center space-x-1 px-3 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Add Medicine</span>
              </button>
            </div>

            {/* Medicines List */}
            <div className="space-y-3">
              {medications.map((med, idx) => (
                <div key={idx} className="p-3 bg-slate-50 border border-slate-200 rounded-xl space-y-2">
                  <div className="grid grid-cols-3 gap-2">
                    <input
                      type="text"
                      placeholder="Brand Name (e.g. Napa)"
                      required
                      value={med.brand_name}
                      onChange={(e) => updateMedicine(idx, 'brand_name', e.target.value)}
                      className="p-2 border border-slate-300 rounded-lg text-xs font-bold"
                    />
                    <input
                      type="text"
                      placeholder="Generic (e.g. Paracetamol)"
                      required
                      value={med.generic_name}
                      onChange={(e) => updateMedicine(idx, 'generic_name', e.target.value)}
                      className="p-2 border border-slate-300 rounded-lg text-xs"
                    />
                    <input
                      type="text"
                      placeholder="Strength (e.g. 500mg)"
                      required
                      value={med.strength}
                      onChange={(e) => updateMedicine(idx, 'strength', e.target.value)}
                      className="p-2 border border-slate-300 rounded-lg text-xs"
                    />
                  </div>
                  <div className="grid grid-cols-4 gap-2">
                    <select
                      value={med.dosage_form}
                      onChange={(e) => updateMedicine(idx, 'dosage_form', e.target.value)}
                      className="p-2 border border-slate-300 rounded-lg text-xs"
                    >
                      <option value="Tablet">Tablet</option>
                      <option value="Capsule">Capsule</option>
                      <option value="Syrup">Syrup</option>
                      <option value="Injection">Injection</option>
                    </select>
                    <input
                      type="text"
                      placeholder="Pattern: 1+0+1"
                      required
                      value={med.schedule_pattern}
                      onChange={(e) => updateMedicine(idx, 'schedule_pattern', e.target.value)}
                      className="p-2 border border-slate-300 rounded-lg text-xs font-mono font-bold"
                    />
                    <input
                      type="text"
                      placeholder="Instructions: After meal"
                      value={med.instructions}
                      onChange={(e) => updateMedicine(idx, 'instructions', e.target.value)}
                      className="p-2 border border-slate-300 rounded-lg text-xs"
                    />
                    <div className="flex items-center space-x-1">
                      <input
                        type="number"
                        placeholder="Days"
                        value={med.duration_days}
                        onChange={(e) => updateMedicine(idx, 'duration_days', parseInt(e.target.value, 10))}
                        className="w-16 p-2 border border-slate-300 rounded-lg text-xs"
                      />
                      <button
                        type="button"
                        onClick={() => removeMedicine(idx)}
                        className="p-2 text-rose-500 hover:bg-rose-50 rounded-lg"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* General Advice & Follow-Up */}
            <div className="grid grid-cols-3 gap-3 pt-3">
              <div className="col-span-2">
                <label className="block text-xs font-bold text-slate-700 mb-1">General Advice</label>
                <input
                  type="text"
                  value={advice}
                  onChange={(e) => setAdvice(e.target.value)}
                  className="w-full p-2.5 text-xs border border-slate-300 rounded-lg"
                />
              </div>
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">Follow-Up (Days)</label>
                <input
                  type="number"
                  value={followUpDays}
                  onChange={(e) => setFollowUpDays(parseInt(e.target.value, 10))}
                  className="w-full p-2.5 text-xs border border-slate-300 rounded-lg"
                />
              </div>
            </div>
          </div>
        </div>

        {/* Footer Actions */}
        <div className="flex items-center justify-between pt-4 border-t border-slate-100">
          {createdRxId ? (
            <div className="flex items-center space-x-3">
              <span className="flex items-center space-x-1 text-xs text-emerald-600 font-bold">
                <Check className="w-4 h-4" />
                <span>Prescription Finalized!</span>
              </span>
              <a
                href={prescriptionsApi.getPdfUrl(createdRxId)}
                target="_blank"
                rel="noreferrer"
                className="flex items-center space-x-1 px-4 py-2 bg-slate-900 text-white rounded-xl text-xs font-bold hover:bg-slate-800"
              >
                <FileDown className="w-4 h-4" />
                <span>Download Vector PDF</span>
              </a>
            </div>
          ) : (
            <div className="text-xs text-slate-400">
              Prescription syncs automatically to patient's active reminders upon save.
            </div>
          )}

          <button
            type="submit"
            disabled={isSubmitting || medications.length === 0}
            className="px-6 py-2.5 bg-medivault-primary text-white rounded-xl text-xs font-bold hover:bg-teal-700 transition shadow-sm disabled:opacity-50"
          >
            {isSubmitting ? 'Finalizing Prescription...' : 'Sign & Finalize Prescription'}
          </button>
        </div>
      </form>
    </div>
  );
};

