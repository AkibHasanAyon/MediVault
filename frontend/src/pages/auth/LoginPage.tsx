import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import {
  Shield,
  Mail,
  KeyRound,
  ArrowRight,
  UserCheck,
  Stethoscope,
  Users,
  UserPlus,
  LogIn,
  AlertCircle,
  Sparkles,
  Phone,
} from 'lucide-react';
import { authApi } from '../../api/auth';

export const LoginPage: React.FC = () => {
  const { loginWithOtp, register, isLoading } = useAuth();
  const navigate = useNavigate();

  // Mode: 'LOGIN' or 'REGISTER'
  const [mode, setMode] = useState<'LOGIN' | 'REGISTER'>('LOGIN');

  // Step: 'INPUT' or 'OTP'
  const [step, setStep] = useState<'INPUT' | 'OTP'>('INPUT');

  // Login / Verification state
  const [email, setEmail] = useState('');
  const [otp, setOtp] = useState('');

  // Registration state
  const [fullName, setFullName] = useState('');
  const [regEmail, setRegEmail] = useState('');
  const [role, setRole] = useState<'PATIENT' | 'DOCTOR' | 'ASSISTANT'>('PATIENT');
  const [bmdcNumber, setBmdcNumber] = useState('');
  const [specialty, setSpecialty] = useState('General Medicine');
  const [phone, setPhone] = useState('');
  const [gender, setGender] = useState<'MALE' | 'FEMALE' | 'OTHER'>('MALE');
  const [bloodGroup, setBloodGroup] = useState<string>('UNKNOWN');
  const [dob, setDob] = useState('');

  // UI state
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successNotice, setSuccessNotice] = useState<string | null>(null);
  const [isResending, setIsResending] = useState(false);

  const handleLoginRequest = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    setSuccessNotice(null);
    const targetEmail = email.trim().toLowerCase();
    if (!targetEmail) {
      setErrorMsg('Please enter your registered email address.');
      return;
    }

    try {
      await authApi.requestOtp(targetEmail);
      setSuccessNotice(`Verification code sent to ${targetEmail}. Please check your inbox.`);
      setStep('OTP');
      setOtp('');
    } catch (err: any) {
      if (err?.response?.data?.code === 'USER_NOT_FOUND' || err?.response?.status === 404) {
        setRegEmail(targetEmail);
        setMode('REGISTER');
        setErrorMsg('No registered account found with this email. Please fill in the details below to create your account.');
      } else {
        setErrorMsg(err?.response?.data?.message || 'Failed to dispatch verification code. Please check your email.');
      }
    }
  };

  const handleRegisterSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    setSuccessNotice(null);
    const targetEmail = regEmail.trim().toLowerCase();
    if (!targetEmail) {
      setErrorMsg('Please enter a valid email address.');
      return;
    }

    try {
      await register({
        full_name: fullName.trim(),
        email: targetEmail,
        role,
        bmdc_number: role === 'DOCTOR' ? bmdcNumber.trim() : undefined,
        specialty: role === 'DOCTOR' ? specialty.trim() : undefined,
        phone_number: phone.trim() || undefined,
        gender: role === 'PATIENT' ? gender : undefined,
        blood_group: role === 'PATIENT' ? bloodGroup : undefined,
        date_of_birth: role === 'PATIENT' && dob ? dob : undefined,
      });
      setEmail(targetEmail);
      setSuccessNotice(`Account registered! A 6-digit verification code was sent to ${targetEmail}.`);
      setStep('OTP');
      setOtp('');
    } catch (err: any) {
      const msg =
        err?.response?.data?.message ||
        err?.response?.data?.errors?.email?.[0] ||
        err?.response?.data?.errors?.phone_number?.[0] ||
        'Registration failed. Please check your inputs.';
      setErrorMsg(msg);
    }
  };

  const handleOtpVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    const code = otp.trim();
    if (!code || code.length !== 6) {
      setErrorMsg('Please enter the 6-digit verification code.');
      return;
    }

    try {
      await loginWithOtp(email.trim().toLowerCase(), code);
      const stored = localStorage.getItem('user');
      const userObj = stored ? JSON.parse(stored) : null;
      const targetRole = userObj?.role || role;

      if (targetRole === 'DOCTOR') navigate('/doctor');
      else if (targetRole === 'ASSISTANT') navigate('/assistant');
      else navigate('/patient');
    } catch (err: any) {
      setErrorMsg(err?.response?.data?.message || 'Invalid or expired verification code.');
    }
  };

  const handleResendOtp = async () => {
    setErrorMsg(null);
    setIsResending(true);
    try {
      await authApi.requestOtp(email.trim().toLowerCase());
      setSuccessNotice(`A fresh verification code was sent to ${email.trim()}.`);
    } catch (err: any) {
      setErrorMsg(err?.response?.data?.message || 'Failed to resend verification code.');
    } finally {
      setIsResending(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-medivault-navy to-slate-900 flex items-center justify-center p-4">
      <div className="w-full max-w-lg bg-white rounded-3xl shadow-2xl p-8 border border-slate-100">
        
        {/* Brand Header */}
        <div className="flex flex-col items-center text-center mb-6">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-medivault-primary to-medivault-accent flex items-center justify-center text-white shadow-lg mb-3">
            <Shield className="w-8 h-8" />
          </div>
          <h2 className="text-2xl font-black text-medivault-navy">MediVault Bangladesh</h2>
          <p className="text-xs text-slate-500 mt-1">
            AI-Powered Personal Health Record & Patient-Doctor Chamber Platform
          </p>
        </div>

        {/* Auth Mode Toggle Tabs (Sign In vs Register) */}
        {step === 'INPUT' && (
          <div className="grid grid-cols-2 p-1 bg-slate-100 rounded-2xl mb-6">
            <button
              type="button"
              onClick={() => { setMode('LOGIN'); setErrorMsg(null); setSuccessNotice(null); }}
              className={`py-2.5 rounded-xl text-xs font-bold transition flex items-center justify-center space-x-1.5 ${
                mode === 'LOGIN'
                  ? 'bg-white text-medivault-navy shadow-sm'
                  : 'text-slate-500 hover:text-slate-700'
              }`}
            >
              <LogIn className="w-4 h-4" />
              <span>Sign In (লগইন)</span>
            </button>
            <button
              type="button"
              onClick={() => { setMode('REGISTER'); setErrorMsg(null); setSuccessNotice(null); }}
              className={`py-2.5 rounded-xl text-xs font-bold transition flex items-center justify-center space-x-1.5 ${
                mode === 'REGISTER'
                  ? 'bg-white text-medivault-navy shadow-sm'
                  : 'text-slate-500 hover:text-slate-700'
              }`}
            >
              <UserPlus className="w-4 h-4" />
              <span>Create Account (নিবন্ধন)</span>
            </button>
          </div>
        )}

        {/* Error / Success Banners */}
        {errorMsg && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 text-xs rounded-xl flex items-center space-x-2">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{errorMsg}</span>
          </div>
        )}
        {successNotice && (
          <div className="mb-4 p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs rounded-xl flex items-center space-x-2">
            <Sparkles className="w-4 h-4 flex-shrink-0 text-emerald-600" />
            <span>{successNotice}</span>
          </div>
        )}

        {/* --- STEP 1A: SIGN IN FORM (Email-First) --- */}
        {step === 'INPUT' && mode === 'LOGIN' && (
          <form onSubmit={handleLoginRequest} className="space-y-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
                Registered Email Address (ইমেইল ঠিকানা)
              </label>
              <div className="relative">
                <Mail className="w-5 h-5 text-slate-400 absolute left-3.5 top-3" />
                <input
                  type="email"
                  required
                  placeholder="name@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full pl-11 pr-4 py-3 border border-slate-300 rounded-xl text-sm font-medium focus:ring-2 focus:ring-teal-500 focus:outline-none"
                />
              </div>
              <p className="text-[11px] text-slate-400 mt-1.5">
                We will dispatch a secure 6-digit verification code to your email.
              </p>
            </div>

            <button
              type="submit"
              disabled={isLoading || !email.trim()}
              className="w-full py-3 bg-medivault-primary text-white rounded-xl text-sm font-bold hover:bg-teal-700 transition flex items-center justify-center space-x-2 shadow-sm disabled:opacity-50"
            >
              <span>{isLoading ? 'Sending Code...' : 'Send Verification Code'}</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </form>
        )}

        {/* --- STEP 1B: REGISTER FORM (Email-First, Real Profile Data) --- */}
        {step === 'INPUT' && mode === 'REGISTER' && (
          <form onSubmit={handleRegisterSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                Full Name (পুরো নাম) <span className="text-rose-500">*</span>
              </label>
              <input
                type="text"
                required
                placeholder="e.g. Akib Hasan"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                className="w-full px-3.5 py-2.5 border border-slate-300 rounded-xl text-sm font-medium focus:ring-2 focus:ring-teal-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                Email Address (যাচাইকরণের ইমেইল) <span className="text-rose-500">*</span>
              </label>
              <div className="relative">
                <Mail className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
                <input
                  type="email"
                  required
                  placeholder="ayon.isc@gmail.com"
                  value={regEmail}
                  onChange={(e) => setRegEmail(e.target.value)}
                  className="w-full pl-10 pr-3.5 py-2.5 border border-slate-300 rounded-xl text-sm font-medium focus:ring-2 focus:ring-teal-500 focus:outline-none"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                Role / Account Type (অ্যাকাউন্টের ধরণ)
              </label>
              <div className="grid grid-cols-3 gap-2">
                {[
                  { id: 'PATIENT', label: 'Patient (রোগী)', icon: UserCheck },
                  { id: 'DOCTOR', label: 'Doctor (ডাক্তার)', icon: Stethoscope },
                  { id: 'ASSISTANT', label: 'Assistant', icon: Users },
                ].map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => setRole(item.id as any)}
                    className={`py-2 px-1 text-center rounded-xl border text-xs font-bold transition flex flex-col items-center justify-center space-y-1 ${
                      role === item.id
                        ? 'border-medivault-primary bg-teal-50 text-medivault-primary shadow-sm'
                        : 'border-slate-200 text-slate-600 hover:bg-slate-50'
                    }`}
                  >
                    <item.icon className="w-4 h-4" />
                    <span className="text-[11px]">{item.label}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* If Doctor: BMDC & Specialty */}
            {role === 'DOCTOR' && (
              <div className="grid grid-cols-2 gap-3 p-3 bg-teal-50/60 rounded-xl border border-teal-100">
                <div>
                  <label className="block text-[11px] font-bold text-teal-900 mb-1">
                    BMDC Reg. Number <span className="text-rose-500">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. A-45892"
                    value={bmdcNumber}
                    onChange={(e) => setBmdcNumber(e.target.value)}
                    className="w-full px-3 py-2 bg-white border border-teal-200 rounded-lg text-xs font-mono font-bold focus:outline-none focus:ring-2 focus:ring-teal-500"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-bold text-teal-900 mb-1">
                    Primary Specialty <span className="text-rose-500">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Internal Medicine"
                    value={specialty}
                    onChange={(e) => setSpecialty(e.target.value)}
                    className="w-full px-3 py-2 bg-white border border-teal-200 rounded-lg text-xs font-medium focus:outline-none focus:ring-2 focus:ring-teal-500"
                  />
                </div>
              </div>
            )}

            {/* If Patient: Real Health Profile Details */}
            {role === 'PATIENT' && (
              <div className="grid grid-cols-2 gap-3 p-3 bg-slate-50 rounded-xl border border-slate-200">
                <div>
                  <label className="block text-[11px] font-bold text-slate-700 mb-1">
                    Gender (লিঙ্গ)
                  </label>
                  <select
                    value={gender}
                    onChange={(e) => setGender(e.target.value as any)}
                    className="w-full px-2.5 py-2 bg-white border border-slate-200 rounded-lg text-xs font-medium focus:ring-2 focus:ring-teal-500 focus:outline-none"
                  >
                    <option value="MALE">Male (পুরুষ)</option>
                    <option value="FEMALE">Female (নারী)</option>
                    <option value="OTHER">Other (অন্যান্য)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-[11px] font-bold text-slate-700 mb-1">
                    Blood Group (রক্তের গ্রুপ)
                  </label>
                  <select
                    value={bloodGroup}
                    onChange={(e) => setBloodGroup(e.target.value)}
                    className="w-full px-2.5 py-2 bg-white border border-slate-200 rounded-lg text-xs font-medium focus:ring-2 focus:ring-teal-500 focus:outline-none"
                  >
                    <option value="UNKNOWN">Select / Unknown</option>
                    <option value="A+">A+</option>
                    <option value="A-">A-</option>
                    <option value="B+">B+</option>
                    <option value="B-">B-</option>
                    <option value="AB+">AB+</option>
                    <option value="AB-">AB-</option>
                    <option value="O+">O+</option>
                    <option value="O-">O-</option>
                  </select>
                </div>

                <div className="col-span-2">
                  <label className="block text-[11px] font-bold text-slate-700 mb-1">
                    Date of Birth (জন্ম তারিখ - Optional)
                  </label>
                  <input
                    type="date"
                    value={dob}
                    onChange={(e) => setDob(e.target.value)}
                    className="w-full px-2.5 py-1.5 bg-white border border-slate-200 rounded-lg text-xs font-medium focus:ring-2 focus:ring-teal-500 focus:outline-none"
                  />
                </div>
              </div>
            )}

            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                Phone Number (মোবাইল নম্বর - Optional)
              </label>
              <div className="relative">
                <Phone className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
                <input
                  type="text"
                  placeholder="017XXXXXXXX"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  className="w-full pl-10 pr-3.5 py-2.5 border border-slate-300 rounded-xl text-sm font-medium focus:ring-2 focus:ring-teal-500 focus:outline-none"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading || !fullName.trim() || !regEmail.trim()}
              className="w-full py-3 bg-medivault-primary text-white rounded-xl text-sm font-bold hover:bg-teal-700 transition flex items-center justify-center space-x-2 shadow-sm disabled:opacity-50"
            >
              <span>{isLoading ? 'Creating Account...' : 'Register & Send Code'}</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </form>
        )}

        {/* --- STEP 2: OTP VERIFICATION (Real Code Verification) --- */}
        {step === 'OTP' && (
          <form onSubmit={handleOtpVerify} className="space-y-4">
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider">
                  Verification Code (OTP)
                </label>
                <button
                  type="button"
                  onClick={() => { setStep('INPUT'); setErrorMsg(null); setSuccessNotice(null); }}
                  className="text-xs text-teal-600 hover:underline font-semibold"
                >
                  Change Email
                </button>
              </div>

              <div className="p-2.5 bg-slate-50 border border-slate-200 rounded-xl mb-3 text-xs text-slate-600 flex items-center justify-between">
                <span>Target: <strong className="text-slate-800">{email}</strong></span>
                <span className="text-[11px] bg-teal-100 text-teal-800 px-2 py-0.5 rounded-full font-bold">Email Code</span>
              </div>

              <div className="relative">
                <KeyRound className="w-5 h-5 text-slate-400 absolute left-3.5 top-3" />
                <input
                  type="text"
                  required
                  maxLength={6}
                  placeholder="Enter 6-digit code"
                  value={otp}
                  onChange={(e) => setOtp(e.target.value)}
                  className="w-full pl-11 pr-4 py-3 border border-slate-300 rounded-xl text-base font-mono font-bold tracking-widest text-center focus:ring-2 focus:ring-teal-500 focus:outline-none"
                />
              </div>
              <p className="text-[11px] text-slate-500 mt-2 text-center">
                Please enter the 6-digit verification code sent to your email inbox. (Also check Spam folder).
              </p>
            </div>

            <button
              type="submit"
              disabled={isLoading || otp.trim().length !== 6}
              className="w-full py-3 bg-medivault-primary text-white rounded-xl text-sm font-bold hover:bg-teal-700 transition flex items-center justify-center space-x-2 shadow-sm disabled:opacity-50"
            >
              <span>{isLoading ? 'Verifying...' : 'Verify & Enter Portal'}</span>
              <ArrowRight className="w-4 h-4" />
            </button>

            <div className="pt-2 text-center">
              <button
                type="button"
                disabled={isResending}
                onClick={handleResendOtp}
                className="text-xs font-semibold text-medivault-primary hover:underline disabled:opacity-50"
              >
                {isResending ? 'Resending code...' : "Didn't receive code? Resend Code"}
              </button>
            </div>
          </form>
        )}

        {/* Quick Demo Accounts */}
        <div className="mt-8 pt-6 border-t border-slate-100">
          <p className="text-[11px] font-bold text-slate-400 uppercase tracking-wider text-center mb-3">
            Quick Sign-In Demo Emails
          </p>
          <div className="grid grid-cols-3 gap-2">
            <button
              type="button"
              onClick={() => {
                setMode('LOGIN');
                setStep('INPUT');
                setEmail('patient@medivault.app');
                setErrorMsg(null);
                setSuccessNotice(null);
              }}
              className="p-2.5 rounded-xl border border-slate-200 hover:border-teal-500 hover:bg-teal-50/50 transition flex flex-col items-center text-center text-xs"
            >
              <UserCheck className="w-4 h-4 text-teal-600 mb-1" />
              <span className="font-semibold text-slate-800">Patient</span>
              <span className="text-[10px] text-slate-400">patient@medivault.app</span>
            </button>
            <button
              type="button"
              onClick={() => {
                setMode('LOGIN');
                setStep('INPUT');
                setEmail('doctor@medivault.app');
                setErrorMsg(null);
                setSuccessNotice(null);
              }}
              className="p-2.5 rounded-xl border border-slate-200 hover:border-teal-500 hover:bg-teal-50/50 transition flex flex-col items-center text-center text-xs"
            >
              <Stethoscope className="w-4 h-4 text-teal-600 mb-1" />
              <span className="font-semibold text-slate-800">Doctor</span>
              <span className="text-[10px] text-slate-400">doctor@medivault.app</span>
            </button>
            <button
              type="button"
              onClick={() => {
                setMode('LOGIN');
                setStep('INPUT');
                setEmail('assistant@medivault.app');
                setErrorMsg(null);
                setSuccessNotice(null);
              }}
              className="p-2.5 rounded-xl border border-slate-200 hover:border-teal-500 hover:bg-teal-50/50 transition flex flex-col items-center text-center text-xs"
            >
              <Users className="w-4 h-4 text-teal-600 mb-1" />
              <span className="font-semibold text-slate-800">Assistant</span>
              <span className="text-[10px] text-slate-400">assistant@medivault.app</span>
            </button>
          </div>
        </div>

      </div>
    </div>
  );
};
