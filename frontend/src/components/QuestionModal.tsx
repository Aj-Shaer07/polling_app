import React, { useState, useEffect } from 'react';
import { Question, QuestionType } from '../types';
import { HelpCircle, Check, X, Sliders, BookOpen, Scale, TrendingUp, FileText } from 'lucide-react';

interface QuestionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: any) => Promise<void>;
  initialData?: Question | null;
  mode: 'create' | 'edit';
}

const QUESTION_TYPES: {
  type: QuestionType;
  title: string;
  icon: any;
  desc: string;
  benchmarkLabel: string;
  benchmarkPlaceholder: string;
  defaultAnswerMode: 'choices' | 'text' | 'numeric';
}[] = [
  {
    type: 'FACTUAL',
    title: 'Factual / Technical',
    icon: BookOpen,
    desc: 'Has a definitive reference answer and formal reasoning pattern.',
    benchmarkLabel: 'Reference / Correct Answer',
    benchmarkPlaceholder: 'e.g., Equal to true valuation (Truthful bidding)',
    defaultAnswerMode: 'choices',
  },
  {
    type: 'SUBJECTIVE',
    title: 'Subjective Viewpoints',
    icon: Scale,
    desc: 'Multiple competing schools of thought, stances, or ethical/policy positions.',
    benchmarkLabel: 'Target Analytical Framework / Tradeoff Benchmark',
    benchmarkPlaceholder: 'e.g., Framework balancing consumer surplus vs. market liquidity',
    defaultAnswerMode: 'choices',
  },
  {
    type: 'PREDICTION',
    title: 'Quantitative Prediction',
    icon: TrendingUp,
    desc: 'Forecast a numerical market outcome, probability, or price.',
    benchmarkLabel: 'Theoretical Benchmark / Expected Value',
    benchmarkPlaceholder: 'e.g., $75 (Optimal equilibrium price)',
    defaultAnswerMode: 'numeric',
  },
  {
    type: 'OPEN_REASONING',
    title: 'Open-Ended Reasoning',
    icon: FileText,
    desc: 'Free-form derivation, conceptual explanation, or proof without discrete choices.',
    benchmarkLabel: 'Solution Rubric / Accepted Proof Steps',
    benchmarkPlaceholder: 'e.g., Must identify dominant strategy and demonstrate contradiction when b > v',
    defaultAnswerMode: 'text',
  },
];

