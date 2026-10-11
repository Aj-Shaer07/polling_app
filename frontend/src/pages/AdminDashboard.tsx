import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { EligibleStudentResponse, User, AuditLogResponse } from '../types';
import {
  Shield,
  Users,
  UserPlus,
  RefreshCw,
  FileSpreadsheet,
  CheckCircle2,
  Clock,
  AlertCircle,
  RotateCcw,
} from 'lucide-react';

export const AdminDashboard: React.FC = () => {
  const [roster, setRoster] = useState<EligibleStudentResponse[]>([]);
  const [professors, setProfessors] = useState<User[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLogResponse[]>([]);

  // Create Professor form
  const [showProfForm, setShowProfForm] = useState(false);
  const [profUsername, setProfUsername] = useState('');
  const [profEmail, setProfEmail] = useState('');
  const [profPassword, setProfPassword] = useState('');

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const handleResetActivation = async (studentId: string) => {
    if (!window.confirm(`Reset activation for student ${studentId}? This clears their password and allows them to register freshly.`)) {
      return;
    }
    setError(null);
    setSuccess(null);
    try {
      await api.resetStudentActivation(studentId);
      setSuccess(`Activation for ${studentId} successfully reset. The student can now re-activate at /student/activate.`);
      await loadAdminData();
    } catch (err: any) {
      setError(err.message || `Failed to reset activation for ${studentId}.`);
    }
  };

  const loadAdminData = async () => {
    try {
      setLoading(true);
      const [rData, pData, aData] = await Promise.all([
        api.getRoster(),
        api.listProfessors(),
        api.getAuditLogs(50),
      ]);
      setRoster(rData);
      setProfessors(pData);
      setAuditLogs(aData);
    } catch (err: any) {
      setError(err.message || 'Failed to load administrator data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAdminData();
  }, []);

  const handleBootstrapRoster = async (force: boolean) => {
    setError(null);
    setSuccess(null);
    try {
      const res = await api.bootstrapRoster(force);
      setSuccess(`Successfully initialized all ${res.total_eligible} eligible students! Students can now set their passwords directly at /activate.`);
      await loadAdminData();
    } catch (err: any) {
      setError(err.message || 'Failed to initialize roster.');
    }
  };

  const handleCreateProfessor = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    try {
      await api.createProfessor({
        username: profUsername.trim(),
        email: profEmail.trim(),
        password: profPassword,
      });
      setShowProfForm(false);
      setProfUsername('');
      setProfEmail('');
      setProfPassword('');
      setSuccess('Professor account successfully created.');
      await loadAdminData();
    } catch (err: any) {
      setError(err.message || 'Failed to create professor.');
    }
  };

  const activatedCount = roster.filter((s) => s.is_activated).length;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <Shield className="w-7 h-7 text-rose-600" />
            System Administration
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            45-Student Eligible Roster, Instructor Provisioning, and Audit Trails
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => handleBootstrapRoster(false)}
            className="flex items-center gap-1.5 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-xl shadow-md transition-all"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Initialize 45 Roster</span>
          </button>
          <button
            onClick={() => setShowProfForm(true)}
            className="flex items-center gap-1.5 px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold rounded-xl shadow-md transition-all"
          >
            <UserPlus className="w-3.5 h-3.5" />
            <span>New Professor</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 flex items-start gap-3 text-rose-700 text-sm">
          <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
          <span>{error}</span>
        </div>
      )}

      {success && (
        <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 flex items-start gap-3 text-emerald-700 text-sm">
          <CheckCircle2 className="w-5 h-5 flex-shrink-0 mt-0.5" />
          <span>{success}</span>
        </div>
      )}

      {/* 3 Metric Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Eligible Roster</span>
            <Users className="w-5 h-5 text-indigo-600" />
          </div>
          <div className="text-3xl font-extrabold text-slate-900 mt-2">
            {roster.length} / 45
          </div>
          <p className="text-xs text-slate-500 mt-1">
            241AI001–241AI044 + 231AI007
          </p>
        </div>

        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Activated Identities</span>
            <CheckCircle2 className="w-5 h-5 text-emerald-600" />
          </div>
          <div className="text-3xl font-extrabold text-emerald-700 mt-2">
            {activatedCount} <span className="text-sm font-normal text-slate-400">/ 45</span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            {roster.length > 0 ? Math.round((activatedCount / roster.length) * 100) : 0}% activation rate
          </p>
        </div>

        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Instructors</span>
            <Users className="w-5 h-5 text-indigo-600" />
          </div>
          <div className="text-3xl font-extrabold text-slate-900 mt-2">
            {professors.length}
          </div>
          <p className="text-xs text-slate-500 mt-1">Active professor accounts</p>
        </div>
      </div>

      {/* Roster & Audit Tables */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Left: 45 Eligible Students */}
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-slate-900 text-base">Eligible Student Roster</h3>
            <span className="text-xs font-semibold px-2 py-0.5 bg-slate-100 rounded-full">
              Fixed 45 Students
            </span>
          </div>

          <div className="max-h-96 overflow-y-auto divide-y divide-slate-100 pr-1">
            {roster.map((s) => (
              <div key={s.id} className="py-2.5 flex items-center justify-between text-xs">
                <span className="font-mono font-bold text-slate-800">{s.student_id}</span>
                <div className="flex items-center gap-2">
                  <span
                    className={`px-2 py-0.5 rounded-full font-semibold text-[10px] ${
                      s.is_activated
                        ? 'bg-emerald-100 text-emerald-800'
                        : 'bg-slate-100 text-slate-600'
                    }`}
                  >
                    {s.is_activated ? 'Activated' : 'Unactivated'}
                  </span>
                  {s.activated_at && (
                    <span className="text-[10px] text-slate-400">
                      {new Date(s.activated_at).toLocaleDateString()}
                    </span>
                  )}
                  {s.is_activated && (
                    <button
                      onClick={() => handleResetActivation(s.student_id)}
                      title="Reset activation to allow student to re-register"
                      className="px-2 py-0.5 rounded text-[10px] font-semibold bg-rose-50 text-rose-600 hover:bg-rose-100 transition-colors flex items-center gap-1 border border-rose-200"
                    >
                      <RotateCcw className="w-2.5 h-2.5" />
                      <span>Reset</span>
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right: Audit Trail */}
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-4">
          <h3 className="font-bold text-slate-900 text-base">Security Audit Logs</h3>
          <div className="max-h-96 overflow-y-auto divide-y divide-slate-100 pr-1">
            {auditLogs.map((log) => (
              <div key={log.id} className="py-2.5 space-y-1 text-xs">
                <div className="flex items-center justify-between">
                  <span className="font-mono font-bold text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded text-[10px]">
                    {log.action}
                  </span>
                  <span className="text-[10px] text-slate-400">
                    {new Date(log.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </span>
                </div>
                <div className="text-slate-600 text-[11px] flex items-center gap-2">
                  <span>Resource: <strong>{log.resource_type}</strong></span>
                  {log.user_id && <span>• User: <code className="text-[10px]">{log.user_id.slice(0, 8)}</code></span>}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* New Professor Modal */}
      {showProfForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-100 space-y-4">
            <h3 className="font-bold text-slate-900 text-lg">Create Professor Account</h3>
            <form onSubmit={handleCreateProfessor} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                  Username
                </label>
                <input
                  type="text"
                  required
                  value={profUsername}
                  onChange={(e) => setProfUsername(e.target.value)}
                  placeholder="prof_smith"
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 text-sm outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                  Email
                </label>
                <input
                  type="email"
                  required
                  value={profEmail}
                  onChange={(e) => setProfEmail(e.target.value)}
                  placeholder="smith@university.edu"
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 text-sm outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                  Initial Password
                </label>
                <input
                  type="password"
                  required
                  minLength={8}
                  value={profPassword}
                  onChange={(e) => setProfPassword(e.target.value)}
                  placeholder="At least 8 characters"
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 text-sm outline-none"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowProfForm(false)}
                  className="px-4 py-2 text-sm text-slate-600 hover:bg-slate-100 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold rounded-lg shadow-md"
                >
                  Create Professor
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
