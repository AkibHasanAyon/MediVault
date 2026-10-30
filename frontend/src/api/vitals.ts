import { apiClient } from './client';

export interface GlucoseLog {
  id: string;
  glucose_value_mmol: number;
  glucose_value_mgdl: number;
  context: 'FASTING' | 'POST_MEAL' | 'BEDTIME' | 'RANDOM';
  recorded_at: string;
  is_danger: boolean;
  notes?: string;
}

export interface BloodPressureLog {
  id: string;
  systolic_mmHg: number;
  diastolic_mmHg: number;
  pulse_bpm: number;
  recorded_at: string;
  is_danger: boolean;
  staging_display?: string;
}

export interface WeightLog {
  id: string;
  weight_kg: number;
  height_cm: number;
  bmi: number;
  bmi_category?: string;
  recorded_at: string;
}

export interface VitalsSummary {
  glucose: {
    latest: GlucoseLog | null;
    avg_90_days: number | null;
    danger_count_30_days: number;
  };
  blood_pressure: {
    latest: BloodPressureLog | null;
    avg_systolic_90_days: number | null;
    avg_diastolic_90_days: number | null;
    crisis_count_30_days: number;
  };
  weight: {
    latest: WeightLog | null;
    current_bmi: number | null;
  };
}

export const vitalsApi = {
  getSummary: async (): Promise<VitalsSummary> => {
    const { data } = await apiClient.get('/health-logs/vitals/summary/');
    return data.data || data;
  },

  getGlucoseLogs: async (limit = 30): Promise<GlucoseLog[]> => {
    const { data } = await apiClient.get(`/health-logs/glucose/?limit=${limit}`);
    return data.results || data;
  },

  logGlucose: async (log: { glucose_value: number; unit?: 'mmol' | 'mgdl'; context: string; notes?: string }) => {
    const { data } = await apiClient.post('/health-logs/glucose/', log);
    return data;
  },

  getBPLogs: async (limit = 30): Promise<BloodPressureLog[]> => {
    const { data } = await apiClient.get(`/health-logs/blood-pressure/?limit=${limit}`);
    return data.results || data;
  },

  logBP: async (log: { systolic_mmHg: number; diastolic_mmHg: number; pulse_bpm: number; notes?: string }) => {
    const { data } = await apiClient.post('/health-logs/blood-pressure/', log);
    return data;
  },

  logWeight: async (log: { weight_kg: number; height_cm?: number }) => {
    const { data } = await apiClient.post('/health-logs/weight/', log);
    return data;
  },

  logSymptom: async (log: { note_text: string; severity: 'MILD' | 'MODERATE' | 'SEVERE'; onset_time?: string }) => {
    const { data } = await apiClient.post('/health-logs/symptoms/', log);
    return data;
  },
};

