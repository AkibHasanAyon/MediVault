import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import { Shield, Phone, KeyRound, ArrowRight, UserCheck, Stethoscope, Users } from 'lucide-react';

export const LoginPage: React.FC = () => {
  const { loginWithOtp, devLoginAs, isLoading } = useAuth();
  const navigate = useNavigate();

  const [phone, setPhone] = useState('01711000011');
  const [otp, setOtp] = useState('123456');
  const [step, setStep] = useState<'PHONE' | 'OTP'>('PHONE');

  const handlePhoneSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (phone.length >= 10) {
      setStep('OTP');
    }
  };

  const handleOtpSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await loginWithOtp(phone, otp);
      navigate('/patient');
    } catch {
      // In dev fallback
      navigate('/patient');
    }
  };

  const handleDevRole = async (role: 'PATIENT' | 'DOCTOR' | 'ASSISTANT') => {
    await devLoginAs(role);
    if (role === 'PATIENT') navigate('/patient');
    else if (role === 'DOCTOR') navigate('/doctor');
    else if (role === 'ASSISTANT') navigate('/assistant');
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-medivault-navy to-slate-900 flex items-center justify-center p-4">
      <div className="w-full max-w-md bg-white rounded-3xl shadow-2xl p-8 border border-slate-100">
        {/* Brand Header */}
        <div className="flex flex-col items-center text-center mb-8">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-medivault-primary to-medivault-accent flex items-center justify-center text-white shadow-lg mb-3">
            <Shield className="w-8 h-8" />
          </div>
          <h2 className="text-2xl font-black text-medivault-navy">MediVault Bangladesh</h2>
          <p className="text-xs text-slate-500 mt-1">
            Secure Personal Health Record & Doctor-Patient Communication
          </p>
        </div>

        {/* Step 1: Phone Input */}
        {step === 'PHONE' ? (
          <form onSubmit={handlePhoneSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
                Mobile Phone Number
              </label>
              <div className="relative">
                <Phone className="w-5 h-5 text-slate-400 absolute left-3.5 top-3" />
                <input
                  type="text"
                  required
                  placeholder="017XXXXXXXX"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  className="w-full pl-11 pr-4 py-3 border border-slate-300 rounded-xl text-sm font-medium focus:ring-2 focus:ring-teal-500 focus:outline-none"
                />
              </div>
              <p className="text-[11px] text-slate-400 mt-1.5">
                We will dispatch a 6-digit verification code to your phone / email.
              </p>
            </div>

            <button
              type="submit"
              className="w-full py-3 bg-medivault-primary text-white rounded-xl text-sm font-bold hover:bg-teal-700 transition flex items-center justify-center space-x-2 shadow-sm"
            >
              <span>Request Verification Code</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </form>
        ) : (
          /* Step 2: OTP Input */
          <form onSubmit={handleOtpSubmit} className="space-y-4">
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider">
                  Verification Code (OTP)
                </label>
                <button
                  type="button"
                  onClick={() => setStep('PHONE')}
                  className="text-xs text-teal-600 hover:underline"
                >
                  Change Number
                </button>
              </div>
              <div className="relative">
                <KeyRound className="w-5 h-5 text-slate-400 absolute left-3.5 top-3" />
                <input
                  type="text"
                  required
                  placeholder="Enter 6-digit code"
                  value={otp}
                  onChange={(e) => setOtp(e.target.value)}
                  className="w-full pl-11 pr-4 py-3 border border-slate-300 rounded-xl text-sm font-mono font-bold tracking-widest text-center focus:ring-2 focus:ring-teal-500 focus:outline-none"
                />
              </div>
              <p className="text-[11px] text-slate-400 mt-1.5 text-center">
                Dev default code is <code className="bg-slate-100 px-1 py-0.5 rounded font-mono">123456</code>
              </p>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-3 bg-medivault-primary text-white rounded-xl text-sm font-bold hover:bg-teal-700 transition flex items-center justify-center space-x-2 shadow-sm disabled:opacity-50"
            >
              <span>{isLoading ? 'Verifying...' : 'Sign In to MediVault'}</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </form>
        )}

        {/* Quick Dev Portals 1-Click Access */}
        <div className="mt-8 pt-6 border-t border-slate-100">
          <p className="text-[11px] font-bold text-slate-400 uppercase tracking-wider text-center mb-3">
            Prototype Quick Access Roles
          </p>
          <div className="grid grid-cols-3 gap-2">
            <button
              onClick={() => handleDevRole('PATIENT')}
              className="p-2.5 rounded-xl border border-slate-200 hover:border-teal-500 hover:bg-teal-50/50 transition flex flex-col items-center text-center text-xs"
            >
              <UserCheck className="w-4 h-4 text-teal-600 mb-1" />
              <span className="font-semibold text-slate-800">Patient</span>
            </button>
            <button
              onClick={() => handleDevRole('DOCTOR')}
              className="p-2.5 rounded-xl border border-slate-200 hover:border-teal-500 hover:bg-teal-50/50 transition flex flex-col items-center text-center text-xs"
            >
              <Stethoscope className="w-4 h-4 text-teal-600 mb-1" />
              <span className="font-semibold text-slate-800">Doctor</span>
            </button>
            <button
              onClick={() => handleDevRole('ASSISTANT')}
              className="p-2.5 rounded-xl border border-slate-200 hover:border-teal-500 hover:bg-teal-50/50 transition flex flex-col items-center text-center text-xs"
            >
              <Users className="w-4 h-4 text-teal-600 mb-1" />
              <span className="font-semibold text-slate-800">Assistant</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

