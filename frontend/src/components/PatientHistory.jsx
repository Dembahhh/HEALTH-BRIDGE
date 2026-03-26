import React, { useState, useEffect } from 'react';
import api from '../services/api';
import RiskBadge from './RiskBadge';
import { Stethoscope, Smartphone } from 'lucide-react';


function getFormattedDate(isoString) {
  if (!isoString) return '';
  const date = new Date(isoString);
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  }).format(date);
}

function ExpandableSummary({ summary }) {
  const [expanded, setExpanded] = useState(false);
  if (!summary) return null;

  const shouldTruncate = summary.length > 150;
  const displayText = expanded || !shouldTruncate ? summary : `${summary.substring(0, 150)}...`;

  return (
    <div className="mt-3 rounded-md p-3 text-sm"
      style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-color)', color: 'var(--text-primary)' }}>

      <p className="whitespace-pre-wrap">{displayText}</p>
      {shouldTruncate && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="font-medium mt-2 hover:underline text-xs"
          style={{ color: 'var(--color-primary)' }}
        >
          {expanded ? 'Show Less' : 'Read Full Summary'}
        </button>
      )}
    </div>
  );
}

export default function PatientHistory({ patientId, patientName, apiBaseUrl = '' }) {
  const [history, setHistory] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let isMounted = true;

    async function loadHistory() {
      setIsLoading(true);
      setError('');
      try {
        const response = await api.get(`/patients/${patientId}/history`);

        const data = response.data;
        if (isMounted) setHistory(data);
      } catch (err) {
        if (isMounted) setError(err.message || 'Could not load patient history');
      } finally {
        if (isMounted) setIsLoading(false);
      }
    }

    if (patientId) {
      loadHistory();
    }

    return () => { isMounted = false; };
  }, [patientId, apiBaseUrl]);

  if (isLoading) {
    return (
      <div className="space-y-4 w-full">
        <h2 className="text-xl font-semibold mb-4" style={{ color: 'var(--text-primary)' }}>Health History {patientName ? `for ${patientName}` : ''}</h2>
        {[1, 2, 3].map((i) => (
          <div key={i} className="p-4 rounded-lg shadow-sm animate-pulse flex space-x-4"
            style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-color)' }}>
            <div className="h-full w-2 rounded-full" style={{ background: 'var(--bg-elevated)' }}></div>
            <div className="flex-1 py-1">
              <div className="h-4 rounded w-1/4 mb-4" style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-color)' }}></div>
              <div className="h-3 rounded w-1/2 mb-2" style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-color)' }}></div>
              <div className="h-3 rounded w-3/4" style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-color)' }}></div>
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 p-4 border border-red-200 rounded-lg w-full">
        <p className="text-red-700">{error}</p>
      </div>
    );
  }

  if (history.length === 0) {
    return (
      <div className="rounded-lg p-8 w-full text-center"
        style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-color)' }}>
        <p className="font-medium" style={{ color: 'var(--text-secondary)' }}>No history found for this patient</p>
        <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>Check-ins and clinical screenings will appear here.</p>
      </div>
    );
  }

  return (
    <div className="w-full">
      <h2 className="text-xl font-semibold mb-6" style={{ color: 'var(--text-primary)' }}>Health History {patientName ? `for ${patientName}` : ''}</h2>
      <div className="space-y-6 relative before:absolute before:inset-0 before:ml-5 before:-translate-x-px md:before:mx-auto md:before:translate-x-0 before:h-full before:w-0.5 before:bg-gradient-to-b before:from-transparent before:via-slate-300 before:to-transparent">
        {history.map((item, index) => {
          const isScreening = item.type === 'screening';
          const isTracking = item.type === 'tracking';
          const date = item.timestamp || item.created_at;

          return (
            <div key={item.id || index} className="relative flex items-center justify-between md:justify-normal md:odd:flex-row-reverse group is-active">
              {/* Timeline marker */}
              <div className="flex items-center justify-center w-10 h-10 rounded-full shadow shrink-0 md:order-1 md:group-odd:-translate-x-1/2 md:group-even:translate-x-1/2"
                style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-color)', color: 'var(--text-muted)' }}>
                {isScreening ? (
                  <Stethoscope className="w-5 h-5" />
                ) : (
                  <Smartphone className="w-5 h-5" />
                )}
              </div>

              {/* Event Card */}
              <div className="w-[calc(100%-4rem)] md:w-[calc(50%-2.5rem)] p-4 rounded-lg shadow"
                style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-color)' }}>
                <div className="flex justify-between items-start mb-2">
                  <div className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
                    {isScreening ? 'Clinical Screening' : 'Patient Check-in'}
                  </div>
                  <time className="text-xs font-medium" style={{ color: 'var(--text-muted)' }}>{getFormattedDate(date)}</time>
                </div>

                {isScreening && (
                  <div className="space-y-3">
                    <div className="text-xs font-medium" style={{ color: 'var(--text-primary)' }}>
                      Role: {item.practitioner_role?.replace('_', ' ')}
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {item.bp_classification && (
                        <RiskBadge
                          category={item.bp_classification.category}
                          label={`BP: ${item.bp_classification.label}`}
                          size="sm"
                        />
                      )}
                      {item.glucose_classification && (
                        <RiskBadge
                          category={item.glucose_classification.category}
                          label={`Glucose: ${item.glucose_classification.label}`}
                          size="sm"
                        />
                      )}
                    </div>
                    {item.agent_summary && (
                      <ExpandableSummary summary={item.agent_summary} />
                    )}
                  </div>
                )}

                {isTracking && (
                  <div className="space-y-2">
                    <div className="flex justify-between items-center p-2 rounded"
                      style={{ background: 'var(--bg-elevated)' }}>
                      <span className="font-medium text-sm capitalize" style={{ color: 'var(--text-secondary)' }}>{item.log_type}</span>
                      <span className="font-bold" style={{ color: 'var(--text-primary)' }}>{item.value}</span>
                    </div>
                    {item.classification && (
                      <RiskBadge
                        category={item.classification.category}
                        label={item.classification.label}
                        size="sm"
                      />
                    )}
                    {item.nudge_text && (
                      <p className="text-sm p-2 rounded italic mt-2"
                        style={{ color: 'var(--color-primary)', background: 'rgba(var(--color-primary-rgb), 0.08)' }}>
                        "{item.nudge_text}"
                      </p>
                    )}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
