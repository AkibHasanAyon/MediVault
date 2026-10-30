import React, { createContext, useContext, useState, useEffect } from 'react';
import { UserProfile, RegisterPayload, authApi } from '../api/auth';

interface AuthContextType {
  user: UserProfile | null;
  role: 'PATIENT' | 'DOCTOR' | 'ASSISTANT' | 'ADMIN' | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  loginWithOtp: (identifier: string, otp: string) => Promise<void>;
  register: (payload: RegisterPayload) => Promise<void>;
  devLoginAs: (role: 'PATIENT' | 'DOCTOR' | 'ASSISTANT') => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserProfile | null>(() => {
    const saved = localStorage.getItem('user');
    return saved ? JSON.parse(saved) : null;
  });
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    const initAuth = async () => {
      const token = localStorage.getItem('access_token');
      if (token) {
        try {
          const profile = await authApi.getProfile();
          setUser(profile);
          localStorage.setItem('user', JSON.stringify(profile));
        } catch {
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          localStorage.removeItem('user');
          setUser(null);
        }
      }
      setIsLoading(false);
    };

    initAuth();
  }, []);

  const loginWithOtp = async (identifier: string, otp: string) => {
    setIsLoading(true);
    try {
      const tokens = await authApi.verifyOtp(identifier, otp);
      if (tokens.access) {
        localStorage.setItem('access_token', tokens.access);
      }
      if (tokens.refresh) {
        localStorage.setItem('refresh_token', tokens.refresh);
      }
      if (tokens.user) {
        localStorage.setItem('user', JSON.stringify(tokens.user));
        setUser(tokens.user);
      }
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (payload: RegisterPayload) => {
    setIsLoading(true);
    try {
      await authApi.register(payload);
    } finally {
      setIsLoading(false);
    }
  };

  const devLoginAs = async (targetRole: 'PATIENT' | 'DOCTOR' | 'ASSISTANT') => {
    setIsLoading(true);
    try {
      const emailMap = {
        PATIENT: 'patient@medivault.app',
        DOCTOR: 'doctor@medivault.app',
        ASSISTANT: 'assistant@medivault.app',
      };
      const email = emailMap[targetRole];

      await authApi.requestOtp(email);
      await loginWithOtp(email, '123456');
    } catch {
      // Fallback simulated profile if offline dev without db otp
      const simulated: UserProfile = {
        id: 'dev-user-id',
        phone_number: targetRole === 'DOCTOR' ? '+8801711000002' : targetRole === 'ASSISTANT' ? '+8801711000003' : '+8801711000011',
        full_name: targetRole === 'DOCTOR' ? 'Prof. Dr. M. A. Hasan' : targetRole === 'ASSISTANT' ? 'Fatima Akter' : 'Abdul Karim',
        email: `${targetRole.toLowerCase()}@medivault.app`,
        role: targetRole,
        is_phone_verified: true,
      };
      localStorage.setItem('user', JSON.stringify(simulated));
      setUser(simulated);
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    setIsLoading(true);
    try {
      await authApi.logout();
    } finally {
      setUser(null);
      setIsLoading(false);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        role: user ? user.role : null,
        isAuthenticated: !!user,
        isLoading,
        loginWithOtp,
        register,
        devLoginAs,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
