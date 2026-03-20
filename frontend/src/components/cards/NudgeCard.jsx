import React from 'react';
import {
  Lightbulb,
  AlertCircle,
  Stethoscope,
  Activity,
  Heart
} from 'lucide-react';

/**
 * NudgeCard displays the AI-generated insight based on tracking logs.
 * 
 * @param {Object} nudge - Object containing { text, action_type, generated_at }
 */
const NudgeCard = ({ nudge }) => {
  if (!nudge) {
    return (
      <div className="rounded-xl border border-blue-100 bg-blue-50/50 p-4">
        <div className="flex items-start gap-3">
          <div className="rounded-full bg-blue-100 p-2 text-blue-600">
            <Lightbulb className="h-5 w-5" />
          </div>
          <div>
            <h4 className="font-medium text-blue-900">Your Health Coach</h4>
            <p className="mt-1 text-sm text-blue-800/80">
              Log your vitals or medications to get personalized insights from your AI health coach.
            </p>
          </div>
        </div>
      </div>
    );
  }

  // Determine styling based on action type
  let config = {
    bg: 'bg-emerald-50/50',
    border: 'border-emerald-100',
    iconBg: 'bg-emerald-100',
    iconText: 'text-emerald-600',
    titleText: 'text-emerald-900',
    bodyText: 'text-emerald-800/80',
    icon: <Heart className="h-5 w-5" />
  };

  if (nudge.action_type === 'referral' || nudge.action_type === 'crisis') {
    config = {
      bg: 'bg-red-50/50',
      border: 'border-red-200',
      iconBg: 'bg-red-100',
      iconText: 'text-red-600',
      titleText: 'text-red-900',
      bodyText: 'text-red-800/90 font-medium',
      icon: <AlertCircle className="h-5 w-5" />
    };
  } else if (nudge.action_type === 'medication' || nudge.text.toLowerCase().includes('medication')) {
    config = {
      bg: 'bg-blue-50/50',
      border: 'border-blue-100',
      iconBg: 'bg-blue-100',
      iconText: 'text-blue-600',
      titleText: 'text-blue-900',
      bodyText: 'text-blue-800/80',
      icon: <Stethoscope className="h-5 w-5" />
    };
  } else if (nudge.action_type === 'bp' || nudge.action_type === 'glucose') {
    config = {
      bg: 'bg-indigo-50/50',
      border: 'border-indigo-100',
      iconBg: 'bg-indigo-100',
      iconText: 'text-indigo-600',
      titleText: 'text-indigo-900',
      bodyText: 'text-indigo-800/80',
      icon: <Activity className="h-5 w-5" />
    };
  }

  return (
    <div className={`rounded-xl border ${config.border} ${config.bg} p-4 shadow-sm transition-all hover:shadow-md`}>
      <div className="flex items-start gap-4">
        <div className={`rounded-full ${config.iconBg} p-2 ${config.iconText} shrink-0`}>
          {config.icon}
        </div>
        <div className="flex-1">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 mb-1">
            <h4 className={`font-semibold ${config.titleText}`}>Insight</h4>
            {nudge.generated_at && (
              <span className={`text-xs ${config.bodyText} opacity-70`}>
                {new Date(nudge.generated_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </span>
            )}
          </div>
          <p className={`text-sm leading-relaxed ${config.bodyText}`}>
            {nudge.text}
          </p>
        </div>
      </div>
    </div>
  );
};

export default NudgeCard;
