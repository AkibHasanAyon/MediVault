import { apiClient } from './client';

export interface DocumentEntity {
  id: string;
  category: 'MEDICATION' | 'LAB_TEST' | 'DIAGNOSIS';
  raw_text: string;
  normalized_name: string;
  numerical_value: number | null;
  unit: string | null;
  reference_range: string | null;
  confidence_score: number;
}

export interface MedicalDocument {
  id: string;
  patient_id: string;
  title: string;
  document_type: 'PRESCRIPTION' | 'LAB_REPORT' | 'DISCHARGE_SUMMARY' | 'OTHER';
  document_date: string;
  file_url: string;
  ocr_raw_text?: string;
  processing_status: 'UPLOADED' | 'PROCESSING_OCR' | 'EXTRACTION_COMPLETE' | 'FAILED';
  is_patient_confirmed: boolean;
  extracted_entities: DocumentEntity[];
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

