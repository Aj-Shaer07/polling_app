import React from 'react';
import { BeliefTransitionItem } from '../../types';
import { ArrowRight, RefreshCw, CheckCircle, MessageSquare } from 'lucide-react';

interface BeliefTransitionsMatrixProps {
  transitions: BeliefTransitionItem[];
}

export const BeliefTransitionsMatrix: React.FC<BeliefTransitionsMatrixProps> = ({ transitions }) => {
  if (!transitions || transitions.length === 0) {
    return (
      <div className="p-8 text-center text-slate-400 text-sm bg-slate-50 rounded-2xl border border-slate-200">
        Belief transitions will populate once Round 2 revisions are submitted.
      </div>
    );
  }

  const totalTransitions = transitions.reduce((acc, t) => acc + t.count, 0);
  const changedTransitions = transitions.filter((t) => t.from_answer !== t.to_answer);
  const totalChanged = changedTransitions.reduce((acc, t) => acc + t.count, 0);
  const changeRate = totalTransitions > 0 ? Math.round((totalChanged / totalTransitions) * 100) : 0;

  return (
    <div className="space-y-4">
      {/* Metric Summary Header */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div className="bg-slate-50 border border-slate-200 rounded-xl p-3.5 text-center">
          <div className="text-xs text-slate-500 font-semibold uppercase tracking-wider">Total Paired</div>
          <div className="text-2xl font-bold text-slate-900 mt-0.5">{totalTransitions}</div>
        </div>
        <div className="bg-indigo-50 border border-indigo-200 rounded-xl p-3.5 text-center">
          <div className="text-xs text-indigo-700 font-semibold uppercase tracking-wider">Switched Position</div>
          <div className="text-2xl font-bold text-indigo-700 mt-0.5">
            {totalChanged} <span className="text-sm font-normal">({changeRate}%)</span>
          </div>
        </div>
        <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-3.5 text-center">
          <div className="text-xs text-emerald-700 font-semibold uppercase tracking-wider">Retained Position</div>
          <div className="text-2xl font-bold text-emerald-700 mt-0.5">
            {totalTransitions - totalChanged} <span className="text-sm font-normal">({100 - changeRate}%)</span>
          </div>
        </div>
      </div>

      {/* Transition pathways list */}
      <div className="divide-y divide-slate-100 border border-slate-200 rounded-xl overflow-hidden bg-white shadow-sm">
        {transitions.map((item, index) => {
          const isChanged = item.from_answer !== item.to_answer;
          return (
            <div key={index} className="p-4 hover:bg-slate-50/70 transition-colors">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="flex items-center gap-2.5">
                  <span
                    className={`inline-flex items-center px-2.5 py-1 rounded-md text-xs font-semibold ${
                      isChanged
                        ? 'bg-amber-100 text-amber-800 border border-amber-200'
                        : 'bg-slate-100 text-slate-700 border border-slate-200'
                    }`}
                  >
                    {isChanged ? (
                      <>
                        <RefreshCw className="w-3 h-3 mr-1" /> Switched
                      </>
                    ) : (
                      <>
                        <CheckCircle className="w-3 h-3 mr-1" /> Retained
                      </>
                    )}
                  </span>

                  <div className="flex items-center gap-2 text-sm font-medium text-slate-800">
                    <span className="bg-slate-100 px-2.5 py-1 rounded-md font-mono text-xs">{item.from_answer}</span>
                    <ArrowRight className="w-4 h-4 text-slate-400 flex-shrink-0" />
                    <span className="bg-indigo-50 text-indigo-900 border border-indigo-100 px-2.5 py-1 rounded-md font-mono text-xs">
                      {item.to_answer}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-4 text-xs text-slate-500">
                  <div>
                    <strong className="text-slate-900 font-bold text-sm">{item.count}</strong> students ({item.percentage}%)
                  </div>
                  <div>
                    Conf: <span className="font-semibold text-slate-700">{item.avg_initial_confidence}</span> →{' '}
                    <span className="font-semibold text-indigo-600">{item.avg_revised_confidence}</span> / 5.0
                  </div>
                </div>
              </div>

              {/* Sample self-reported change reasons */}
              {item.sample_change_reasons && item.sample_change_reasons.length > 0 && (
                <div className="mt-3 pl-3 border-l-2 border-indigo-200 space-y-1">
                  <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1">
                    <MessageSquare className="w-3 h-3" /> Student reported influence:
                  </div>
                  {item.sample_change_reasons.map((reason, rIdx) => (
                    <p key={rIdx} className="text-xs text-slate-600 italic">
                      "{reason}"
                    </p>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
