import { apiClient } from './client';

export interface EphemeralQRData {
  token: string;
  qr_data_uri: string;
  expires_at: string;
  ttl_seconds: number;
  permitted_scope: {
    documents: string;
    vitals_days: number;
  };
}

export interface DoctorScanResult {
  consultation_share_id: string;
  patient_name: string;
  patient_phone: string;
  patient_gender: string;
  patient_age?: number;
  brief_summary: {
    avg_glucose: number | null;
    avg_bp: string | null;
    danger_incidents: number;
    active_medications: Array<{ brand: string; generic: string; schedule: string }>;
    clinical_summary_bullets: string[];
  };
}

export const sharingApi = {
  generateQR: async (scope = { documents: 'all', vitals_days: 90 }): Promise<EphemeralQRData> => {
    const { data } = await apiClient.post('/sharing/qr/generate/', scope);
    return data.data || data;
  },

  revokeQR: async (shareId: string) => {
    const { data } = await apiClient.delete(`/sharing/${shareId}/revoke/`);
    return data;
  },

  scanQR: async (token: string): Promise<DoctorScanResult> => {
    const { data } = await apiClient.post('/sharing/scan/', { token });
    return data.data || data;
  },
};

