import React from 'react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Cell,
} from 'recharts';
import { ConfidenceDistributionItem } from '../../types';

interface ConfidenceDistributionChartProps {
  data: ConfidenceDistributionItem[];
  title?: string;
}

const CONFIDENCE_LABELS: Record<number, string> = {
  1: '1: Pure Guess',
  2: '2: Low',
  3: '3: Moderate',
  4: '4: High',
  5: '5: Certain',
};

const CONFIDENCE_COLORS = ['#94a3b8', '#60a5fa', '#3b82f6', '#4f46e5', '#4338ca'];

export const ConfidenceDistributionChart: React.FC<ConfidenceDistributionChartProps> = ({
  data,
  title = 'Confidence Level Breakdown',
}) => {
  const chartData = data.map((d) => ({
    level: CONFIDENCE_LABELS[d.confidence] || `${d.confidence}`,
    percentage: d.percentage,
    count: d.count,
    confidence: d.confidence,
  }));

  return (
    <div className="space-y-2">
      <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">{title}</div>
      <div className="h-56 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 20 }}>
            <XAxis
              dataKey="level"
              tick={{ fontSize: 11, fill: '#64748b' }}
              interval={0}
            />
            <YAxis unit="%" tick={{ fontSize: 11, fill: '#64748b' }} domain={[0, 100]} />
            <Tooltip
              formatter={(value: any, _, item: any) => [
                `${value}% (${item.payload.count} students)`,
                'Percentage',
              ]}
              contentStyle={{
                backgroundColor: '#ffffff',
                borderColor: '#e2e8f0',
                borderRadius: '0.75rem',
              }}
            />
            <Bar dataKey="percentage" radius={[6, 6, 0, 0]}>
              {chartData.map((_, index) => (
                <Cell key={`conf-cell-${index}`} fill={CONFIDENCE_COLORS[index % CONFIDENCE_COLORS.length]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
