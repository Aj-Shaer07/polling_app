import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { ClassroomSession } from '../types';
import { QRModal } from '../components/QRModal';
import {
  Plus,
  Play,
  QrCode,
  Calendar,
  Users,
  AlertCircle,
  GraduationCap,
  ChevronRight,
} from 'lucide-react';

export const ProfessorDashboard: React.FC = () => {
  const navigate = useNavigate();
  const [sessions, setSessions] = useState<ClassroomSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // New session modal
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [title, setTitle] = useState('');
  const [isCreating, setIsCreating] = useState(false);

  // QR modal
  const [qrModalSession, setQrModalSession] = useState<ClassroomSession | null>(null);

  const loadSessions = async () => {
    try {
      setLoading(true);
      const data = await api.listSessions();
      setSessions(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load sessions.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSessions();
  }, []);

  const handleCreateSession = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;
    setIsCreating(true);
    try {
      const newSession = await api.createSession(title.trim());
      setIsModalOpen(false);
      setTitle('');
      navigate(`/professor/sessions/${newSession.id}`);
    } catch (err: any) {
      setError(err.message || 'Failed to create session.');
    } finally {
      setIsCreating(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <GraduationCap className="w-7 h-7 text-indigo-600" />
            Instructor Dashboard
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Manage live classroom diagnostic sessions and stress-test student beliefs
          </p>
        </div>

        <button
          onClick={() => setIsModalOpen(true)}
          className="flex items-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-xl shadow-md shadow-indigo-100 transition-all self-start sm:self-auto"
        >
          <Plus className="w-5 h-5" />
          <span>New Session</span>
        </button>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 flex items-start gap-3 text-rose-700 text-sm">
          <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
          <span>{error}</span>
        </div>
      )}

      {/* Session Cards */}
      {loading ? (
        <div className="py-16 text-center">
          <div className="w-10 h-10 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin mx-auto mb-3"></div>
          <p className="text-sm text-slate-500 font-medium">Loading classroom sessions...</p>
        </div>
      ) : sessions.length === 0 ? (
        <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center space-y-4">
          <div className="w-16 h-16 bg-indigo-50 rounded-2xl flex items-center justify-center text-indigo-600 mx-auto">
            <Calendar className="w-8 h-8" />
          </div>
          <h3 className="text-lg font-bold text-slate-900">No sessions yet</h3>
          <p className="text-sm text-slate-500 max-w-sm mx-auto">
            Create your first session to generate a unique join code and launch real-time reasoning diagnostics.
          </p>
          <button
            onClick={() => setIsModalOpen(true)}
            className="px-5 py-2.5 bg-indigo-600 text-white font-medium rounded-xl hover:bg-indigo-700 transition-all shadow-md"
          >
            Create First Session
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {sessions.map((sess) => (
            <div
              key={sess.id}
              className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm hover:shadow-md transition-shadow flex flex-col justify-between space-y-4"
            >
              <div>
                <div className="flex items-center justify-between mb-3">
                  <span
                    className={`px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                      sess.status.startsWith('OPEN')
                        ? 'bg-emerald-100 text-emerald-800 animate-pulse'
                        : sess.status === 'COMPLETED'
                        ? 'bg-slate-100 text-slate-700'
                        : 'bg-indigo-50 text-indigo-700'
                    }`}
                  >
                    {sess.status.replace(/_/g, ' ')}
                  </span>
                  <button
                    onClick={() => setQrModalSession(sess)}
                    className="p-1.5 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors"
                    title="View QR Code & Link"
                  >
                    <QrCode className="w-5 h-5" />
                  </button>
                </div>

                <h3 className="font-bold text-slate-900 text-lg line-clamp-1">{sess.title}</h3>
                <div className="mt-2 flex items-center gap-3 text-xs text-slate-500 font-mono">
                  <span>Code: <strong className="text-indigo-600 tracking-wider text-sm">{sess.join_code}</strong></span>
                  <span>•</span>
                  <span>{new Date(sess.created_at).toLocaleDateString()}</span>
                </div>
              </div>

              <div className="pt-4 border-t border-slate-100 flex items-center justify-between">
                <span className="text-xs text-slate-400">45 Eligible Students</span>
                <button
                  onClick={() => navigate(`/professor/sessions/${sess.id}`)}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-900 hover:bg-indigo-600 text-white text-xs font-semibold rounded-lg transition-colors"
                >
                  <Play className="w-3.5 h-3.5" />
                  <span>Launch Control</span>
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create Session Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-100">
            <h3 className="text-lg font-bold text-slate-900 mb-1">Create Classroom Session</h3>
            <p className="text-xs text-slate-500 mb-4">
              Enter a lecture or topic title. A secure 6-character join code and QR code will be generated.
            </p>

            <form onSubmit={handleCreateSession} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
                  Session Topic Title
                </label>
                <input
                  type="text"
                  required
                  autoFocus
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="e.g. Vickrey Second-Price Auction Theory"
                  className="w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-indigo-600 text-sm outline-none"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 text-sm text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isCreating || !title.trim()}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold rounded-lg shadow-md disabled:opacity-50"
                >
                  {isCreating ? 'Creating...' : 'Create & Open'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* QR Modal */}
      {qrModalSession && (
        <QRModal
          isOpen={true}
          onClose={() => setQrModalSession(null)}
          sessionTitle={qrModalSession.title}
          joinCode={qrModalSession.join_code}
        />
      )}
    </div>
  );
};
