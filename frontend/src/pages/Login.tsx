import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { GraduationCap, Shield, School, ArrowRight, AlertCircle } from 'lucide-react';

export const Login: React.FC = () => {
  const { login } = useAuth();
  const navigate = useNavigate();

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      await login(username, password);
      // Determine redirection based on login response or refresh
      // AuthContext will have loaded current user
      // Give a tiny tick or navigate
      navigate('/');
    } catch (err: any) {
      setError(err.message || 'Login failed. Please check credentials.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-[85vh] flex items-center justify-center px-4 py-12">
      <div className="max-w-md w-full space-y-8">
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-indigo-600 text-white shadow-lg shadow-indigo-200 mb-4 font-bold text-2xl">
            Ψ
          </div>
          <h2 className="text-3xl font-extrabold text-slate-900 tracking-tight">
            Class Polling App
          </h2>
          <p className="mt-2 text-sm text-slate-600">
            Instructor & Administrator Access Portal
          </p>
        </div>

        <div className="bg-white p-8 rounded-2xl shadow-xl border border-slate-100">
          {error && (
            <div className="mb-6 p-4 rounded-xl bg-rose-50 border border-rose-200 flex items-start gap-3 text-rose-700 text-sm">
              <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-2">
                Username or Email
              </label>
              <input
                type="text"
                required
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="prof_smith or admin"
                className="w-full px-4 py-3 rounded-xl border border-slate-300 focus:ring-2 focus:ring-indigo-600 focus:border-indigo-600 text-sm outline-none transition-all"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-2">
                Password
              </label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                className="w-full px-4 py-3 rounded-xl border border-slate-300 focus:ring-2 focus:ring-indigo-600 focus:border-indigo-600 text-sm outline-none transition-all"
              />
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full py-3 px-4 rounded-xl text-white font-medium bg-indigo-600 hover:bg-indigo-700 shadow-md shadow-indigo-100 disabled:opacity-50 transition-all flex items-center justify-center gap-2"
            >
              {isSubmitting ? (
                <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
              ) : (
                <>
                  <span>Sign In</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>

          <div className="mt-8 pt-6 border-t border-slate-100 text-center space-y-3">
            <p className="text-xs text-slate-500 font-medium">Are you a student in class?</p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-3 text-xs">
              <Link
                to="/student/activate"
                className="w-full sm:w-auto px-4 py-2 bg-emerald-50 text-emerald-700 hover:bg-emerald-100 rounded-lg font-semibold flex items-center justify-center gap-1.5 transition-colors"
              >
                <School className="w-4 h-4" />
                Activate Student ID
              </Link>
              <Link
                to="/student/login"
                className="w-full sm:w-auto px-4 py-2 bg-slate-100 text-slate-700 hover:bg-slate-200 rounded-lg font-semibold flex items-center justify-center gap-1.5 transition-colors"
              >
                Student Sign In
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
