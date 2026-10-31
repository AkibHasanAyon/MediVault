import { apiClient } from './client';

export interface GlucoseLog {
  id: string;
  glucose_value_mmol: number;
  glucose_value_mgdl: number;
  context: 'FASTING' | 'POST_MEAL' | 'BEDTIME' | 'RANDOM';
  recorded_at: string;
  is_danger: boolean;
  is_out_of_range?: boolean;
  warning_message?: string;
  recommendation?: string;
  clinical_assessment?: any;
  notes?: string;
}

export interface BloodPressureLog {
  id: string;
  systolic_mmHg: number;
  diastolic_mmHg: number;
  pulse_bpm: number;
  recorded_at: string;
  is_danger: boolean;
  bp_stage?: string;
  staging_display?: string;
  is_out_of_range?: boolean;
  warning_message?: string;
  recommendation?: string;
  clinical_assessment?: any;
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
  latest_glucose?: GlucoseLog | null;
  seven_day_avg_glucose?: number | null;
  latest_bp?: BloodPressureLog | null;
  latest_weight?: WeightLog | null;
  unacknowledged_danger_alerts_count?: number;
  active_danger_alerts?: any[];
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
    const raw = data.data || data || {};
    return {
      latest_glucose: raw.latest_glucose || null,
      seven_day_avg_glucose: raw.seven_day_avg_glucose || null,
      latest_bp: raw.latest_bp || null,
      latest_weight: raw.latest_weight || null,
      unacknowledged_danger_alerts_count: raw.unacknowledged_danger_alerts_count || 0,
      active_danger_alerts: raw.active_danger_alerts || [],
      glucose: raw.glucose || {
        latest: raw.latest_glucose || null,
        avg_90_days: raw.seven_day_avg_glucose || null,
        danger_count_30_days: raw.unacknowledged_danger_alerts_count || 0,
      },
      blood_pressure: raw.blood_pressure || {
        latest: raw.latest_bp || null,
        avg_systolic_90_days: null,
        avg_diastolic_90_days: null,
        crisis_count_30_days: 0,
      },
      weight: raw.weight || {
        latest: raw.latest_weight || null,
        current_bmi: raw.latest_weight?.bmi || null,
      },
    };
  },

  getGlucoseLogs: async (limit = 30): Promise<GlucoseLog[]> => {
    const { data } = await apiClient.get(`/health-logs/glucose/?limit=${limit}`);
    return data.results || data;
  },

  logGlucose: async (log: {
    glucose_value?: number;
    glucose_value_mmol?: number;
    glucose_value_mgdl?: number;
    unit?: 'mmol' | 'mgdl';
    context?: string;
    reading_type?: string;
    notes?: string;
  }) => {
    const payload = {
      glucose_value_mmol: log.glucose_value_mmol ?? (log.unit === 'mgdl' ? undefined : log.glucose_value),
      glucose_value_mgdl: log.glucose_value_mgdl ?? (log.unit === 'mgdl' ? log.glucose_value : undefined),
      reading_type: log.reading_type ?? log.context ?? 'FASTING',
      notes: log.notes ?? '',
    };
    const { data } = await apiClient.post('/health-logs/glucose/', payload);
    return data;
  },

  getBPLogs: async (limit = 30): Promise<BloodPressureLog[]> => {
    const { data } = await apiClient.get(`/health-logs/blood-pressure/?limit=${limit}`);
    return data.results || data;
  },

  getWeightLogs: async (limit = 30): Promise<WeightLog[]> => {
    const { data } = await apiClient.get(`/health-logs/weight/?limit=${limit}`);
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

