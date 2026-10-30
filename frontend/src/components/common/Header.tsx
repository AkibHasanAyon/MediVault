import React from 'react';
import { useAuth } from '../../context/AuthContext';
import { useLanguage } from '../../context/LanguageContext';
import { Shield, Globe, LogOut, User as UserIcon, Activity, Stethoscope, Users } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';

export const Header: React.FC = () => {
  const { user, role, devLoginAs, logout, isAuthenticated } = useAuth();
  const { language, toggleLanguage, t } = useLanguage();
  const navigate = useNavigate();

  const handleRoleSwitch = async (newRole: 'PATIENT' | 'DOCTOR' | 'ASSISTANT') => {
    await devLoginAs(newRole);
    if (newRole === 'PATIENT') navigate('/patient');
    else if (newRole === 'DOCTOR') navigate('/doctor');
    else if (newRole === 'ASSISTANT') navigate('/assistant');
  };

  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand */}
        <Link to="/" className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-medivault-primary to-medivault-accent flex items-center justify-center text-white shadow-md">
            <Shield className="w-6 h-6" />
          </div>
          <div>
            <span className="text-xl font-bold tracking-tight text-medivault-navy">MediVault</span>
            <span className="hidden sm:inline-block ml-2 text-xs font-medium px-2 py-0.5 rounded-full bg-teal-50 text-medivault-primary border border-teal-200">
              Bangladesh
            </span>
          </div>
        </Link>

        {/* Navigation links & role badges */}
        <nav className="hidden md:flex items-center space-x-1">
          {isAuthenticated && (
            <>
              <Link
                to="/patient"
                className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition ${
                  role === 'PATIENT' ? 'bg-teal-50 text-medivault-primary' : 'text-slate-600 hover:bg-slate-50'
                }`}
              >
                <Activity className="w-4 h-4" />
                <span>{t('patient_portal')}</span>
              </Link>
              <Link
                to="/doctor"
                className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition ${
                  role === 'DOCTOR' ? 'bg-teal-50 text-medivault-primary' : 'text-slate-600 hover:bg-slate-50'
                }`}
              >
                <Stethoscope className="w-4 h-4" />
                <span>{t('doctor_chamber')}</span>
              </Link>
              <Link
                to="/assistant"
                className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition ${
                  role === 'ASSISTANT' ? 'bg-teal-50 text-medivault-primary' : 'text-slate-600 hover:bg-slate-50'
                }`}
              >
                <Users className="w-4 h-4" />
                <span>{t('assistant_desk')}</span>
              </Link>
            </>
          )}
        </nav>

        {/* Right Actions: Dev Role Switcher, Language Toggle, User profile */}
        <div className="flex items-center space-x-3">
          {/* Quick Dev Switcher for prototype testing */}
          <div className="hidden lg:flex items-center bg-slate-100 rounded-lg p-1 text-xs">
            <span className="px-2 text-slate-500 font-medium">Switch:</span>
            <button
              onClick={() => handleRoleSwitch('PATIENT')}
              className={`px-2 py-1 rounded font-medium transition ${
                role === 'PATIENT' ? 'bg-white text-medivault-primary shadow-sm' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Patient
            </button>
            <button
              onClick={() => handleRoleSwitch('DOCTOR')}
              className={`px-2 py-1 rounded font-medium transition ${
                role === 'DOCTOR' ? 'bg-white text-medivault-primary shadow-sm' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Doctor
            </button>
            <button
              onClick={() => handleRoleSwitch('ASSISTANT')}
              className={`px-2 py-1 rounded font-medium transition ${
                role === 'ASSISTANT' ? 'bg-white text-medivault-primary shadow-sm' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Assistant
            </button>
          </div>

          {/* Bilingual Language Switcher */}
          <button
            onClick={toggleLanguage}
            className="flex items-center space-x-1 px-3 py-1.5 rounded-lg border border-slate-200 text-sm font-medium text-slate-700 hover:bg-slate-50 transition"
            title="Toggle Bangla / English"
          >
            <Globe className="w-4 h-4 text-medivault-primary" />
            <span>{language === 'en' ? 'বাংলা' : 'EN'}</span>
          </button>

          {/* User profile / Logout */}
          {isAuthenticated ? (
            <div className="flex items-center space-x-2">
              <div className="flex items-center space-x-2 pl-2 border-l border-slate-200">
                <div className="w-8 h-8 rounded-full bg-slate-200 flex items-center justify-center text-slate-700 font-semibold text-xs">
                  {user?.full_name?.charAt(0) || <UserIcon className="w-4 h-4" />}
                </div>
                <div className="hidden xl:block text-left">
                  <p className="text-xs font-semibold text-slate-900 leading-tight">{user?.full_name}</p>
                  <p className="text-[10px] text-slate-500 uppercase">{user?.role}</p>
                </div>
              </div>
              <button
                onClick={logout}
                className="p-2 rounded-lg text-slate-500 hover:text-rose-600 hover:bg-rose-50 transition"
                title={t('logout')}
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          ) : (
            <Link
              to="/login"
              className="px-4 py-2 rounded-lg bg-medivault-primary text-white text-sm font-medium hover:bg-teal-700 transition shadow-sm"
            >
              {t('login')}
            </Link>
          )}
        </div>
      </div>
    </header>
  );
};

