import React, { useState } from 'react';
import { UserPlus, Clock, CheckCircle2 } from 'lucide-react';
import { Modal } from '../common/Modal';
import { queueApi, QueueEntry } from '../../api/queue';

interface WalkInRegistrationModalProps {
  isOpen: boolean;
  onClose: () => void;
  doctorId: string;
  clinicId?: string;
  onSuccess: (entry: QueueEntry) => void;
}

export const WalkInRegistrationModal: React.FC<WalkInRegistrationModalProps> = ({
  isOpen,
  onClose,
  doctorId,
  clinicId,
  onSuccess,
}) => {
  const [phone, setPhone] = useState('01711223344');
  const [name, setName] = useState('Kamal Hossain');
  const [gender, setGender] = useState('MALE');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [issuedEntry, setIssuedEntry] = useState<{
    entry: QueueEntry;
    position: number;
    wait: number;
  } | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      const res = await queueApi.assignToken({
        patient_phone: phone,
        patient_name: name,
        gender,
        doctor_id: doctorId,
        clinic_id: clinicId,
      });

      setIssuedEntry({
        entry: res.data,
        position: res.position_in_queue,
        wait: res.estimated_wait_minutes,
      });
      onSuccess(res.data);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReset = () => {
    setIssuedEntry(null);
    onClose();
  };

  return (
    <Modal isOpen={isOpen} onClose={handleReset} title="Issue Chamber Serial Token">
      {issuedEntry ? (
        <div className="text-center py-4 space-y-4">
          <div className="w-16 h-16 rounded-full bg-emerald-100 text-emerald-600 mx-auto flex items-center justify-center">
            <CheckCircle2 className="w-8 h-8" />
          </div>
          <div>
            <h4 className="text-xl font-black text-medivault-navy">Serial Token Issued!</h4>
            <div className="text-4xl font-extrabold text-teal-600 font-mono my-3">
              {issuedEntry.entry.token_display}
            </div>
            <p className="text-sm font-semibold text-slate-800">{issuedEntry.entry.patient_name}</p>
            <p className="text-xs text-slate-500">{issuedEntry.entry.patient_phone}</p>
          </div>

          <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 text-xs text-slate-600 flex justify-around">
            <div>
              <span className="block text-slate-400">Queue Position</span>
              <strong className="text-sm text-slate-900">#{issuedEntry.position} in line</strong>
            </div>
            <div>
              <span className="block text-slate-400">Estimated Wait</span>
              <strong className="text-sm text-slate-900">~{issuedEntry.wait} minutes</strong>
            </div>
          </div>

          <button
            onClick={handleReset}
            className="w-full py-2.5 bg-medivault-primary text-white rounded-xl text-xs font-bold hover:bg-teal-700 transition"
          >
            Done
          </button>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Patient Mobile Phone (Bangladesh)
            </label>
            <input
              type="text"
              required
              placeholder="e.g. 01712345678"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              className="w-full p-2.5 border border-slate-300 rounded-xl text-sm focus:ring-2 focus:ring-teal-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Patient Full Name</label>
            <input
              type="text"
              required
              placeholder="e.g. Kamal Hossain"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full p-2.5 border border-slate-300 rounded-xl text-sm focus:ring-2 focus:ring-teal-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Gender</label>
            <select
              value={gender}
              onChange={(e) => setGender(e.target.value)}
              className="w-full p-2.5 border border-slate-300 rounded-xl text-sm"
            >
              <option value="MALE">Male</option>
              <option value="FEMALE">Female</option>
              <option value="OTHER">Other</option>
            </select>
          </div>

          <div className="flex justify-end space-x-2 pt-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border border-slate-200 rounded-lg text-xs font-medium text-slate-600 hover:bg-slate-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-5 py-2 bg-medivault-primary text-white rounded-lg text-xs font-bold hover:bg-teal-700 disabled:opacity-50 flex items-center space-x-1.5"
            >
              <UserPlus className="w-4 h-4" />
              <span>{isSubmitting ? 'Generating...' : 'Issue Serial Token'}</span>
            </button>
          </div>
        </form>
      )}
    </Modal>
  );
};

