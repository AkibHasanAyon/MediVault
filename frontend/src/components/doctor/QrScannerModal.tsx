import React, { useState } from 'react';
import { QrCode, Scan, CheckCircle, AlertCircle } from 'lucide-react';
import { Modal } from '../common/Modal';
import { sharingApi, DoctorScanResult } from '../../api/sharing';

interface QrScannerModalProps {
  isOpen: boolean;
  onClose: () => void;
  onScanSuccess: (result: DoctorScanResult) => void;
}

export const QrScannerModal: React.FC<QrScannerModalProps> = ({ isOpen, onClose, onScanSuccess }) => {
  const [tokenInput, setTokenInput] = useState('');
  const [isScanning, setIsScanning] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  const handleScan = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!tokenInput.trim()) return;

    setIsScanning(true);
    setErrorMsg('');

    // Extract token if user pasted full medivault URI
    let cleanToken = tokenInput.trim();
    if (cleanToken.includes('token=')) {
      cleanToken = cleanToken.split('token=')[1].split('&')[0];
    }

    try {
      const res = await sharingApi.scanQR(cleanToken);
      onScanSuccess(res);
      onClose();
    } catch {
      setErrorMsg('Invalid or expired QR token. Please request a new pass from the patient.');
    } finally {
      setIsScanning(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Scan Consultation QR Code">
      <form onSubmit={handleScan} className="space-y-4">
        <div className="flex flex-col items-center justify-center p-6 border-2 border-dashed border-teal-200 bg-teal-50/40 rounded-2xl text-center">
          <Scan className="w-12 h-12 text-medivault-primary mb-2 animate-pulse" />
          <h4 className="text-sm font-bold text-medivault-navy">Chamber Handshake Scanner</h4>
          <p className="text-xs text-slate-500 mt-1 max-w-xs">
            Scan with connected barcode camera or enter patient's 30-minute ephemeral consultation token below.
          </p>
        </div>

        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1">
            Token or QR Payload
          </label>
          <input
            type="text"
            required
            placeholder="Paste raw token or medivault://consultation?token=..."
            value={tokenInput}
            onChange={(e) => setTokenInput(e.target.value)}
            className="w-full p-2.5 border border-slate-300 rounded-xl text-xs font-mono focus:ring-2 focus:ring-teal-500 focus:outline-none"
          />
        </div>

        {errorMsg && (
          <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 rounded-xl text-xs flex items-center space-x-1.5">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{errorMsg}</span>
          </div>
        )}

        <div className="flex justify-end space-x-2 pt-2">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 border border-slate-200 rounded-lg text-xs font-medium text-slate-600 hover:bg-slate-50"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={isScanning || !tokenInput.trim()}
            className="px-5 py-2 bg-medivault-primary text-white rounded-lg text-xs font-bold hover:bg-teal-700 disabled:opacity-50"
          >
            {isScanning ? 'Verifying...' : 'Authorize & Unlock'}
          </button>
        </div>
      </form>
    </Modal>
  );
};

