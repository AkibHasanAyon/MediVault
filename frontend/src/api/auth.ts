import { apiClient } from './client';

export interface UserProfile {
  id: string;
  phone_number: string;
  full_name: string;
  email: string | null;
  role: 'PATIENT' | 'DOCTOR' | 'ASSISTANT' | 'ADMIN';
  is_phone_verified: boolean;
  patient_profile_id?: string;
  doctor_profile_id?: string;
  assistant_profile_id?: string;
  clinic_id?: string;
  bmdc_number?: string;
}

export interface AuthTokens {
  access: string;
  refresh: string;
  user: UserProfile;
}

export interface RegisterPayload {
  email: string;
  full_name: string;
  role: 'PATIENT' | 'DOCTOR' | 'ASSISTANT';
  bmdc_number?: string;
  specialty?: string;
  phone_number?: string;
  gender?: string;
  blood_group?: string;
  date_of_birth?: string;
}

export const authApi = {
  requestOtp: async (identifier: string) => {
    const isEmail = identifier.includes('@');
    const payload = isEmail ? { email: identifier } : { phone_number: identifier };
    const { data } = await apiClient.post('/auth/otp/request/', payload);
    return data;
  },

  verifyOtp: async (identifier: string, otpCode: string): Promise<AuthTokens> => {
    const isEmail = identifier.includes('@');
    const payload = isEmail
      ? { email: identifier, otp_code: otpCode }
      : { phone_number: identifier, otp_code: otpCode };
    const { data } = await apiClient.post('/auth/otp/verify/', payload);
    return data.data ? data.data : data;
  },

  register: async (payload: RegisterPayload) => {
    const { data } = await apiClient.post('/auth/register/', payload);
    return data;
  },

  getProfile: async (): Promise<UserProfile> => {
    const { data } = await apiClient.get('/auth/profile/');
    return data.data ? data.data : data;
  },

  logout: async () => {
    const refreshToken = localStorage.getItem('refresh_token');
    if (refreshToken) {
      try {
        await apiClient.post('/auth/logout/', { refresh: refreshToken });
      } catch {
        // Ignore logout errors
      }
    }
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
  },
};
