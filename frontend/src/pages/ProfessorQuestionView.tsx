import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { api } from '../api/client';
import { SessionWebSocket } from '../api/ws';
import {
  ClassroomSession,
  Question,
  AggregateAnalysisResponse,
  ReasoningCategoryResponse,
  ChallengeProposalResponse,
  ParticipationDashboard,
} from '../types';
import { AnswerDistributionChart } from '../components/charts/AnswerDistributionChart';
import { ConfidenceDistributionChart } from '../components/charts/ConfidenceDistributionChart';
import { BeliefTransitionsMatrix } from '../components/charts/BeliefTransitionsMatrix';
import { QuestionModal } from '../components/QuestionModal';
import {
  ArrowLeft,
  Play,
  Sparkles,
  Edit3,
  CheckCircle,
  AlertCircle,
  HelpCircle,
  Lightbulb,
  Check,
  Send,
  RotateCcw,
  BarChart2,
  Users,
  Layers,
} from 'lucide-react';

export const ProfessorQuestionView: React.FC = () => {
  const { sessionId, questionId } = useParams<{ sessionId: string; questionId: string }>();
  const navigate = useNavigate();

  const [session, setSession] = useState<ClassroomSession | null>(null);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [question, setQuestion] = useState<Question | null>(null);

  const [results, setResults] = useState<AggregateAnalysisResponse | null>(null);
  const [categories, setCategories] = useState<ReasoningCategoryResponse[]>([]);
  const [challenge, setChallenge] = useState<ChallengeProposalResponse | null>(null);
  const [participation, setParticipation] = useState<ParticipationDashboard | null>(null);

  // Challenge Review Modal
  const [isChallengeModalOpen, setIsChallengeModalOpen] = useState(false);
  const [editedChallengeText, setEditedChallengeText] = useState('');
  const [instructorNotes, setInstructorNotes] = useState('');
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);

  const [loading, setLoading] = useState(true);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedRound, setSelectedRound] = useState<1 | 2>(1);
  const [selectedAnswerFilter, setSelectedAnswerFilter] = useState<string | null>(null);

  const loadData = async () => {
    if (!sessionId || !questionId) return;
    try {
      const [sessData, qListData, qData, partData] = await Promise.all([
        api.getSession(sessionId),
        api.getSessionQuestions(sessionId),
        api.getQuestion(questionId),
        api.getParticipation(sessionId),
      ]);
      setSession(sessData);
      setQuestions(qListData);
      setQuestion((prevQ) => {
        if (prevQ?.status !== qData.status) {
          if (qData.status === 'OPEN_ROUND_2') {
            setSelectedRound(2);
            setSelectedAnswerFilter(null);
          } else if (qData.status === 'OPEN_ROUND_1') {
            setSelectedRound(1);
            setSelectedAnswerFilter(null);
          }
        }
        return qData;
      });
      setParticipation(partData);

      // Try loading results, categories, and challenges for this question
      try {
        const res = await api.getQuestionResults(questionId);
        setResults(res);
      } catch {
        setResults(null);
      }

      try {
        const cats = await api.getCategories(questionId);
        setCategories(cats);
      } catch {
        setCategories([]);
      }

      try {
        const ch = (await api.getChallenge(questionId)) as ChallengeProposalResponse;
        setChallenge((prev) => {
          if (ch && prev?.id !== ch.id) {
            setEditedChallengeText(ch.edited_text || ch.challenge_text);
            setInstructorNotes(ch.instructor_notes || '');
          }
          return ch;
        });
      } catch {
        setChallenge(null);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load question details.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();

    if (sessionId) {
      const ws = new SessionWebSocket(sessionId);
      ws.on('response_recorded', () => loadData());
      ws.on('analysis_ready', () => loadData());
      ws.on('question_status_changed', () => loadData());
      ws.on('challenge_approved', () => loadData());
      return () => ws.destroy();
    }
  }, [sessionId, questionId]);

  const handleUpdateStatus = async (newStatus: string) => {
    if (!questionId) return;
    setError(null);
    try {
      const updated = await api.updateQuestionStatus(questionId, newStatus);
      setQuestion(updated);
      await loadData();
    } catch (err: any) {
      setError(err.message || 'Failed to update question status.');
    }
  };

  const handleAnalyze = async () => {
    if (!questionId) return;
    setIsAnalyzing(true);
    setError(null);
    try {
      await api.updateQuestionStatus(questionId, 'ANALYZING');
      const analysisRes = await api.triggerAnalysis(questionId);
      if (analysisRes?.challenge_id) {
        await api.updateQuestionStatus(questionId, 'CHALLENGE_PENDING');
      }
      await loadData();
      setIsChallengeModalOpen(true);
    } catch (err: any) {
      setError(err.message || 'AI analysis failed.');
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleApproveChallenge = async () => {
    if (!challenge || !questionId) return;
    try {
      setError(null);
      await api.reviewChallenge(challenge.id, {
        status: 'APPROVED',
        edited_text: editedChallengeText.trim() || undefined,
        instructor_notes: instructorNotes.trim() || undefined,
      });
      await api.updateQuestionStatus(questionId, 'OPEN_ROUND_2');
      setIsChallengeModalOpen(false);
      await loadData();
    } catch (err: any) {
      setError(err.message || 'Failed to approve challenge.');
    }
  };

  const handleEditQuestion = async (data: any) => {
    if (!questionId) return;
    setError(null);
    try {
      await api.updateQuestion(questionId, data);
      setIsEditModalOpen(false);
      await loadData();
    } catch (err: any) {
      setError(err.message || 'Failed to update question.');
      throw err;
    }
  };

  if (loading) {
    return (
      <div className="min-h-[70vh] flex items-center justify-center">
        <div className="w-10 h-10 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  if (!question || !session) {
    return (
      <div className="max-w-4xl mx-auto py-12 text-center space-y-4">
        <AlertCircle className="w-12 h-12 text-rose-500 mx-auto" />
        <h2 className="text-xl font-bold text-slate-800">Question Not Found</h2>
        <Link
          to={`/professor/sessions/${sessionId}`}
          className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-xl text-sm font-semibold"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Session Overview</span>
        </Link>
      </div>
    );
  }

  const currentStatus = question.status || 'DRAFT';
  const r1Count = results?.round_1_total || 0;
  const r2Count = results?.round_2_total || 0;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      {/* Breadcrumb & Navigation */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-200 pb-4">
        <div className="flex items-center gap-3">
          <Link
            to={`/professor/sessions/${sessionId}`}
            className="flex items-center gap-1.5 text-xs font-semibold text-slate-500 hover:text-slate-800 bg-white px-3 py-1.5 rounded-lg border border-slate-200 shadow-sm transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>All Questions ({session.title})</span>
          </Link>
          <span className="text-slate-300">/</span>
          <span className="text-xs font-bold text-indigo-700 bg-indigo-50 px-2.5 py-1 rounded-md">
            Question #{question.order_index}
          </span>
        </div>

        {/* Switch Question Dropdown */}
        {questions.length > 1 && (
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500 font-medium">Switch Question:</span>
            <select
              value={question.id}
              onChange={(e) => navigate(`/professor/sessions/${sessionId}/questions/${e.target.value}`)}
              className="text-xs font-semibold bg-white border border-slate-200 rounded-lg px-2.5 py-1 text-slate-800 outline-none"
            >
              {questions.map((q) => (
                <option key={q.id} value={q.id}>
                  Q{q.order_index}: {q.question_text.slice(0, 35)}... ({q.status || 'DRAFT'})
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 flex items-start gap-3 text-rose-700 text-sm">
          <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
          <span>{error}</span>
        </div>
      )}

      {/* Question Header & Round Controls */}
      <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 flex flex-col lg:flex-row lg:items-center justify-between gap-6">
        <div className="space-y-2 flex-1">
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-indigo-100 text-indigo-800 uppercase tracking-wide">
              {question.question_type}
            </span>
            <span
              className={`px-3 py-0.5 rounded-full text-xs font-bold uppercase tracking-wider ${
                currentStatus.startsWith('OPEN')
                  ? 'bg-emerald-100 text-emerald-800 animate-pulse'
                  : currentStatus === 'COMPLETED'
                  ? 'bg-slate-100 text-slate-700'
                  : 'bg-amber-100 text-amber-800'
              }`}
            >
              Status: {currentStatus.replace(/_/g, ' ')}
            </span>
          </div>
          <h1 className="text-xl sm:text-2xl font-extrabold text-slate-900 leading-snug">
            {question.question_text}
          </h1>
          {question.reference_answer && (
            <p className="text-xs text-slate-500">
              <strong className="text-slate-700">Reference Answer:</strong> {question.reference_answer}
            </p>
          )}
        </div>

        {/* Round Workflow Action Buttons */}
        <div className="flex flex-wrap items-center gap-2">
          {currentStatus === 'DRAFT' && (
            <>
              <button
                onClick={() => setIsEditModalOpen(true)}
                className="flex items-center gap-1.5 px-4 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-sm font-semibold rounded-xl transition-all border border-slate-200"
              >
                <Edit3 className="w-4 h-4" />
                <span>Edit Question</span>
              </button>
              <button
                onClick={() => handleUpdateStatus('OPEN_ROUND_1')}
                className="flex items-center gap-2 px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-semibold rounded-xl shadow-md transition-all"
              >
                <Play className="w-4 h-4 fill-white" />
                <span>Open Round 1</span>
              </button>
            </>
          )}

          {currentStatus === 'OPEN_ROUND_1' && (
            <button
              onClick={handleAnalyze}
              disabled={isAnalyzing}
              className="flex items-center gap-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold rounded-xl shadow-md transition-all disabled:opacity-50"
            >
              <Sparkles className="w-4 h-4" />
              <span>{isAnalyzing ? 'Analyzing...' : 'Close & Analyze Round 1'}</span>
            </button>
          )}

          {currentStatus === 'CHALLENGE_PENDING' && challenge && (
            <button
              onClick={() => setIsChallengeModalOpen(true)}
              className="flex items-center gap-2 px-5 py-2.5 bg-amber-500 hover:bg-amber-600 text-white text-sm font-semibold rounded-xl shadow-md transition-all"
            >
              <Edit3 className="w-4 h-4" />
              <span>Review Challenge Proposal</span>
            </button>
          )}

          {currentStatus === 'OPEN_ROUND_2' && (
            <button
              onClick={() => handleUpdateStatus('COMPLETED')}
              className="flex items-center gap-2 px-5 py-2.5 bg-slate-900 hover:bg-slate-800 text-white text-sm font-semibold rounded-xl shadow-md transition-all"
            >
              <Check className="w-4 h-4" />
              <span>Close Round 2 / Complete Question</span>
            </button>
          )}

          {currentStatus === 'COMPLETED' && (
            <button
              onClick={() => handleUpdateStatus('OPEN_ROUND_1')}
              className="flex items-center gap-1.5 px-3.5 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-xl transition-all"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Reopen Question</span>
            </button>
          )}
        </div>
      </div>

      {/* 4 Stage Workflow Stepper */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
        <button
          type="button"
          onClick={() => {
            setSelectedRound(1);
            setSelectedAnswerFilter(null);
          }}
          className={`p-3 rounded-xl border text-center transition-all cursor-pointer ${
            selectedRound === 1
              ? 'bg-emerald-50 border-emerald-500 font-bold text-emerald-900 ring-2 ring-emerald-200'
              : currentStatus === 'OPEN_ROUND_1'
              ? 'bg-emerald-50/60 border-emerald-300 font-bold text-emerald-900'
              : r1Count > 0
              ? 'bg-slate-50 border-slate-200 text-slate-700 hover:bg-slate-100'
              : 'bg-white border-slate-100 text-slate-400'
          }`}
        >
          <div className="font-semibold text-[10px] uppercase tracking-wider text-slate-400">Step 1 (Click to View)</div>
          <div className="font-bold mt-0.5">Round 1 (Initial)</div>
          <div className="text-[11px] text-slate-500 mt-1">{r1Count} Submissions</div>
        </button>

        <div
          className={`p-3 rounded-xl border text-center transition-all ${
            currentStatus === 'ANALYZING'
              ? 'bg-indigo-50 border-indigo-400 font-bold text-indigo-900 ring-2 ring-indigo-200'
              : categories.length > 0
              ? 'bg-slate-50 border-slate-200 text-slate-700'
              : 'bg-white border-slate-100 text-slate-400'
          }`}
        >
          <div className="font-semibold text-[10px] uppercase tracking-wider text-slate-400">Step 2</div>
          <div className="font-bold mt-0.5">AI Reasoning Clustering</div>
          <div className="text-[11px] text-slate-500 mt-1">{categories.length} Categories</div>
        </div>

        <div
          className={`p-3 rounded-xl border text-center transition-all ${
            currentStatus === 'CHALLENGE_PENDING'
              ? 'bg-amber-50 border-amber-400 font-bold text-amber-900 ring-2 ring-amber-200'
              : challenge?.status === 'APPROVED'
              ? 'bg-slate-50 border-slate-200 text-slate-700'
              : 'bg-white border-slate-100 text-slate-400'
          }`}
        >
          <div className="font-semibold text-[10px] uppercase tracking-wider text-slate-400">Step 3</div>
          <div className="font-bold mt-0.5">Challenge Counterexample</div>
          <div className="text-[11px] text-slate-500 mt-1">
            {challenge?.status === 'APPROVED' ? 'Approved' : 'Pending Review'}
          </div>
        </div>

        <button
          type="button"
          onClick={() => {
            setSelectedRound(2);
            setSelectedAnswerFilter(null);
          }}
          className={`p-3 rounded-xl border text-center transition-all cursor-pointer ${
            selectedRound === 2
              ? 'bg-purple-50 border-purple-500 font-bold text-purple-900 ring-2 ring-purple-200'
              : currentStatus === 'OPEN_ROUND_2'
              ? 'bg-purple-50/60 border-purple-300 font-bold text-purple-900'
              : r2Count > 0
              ? 'bg-slate-50 border-slate-200 text-slate-700 hover:bg-slate-100'
              : 'bg-white border-slate-100 text-slate-400'
          }`}
        >
          <div className="font-semibold text-[10px] uppercase tracking-wider text-slate-400">Step 4 (Click to View)</div>
          <div className="font-bold mt-0.5">Round 2 (Revisions)</div>
          <div className="text-[11px] text-slate-500 mt-1">{r2Count} Revisions</div>
        </button>
      </div>

      {/* Visual Analytics Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-2">
          <h3 className="font-bold text-slate-900 text-sm">
            Answer Distribution (Round 1 vs Round 2)
          </h3>
          <AnswerDistributionChart
            round1Data={results?.round_1_distributions || []}
            round2Data={results?.round_2_distributions || []}
            referenceAnswer={question.reference_answer}
          />
        </div>
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-2">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-slate-900 text-sm">
              {selectedRound === 1
                ? 'Round 1: Initial Confidence Ratings (1 to 5)'
                : 'Round 2: Revised Confidence Ratings (1 to 5)'}
            </h3>
            <div className="flex items-center gap-1 bg-slate-100 p-0.5 rounded-lg text-[11px]">
              <button
                type="button"
                onClick={() => setSelectedRound(1)}
                className={`px-2 py-0.5 rounded-md font-semibold transition-all ${
                  selectedRound === 1 ? 'bg-white text-indigo-700 shadow-sm' : 'text-slate-600'
                }`}
              >
                R1
              </button>
              <button
                type="button"
                onClick={() => setSelectedRound(2)}
                className={`px-2 py-0.5 rounded-md font-semibold transition-all ${
                  selectedRound === 2 ? 'bg-white text-amber-700 shadow-sm' : 'text-slate-600'
                }`}
              >
                R2
              </button>
            </div>
          </div>
          <ConfidenceDistributionChart
            data={
              selectedRound === 1
                ? results?.confidence_distributions_round_1 || []
                : results?.confidence_distributions_round_2 || []
            }
            title={selectedRound === 1 ? 'Initial Confidence Distribution' : 'Revised Confidence Distribution'}
          />
        </div>
      </div>

      {/* Approved Challenge Card (if approved) */}
      {challenge && challenge.status === 'APPROVED' && (
        <div className="bg-gradient-to-r from-amber-50 to-orange-50 rounded-2xl border border-amber-200 p-6 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-amber-800 uppercase tracking-wider flex items-center gap-1.5">
              <Lightbulb className="w-4 h-4 text-amber-600" />
              Approved Challenge Presented to Students in Round 2
            </span>
            <span className="text-xs font-bold bg-amber-200/60 text-amber-900 px-2.5 py-0.5 rounded-full">
              Live in Round 2
            </span>
          </div>
          <p className="text-base font-semibold text-slate-900 italic">
            "{challenge.edited_text || challenge.challenge_text}"
          </p>
          {challenge.targeted_reasoning_pattern && (
            <p className="text-xs text-amber-900">
              <strong>Targeted Misconception Pattern:</strong> {challenge.targeted_reasoning_pattern}
            </p>
          )}
        </div>
      )}

      {/* How Students Answered in the Particular Round (Round 1 vs Round 2) */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-100 pb-4">
          <div>
            <h3 className="font-bold text-slate-900 text-base flex items-center gap-2">
              <Users className="w-5 h-5 text-indigo-600" />
              <span>
                Student Responses in Round {selectedRound} (
                {selectedRound === 1 ? 'Initial Beliefs' : 'Post-Challenge Revisions'})
              </span>
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Inspect how each student answered, their confidence level, and their written reasoning in Round {selectedRound}.
            </p>
          </div>

          <div className="flex items-center gap-1.5 bg-slate-100 p-1 rounded-xl text-xs">
            <button
              type="button"
              onClick={() => {
                setSelectedRound(1);
                setSelectedAnswerFilter(null);
              }}
              className={`px-3.5 py-1.5 rounded-lg font-bold transition-all ${
                selectedRound === 1
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Round 1 ({r1Count})
            </button>
            <button
              type="button"
              onClick={() => {
                setSelectedRound(2);
                setSelectedAnswerFilter(null);
              }}
              className={`px-3.5 py-1.5 rounded-lg font-bold transition-all ${
                selectedRound === 2
                  ? 'bg-amber-600 text-white shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Round 2 ({r2Count})
            </button>
          </div>
        </div>

        {/* Option Breakdown Filter Pills for Selected Round */}
        {(() => {
          const activeDist =
            selectedRound === 1
              ? results?.round_1_distributions || []
              : results?.round_2_distributions || [];
          const activeResponses =
            selectedRound === 1
              ? results?.round_1_responses || []
              : results?.round_2_responses || [];
          const filteredResponses = selectedAnswerFilter
            ? activeResponses.filter((r) => r.answer.trim() === selectedAnswerFilter)
            : activeResponses;

          if (activeResponses.length === 0) {
            return (
              <div className="p-8 text-center text-slate-400 text-sm bg-slate-50 rounded-xl border border-slate-100">
                No student responses submitted for Round {selectedRound} yet.
              </div>
            );
          }

          return (
            <div className="space-y-4">
              {/* Filter by Answer Option in this Round */}
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-xs font-semibold text-slate-500">Filter by answer:</span>
                <button
                  type="button"
                  onClick={() => setSelectedAnswerFilter(null)}
                  className={`px-3 py-1.5 rounded-xl text-xs font-bold border transition-all ${
                    selectedAnswerFilter === null
                      ? 'bg-slate-900 text-white border-slate-900'
                      : 'bg-slate-50 text-slate-700 border-slate-200 hover:bg-slate-100'
                  }`}
                >
                  All ({activeResponses.length})
                </button>
                {activeDist.map((d, idx) => {
                  const isSelected = selectedAnswerFilter === d.answer;
                  const isBench = d.is_reference_correct === true;
                  return (
                    <button
                      key={idx}
                      type="button"
                      onClick={() =>
                        setSelectedAnswerFilter(isSelected ? null : d.answer)
                      }
                      className={`px-3 py-1.5 rounded-xl text-xs font-semibold border transition-all flex items-center gap-1.5 ${
                        isSelected
                          ? isBench
                            ? 'bg-emerald-600 text-white border-emerald-600 shadow-sm'
                            : 'bg-indigo-600 text-white border-indigo-600 shadow-sm'
                          : isBench
                          ? 'bg-emerald-50 text-emerald-800 border-emerald-300 hover:bg-emerald-100'
                          : 'bg-white text-slate-700 border-slate-200 hover:bg-slate-50'
                      }`}
                    >
                      <span>{d.answer}</span>
                      <span className="opacity-80 font-bold">
                        ({d.count} • {d.percentage}%)
                      </span>
                      {isBench && <CheckCircle className="w-3.5 h-3.5" />}
                    </button>
                  );
                })}
              </div>

              {/* Individual Student Cards for Selected Round */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-h-[460px] overflow-y-auto pr-1">
                {filteredResponses.map((resp) => {
                  const isBench = resp.is_reference_correct === true;
                  return (
                    <div
                      key={resp.id}
                      className={`p-4 rounded-xl border space-y-2 transition-all ${
                        isBench
                          ? 'bg-emerald-50/40 border-emerald-200'
                          : 'bg-slate-50/70 border-slate-200'
                      }`}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-mono text-xs font-extrabold px-2.5 py-0.5 rounded-md bg-white border border-slate-200 text-slate-800">
                          {resp.student_id}
                        </span>
                        <div className="flex items-center gap-1.5">
                          {selectedRound === 2 && resp.changed_answer !== null && resp.changed_answer !== undefined && (
                            <span
                              className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                                resp.changed_answer
                                  ? 'bg-amber-100 text-amber-800 border border-amber-200'
                                  : 'bg-slate-200 text-slate-700'
                              }`}
                            >
                              {resp.changed_answer ? 'Switched Answer' : 'Retained Answer'}
                            </span>
                          )}
                          <span className="text-xs font-semibold text-slate-600 bg-white px-2 py-0.5 rounded-md border border-slate-200">
                            Conf: <strong>{resp.confidence}/5</strong>
                          </span>
                        </div>
                      </div>

                      <div className="flex items-center justify-between gap-2">
                        <div
                          className={`text-sm font-bold px-2.5 py-1 rounded-lg inline-flex items-center gap-1.5 ${
                            isBench
                              ? 'bg-emerald-100 text-emerald-900 border border-emerald-300'
                              : selectedRound === 1
                              ? 'bg-indigo-50 text-indigo-900 border border-indigo-200'
                              : 'bg-amber-50 text-amber-900 border border-amber-200'
                          }`}
                        >
                          {isBench && <CheckCircle className="w-3.5 h-3.5 text-emerald-600 flex-shrink-0" />}
                          <span>{resp.answer}</span>
                        </div>
                        {resp.category_title && (
                          <span className="text-[10px] font-semibold text-slate-500 bg-white px-2 py-0.5 rounded border border-slate-200 truncate max-w-[180px]">
                            {resp.category_title}
                          </span>
                        )}
                      </div>

                      {selectedRound === 1 && resp.explanation && (
                        <p className="text-xs text-slate-700 italic bg-white/90 p-2.5 rounded-lg border border-slate-200/80">
                          "{resp.explanation}"
                        </p>
                      )}

                      {selectedRound === 2 && resp.change_reason && (
                        <p className="text-xs text-slate-700 italic bg-white/90 p-2.5 rounded-lg border border-amber-200/80">
                          "{resp.change_reason}"
                        </p>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })()}
      </div>

      {/* Round 2 Revisions & Belief Transitions Matrix */}
      {r2Count > 0 && (
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-4">
          <h3 className="font-bold text-slate-900 text-base">
            Class Belief Transitions Matrix (Round 1 → Round 2)
          </h3>
          <BeliefTransitionsMatrix
            transitions={results?.belief_transitions || []}
          />
        </div>
      )}

      {/* AI Discovered Reasoning Categories */}
      {categories.length > 0 && (
        <div className="bg-white rounded-2xl border border-slate-200 p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-slate-900 text-base flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-indigo-600" />
              <span>AI Discovered Reasoning Categories & Mental Models</span>
            </h3>
            <span className="text-xs text-slate-500 font-semibold bg-slate-100 px-2.5 py-0.5 rounded-full">
              {categories.length} Discovered Clusters
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {categories.map((cat) => (
              <div
                key={cat.id}
                className={`p-4 rounded-xl border ${
                  cat.is_misconception
                    ? 'bg-rose-50/50 border-rose-200'
                    : 'bg-emerald-50/50 border-emerald-200'
                }`}
              >
                <div className="flex items-center justify-between">
                  <h4 className="font-bold text-sm text-slate-900">{cat.title}</h4>
                  <span
                    className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                      cat.is_misconception
                        ? 'bg-rose-100 text-rose-800'
                        : 'bg-emerald-100 text-emerald-800'
                    }`}
                  >
                    {cat.is_misconception ? 'Misconception' : 'Valid Model'}
                  </span>
                </div>
                <p className="text-xs text-slate-600 mt-1">{cat.description}</p>
                {cat.sample_explanations && cat.sample_explanations.length > 0 && (
                  <div className="mt-2 space-y-1">
                    {cat.sample_explanations.slice(0, 2).map((q, idx) => (
                      <p key={idx} className="text-[11px] text-slate-500 italic bg-white/70 p-1.5 rounded">
                        "{q}"
                      </p>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}


      {/* Challenge Review Modal */}
      {isChallengeModalOpen && challenge && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm">
          <div className="bg-white rounded-2xl max-w-xl w-full p-6 shadow-2xl border border-slate-100 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="font-bold text-slate-900 text-base flex items-center gap-2">
                <Lightbulb className="w-5 h-5 text-amber-500" />
                Review AI-Generated Challenge Counterexample
              </h3>
              <button
                onClick={() => setIsChallengeModalOpen(false)}
                className="text-xs text-slate-400 hover:text-slate-600"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                  Challenge Prompt (What students will read)
                </label>
                <textarea
                  rows={4}
                  value={editedChallengeText}
                  onChange={(e) => setEditedChallengeText(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 text-sm focus:ring-2 focus:ring-indigo-600 outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                  Instructor Notes (Optional)
                </label>
                <input
                  type="text"
                  value={instructorNotes}
                  onChange={(e) => setInstructorNotes(e.target.value)}
                  placeholder="e.g. Focused counterexample on paying more than valuation."
                  className="w-full px-3.5 py-2 rounded-xl border border-slate-300 text-xs outline-none"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-100">
              <button
                onClick={() => setIsChallengeModalOpen(false)}
                className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-xl"
              >
                Cancel
              </button>
              <button
                onClick={handleApproveChallenge}
                className="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold rounded-xl shadow-md transition-all flex items-center gap-1.5"
              >
                <Check className="w-4 h-4" />
                <span>Approve & Open Round 2 Revisions</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Edit Question Modal */}
      <QuestionModal
        isOpen={isEditModalOpen}
        onClose={() => setIsEditModalOpen(false)}
        onSubmit={handleEditQuestion}
        initialData={question}
        mode="edit"
      />
    </div>
  );
};
