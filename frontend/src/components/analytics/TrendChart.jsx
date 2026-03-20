import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer
} from 'recharts';

/**
 * Reusable TrendChart component using Recharts.
 * 
 * @param {Array} data - Array of objects containing the chart data
 * @param {String} dataKey - The key corresponding to the primary line
 * @param {String} color - The stroke color of the primary line
 * @param {String} secondaryDataKey - Optional key for a secondary line (e.g. diastolic BP)
 * @param {String} secondaryColor - Optional color for secondary line
 */
const TrendChart = ({ data, dataKey, color = '#2563eb', secondaryDataKey, secondaryColor = '#94a3b8' }) => {
  if (!data || data.length === 0) {
    return (
      <div className="flex h-48 w-full items-center justify-center rounded-lg bg-gray-50 border border-neutral-100">
        <p className="text-sm text-neutral-400">No data available for this week</p>
      </div>
    );
  }

  return (
    <div className="h-48 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E5E7EB" />
          <XAxis 
            dataKey="date" 
            axisLine={false}
            tickLine={false}
            tick={{ fontSize: 12, fill: '#6B7280' }}
            padding={{ left: 10, right: 10 }}
          />
          <YAxis 
            axisLine={false}
            tickLine={false}
            tick={{ fontSize: 12, fill: '#6B7280' }}
          />
          <Tooltip 
            contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
          />
          <Line 
            type="monotone" 
            dataKey={dataKey} 
            stroke={color} 
            strokeWidth={3}
            dot={{ r: 4, fill: color, strokeWidth: 2, stroke: 'white' }} 
            activeDot={{ r: 6 }} 
          />
          
          {secondaryDataKey && (
             <Line 
               type="monotone" 
               dataKey={secondaryDataKey} 
               stroke={secondaryColor} 
               strokeWidth={3}
               dot={{ r: 4, fill: secondaryColor, strokeWidth: 2, stroke: 'white' }} 
               activeDot={{ r: 6 }} 
             />
          )}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

export default TrendChart;
