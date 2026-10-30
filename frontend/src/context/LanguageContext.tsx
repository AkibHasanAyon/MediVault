import React, { createContext, useContext, useState, useEffect } from 'react';

type Language = 'en' | 'bn';

interface LanguageContextType {
  language: Language;
  toggleLanguage: () => void;
  setLanguage: (lang: Language) => void;
  t: (key: string, defaultText?: string) => string;
}

const translations: Record<string, Record<Language, string>> = {
  // Navigation & Common
  app_name: { en: 'MediVault', bn: 'মেডিভল্ট' },
  dashboard: { en: 'Dashboard', bn: 'ড্যাশবোর্ড' },
  patient_portal: { en: 'Patient Portal', bn: 'রোগী পোর্টাল' },
  doctor_chamber: { en: 'Doctor Chamber Desk', bn: 'ডাক্তার চেম্বার ডেস্ক' },
  assistant_desk: { en: 'Assistant Queue Desk', bn: 'সহকারী সিরিয়াল ডেস্ক' },
  waiting_room_display: { en: 'Waiting Room Display', bn: 'ওয়েটিং রুম টিভি ডিসপ্লে' },
  logout: { en: 'Log Out', bn: 'লগ আউট' },
  login: { en: 'Sign In', bn: 'সাইন ইন' },
  phone_number: { en: 'Phone Number', bn: 'মোবাইল নম্বর' },
  verify_otp: { en: 'Verify OTP', bn: 'ওটিপি যাচাই করুন' },

  // Vitals & Health
  vitals: { en: 'Vitals & Health Logs', bn: 'স্বাস্থ্য পরিমাপ ও লক্ষণ' },
  blood_glucose: { en: 'Blood Glucose', bn: 'রক্তের গ্লুকোজ' },
  blood_pressure: { en: 'Blood Pressure', bn: 'রক্তচাপ (BP)' },
  weight_bmi: { en: 'Weight & BMI', bn: 'ওজন ও বিএমআই' },
  fasting: { en: 'Fasting', bn: 'খালি পেটে (Fasting)' },
  post_meal: { en: 'Post Meal (2h)', bn: 'খাওয়ার ২ ঘণ্টা পর' },
  danger_alert: { en: 'Danger Alert', bn: 'বিপদ সতর্কতা' },

  // Documents
  medical_records: { en: 'Medical Vault', bn: 'মেডিকেল ভল্ট ও প্রেসক্রিপশন' },
  upload_document: { en: 'Upload Record / Rx', bn: 'প্রেসক্রিপশন / রিপোর্ট আপলোড' },
  ask_ai: { en: 'Ask AI Clinical Assistant', bn: 'এআই সহকারীকে জিজ্ঞাসা করুন' },
  share_qr: { en: 'Consultation QR', bn: 'পরামর্শ কিউআর কোড' },

  // Medications
  medication_tracker: { en: 'Medication Schedule', bn: 'ঔষধের সময়সূচী' },
  today_doses: { en: "Today's Doses", bn: 'আজকের ঔষধ' },
  mark_taken: { en: 'Taken', bn: 'খেয়েছি' },
  mark_skip: { en: 'Skip', bn: 'বাদ' },
  adherence: { en: 'Adherence', bn: 'নিয়মানুবর্তিতা' },

  // Queue & Chamber
  chamber_queue: { en: 'Chamber Queue', bn: 'চেম্বার সিরিয়াল' },
  call_next: { en: 'Call Next Patient', bn: 'পরবর্তী রোগীকে ডাকুন' },
  start_consultation: { en: 'Start Consultation', bn: 'পরামর্শ শুরু করুন' },
  finish_consultation: { en: 'Finish Consultation', bn: 'পরামর্শ সমাপ্ত' },
  skip_patient: { en: 'Skip / Absent', bn: 'অনুপস্থিত / পরে' },
  current_patient: { en: 'Current Patient in Chamber', bn: 'বর্তমানে চেম্বারে উপস্থিত' },
  waiting_in_lobby: { en: 'Waiting in Lobby', bn: 'লবিতে অপেক্ষমাণ' },
  assign_token: { en: 'Issue Serial Token', bn: 'নতুন সিরিয়াল দিন' },
  daily_summary: { en: 'Daily Summary', bn: 'দৈনিক সারসংক্ষেপ' },
};

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

export const LanguageProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [language, setLanguageState] = useState<Language>(() => {
    return (localStorage.getItem('medivault_lang') as Language) || 'en';
  });

  useEffect(() => {
    localStorage.setItem('medivault_lang', language);
  }, [language]);

  const toggleLanguage = () => {
    setLanguageState((prev) => (prev === 'en' ? 'bn' : 'en'));
  };

  const setLanguage = (lang: Language) => {
    setLanguageState(lang);
  };

  const t = (key: string, defaultText?: string): string => {
    if (translations[key] && translations[key][language]) {
      return translations[key][language];
    }
    return defaultText || key;
  };

  return (
    <LanguageContext.Provider value={{ language, toggleLanguage, setLanguage, t }}>
      {children}
    </LanguageContext.Provider>
  );
};

export const useLanguage = () => {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error('useLanguage must be used within a LanguageProvider');
  }
  return context;
};