export const QuestionModal: React.FC<QuestionModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  initialData,
  mode,
}) => {
  const [questionType, setQuestionType] = useState<QuestionType>('FACTUAL');
  const [questionText, setQuestionText] = useState('');
  const [answerFormat, setAnswerFormat] = useState<'choices' | 'text' | 'numeric'>('choices');
  const [choicesText, setChoicesText] = useState('');
  const [referenceAnswer, setReferenceAnswer] = useState('');
  const [acceptedReasoning, setAcceptedReasoning] = useState('');
  const [confidenceRequired, setConfidenceRequired] = useState(true);
  const [reasoningRequired, setReasoningRequired] = useState(true);
  const [predictionEnabled, setPredictionEnabled] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (initialData && mode === 'edit') {
      setQuestionType(initialData.question_type);
      setQuestionText(initialData.question_text);
      setReferenceAnswer(initialData.reference_answer || '');
      setAcceptedReasoning(initialData.accepted_reasoning || '');
      setConfidenceRequired(initialData.confidence_required);
      setReasoningRequired(initialData.reasoning_required);
      setPredictionEnabled(initialData.prediction_enabled);

      if (initialData.choices && initialData.choices.length > 0) {
        setAnswerFormat('choices');
        setChoicesText(initialData.choices.join('\n'));
      } else if (initialData.question_type === 'PREDICTION') {
        setAnswerFormat('numeric');
        setChoicesText('');
      } else {
        setAnswerFormat('text');
        setChoicesText('');
      }
    } else {
      // Default reset for create mode
      setQuestionType('FACTUAL');
      setQuestionText('');
      setAnswerFormat('choices');
      setChoicesText('Option A: Bid above valuation\nOption B: Bid below valuation\nOption C: Bid exactly equal to valuation');
      setReferenceAnswer('');
      setAcceptedReasoning('');
      setConfidenceRequired(true);
      setReasoningRequired(true);
      setPredictionEnabled(false);
    }
  }, [initialData, mode, isOpen]);

  // Adjust answer format when question type changes
  const handleTypeChange = (newType: QuestionType) => {
    setQuestionType(newType);
    const meta = QUESTION_TYPES.find((q) => q.type === newType);
    if (meta) {
      setAnswerFormat(meta.defaultAnswerMode);
      if (newType === 'PREDICTION') {
        setPredictionEnabled(true);
      }
    }
  };

  if (!isOpen) return null;

  const currentMeta = QUESTION_TYPES.find((q) => q.type === questionType) || QUESTION_TYPES[0];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      let parsedChoices: string[] | null = null;
      if (answerFormat === 'choices') {
        parsedChoices = choicesText
          .split('\n')
          .map((c) => c.trim())
          .filter((c) => c.length > 0);
        if (parsedChoices.length < 2) {
          throw new Error('Please provide at least 2 choices for Multiple Choice format.');
        }
      }

      await onSubmit({
        question_text: questionText.trim(),
        question_type: questionType,
        choices: parsedChoices,
        reference_answer: referenceAnswer.trim() || null,
        accepted_reasoning: acceptedReasoning.trim() || null,
        confidence_required: confidenceRequired,
        reasoning_required: reasoningRequired,
        prediction_enabled: predictionEnabled,
      });

      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to save question.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fade-in">
      <div className="bg-white rounded-2xl max-w-2xl w-full p-6 shadow-2xl border border-slate-100 max-h-[92vh] overflow-y-auto space-y-5">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div>
            <h3 className="font-extrabold text-slate-900 text-lg">
              {mode === 'edit' ? 'Edit Question' : 'Add New Diagnostic Question'}
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Configure question type, student answer format, and instructor benchmarks.
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {error && (
          <div className="p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-5">
          {/* 1. Question Type Selector */}
          <div>
            <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
              1. Select Question Type
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              {QUESTION_TYPES.map((qt) => {
                const Icon = qt.icon;
                const isSelected = questionType === qt.type;
                return (
                  <button
                    key={qt.type}
                    type="button"
                    onClick={() => handleTypeChange(qt.type)}
                    className={`p-3 rounded-xl border text-left transition-all ${
                      isSelected
                        ? 'border-indigo-600 bg-indigo-50/60 ring-2 ring-indigo-500/20'
                        : 'border-slate-200 hover:border-slate-300 bg-slate-50/50'
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <Icon className={`w-4 h-4 ${isSelected ? 'text-indigo-600' : 'text-slate-500'}`} />
                      <span className={`text-xs font-bold ${isSelected ? 'text-indigo-950' : 'text-slate-800'}`}>
                        {qt.title}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-500 mt-1 leading-snug">{qt.desc}</p>
                  </button>
                );
              })}
            </div>
          </div>

          {/* 2. Question Prompt */}
          <div>
            <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
              2. Question Prompt
            </label>
            <textarea
              required
              rows={3}
              value={questionText}
              onChange={(e) => setQuestionText(e.target.value)}
              placeholder="e.g. In a second-price sealed-bid auction with private values, what is the weakly dominant bidding strategy?"
              className="w-full px-4 py-3 rounded-xl border border-slate-300 focus:ring-2 focus:ring-indigo-600 text-sm outline-none transition-all placeholder:text-slate-400"
            />
          </div>

          {/* 3. Student Answering Format */}
          <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 space-y-3">
            <div className="flex items-center justify-between">
              <label className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                3. Student Answering Format
              </label>
              <div className="flex items-center gap-1 bg-white p-1 rounded-lg border border-slate-200 text-xs">
                <button
                  type="button"
                  onClick={() => setAnswerFormat('choices')}
                  className={`px-2.5 py-1 rounded-md font-semibold transition-colors ${
                    answerFormat === 'choices' ? 'bg-indigo-600 text-white' : 'text-slate-600 hover:bg-slate-100'
                  }`}
                >
                  Multiple Choice
                </button>
                <button
                  type="button"
                  onClick={() => setAnswerFormat('text')}
                  className={`px-2.5 py-1 rounded-md font-semibold transition-colors ${
                    answerFormat === 'text' ? 'bg-indigo-600 text-white' : 'text-slate-600 hover:bg-slate-100'
                  }`}
                >
                  Free-Form Text
                </button>
                {questionType === 'PREDICTION' && (
                  <button
                    type="button"
                    onClick={() => setAnswerFormat('numeric')}
                    className={`px-2.5 py-1 rounded-md font-semibold transition-colors ${
                      answerFormat === 'numeric' ? 'bg-indigo-600 text-white' : 'text-slate-600 hover:bg-slate-100'
                    }`}
                  >
                    Numerical Estimate
                  </button>
                )}
              </div>
            </div>

            {answerFormat === 'choices' ? (
              <div>
                <span className="text-[11px] text-slate-500 block mb-1">
                  Enter answer choices (one per line):
                </span>
                <textarea
                  rows={4}
                  value={choicesText}
                  onChange={(e) => setChoicesText(e.target.value)}
                  placeholder="Option A&#10;Option B&#10;Option C"
                  className="w-full p-3 bg-white rounded-xl border border-slate-300 text-xs font-mono outline-none focus:ring-2 focus:ring-indigo-600"
                />
              </div>
            ) : answerFormat === 'numeric' ? (
              <p className="text-xs text-indigo-700 bg-indigo-50/70 p-2.5 rounded-lg border border-indigo-100">
                Students will enter a quantitative number or price estimate along with their confidence and rationale.
              </p>
            ) : (
              <p className="text-xs text-indigo-700 bg-indigo-50/70 p-2.5 rounded-lg border border-indigo-100">
                Students will provide an open written explanation/derivation without multiple-choice options.
              </p>
            )}
          </div>

          {/* 4. Instructor Benchmark */}
          <div className="space-y-3">
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                4. {currentMeta.benchmarkLabel}
              </label>
              <input
                type="text"
                value={referenceAnswer}
                onChange={(e) => setReferenceAnswer(e.target.value)}
                placeholder={currentMeta.benchmarkPlaceholder}
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 text-sm outline-none focus:ring-2 focus:ring-indigo-600"
              />
              <span className="text-[11px] text-slate-400 mt-0.5 block">
                Revealed to students after session completion to verify learning against instructor benchmark.
              </span>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-600 uppercase tracking-wider mb-1">
                Accepted Reasoning Criteria / Rubric (Optional)
              </label>
              <input
                type="text"
                value={acceptedReasoning}
                onChange={(e) => setAcceptedReasoning(e.target.value)}
                placeholder="Key conceptual steps or accepted logic for the AI diagnostic..."
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-xs outline-none focus:ring-1 focus:ring-indigo-500"
              />
            </div>
          </div>

          {/* 5. Participation Options */}
          <div className="flex flex-wrap items-center gap-4 pt-1 border-t border-slate-100 text-xs">
            <label className="flex items-center gap-2 cursor-pointer text-slate-700">
              <input
                type="checkbox"
                checked={confidenceRequired}
                onChange={(e) => setConfidenceRequired(e.target.checked)}
                className="rounded text-indigo-600 focus:ring-indigo-500"
              />
              <span>Require Confidence Rating (1–5)</span>
            </label>

            <label className="flex items-center gap-2 cursor-pointer text-slate-700">
              <input
                type="checkbox"
                checked={reasoningRequired}
                onChange={(e) => setReasoningRequired(e.target.checked)}
                className="rounded text-indigo-600 focus:ring-indigo-500"
              />
              <span>Require Written Explanation</span>
            </label>
          </div>

          {/* Footer Buttons */}
          <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-slate-100">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-xl transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting || !questionText.trim()}
              className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-xs font-bold rounded-xl shadow-md transition-all flex items-center gap-1.5"
            >
              {isSubmitting ? (
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
              ) : (
                <>
                  <Check className="w-4 h-4" />
                  <span>{mode === 'edit' ? 'Update Question' : 'Save Question'}</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
