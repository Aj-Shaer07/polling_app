import React, { useState, useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { api } from '../api/client';
import { SessionWebSocket } from '../api/ws';
import {
  Question,
  ClassroomSession,
  StudentResponseView,
  ChallengeStudentView,
} from '../types';
import {
  School,
  ArrowRight,
  CheckCircle2,
  Clock,
  Sparkles,
  AlertCircle,
  HelpCircle,
  TrendingUp,
  RefreshCw,
  Lightbulb,
  Check,
  CheckCircle,
} from 'lucide-react';

const CONFIDENCE_DESCRIPTIONS: Record<number, string> = {
  1: '1 - Complete Guess',
  2: '2 - Low Confidence',
  3: '3 - Somewhat Confident',
  4: '4 - High Confidence',
  5: '5 - Completely Certain',
};

export const StudentSession: React.FC = () => {
  const { user } = useAuth();
  const [searchParams] = useSearchParams();

  const [joinCode, setJoinCode] = useState(searchParams.get('code') || '');
  const [session, setSession] = useState<ClassroomSession | null>(null);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [activeQuestion, setActiveQuestion] = useState<Question | null>(null);
  const activeQuestionRef = useRef<Question | null>(null);
  const [followUpQuestion, setFollowUpQuestion] = useState<Question | null>(null);
  const [challenge, setChallenge] = useState<ChallengeStudentView | null>(null);
  const [myResponses, setMyResponses] = useState<StudentResponseView[]>([]);

  // Form states
  const [answer, setAnswer] = useState('');
  const [confidence, setConfidence] = useState<number>(3);
  const [explanation, setExplanation] = useState('');
  const [prediction, setPrediction] = useState('');
  const [changedAnswer, setChangedAnswer] = useState(false);
  const [changeReason, setChangeReason] = useState('');

  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [loading, setLoading] = useState(false);
  const [wsClient, setWsClient] = useState<SessionWebSocket | null>(null);

  const loadQuestionData = async (q: Question, forceResetForm = false) => {
    const prevQ = activeQuestionRef.current;
    const isDifferentQuestion = prevQ?.id !== q.id;
    const isDifferentStatus = prevQ?.status !== q.status;

    activeQuestionRef.current = q;
    setActiveQuestion(q);

    if (forceResetForm || isDifferentQuestion || isDifferentStatus) {
      setAnswer('');
      if (forceResetForm || isDifferentQuestion) {
        setExplanation('');
        setPrediction('');
        setChangeReason('');
        setChangedAnswer(false);
      }
    }

    try {
      const respList = await api.getMyResponses(q.id);
      setMyResponses(respList);

      const qStatus = q.status || 'DRAFT';
      if (['OPEN_ROUND_2', 'FOLLOW_UP', 'COMPLETED'].includes(qStatus)) {
        try {
          const ch = (await api.getChallenge(q.id)) as ChallengeStudentView;
          setChallenge(ch);
        } catch {
          setChallenge(null);
        }
      } else {
        setChallenge(null);
      }
    } catch {
      // ignore
    }
  };

  // Load active session state
  const refreshSessionData = async (sessionId: string, selectedQId?: string) => {
    try {
      const sess = await api.getSession(sessionId);
      setSession(sess);

      const qList = await api.getSessionQuestions(sessionId);
      setQuestions(qList);

      const currentId = activeQuestionRef.current?.id;
      const targetId = selectedQId || currentId;
      const targetQ = (targetId ? qList.find((q) => q.id === targetId) : null) || qList[0];
      const fuQ = qList.find((q) => q.is_follow_up);
      setFollowUpQuestion(fuQ || null);

      if (targetQ) {
        await loadQuestionData(targetQ, Boolean(selectedQId && selectedQId !== currentId));
      }
    } catch (err: any) {
      setError(err.message || 'Failed to refresh session state.');
    }
  };

  // 3-second heartbeat polling to guarantee real-time sync across questions and rounds
  useEffect(() => {
    if (!session?.id) return;
    const interval = setInterval(() => {
      refreshSessionData(session.id);
    }, 3000);
    return () => clearInterval(interval);
  }, [session?.id]);

  const handleJoin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const joinRes = await api.joinSession(joinCode.trim().toUpperCase());
      await refreshSessionData(joinRes.session_id);

      // Connect WebSocket for instantaneous reactive updates
      const ws = new SessionWebSocket(joinRes.session_id);
      ws.on('status_changed', () => refreshSessionData(joinRes.session_id));
      ws.on('question_status_changed', () => refreshSessionData(joinRes.session_id));
      ws.on('question_updated', () => refreshSessionData(joinRes.session_id));
      ws.on('challenge_approved', () => refreshSessionData(joinRes.session_id));
      ws.on('analysis_ready', () => refreshSessionData(joinRes.session_id));
      setWsClient(ws);
    } catch (err: any) {
      setError(err.message || 'Unable to join session. Verify your join code.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (searchParams.get('code') && !session) {
      setJoinCode(searchParams.get('code') || '');
    }
    return () => {
      if (wsClient) wsClient.destroy();
    };
  }, []);

  // Submit Round 1
  const handleRound1Submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeQuestion) return;
    setError(null);
    setIsSubmitting(true);

    try {
      const resp = await api.submitRound1(activeQuestion.id, {
        answer,
        confidence,
        explanation: activeQuestion.reasoning_required ? explanation : undefined,
        prediction: activeQuestion.prediction_enabled ? prediction : undefined,
      });
      setMyResponses([resp]);
    } catch (err: any) {
      setError(err.message || 'Failed to submit response.');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Submit Round 2
  const handleRound2Submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeQuestion) return;
    setError(null);
    setIsSubmitting(true);

    try {
      const resp = await api.submitRound2(activeQuestion.id, {
        answer,
        confidence,
        changed_answer: changedAnswer,
        change_reason: changeReason,
      });
      setMyResponses((prev) => [...prev.filter((r) => r.round_number !== 2), resp]);
    } catch (err: any) {
      setError(err.message || 'Failed to submit revised response.');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Submit Follow-Up
  const handleFollowUpSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!followUpQuestion) return;
    setError(null);
    setIsSubmitting(true);

    try {
      await api.submitFollowUp(followUpQuestion.id, {
        answer,
        confidence,
        explanation,
      });
      if (session) await refreshSessionData(session.id);
    } catch (err: any) {
      setError(err.message || 'Failed to submit follow-up response.');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Screen 1: Join Session
  if (!session) {
    return (
      <div className="min-h-[85vh] flex items-center justify-center px-4 py-8">
        <div className="max-w-md w-full space-y-6">
          <div className="text-center">
            <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl bg-indigo-600 text-white shadow-md shadow-indigo-100 mb-3">
              <School className="w-6 h-6" />
            </div>
            <h2 className="text-2xl font-extrabold text-slate-900 tracking-tight">
              Join Classroom Session
            </h2>
            <p className="mt-1 text-xs text-slate-500">
              Enter the 6-character code presented by your professor
            </p>
          </div>

          <div className="bg-white p-6 rounded-2xl shadow-xl border border-slate-100 space-y-4">
            {error && (
              <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl flex items-start gap-2.5 text-rose-700 text-xs">
                <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                <span>{error}</span>
              </div>
            )}

            <form onSubmit={handleJoin} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
                  Class Join Code
                </label>
                <input
                  type="text"
                  required
                  maxLength={6}
                  value={joinCode}
                  onChange={(e) => setJoinCode(e.target.value.toUpperCase())}
                  placeholder="e.g. 9SMJZL"
                  className="w-full px-4 py-3 rounded-xl border border-slate-300 focus:ring-2 focus:ring-indigo-600 font-mono text-center tracking-widest text-lg uppercase outline-none"
                />
              </div>

              <button
                type="submit"
                disabled={loading || joinCode.length < 4}
                className="w-full py-3 px-4 rounded-xl text-white font-semibold bg-indigo-600 hover:bg-indigo-700 shadow-md shadow-indigo-100 disabled:opacity-50 transition-all flex items-center justify-center gap-2 text-sm"
              >
                {loading ? (
                  <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                ) : (
                  <>
                    <span>Enter Classroom</span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </form>
          </div>
        </div>
      </div>
    );
  }

  const round1Submitted = myResponses.some((r) => r.round_number === 1);
  const round2Submitted = myResponses.some((r) => r.round_number === 2);
  const r1Resp = myResponses.find((r) => r.round_number === 1);
  const r2Resp = myResponses.find((r) => r.round_number === 2);
  const fuResp = myResponses.find((r) => r.round_number === 3);

  const currentQStatus = activeQuestion?.status || 'DRAFT';

  return (
    <div className="max-w-2xl mx-auto px-4 py-6 space-y-6">
      {/* Session Top Bar (Clean, no confusing DRAFT badge) */}
      <div className="bg-white p-4 rounded-2xl shadow-sm border border-slate-200 flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 font-mono">
              SESSION: {session.join_code}
            </span>
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
              <span>Live Classroom</span>
            </span>
          </div>
          <h2 className="text-lg font-extrabold text-slate-900 mt-1">{session.title}</h2>
        </div>
        <div className="text-right">
          <span className="text-xs font-mono font-bold text-slate-700 bg-slate-50 px-2.5 py-1 rounded-lg border border-slate-200">
            {user?.student_id || user?.username}
          </span>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 flex items-start gap-3 text-rose-700 text-sm">
          <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
          <span>{error}</span>
        </div>
      )}

      {/* Multiple Questions Selector (if more than 1 question) */}
      {questions.length > 1 && (
        <div className="bg-white p-3 rounded-2xl border border-slate-200 shadow-sm space-y-1.5">
          <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
            Lecture Questions ({questions.length})
          </div>
          <div className="flex items-center gap-2 overflow-x-auto pb-1">
            {questions.map((q) => {
              const isSelected = activeQuestion?.id === q.id;
              const qStat = q.status || 'DRAFT';
              return (
                <button
                  key={q.id}
                  onClick={() => loadQuestionData(q)}
                  className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all flex items-center gap-1.5 flex-shrink-0 ${
                    isSelected
                      ? 'bg-indigo-600 text-white shadow-sm'
                      : 'bg-slate-50 text-slate-700 border border-slate-200 hover:bg-slate-100'
                  }`}
                >
                  <span>Q{q.order_index}</span>
                  <span className="text-[10px] opacity-75 font-normal">
                    {qStat === 'OPEN_ROUND_1'
                      ? 'Round 1'
                      : qStat === 'OPEN_ROUND_2'
                      ? 'Round 2'
                      : qStat === 'COMPLETED'
                      ? 'Completed'
                      : 'Draft'}
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* State 1: DRAFT - Single clean Waiting Box */}
      {currentQStatus === 'DRAFT' && (
        <div className="bg-white p-8 rounded-2xl shadow-sm border border-slate-200 text-center space-y-4">
          <div className="w-12 h-12 bg-amber-50 rounded-2xl flex items-center justify-center mx-auto text-amber-600">
            <Clock className="w-6 h-6 animate-spin" />
          </div>
          <h3 className="text-lg font-bold text-slate-900">Waiting for Instructor</h3>
          <p className="text-sm text-slate-500 max-w-sm mx-auto">
            You are connected as <code className="font-mono font-bold text-slate-700">{user?.student_id}</code>.
            Round 1 will appear automatically on this screen when the professor starts this question.
          </p>
        </div>
      )}

      {/* State 2: OPEN_ROUND_1 */}
      {currentQStatus === 'OPEN_ROUND_1' && activeQuestion && (
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 space-y-6">
          <div className="border-b border-slate-100 pb-4">
            <span className="text-xs font-bold uppercase tracking-wider text-indigo-600">
              Round 1: Initial Belief (Question #{activeQuestion.order_index})
            </span>
            <h3 className="text-xl font-bold text-slate-900 mt-1">{activeQuestion.question_text}</h3>
          </div>

          {round1Submitted ? (
            <div className="p-6 bg-emerald-50 rounded-2xl border border-emerald-200 text-center space-y-2">
              <CheckCircle2 className="w-10 h-10 text-emerald-600 mx-auto" />
              <h4 className="font-bold text-emerald-900 text-base">Round 1 Response Recorded!</h4>
              <p className="text-xs text-emerald-700">
                You selected: <strong>"{r1Resp?.answer}"</strong> with confidence <strong>{r1Resp?.confidence}/5</strong>.
              </p>
              <p className="text-xs text-slate-500 pt-2">
                Waiting for the professor to close Round 1 and analyze class reasoning.
              </p>
            </div>
          ) : (
            <form onSubmit={handleRound1Submit} className="space-y-6">
              {/* Adaptive Answer Input: Choices vs Prediction vs Text */}
              {activeQuestion.choices && activeQuestion.choices.length > 0 ? (
                <div className="space-y-2.5">
                  <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider">
                    Select Your Answer:
                  </label>
                  <div className="grid grid-cols-1 gap-2.5">
                    {activeQuestion.choices.map((choice, idx) => (
                      <button
                        type="button"
                        key={idx}
                        onClick={() => setAnswer(choice)}
                        className={`w-full p-3.5 text-left rounded-xl border text-sm font-medium transition-all flex items-center justify-between ${
                          answer === choice
                            ? 'bg-indigo-50 border-indigo-600 text-indigo-900 shadow-sm ring-1 ring-indigo-600'
                            : 'border-slate-200 hover:border-slate-300 bg-slate-50 text-slate-800'
                        }`}
                      >
                        <span>{choice}</span>
                        {answer === choice && <CheckCircle2 className="w-4 h-4 text-indigo-600" />}
                      </button>
                    ))}
                  </div>
                </div>
              ) : activeQuestion.question_type === 'PREDICTION' ? (
                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-2">
                    Your Numerical Prediction / Estimate:
                  </label>
                  <input
                    type="text"
                    required
                    value={answer}
                    onChange={(e) => setAnswer(e.target.value)}
                    placeholder="Enter your quantitative estimate or price..."
                    className="w-full p-3.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-indigo-600 text-sm outline-none"
                  />
                </div>
              ) : (
                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-2">
                    Your Response:
                  </label>
                  <textarea
                    required
                    rows={3}
                    value={answer}
                    onChange={(e) => setAnswer(e.target.value)}
                    placeholder="Enter your answer or perspective..."
                    className="w-full p-3.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-indigo-600 text-sm outline-none"
                  />
                </div>
              )}

              {/* Confidence Slider */}
              {activeQuestion.confidence_required && (
                <div className="space-y-2 p-4 bg-slate-50 rounded-xl border border-slate-200">
                  <div className="flex justify-between items-center">
                    <label className="text-xs font-semibold text-slate-700 uppercase tracking-wider">
                      Confidence Rating
                    </label>
                    <span className="text-xs font-bold text-indigo-600">
                      {CONFIDENCE_DESCRIPTIONS[confidence]}
                    </span>
                  </div>
                  <input
                    type="range"
                    min="1"
                    max="5"
                    step="1"
                    value={confidence}
                    onChange={(e) => setConfidence(parseInt(e.target.value))}
                    className="w-full accent-indigo-600 h-2 bg-slate-200 rounded-lg cursor-pointer"
                  />
                  <div className="flex justify-between text-[10px] text-slate-400 font-medium">
                    <span>1 (Pure Guess)</span>
                    <span>3 (Somewhat)</span>
                    <span>5 (Certain)</span>
                  </div>
                </div>
              )}

              {/* Written reasoning explanation */}
              {activeQuestion.reasoning_required && (
                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
                    Why do you believe this? (Reasoning explanation)
                  </label>
                  <textarea
                    required
                    rows={3}
                    value={explanation}
                    onChange={(e) => setExplanation(e.target.value)}
                    placeholder="Briefly state your underlying rationale or thought process..."
                    className="w-full p-3.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-indigo-600 text-sm outline-none"
                  />
                </div>
              )}

              <button
                type="submit"
                disabled={isSubmitting || !answer}
                className="w-full py-3.5 px-4 rounded-xl text-white font-medium bg-indigo-600 hover:bg-indigo-700 shadow-md shadow-indigo-100 disabled:opacity-50 transition-all flex items-center justify-center gap-2"
              >
                {isSubmitting ? (
                  <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                ) : (
                  <>
                    <span>Submit Initial Belief</span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </form>
          )}
        </div>
      )}

      {/* State 3: ANALYZING or CHALLENGE_PENDING */}
      {['ANALYZING', 'CHALLENGE_PENDING'].includes(currentQStatus) && (
        <div className="bg-white p-8 rounded-2xl shadow-sm border border-slate-200 text-center space-y-4">
          <div className="w-12 h-12 bg-indigo-50 rounded-2xl flex items-center justify-center mx-auto text-indigo-600">
            <Sparkles className="w-6 h-6 animate-pulse" />
          </div>
          <h3 className="text-lg font-bold text-slate-900">Reasoning Diagnostic in Progress</h3>
          <p className="text-sm text-slate-500 max-w-sm mx-auto">
            Round 1 submissions are closed. The instructor is analyzing class reasoning patterns and preparing a targeted challenge.
          </p>
          {r1Resp && (
            <div className="text-xs text-slate-600 p-3 bg-slate-50 rounded-xl border border-slate-200 inline-block max-w-md mx-auto">
              Your Round 1 submission was: <strong className="text-slate-800">"{r1Resp.answer}"</strong> (Confidence: {r1Resp.confidence}/5)
            </div>
          )}
        </div>
      )}

      {/* State 4: OPEN_ROUND_2 - Challenge & Revision */}
      {currentQStatus === 'OPEN_ROUND_2' && activeQuestion && (
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 space-y-6">
          <div className="border-b border-slate-100 pb-4">
            <span className="text-xs font-bold uppercase tracking-wider text-amber-600">
              Round 2: Targeted Challenge & Revision
            </span>
            <h3 className="text-xl font-bold text-slate-900 mt-1">{activeQuestion.question_text}</h3>
          </div>

          {/* Challenge Box */}
          <div className="p-5 bg-gradient-to-br from-indigo-50 to-amber-50 rounded-2xl border border-indigo-200 space-y-2">
            <div className="flex items-center gap-1.5 text-xs font-bold text-indigo-700 uppercase tracking-wider">
              <Sparkles className="w-4 h-4 text-amber-500" />
              <span>Targeted Challenge for the Class</span>
            </div>
            <p className="text-base font-semibold text-slate-900 leading-relaxed">
              "{challenge?.challenge_text || 'Consider alternative cases and edge scenarios before finalizing your position.'}"
            </p>
          </div>

          <div className="text-xs text-slate-500 p-3 bg-slate-50 rounded-xl border border-slate-200">
            Your Round 1 submission was: <strong className="text-slate-800">"{r1Resp?.answer || 'Not answered'}"</strong>
          </div>

          {round2Submitted ? (
            <div className="p-6 bg-emerald-50 rounded-2xl border border-emerald-200 text-center space-y-2">
              <CheckCircle2 className="w-10 h-10 text-emerald-600 mx-auto" />
              <h4 className="font-bold text-emerald-900 text-base">Revision Submitted!</h4>
              <p className="text-xs text-emerald-700">
                You selected: <strong>"{r2Resp?.answer}"</strong> with revised confidence <strong>{r2Resp?.confidence}/5</strong>.
              </p>
              <p className="text-xs text-slate-500 pt-2">
                Waiting for the instructor to conclude this question.
              </p>
            </div>
          ) : (
            <form onSubmit={handleRound2Submit} className="space-y-6">
              {/* Choices or input */}
              {activeQuestion.choices && activeQuestion.choices.length > 0 ? (
                <div className="space-y-2.5">
                  <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider">
                    After considering the challenge, what is your answer now?
                  </label>
                  <div className="grid grid-cols-1 gap-2.5">
                    {activeQuestion.choices.map((choice, idx) => (
                      <button
                        type="button"
                        key={idx}
                        onClick={() => {
                          setAnswer(choice);
                          setChangedAnswer(choice !== r1Resp?.answer);
                        }}
                        className={`w-full p-3.5 text-left rounded-xl border text-sm font-medium transition-all flex items-center justify-between ${
                          answer === choice
                            ? 'bg-amber-50 border-amber-600 text-amber-900 shadow-sm ring-1 ring-amber-600'
                            : 'border-slate-200 hover:border-slate-300 bg-slate-50 text-slate-800'
                        }`}
                      >
                        <span>{choice}</span>
                        {choice === r1Resp?.answer && (
                          <span className="text-[10px] text-slate-400 font-normal">(Initial answer)</span>
                        )}
                      </button>
                    ))}
                  </div>
                </div>
              ) : activeQuestion.question_type === 'PREDICTION' ? (
                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-2">
                    Revised Prediction / Estimate:
                  </label>
                  <input
                    type="text"
                    required
                    value={answer}
                    onChange={(e) => {
                      setAnswer(e.target.value);
                      setChangedAnswer(e.target.value !== r1Resp?.answer);
                    }}
                    placeholder="Enter revised estimate..."
                    className="w-full p-3.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-amber-500 text-sm outline-none"
                  />
                </div>
              ) : (
                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-2">
                    Revised Answer:
                  </label>
                  <textarea
                    required
                    rows={3}
                    value={answer}
                    onChange={(e) => {
                      setAnswer(e.target.value);
                      setChangedAnswer(e.target.value !== r1Resp?.answer);
                    }}
                    className="w-full p-3.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-amber-500 text-sm outline-none"
                  />
                </div>
              )}

              {/* Revised Confidence */}
              <div className="space-y-2 p-4 bg-slate-50 rounded-xl border border-slate-200">
                <div className="flex justify-between items-center">
                  <label className="text-xs font-semibold text-slate-700 uppercase tracking-wider">
                    Revised Confidence Rating
                  </label>
                  <span className="text-xs font-bold text-amber-600">
                    {CONFIDENCE_DESCRIPTIONS[confidence]}
                  </span>
                </div>
                <input
                  type="range"
                  min="1"
                  max="5"
                  step="1"
                  value={confidence}
                  onChange={(e) => setConfidence(parseInt(e.target.value))}
                  className="w-full accent-amber-600 h-2 bg-slate-200 rounded-lg cursor-pointer"
                />
              </div>

              {/* What influenced your decision */}
              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
                  What influenced your decision to retain or change your answer?
                </label>
                <textarea
                  required
                  rows={3}
                  value={changeReason}
                  onChange={(e) => setChangeReason(e.target.value)}
                  placeholder="Explain why the challenge persuaded you or why your initial rationale held up..."
                  className="w-full p-3.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-amber-500 text-sm outline-none"
                />
              </div>

              <button
                type="submit"
                disabled={isSubmitting || !answer}
                className="w-full py-3.5 px-4 rounded-xl text-white font-medium bg-amber-600 hover:bg-amber-700 shadow-md shadow-amber-100 disabled:opacity-50 transition-all flex items-center justify-center gap-2"
              >
                {isSubmitting ? (
                  <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                ) : (
                  <>
                    <span>Submit Revised Position</span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </form>
          )}
        </div>
      )}

      {/* State 5: FOLLOW_UP Assessment */}
      {currentQStatus === 'FOLLOW_UP' && followUpQuestion && (
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 space-y-6">
          <div className="border-b border-slate-100 pb-4">
            <span className="text-xs font-semibold uppercase tracking-wider text-emerald-600">
              Concept Retention Assessment
            </span>
            <h3 className="text-xl font-bold text-slate-900 mt-1">
              {followUpQuestion.question_text}
            </h3>
          </div>

          <form onSubmit={handleFollowUpSubmit} className="space-y-6">
            <textarea
              required
              rows={3}
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              placeholder="Enter your response..."
              className="w-full p-3.5 rounded-xl border border-slate-300 text-sm"
            />

            <button
              type="submit"
              disabled={isSubmitting || !answer}
              className="w-full py-3.5 px-4 rounded-xl text-white font-medium bg-emerald-600 hover:bg-emerald-700 shadow-md shadow-emerald-100 disabled:opacity-50 transition-all flex items-center justify-center gap-2"
            >
              {isSubmitting ? (
                <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
              ) : (
                <>
                  <span>Submit Follow-up Response</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>
        </div>
      )}

      {/* State 6: COMPLETED - Student's Own Answers & Benchmark Review (No Class Distribution) */}
      {(currentQStatus === 'COMPLETED' || session.status === 'COMPLETED') && (
        <div className="space-y-6">
          <div className="bg-emerald-50 border border-emerald-200 rounded-2xl p-6 text-center space-y-2">
            <CheckCircle2 className="w-12 h-12 text-emerald-600 mx-auto" />
            <h3 className="text-xl font-bold text-emerald-900">
              {session.status === 'COMPLETED' ? 'Session Concluded' : 'Question Completed'}
            </h3>
            <p className="text-xs text-emerald-700">
              This diagnostic exercise has concluded. Review your submissions and the instructor benchmark below.
            </p>
          </div>

          {/* Student Submissions Review Card */}
          <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 space-y-5">
            <h4 className="font-extrabold text-slate-900 text-base flex items-center gap-2">
              <CheckCircle className="w-5 h-5 text-indigo-600" />
              <span>Your Submissions for Q#{activeQuestion?.order_index}</span>
            </h4>

            {/* Round 1 Review */}
            <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                  Round 1: Initial Response
                </span>
                <span className="text-xs font-semibold text-slate-500">
                  Confidence: {r1Resp?.confidence || 'N/A'}/5
                </span>
              </div>
              <p className="text-sm font-bold text-slate-900">
                "{r1Resp?.answer || 'Not answered'}"
              </p>
              {r1Resp?.explanation && (
                <p className="text-xs text-slate-600 italic bg-white p-2 rounded-lg border border-slate-200">
                  Rationale: "{r1Resp.explanation}"
                </p>
              )}
            </div>

            {/* Challenge Review */}
            {challenge && (
              <div className="p-4 bg-indigo-50/60 rounded-xl border border-indigo-200 space-y-1.5">
                <span className="text-xs font-bold text-indigo-800 uppercase tracking-wider flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-amber-500" />
                  <span>Targeted Challenge Presented to Class</span>
                </span>
                <p className="text-xs font-medium text-slate-800 leading-relaxed italic">
                  "{challenge.challenge_text}"
                </p>
              </div>
            )}

            {/* Round 2 Review */}
            {r2Resp && (
              <div className="p-4 bg-amber-50/50 rounded-xl border border-amber-200 space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-amber-900 uppercase tracking-wider">
                    Round 2: Revised Position
                  </span>
                  <span className="text-xs font-semibold text-amber-800">
                    Confidence: {r2Resp.confidence}/5
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-bold text-slate-900">
                    "{r2Resp.answer}"
                  </span>
                  <span
                    className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                      r2Resp.changed_answer
                        ? 'bg-amber-200 text-amber-900'
                        : 'bg-slate-200 text-slate-800'
                    }`}
                  >
                    {r2Resp.changed_answer ? 'Changed Position' : 'Retained Initial Position'}
                  </span>
                </div>
                {r2Resp.change_reason && (
                  <p className="text-xs text-slate-600 italic bg-white p-2 rounded-lg border border-amber-200">
                    Why: "{r2Resp.change_reason}"
                  </p>
                )}
              </div>
            )}

            {/* Instructor Benchmark Revealed */}
            {activeQuestion?.reference_answer && (
              <div className="p-4 bg-emerald-50/70 rounded-xl border border-emerald-300 space-y-2">
                <div className="flex items-center gap-1.5 text-xs font-bold text-emerald-800 uppercase tracking-wider">
                  <Lightbulb className="w-4 h-4 text-emerald-600" />
                  <span>Instructor Benchmark / Reference Solution</span>
                </div>
                <p className="text-sm font-bold text-emerald-950">
                  {activeQuestion.reference_answer}
                </p>
                {activeQuestion.accepted_reasoning && (
                  <p className="text-xs text-emerald-800 bg-white/80 p-2.5 rounded-lg border border-emerald-200 leading-relaxed">
                    <strong>Reasoning Benchmark:</strong> {activeQuestion.accepted_reasoning}
                  </p>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
