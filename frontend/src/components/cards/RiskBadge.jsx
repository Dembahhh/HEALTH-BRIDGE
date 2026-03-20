import React from 'react';

/**
 * RiskBadge component to display blood pressure risk levels.
 * Categorization follows AHA/ACC 2017 guidelines:
 * - Normal: < 120/80
 * - Elevated: 120-129/<80
 * - Stage 1: 130-139/80-89
 * - Stage 2: >= 140/90
 */
const RiskBadge = ({ systolic, diastolic }) => {
  let label = 'Normal';
  let colorClass = 'bg-emerald-100 text-emerald-700 border-emerald-200';

  if (systolic >= 140 || diastolic >= 90) {
    label = 'Stage 2';
    colorClass = 'bg-rose-100 text-rose-700 border-rose-200';
  } else if (systolic >= 130 || diastolic >= 80) {
    label = 'Stage 1';
    colorClass = 'bg-orange-100 text-orange-700 border-orange-200';
  } else if (systolic >= 120) {
    label = 'Elevated';
    colorClass = 'bg-amber-100 text-amber-700 border-amber-200';
  }

  return (
    <span className={`px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider border rounded-full ${colorClass}`}>
      {label}
    </span>
  );
};

export default RiskBadge;
