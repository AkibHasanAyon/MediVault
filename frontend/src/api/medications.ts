import { apiClient } from './client';

export interface MedicationReminder {
  id: string;
  medication_id: string;
  brand_name: string;
  generic_name: string;
  strength: string;
  dose_time: string; // HH:MM:SS
  time_slot: 'MORNING' | 'NOON' | 'NIGHT';
  status: 'PENDING' | 'TAKEN' | 'SKIPPED' | 'SNOOZED';
  instructions: string;
  notification_enabled: boolean;
}

export interface TodayMedicationsResponse {
  date: string;
  adherence_percentage?: number;
  doses_taken?: number;
  total_scheduled?: number;
  total_doses?: number;
  doses?: any[];
  schedule?: {
    morning: MedicationReminder[];
    noon: MedicationReminder[];
    night: MedicationReminder[];
  };
}

export interface Medication {
  id: string;
  brand_name: string;
  generic_name: string;
  strength: string;
  dosage_form: string;
  schedule_pattern: string;
  instructions: string;
  is_active: boolean;
  provenance: 'PATIENT_ENTERED' | 'OCR_EXTRACTED' | 'CLINICIAN_AUTHORED';
  start_date: string;
}

export const medicationsApi = {
  getTodaySchedule: async (): Promise<TodayMedicationsResponse> => {
    const { data } = await apiClient.get('/medications/today/');
    return data.data || data;
  },

  logDoseStatus: async (reminderId: string, action: 'TAKEN' | 'SKIPPED' | 'SNOOZED', reason?: string) => {
    const { data } = await apiClient.post(`/medications/reminders/${reminderId}/action/`, {
      action,
      reason,
    });
    return data;
  },

  getActiveMedications: async (): Promise<Medication[]> => {
    const { data } = await apiClient.get('/medications/');
    return data.results || data;
  },
};

