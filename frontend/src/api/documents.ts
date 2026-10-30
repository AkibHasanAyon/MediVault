import { apiClient } from './client';

export interface DocumentEntity {
  id: string;
  entity_type?: 'MEDICATION' | 'LAB_TEST' | 'DIAGNOSIS' | 'ALLERGY' | 'ADVICE';
  category?: 'MEDICATION' | 'LAB_TEST' | 'DIAGNOSIS';
  entity_name?: string;
  normalized_name?: string;
  raw_text?: string;
  raw_snippet?: string;
  entity_value?: string;
  numerical_value?: number | null;
  unit?: string | null;
  reference_range?: string | null;
  is_abnormal?: boolean;
  confidence_score?: number;
  provenance?: string;
}

export interface MedicalDocument {
  id: string;
  patient_id?: string;
  title: string;
  document_type: 'PRESCRIPTION' | 'LAB_REPORT' | 'DISCHARGE' | 'DISCHARGE_SUMMARY' | 'RADIOLOGY' | 'OTHER';
  document_date: string;
  file_url: string;
  issuing_doctor_name?: string;
  issuing_clinic_name?: string;
  raw_ocr_text?: string;
  ocr_raw_text?: string;
  processing_status: 'PENDING' | 'PROCESSING_OCR' | 'EXTRACTING_AI' | 'COMPLETED' | 'FAILED' | 'UPLOADED' | 'EXTRACTION_COMPLETE';
  user_confirmed?: boolean;
  is_patient_confirmed?: boolean;
  extracted_entities?: DocumentEntity[];
  medication_count?: number;
  lab_test_count?: number;
  diagnosis_count?: number;
  created_at: string;
}

export const documentsApi = {
  getTimeline: async (type?: string): Promise<MedicalDocument[]> => {
    const url = type ? `/documents/?type=${type}` : '/documents/';
    const { data } = await apiClient.get(url);
    return data.results || data;
  },

  getDocument: async (id: string): Promise<MedicalDocument> => {
    const { data } = await apiClient.get(`/documents/${id}/`);
    return data;
  },

  uploadDocument: async (formData: FormData): Promise<MedicalDocument> => {
    const { data } = await apiClient.post('/documents/upload/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return data.data || data;
  },

  confirmDocument: async (id: string) => {
    const { data } = await apiClient.post(`/documents/${id}/confirm/`);
    return data;
  },
};

