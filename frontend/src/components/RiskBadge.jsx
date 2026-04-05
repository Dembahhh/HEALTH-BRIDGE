import React from 'react';
import { getSeverityClass } from '../utils/clinicalColors';

const colorMap = {
  normal: 'bg-green-100 text-green-800',
  elevated: 'bg-yellow-100 text-yellow-800',
  pre_diabetic: 'bg-yellow-100 text-yellow-800',
  low_risk: 'bg-yellow-100 text-yellow-800',
  stage_1: 'bg-orange-100 text-orange-800',
  moderate_risk: 'bg-orange-100 text-orange-800',
  stage_2: 'bg-red-100 text-red-800',
  diabetic: 'bg-red-100 text-red-800',
  high_risk: 'bg-red-100 text-red-800',
  crisis: 'bg-red-700 text-white',
};

const sizeMap = {
  sm: 'px-2 py-0.5 text-xs',
  md: 'px-3 py-1 text-sm',
};

export default function RiskBadge({ category, label, size = 'md' }) {
  const colorClass = colorMap[category] || 'bg-gray-100 text-gray-800';
  const sizeClass = sizeMap[size] || sizeMap.md;

  return (
    <span className={`inline-flex items-center justify-center font-medium rounded-full ${colorClass} ${sizeClass}`}>
      {label}
    </span>
  );
}
