import React from 'react';
import { useNavigate } from 'react-router-dom';
import ScreeningWizard from '../components/ScreeningWizard';

export default function ScreeningPage() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen" style={{ background: 'var(--bg-primary)' }}>
      <div className="max-w-4xl mx-auto px-4 py-8 pb-24">
        {/* Page Header */}
        <div className="flex items-center mb-8 border-b pb-4" style={{ borderColor: 'var(--border-color)' }}>
          <button
            onClick={() => navigate(-1)}
            className="mr-4 p-2 rounded-full transition-colors"
            style={{ color: 'var(--text-secondary)', background: 'var(--bg-elevated)' }}
            aria-label="Go back"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
          </button>
          <div>
            <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>NCD Screening</h1>
            <p className="text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>Hypertension & Diabetes</p>
          </div>
        </div>

        {/* Main Content */}
        <div className="w-full">
          <ScreeningWizard />
        </div>
      </div>
    </div>
  );
}
