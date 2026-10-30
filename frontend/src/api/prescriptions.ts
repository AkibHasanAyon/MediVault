import { apiClient } from './client';

export interface PrescribedMedicine {
  brand_name: string;
  generic_name: string;
  strength: string;
  dosage_form: string;
  schedule_pattern: string; // e.g. 1+0+1
  instructions: string;
  duration_days: number;
}

export interface DrugInteractionResult {
  has_contraindications: boolean;
  requires_clinical_override: boolean;
  highest_severity: 'CONTRAINDICATED' | 'SEVERE' | 'MODERATE' | 'NONE';
  interactions: Array<{
    drug_a: string;
    drug_b: string;
    severity: 'CONTRAINDICATED' | 'SEVERE' | 'MODERATE' | 'INFO';
    description: string;
    recommendation: string;
  }>;
}

export interface CreatePrescriptionPayload {
  patient_id: string;
  clinic_id?: string;
  chief_complaints: string;
  clinical_findings?: string;
  diagnoses: string[];
  medications: PrescribedMedicine[];
  general_advice?: string;
  next_follow_up_days?: number;
  clinical_override_notes?: string;
}

export const prescriptionsApi = {
  checkInteractions: async (payload: {
    patient_id: string;
    drugs: Array<{ brand_name: string; generic_name: string }>;
  }): Promise<DrugInteractionResult> => {
    const { data } = await apiClient.post('/prescriptions/check-interactions/', payload);
    return data.data || data;
  },

  createPrescription: async (payload: CreatePrescriptionPayload) => {
    const { data } = await apiClient.post('/prescriptions/', payload);
    return data.data || data;
  },

  getPdfUrl: (prescriptionId: string) => {
    return `/api/v1/prescriptions/${prescriptionId}/pdf/`;
  },
};

