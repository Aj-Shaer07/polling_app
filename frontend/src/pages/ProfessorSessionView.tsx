import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { api } from '../api/client';
import { SessionWebSocket } from '../api/ws';
import {
  ClassroomSession,
  Question,
  QuestionType,
  ParticipationDashboard,
  SessionStatus,
} from '../types';
import { QRModal } from '../components/QRModal';
import {
  QrCode,
  Users,
  Plus,
  ArrowRight,
  CheckCircle,
  AlertCircle,
  HelpCircle,
  Trash2,
  RefreshCw,
  Power,
  RotateCcw,
  Layers,
  Sparkles,
  Edit3,
} from 'lucide-react';
import { QuestionModal } from '../components/QuestionModal';

export const ProfessorSessionView: React.FC = () => {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();

  const [session, setSession] = useState<ClassroomSession | null>(null);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [participation, setParticipation] = useState<ParticipationDashboard | null>(null);

  // Modals & form state
  const [isQrOpen, setIsQrOpen] = useState(false);
  const [showQuestionForm, setShowQuestionForm] = useState(false);
  const [editingQuestion, setEditingQuestion] = useState<Question | null>(null);

  // Attendance filter
  const [rosterFilter, setRosterFilter] = useState<'ALL' | 'JOINED' | 'NOT_JOINED'>('ALL');

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const refreshSessionData = async () => {
    if (!sessionId) return;
    try {
      const [sess, part, qList] = await Promise.all([
        api.getSession(sessionId),
        api.getParticipation(sessionId),
        api.getSessionQuestions(sessionId),
      ]);
      setSession(sess);
      setParticipation(part);
      setQuestions(qList);
    } catch (err: any) {
      setError(err.message || 'Failed to refresh session data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refreshSessionData();

    if (sessionId) {
      const ws = new SessionWebSocket(sessionId);
      ws.on('participant_joined', () => refreshSessionData());
      ws.on('response_recorded', () => refreshSessionData());
      ws.on('question_status_changed', () => refreshSessionData());
      ws.on('status_changed', () => refreshSessionData());
      return () => ws.destroy();
    }
  }, [sessionId]);

  const handleToggleEndSession = async () => {
    if (!sessionId || !session) return;
    setError(null);
    setSuccess(null);
    try {
      const targetStatus: SessionStatus =
        session.status === 'COMPLETED' ? 'OPEN_ROUND_1' : 'COMPLETED';
      await api.updateSessionStatus(sessionId, targetStatus);
      setSuccess(
        targetStatus === 'COMPLETED'
          ? 'Classroom lecture session has been ended.'
          : 'Lecture session resumed!'
      );
      await refreshSessionData();
    } catch (err: any) {
      setError(err.message || 'Failed to update session status.');
    }
  };

  const handleSaveQuestion = async (data: any) => {
    if (!sessionId) return;
    setError(null);
    setSuccess(null);

    try {
      if (editingQuestion) {
        await api.updateQuestion(editingQuestion.id, data);
        setSuccess(`Question #${editingQuestion.order_index} updated successfully!`);
      } else {
        const created = await api.createQuestion(sessionId, data);
        setSuccess(`Question #${created.order_index} successfully added!`);
      }
      setShowQuestionForm(false);
      setEditingQuestion(null);
      await refreshSessionData();
    } catch (err: any) {
      setError(err.message || 'Failed to save question.');
      throw err;
    }
  };

  const handleDeleteQuestion = async (qId: string, qOrder: number) => {
    if (!window.confirm(`Delete Question #${qOrder}? All responses for this question will be deleted.`)) {
      return;
    }
    setError(null);
    try {
      await api.deleteQuestion(qId);
      setSuccess(`Question #${qOrder} deleted.`);
      await refreshSessionData();
    } catch (err: any) {
      setError(err.message || 'Failed to delete question.');
    }
  };

  if (loading) {
    return (
      <div className="min-h-[70vh] flex items-center justify-center">
        <div className="w-10 h-10 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  if (!session) {
    return (
      <div className="max-w-4xl mx-auto py-12 text-center space-y-4">
        <AlertCircle className="w-12 h-12 text-rose-500 mx-auto" />
        <h2 className="text-xl font-bold text-slate-800">Session Not Found</h2>
        <Link
          to="/professor"
          className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-xl text-sm font-semibold"
        >
          <span>Return to Dashboard</span>
        </Link>
      </div>
    );
  }

  const isCompleted = session.status === 'COMPLETED';
  const joinedCount = participation?.joined_count || 0;
  const eligibleTotal = participation?.eligible_total || 45;

  const filteredStudents = (participation?.students || []).filter((s) => {
    if (rosterFilter === 'JOINED') return s.joined;
    if (rosterFilter === 'NOT_JOINED') return !s.joined;
    return true;
  });

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      {/* Top Header Card */}
      <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1.5">
          <div className="flex items-center gap-3">
            <span
              className={`px-3 py-0.5 rounded-full text-xs font-bold uppercase tracking-wider ${
                isCompleted
                  ? 'bg-slate-100 text-slate-700'
                  : 'bg-emerald-100 text-emerald-800 animate-pulse'
              }`}
            >
              {isCompleted ? 'Session Completed' : 'Session Active'}
            </span>

            <button
              onClick={() => setIsQrOpen(true)}
              className="flex items-center gap-1.5 px-3 py-1 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 text-xs font-bold rounded-full transition-colors font-mono"
            >
              <QrCode className="w-3.5 h-3.5" />
              <span>JOIN CODE: {session.join_code}</span>
            </button>
          </div>

          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
            {session.title}
          </h1>
          <p className="text-xs text-slate-500">
            Instructor classroom session • Students join via code or QR to participate in questions.
          </p>
        </div>

        {/* Top Controls: End/Resume Session & Add Question */}
        <div className="flex flex-wrap items-center gap-2.5">
          <button
            onClick={() => setShowQuestionForm(true)}
            className="flex items-center gap-1.5 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold rounded-xl shadow-md transition-all"
          >
            <Plus className="w-4 h-4" />
            <span>Add New Question</span>
          </button>

          <button
            onClick={handleToggleEndSession}
            className={`flex items-center gap-1.5 px-4 py-2.5 text-xs font-bold rounded-xl transition-all shadow-sm ${
              isCompleted
                ? 'bg-emerald-600 hover:bg-emerald-700 text-white'
                : 'bg-slate-900 hover:bg-slate-800 text-white'
            }`}
          >
            {isCompleted ? (
              <>
                <RotateCcw className="w-3.5 h-3.5" />
                <span>Reopen Session</span>
              </>
            ) : (
              <>
                <Power className="w-3.5 h-3.5" />
                <span>End Session</span>
              </>
            )}
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
          <CheckCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
          <span>{success}</span>
        </div>
      )}

      {/* 3 Metric Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-bold uppercase tracking-wider">Attendance</span>
            <Users className="w-4 h-4 text-indigo-600" />
          </div>
          <div className="text-2xl font-extrabold text-slate-900 mt-2">
            {joinedCount} <span className="text-sm font-normal text-slate-400">/ {eligibleTotal}</span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Eligible students connected to this lecture
          </p>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-bold uppercase tracking-wider">Questions in Session</span>
            <Layers className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="text-2xl font-extrabold text-emerald-700 mt-2">
            {questions.length}
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Diagnostic & belief stress-testing prompts
          </p>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-bold uppercase tracking-wider">Session Lifecycle</span>
            <Sparkles className="w-4 h-4 text-amber-500" />
          </div>
          <div className="text-2xl font-extrabold text-slate-900 mt-2">
            {isCompleted ? 'Finished' : 'In Progress'}
          </div>
          <p className="text-xs text-slate-500 mt-1">
            {isCompleted ? 'Instructor ended lecture' : 'Accepting student participation'}
          </p>
        </div>
      </div>

      {/* Section: Session Questions List */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
              <Layers className="w-5 h-5 text-indigo-600" />
              <span>Questions for this Session</span>
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Each question has its own Round 1, AI reasoning clustering, counterexample challenge, and Round 2 revisions.
            </p>
          </div>

          <button
            onClick={() => setShowQuestionForm(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 text-xs font-bold rounded-lg transition-colors"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Add Question</span>
          </button>
        </div>

        {questions.length === 0 ? (
          <div className="py-12 text-center border-2 border-dashed border-slate-200 rounded-xl space-y-3">
            <HelpCircle className="w-10 h-10 text-slate-400 mx-auto" />
            <h3 className="font-bold text-slate-800 text-base">No Questions Added Yet</h3>
            <p className="text-xs text-slate-500 max-w-md mx-auto">
              Add your first lecture question to start collecting initial student beliefs and testing misconceptions.
            </p>
            <button
              onClick={() => setShowQuestionForm(true)}
              className="inline-flex items-center gap-1.5 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold rounded-xl shadow-md transition-all"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Create Question #1</span>
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4">
            {questions.map((q) => {
              const qStatus = q.status || 'DRAFT';
              return (
                <div
                  key={q.id}
                  className="p-5 rounded-xl border border-slate-200 hover:border-indigo-300 transition-all bg-slate-50/50 flex flex-col md:flex-row md:items-center justify-between gap-4"
                >
                  <div className="space-y-1.5 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-xs text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded">
                        Question #{q.order_index}
                      </span>
                      <span className="text-[10px] font-bold uppercase tracking-wider bg-slate-200 text-slate-700 px-2 py-0.5 rounded">
                        {q.question_type}
                      </span>
                      <span
                        className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded ${
                          qStatus.startsWith('OPEN')
                            ? 'bg-emerald-100 text-emerald-800 animate-pulse'
                            : qStatus === 'COMPLETED'
                            ? 'bg-slate-200 text-slate-700'
                            : 'bg-amber-100 text-amber-800'
                        }`}
                      >
                        {qStatus.replace(/_/g, ' ')}
                      </span>
                    </div>

                    <h3 className="font-bold text-slate-900 text-base">
                      {q.question_text}
                    </h3>

                    {q.choices && q.choices.length > 0 && (
                      <div className="flex flex-wrap gap-1.5 mt-1">
                        {q.choices.map((c, i) => (
                          <span
                            key={i}
                            className="text-[11px] bg-white border border-slate-200 px-2 py-0.5 rounded text-slate-600"
                          >
                            {c}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>

                  <div className="flex items-center gap-2 flex-shrink-0">
                    {qStatus === 'DRAFT' && (
                      <button
                        onClick={() => setEditingQuestion(q)}
                        title="Edit Question"
                        className="p-2 text-slate-500 hover:text-indigo-600 hover:bg-indigo-50 rounded-xl transition-colors border border-slate-200"
                      >
                        <Edit3 className="w-4 h-4" />
                      </button>
                    )}

                    <button
                      onClick={() =>
                        navigate(`/professor/sessions/${sessionId}/questions/${q.id}`)
                      }
                      className="flex items-center gap-1.5 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold rounded-xl shadow-md transition-all"
                    >
                      <span>Manage Question & Rounds</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </button>

                    <button
                      onClick={() => handleDeleteQuestion(q.id, q.order_index)}
                      title="Delete Question"
                      className="p-2 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-xl transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Classroom Attendance Roster */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <Users className="w-5 h-5 text-indigo-600" />
              <span>Session Attendance (45 Students)</span>
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Live status of the 45 eligible student accounts for this lecture.
            </p>
          </div>

          <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-xl text-xs font-semibold">
            {(['ALL', 'JOINED', 'NOT_JOINED'] as const).map((filter) => (
              <button
                key={filter}
                onClick={() => setRosterFilter(filter)}
                className={`px-3 py-1 rounded-lg transition-colors ${
                  rosterFilter === filter
                    ? 'bg-white text-slate-900 shadow-sm'
                    : 'text-slate-500 hover:text-slate-800'
                }`}
              >
                {filter.replace('_', ' ')}
              </button>
            ))}
          </div>
        </div>

        <div className="max-h-64 overflow-y-auto grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-2 pr-1">
          {filteredStudents.map((s) => (
            <div
              key={s.student_id}
              className={`p-2.5 rounded-xl border text-xs flex items-center justify-between ${
                s.joined
                  ? 'bg-emerald-50/60 border-emerald-200 text-emerald-950'
                  : 'bg-slate-50 border-slate-200 text-slate-500'
              }`}
            >
              <span className="font-mono font-bold">{s.student_id}</span>
              <span
                className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                  s.joined ? 'bg-emerald-200 text-emerald-900' : 'bg-slate-200 text-slate-600'
                }`}
              >
                {s.joined ? 'Joined' : 'Absent'}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Question Modal (Create & Edit) */}
      <QuestionModal
        isOpen={showQuestionForm || editingQuestion !== null}
        onClose={() => {
          setShowQuestionForm(false);
          setEditingQuestion(null);
        }}
        onSubmit={handleSaveQuestion}
        initialData={editingQuestion}
        mode={editingQuestion ? 'edit' : 'create'}
      />

      {/* QR Code Presentation Modal */}
      {isQrOpen && (
        <QRModal
          isOpen={isQrOpen}
          onClose={() => setIsQrOpen(false)}
          joinCode={session.join_code}
          sessionTitle={session.title}
        />
      )}
    </div>
  );
};
