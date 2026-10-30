import React, { useState, useEffect } from 'react';
import { QRCodeSVG } from 'qrcode.react';
import { QrCode, ShieldAlert, Clock, RefreshCw, XCircle } from 'lucide-react';
import { Modal } from '../common/Modal';
import { EphemeralQRData, sharingApi } from '../../api/sharing';

interface EphemeralQrModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const EphemeralQrModal: React.FC<EphemeralQrModalProps> = ({ isOpen, onClose }) => {
  const [qrData, setQrData] = useState<EphemeralQRData | null>(null);
  const [remainingSeconds, setRemainingSeconds] = useState<number>(1800);
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [isRevoked, setIsRevoked] = useState<boolean>(false);

  const generateNewQR = async () => {
    setIsGenerating(true);
    setIsRevoked(false);
    try {
      const data = await sharingApi.generateQR();
      setQrData(data);
      setRemainingSeconds(data.ttl_seconds || 1800);
    } finally {
      setIsGenerating(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      generateNewQR();
    }
  }, [isOpen]);

  // Live Countdown Timer
  useEffect(() => {
    if (!isOpen || remainingSeconds <= 0 || isRevoked) return;
    const interval = setInterval(() => {
      setRemainingSeconds((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => clearInterval(interval);
  }, [isOpen, remainingSeconds, isRevoked]);

  const handleRevoke = async () => {
    if (qrData?.token) {
      await sharingApi.revokeQR(qrData.token);
      setIsRevoked(true);
    }
  };

  const formatTime = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Consultation QR Pass (30-Minute Ephemeral)">
      <div className="flex flex-col items-center text-center space-y-4">
        <p className="text-xs text-slate-500 max-w-sm">
          Present this secure QR code to your doctor at the chamber desk. This unlocks your 10-second summary and records for 30 minutes.
        </p>

        {isGenerating ? (
          <div className="w-56 h-56 rounded-2xl bg-slate-50 flex items-center justify-center">
            <RefreshCw className="w-8 h-8 text-teal-600 animate-spin" />
          </div>
        ) : isRevoked ? (
          <div className="w-56 h-56 rounded-2xl bg-rose-50 border border-rose-200 flex flex-col items-center justify-center p-4">
            <XCircle className="w-12 h-12 text-rose-500 mb-2" />
            <span className="text-sm font-bold text-rose-800">Access Revoked</span>
            <span className="text-xs text-rose-600 mt-1">Doctor access has been instantly blocked</span>
            <button
              onClick={generateNewQR}
              className="mt-3 px-3 py-1.5 bg-rose-600 text-white text-xs font-semibold rounded-lg hover:bg-rose-700"
            >
              Generate New Pass
            </button>
          </div>
        ) : (
          <div className="p-4 bg-white rounded-2xl border-2 border-dashed border-teal-300 shadow-inner">
            {qrData?.token ? (
              <QRCodeSVG
                value={`medivault://consultation?token=${qrData.token}`}
                size={200}
                level="H"
                includeMargin={true}
              />
            ) : (
              <div className="w-48 h-48 flex items-center justify-center text-slate-400">Loading QR...</div>
            )}
          </div>
        )}

        {/* Timer & Scope */}
        {!isRevoked && (
          <div className="flex items-center space-x-2 text-xs font-bold text-medivault-navy bg-slate-100 px-3 py-1.5 rounded-full">
            <Clock className="w-3.5 h-3.5 text-medivault-primary" />
            <span>Expires in: {formatTime(remainingSeconds)}</span>
          </div>
        )}

        <div className="w-full bg-slate-50 p-3 rounded-xl border border-slate-100 text-left text-xs text-slate-500">
          <p className="font-semibold text-slate-700 mb-1">Permitted Scoped Access:</p>
          <ul className="list-disc list-inside space-y-0.5 text-[11px]">
            <li>90-Day Vital averages (Blood Glucose & BP)</li>
            <li>Active medication roster & allergy warnings</li>
            <li>Recent prescriptions and lab reports</li>
          </ul>
        </div>

        {/* Revoke Action */}
        {!isRevoked && (
          <button
            onClick={handleRevoke}
            className="w-full py-2.5 rounded-xl border border-rose-200 text-rose-600 hover:bg-rose-50 text-xs font-bold transition flex items-center justify-center space-x-1.5"
          >
            <ShieldAlert className="w-4 h-4 text-rose-500" />
            <span>Revoke Doctor Access Now</span>
          </button>
        )}
      </div>
    </Modal>
  );
};

