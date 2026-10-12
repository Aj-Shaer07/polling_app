import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { LogOut, Shield, GraduationCap, School } from 'lucide-react';

export const Navbar: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [backendWaking, setBackendWaking] = useState(false);

  useEffect(() => {
    const handler = (e: Event) => {
      const custom = e as CustomEvent<{ waking: boolean }>;
      setBackendWaking(Boolean(custom.detail?.waking));
    };
    window.addEventListener('bst_backend_waking', handler);
    return () => window.removeEventListener('bst_backend_waking', handler);
  }, []);

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-30 shadow-sm">
      {backendWaking && (
        <div className="bg-amber-50 border-b border-amber-200 px-4 py-1.5 text-center text-xs font-medium text-amber-800 flex items-center justify-center gap-2">
          <span className="w-2 h-2 rounded-full bg-amber-500 animate-ping"></span>
          <span>Classroom backend is waking up from sleep on Render — retrying automatically...</span>
        </div>
      )}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <Link to="/" className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-indigo-600 flex items-center justify-center text-white font-bold text-xl shadow-md">
            Ψ
          </div>
          <div>
            <span className="font-bold text-lg text-slate-900 tracking-tight flex items-center gap-2">
              Class Polling App
            </span>
            <span className="text-xs text-slate-500 hidden sm:block">
              AI-Powered Live Classroom Diagnostic
            </span>
          </div>
        </Link>

        {user && (
          <div className="flex items-center space-x-4">
            <div className="hidden sm:flex items-center space-x-2 px-3 py-1 bg-slate-100 rounded-full text-xs font-medium text-slate-700">
              {user.role === 'ADMIN' && <Shield className="w-3.5 h-3.5 text-rose-600" />}
              {user.role === 'PROFESSOR' && <GraduationCap className="w-3.5 h-3.5 text-indigo-600" />}
              {user.role === 'STUDENT' && <School className="w-3.5 h-3.5 text-emerald-600" />}
              <span>{user.student_id ? user.student_id : user.username}</span>
              <span className="text-slate-400">|</span>
              <span className="font-semibold">{user.role}</span>
            </div>

            <button
              onClick={handleLogout}
              className="flex items-center space-x-1.5 px-3 py-1.5 text-sm font-medium text-slate-600 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors"
              title="Logout"
            >
              <LogOut className="w-4 h-4" />
              <span className="hidden sm:inline">Logout</span>
            </button>
          </div>
        )}
      </div>
    </header>
  );
};
