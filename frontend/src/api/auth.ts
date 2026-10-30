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

export const authApi = {
  requestOtp: async (phoneNumber: string) => {
    const { data } = await apiClient.post('/auth/otp/request/', { phone_number: phoneNumber });
    return data;
  },

  verifyOtp: async (phoneNumber: string, otpCode: string): Promise<AuthTokens> => {
    const { data } = await apiClient.post('/auth/otp/verify/', {
      phone_number: phoneNumber,
      otp_code: otpCode,
    });
    return data;
  },

  getProfile: async (): Promise<UserProfile> => {
    const { data } = await apiClient.get('/auth/profile/');
    return data;
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

