import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { Navbar } from './components/Navbar';
import { ProtectedRoute } from './components/ProtectedRoute';
import { Login } from './pages/Login';
import { StudentActivation } from './pages/StudentActivation';
import { StudentLogin } from './pages/StudentLogin';
import { StudentSession } from './pages/StudentSession';
import { ProfessorDashboard } from './pages/ProfessorDashboard';
import { ProfessorSessionView } from './pages/ProfessorSessionView';
import { ProfessorQuestionView } from './pages/ProfessorQuestionView';
import { AdminDashboard } from './pages/AdminDashboard';
import { NotFound } from './pages/NotFound';

const RootRedirect: React.FC = () => {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (user.role === 'STUDENT') {
    return <Navigate to="/student" replace />;
  } else if (user.role === 'ADMIN') {
    return <Navigate to="/admin" replace />;
  } else {
    return <Navigate to="/professor" replace />;
  }
};

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <BrowserRouter>
        <div className="min-h-screen flex flex-col bg-slate-50 font-sans selection:bg-indigo-500 selection:text-white">
          <Navbar />
          <main className="flex-1">
            <Routes>
              {/* Public Auth Routes */}
              <Route path="/login" element={<Login />} />
              <Route path="/activate" element={<Navigate to="/student/activate" replace />} />
              <Route path="/student/activate" element={<StudentActivation />} />
              <Route path="/student/login" element={<StudentLogin />} />

              {/* Student Routes */}
              <Route
                path="/student"
                element={
                  <ProtectedRoute allowedRoles={['STUDENT']}>
                    <StudentSession />
                  </ProtectedRoute>
                }
              />

              {/* Professor Routes */}
              <Route
                path="/professor"
                element={
                  <ProtectedRoute allowedRoles={['PROFESSOR']}>
                    <ProfessorDashboard />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/professor/sessions/:sessionId"
                element={
                  <ProtectedRoute allowedRoles={['PROFESSOR']}>
                    <ProfessorSessionView />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/professor/sessions/:sessionId/questions/:questionId"
                element={
                  <ProtectedRoute allowedRoles={['PROFESSOR']}>
                    <ProfessorQuestionView />
                  </ProtectedRoute>
                }
              />

              {/* Admin Routes */}
              <Route
                path="/admin"
                element={
                  <ProtectedRoute allowedRoles={['ADMIN']}>
                    <AdminDashboard />
                  </ProtectedRoute>
                }
              />

              {/* Default Home / Role Gateway */}
              <Route path="/" element={<RootRedirect />} />
              <Route path="*" element={<NotFound />} />
            </Routes>
          </main>
        </div>
      </BrowserRouter>
    </AuthProvider>
  );
};

export default App;
