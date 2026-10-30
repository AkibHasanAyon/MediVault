import { apiClient } from './client';

export interface QueueEntry {
  id: string;
  clinic: string;
  clinic_name: string;
  doctor: string;
  doctor_name: string;
  doctor_specialties: string;
  patient: string;
  patient_name: string;
  patient_phone: string;
  family_member_name?: string | null;
  token_number: number;
  token_display: string;
  queue_date: string;
  state: 'WAITING' | 'CALLED_IN' | 'IN_CHAMBER' | 'DONE' | 'SKIPPED' | 'NO_SHOW';
  estimated_wait_minutes: number;
  called_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface DoctorLiveQueue {
  success: boolean;
  date: string;
  doctor_name: string;
  current_patient: QueueEntry | null;
  called_patient: QueueEntry | null;
  next_waiting: QueueEntry[];
  stats: {
    total_registered: number;
    waiting_count: number;
    in_consultation: number;
    completed_count: number;
    skipped_count: number;
  };
}

export interface ChamberDisplay {
  doctor_id: string;
  doctor_name: string;
  specialties: string;
  chamber_number: string;
  current_token: string;
  current_state: string;
  upcoming_tokens: string[];
  waiting_count: number;
}

export interface ClinicDisplayResponse {
  success: boolean;
  clinic_name: string;
  branch: string;
  date: string;
  chambers: ChamberDisplay[];
}

export interface DailyQueueSummary {
  success: boolean;
  date: string;
  metrics: {
    total_registered: number;
    total_completed: number;
    total_waiting: number;
    total_in_chamber: number;
    total_skipped: number;
    total_no_show: number;
    avg_wait_minutes: number;
    avg_consultation_minutes: number;
    no_show_rate_percent: number;
  };
}

export const queueApi = {
  // Assistant Desk
  assignToken: async (payload: {
    patient_phone: string;
    patient_name?: string;
    doctor_id: string;
    clinic_id?: string;
    gender?: string;
  }): Promise<{ data: QueueEntry; position_in_queue: number; estimated_wait_minutes: number }> => {
    const { data } = await apiClient.post('/assistant/queue/assign-token/', payload);
    return data;
  },

  getTodayQueue: async (clinicId?: string, doctorId?: string): Promise<QueueEntry[]> => {
    const params = new URLSearchParams();
    if (clinicId) params.append('clinic_id', clinicId);
    if (doctorId) params.append('doctor_id', doctorId);
    const { data } = await apiClient.get(`/assistant/queue/today/?${params.toString()}`);
    return data.data || [];
  },

  updateStatus: async (entryId: string, state: QueueEntry['state']): Promise<QueueEntry> => {
    const { data } = await apiClient.patch(`/assistant/queue/${entryId}/status/`, { state });
    return data.data;
  },

  getDailySummary: async (clinicId?: string): Promise<DailyQueueSummary> => {
    const url = clinicId ? `/assistant/queue/daily-summary/?clinic_id=${clinicId}` : '/assistant/queue/daily-summary/';
    const { data } = await apiClient.get(url);
    return data;
  },

  // Doctor Chamber
  getDoctorLiveQueue: async (): Promise<DoctorLiveQueue> => {
    const { data } = await apiClient.get('/doctor/queue/live/');
    return data;
  },

  doctorCallNext: async (entryId?: string) => {
    const { data } = await apiClient.post('/doctor/queue/call-next/', { entry_id: entryId });
    return data;
  },

  doctorStartConsultation: async (entryId: string) => {
    const { data } = await apiClient.post(`/doctor/queue/${entryId}/start-consultation/`);
    return data;
  },

  doctorFinishConsultation: async (entryId: string) => {
    const { data } = await apiClient.post(`/doctor/queue/${entryId}/finish-consultation/`);
    return data;
  },

  doctorSkipPatient: async (entryId: string) => {
    const { data } = await apiClient.post(`/doctor/queue/${entryId}/skip/`);
    return data;
  },

  // TV / Public Display
  getClinicDisplay: async (clinicId: string): Promise<ClinicDisplayResponse> => {
    const { data } = await apiClient.get(`/queue/display/${clinicId}/`);
    return data;
  },
};

