import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { ProtectedRoute } from './ProtectedRoute';
import { LoginPage } from '../pages/auth/LoginPage';
import { PatientDashboard } from '../pages/patient/PatientDashboard';
import { DoctorChamberPage } from '../pages/doctor/DoctorChamberPage';
import { AssistantDeskPage } from '../pages/assistant/AssistantDeskPage';
import { WaitingRoomTvPage } from '../pages/display/WaitingRoomTvPage';

export const AppRoutes: React.FC = () => {
  const { user, isAuthenticated } = useAuth();

  return (
    <Routes>
      {/* Public Routes */}
      <Route path="/login" element={<LoginPage />} />
      <Route path="/display/:clinicId" element={<WaitingRoomTvPage />} />
      <Route path="/display" element={<WaitingRoomTvPage />} />

      {/* Patient Portal */}
      <Route element={<ProtectedRoute allowedRoles={['PATIENT']} />}>
        <Route path="/patient" element={<PatientDashboard />} />
      </Route>

      {/* Doctor Chamber */}
      <Route element={<ProtectedRoute allowedRoles={['DOCTOR']} />}>
        <Route path="/doctor" element={<DoctorChamberPage />} />
      </Route>

      {/* Assistant Desk */}
      <Route element={<ProtectedRoute allowedRoles={['ASSISTANT', 'ADMIN']} />}>
        <Route path="/assistant" element={<AssistantDeskPage />} />
      </Route>

      {/* Root Redirection */}
      <Route
        path="/"
        element={
          isAuthenticated && user ? (
            user.role === 'PATIENT' ? (
              <Navigate to="/patient" replace />
            ) : user.role === 'DOCTOR' ? (
              <Navigate to="/doctor" replace />
            ) : (
              <Navigate to="/assistant" replace />
            )
          ) : (
            <Navigate to="/login" replace />
          )
        }
      />

      {/* Fallback */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
};

