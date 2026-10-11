import React from 'react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  Cell,
} from 'recharts';
import { AnswerDistributionItem } from '../../types';
import { CheckCircle2 } from 'lucide-react';

interface AnswerDistributionChartProps {
  round1Data: AnswerDistributionItem[];
  round2Data?: AnswerDistributionItem[];
  referenceAnswer?: string | null;
}

export const AnswerDistributionChart: React.FC<AnswerDistributionChartProps> = ({
  round1Data,
  round2Data = [],
  referenceAnswer,
}) => {
  // Merge answers from both rounds into a common list
  const answerKeys = Array.from(
    new Set([...round1Data.map((d) => d.answer), ...round2Data.map((d) => d.answer)])
  );

  const chartData = answerKeys.map((ans) => {
    const r1 = round1Data.find((d) => d.answer === ans);
    const r2 = round2Data.find((d) => d.answer === ans);
    const isCorrect = referenceAnswer
      ? ans.trim().toLowerCase() === referenceAnswer.trim().toLowerCase()
      : false;

    return {
      answer: ans,
      isCorrect,
      'Round 1 (%)': r1 ? r1.percentage : 0,
      'Round 1 Count': r1 ? r1.count : 0,
      'Round 1 Avg Conf': r1 ? r1.average_confidence : 0,
      'Round 2 (%)': r2 ? r2.percentage : 0,
      'Round 2 Count': r2 ? r2.count : 0,
      'Round 2 Avg Conf': r2 ? r2.average_confidence : 0,
    };
  });

  if (chartData.length === 0) {
    return (
      <div className="h-64 flex items-center justify-center text-slate-400 text-sm">
        No response data available yet.
      </div>
    );
  }

  const hasRound2 = round2Data.length > 0;

  return (
    <div className="space-y-4">
      <div className="h-72 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 10, right: 20, left: -10, bottom: 25 }}>
            <XAxis
              dataKey="answer"
              tick={{ fontSize: 12, fill: '#64748b' }}
              interval={0}
              angle={-15}
              textAnchor="end"
            />
            <YAxis
              unit="%"
              tick={{ fontSize: 12, fill: '#64748b' }}
              domain={[0, 100]}
            />
            <Tooltip
              formatter={(value: any, name: any, item: any) => {
                if (name === 'Round 1 (%)') {
                  return [`${value}% (${item.payload['Round 1 Count']} responses, avg conf: ${item.payload['Round 1 Avg Conf']}/5)`, 'Round 1'];
                }
                if (name === 'Round 2 (%)') {
                  return [`${value}% (${item.payload['Round 2 Count']} responses, avg conf: ${item.payload['Round 2 Avg Conf']}/5)`, 'Round 2'];
                }
                return [value, name];
              }}
              contentStyle={{
                backgroundColor: '#ffffff',
                borderColor: '#e2e8f0',
                borderRadius: '0.75rem',
                boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
              }}
            />
            <Legend verticalAlign="top" height={36} />
            <Bar dataKey="Round 1 (%)" fill="#6366f1" radius={[6, 6, 0, 0]}>
              {chartData.map((entry, index) => (
                <Cell
                  key={`cell-r1-${index}`}
                  fill={entry.isCorrect ? '#10b981' : '#6366f1'}
                />
              ))}
            </Bar>
            {hasRound2 && (
              <Bar dataKey="Round 2 (%)" fill="#f59e0b" radius={[6, 6, 0, 0]}>
                {chartData.map((entry, index) => (
                  <Cell
                    key={`cell-r2-${index}`}
                    fill={entry.isCorrect ? '#059669' : '#f59e0b'}
                  />
                ))}
              </Bar>
            )}
          </BarChart>
        </ResponsiveContainer>
      </div>

      {referenceAnswer && (
        <div className="flex items-center gap-2 text-xs font-medium text-emerald-700 bg-emerald-50 px-3 py-2 rounded-lg border border-emerald-200">
          <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
          <span>
            <strong>Reference Answer:</strong> {referenceAnswer} (highlighted in green)
          </span>
        </div>
      )}
    </div>
  );
};
