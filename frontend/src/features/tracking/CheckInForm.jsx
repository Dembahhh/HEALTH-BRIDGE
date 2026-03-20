import React, { useState } from 'react';
import { trackingApi } from '../../services/api';
import { Activity, Droplets, Pill, Loader2, CheckCircle2 } from 'lucide-react';

const CheckInForm = ({ onLogSuccess }) => {
  const [activeTab, setActiveTab] = useState('bp'); // bp, glucose, medication
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [successMsg, setSuccessMsg] = useState('');
  const [errorMsg, setErrorMsg] = useState('');

  // Form states
  const [bp, setBp] = useState({ systolic: '', diastolic: '' });
  const [glucose, setGlucose] = useState({ value: '', test_type: 'random', unit: 'mmol_l' });
  // Simplified medication UI for this phase: just marking all as taken or skipped
  const [medsStatus, setMedsStatus] = useState('taken');

  const handleLog = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    setErrorMsg('');
    setSuccessMsg('');

    try {
      let payload = { log_type: activeTab };

      if (activeTab === 'bp') {
        if (!bp.systolic || !bp.diastolic) throw new Error("Please enter both readings");
        payload.systolic = parseInt(bp.systolic);
        payload.diastolic = parseInt(bp.diastolic);
      } else if (activeTab === 'glucose') {
        if (!glucose.value) throw new Error("Please enter a glucose value");
        payload.glucose_value = parseFloat(glucose.value);
        payload.glucose_test_type = glucose.test_type;
        payload.glucose_unit = glucose.unit;
      } else if (activeTab === 'medication') {
        // Mock payload for medication for Phase 1 demo
        payload.medications = [
          { name: "Daily Meds", dosage: "1 dose", taken: medsStatus === 'taken' }
        ];
      }

      await trackingApi.logTracking(payload);

      setSuccessMsg(`Successfully logged your ${activeTab}.`);

      // Reset forms
      setBp({ systolic: '', diastolic: '' });
      setGlucose({ ...glucose, value: '' });

      if (onLogSuccess) {
        // Add a slight delay so the backend background task finishes generating the nudge
        setTimeout(onLogSuccess, 1500);
      }

      // Clear success message after 3 seconds
      setTimeout(() => setSuccessMsg(''), 3000);

    } catch (err) {
      console.error(err);
      setErrorMsg(err.message || err.response?.data?.detail || "Failed to log data");
    } finally {
      setIsSubmitting(false);
    }
  };

  const tabs = [
    { id: 'bp', label: 'Blood Pressure', icon: <Activity className="h-4 w-4" /> },
    { id: 'glucose', label: 'Blood Sugar', icon: <Droplets className="h-4 w-4" /> },
    { id: 'medication', label: 'Medications', icon: <Pill className="h-4 w-4" /> },
  ];

  return (
    <div className="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm">
      <h3 className="text-lg font-semibold text-neutral-900 mb-4">Quick Check-in</h3>

      {/* Tabs */}
      <div className="flex space-x-2 border-b border-neutral-100 pb-4 mb-5 overflow-x-auto no-scrollbar">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => { setActiveTab(tab.id); setErrorMsg(''); setSuccessMsg(''); }}
            className={`flex items-center gap-2 whitespace-nowrap rounded-full px-4 py-2 text-sm font-medium transition-colors ${activeTab === tab.id
                ? 'bg-primary-50 text-primary-700 ring-1 ring-primary-600/20'
                : 'bg-neutral-50 text-neutral-600 hover:bg-neutral-100'
              }`}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      <form onSubmit={handleLog} className="space-y-4">
        {activeTab === 'bp' && (
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-1">Systolic (Top)</label>
              <input
                type="number"
                required
                className="w-full rounded-xl border border-neutral-300 px-4 py-3 text-lg focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20 transition-all"
                placeholder="120"
                value={bp.systolic}
                onChange={(e) => setBp({ ...bp, systolic: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-1">Diastolic (Bottom)</label>
              <input
                type="number"
                required
                className="w-full rounded-xl border border-neutral-300 px-4 py-3 text-lg focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20 transition-all"
                placeholder="80"
                value={bp.diastolic}
                onChange={(e) => setBp({ ...bp, diastolic: e.target.value })}
              />
            </div>
          </div>
        )}

        {activeTab === 'glucose' && (
          <div className="space-y-4">
            <div className="flex gap-4">
              <div className="flex-1">
                <label className="block text-sm font-medium text-neutral-700 mb-1">Reading</label>
                <input
                  type="number"
                  step="0.1"
                  required
                  className="w-full rounded-xl border border-neutral-300 px-4 py-3 text-lg focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20 transition-all"
                  placeholder="5.5"
                  value={glucose.value}
                  onChange={(e) => setGlucose({ ...glucose, value: e.target.value })}
                />
              </div>
              <div className="w-1/3">
                <label className="block text-sm font-medium text-neutral-700 mb-1">Unit</label>
                <select
                  className="w-full rounded-xl border border-neutral-300 px-4 py-3 text-base bg-white focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20 transition-all"
                  value={glucose.unit}
                  onChange={(e) => setGlucose({ ...glucose, unit: e.target.value })}
                >
                  <option value="mmol_l">mmol/L</option>
                  <option value="mg_dl">mg/dL</option>
                </select>
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-2">When was this test?</label>
              <div className="flex gap-3">
                <label className={`flex flex-1 cursor-pointer items-center justify-center rounded-lg border px-4 py-3 text-sm font-medium transition-all ${glucose.test_type === 'fasting' ? 'border-primary-600 bg-primary-50 text-primary-700' : 'border-neutral-200 text-neutral-600 hover:bg-neutral-50'}`}>
                  <input type="radio" className="peer sr-only" name="test_type" value="fasting" checked={glucose.test_type === 'fasting'} onChange={() => setGlucose({ ...glucose, test_type: 'fasting' })} />
                  Fasting
                </label>
                <label className={`flex flex-1 cursor-pointer items-center justify-center rounded-lg border px-4 py-3 text-sm font-medium transition-all ${glucose.test_type === 'random' ? 'border-primary-600 bg-primary-50 text-primary-700' : 'border-neutral-200 text-neutral-600 hover:bg-neutral-50'}`}>
                  <input type="radio" className="peer sr-only" name="test_type" value="random" checked={glucose.test_type === 'random'} onChange={() => setGlucose({ ...glucose, test_type: 'random' })} />
                  Random
                </label>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'medication' && (
          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-2">Did you take your medications today?</label>
            <div className="flex gap-3">
              <button
                type="button"
                className={`flex-1 rounded-xl border py-4 text-center font-medium transition-all ${medsStatus === 'taken' ? 'border-emerald-600 bg-emerald-50 text-emerald-700 ring-1 ring-emerald-600/20' : 'border-neutral-200 text-neutral-600 hover:bg-neutral-50'}`}
                onClick={() => setMedsStatus('taken')}
              >
                Yes, Took Them
              </button>
              <button
                type="button"
                className={`flex-1 rounded-xl border py-4 text-center font-medium transition-all ${medsStatus === 'skipped' ? 'border-red-600 bg-red-50 text-red-700 ring-1 ring-red-600/20' : 'border-neutral-200 text-neutral-600 hover:bg-neutral-50'}`}
                onClick={() => setMedsStatus('skipped')}
              >
                Missed Them
              </button>
            </div>
          </div>
        )}

        {errorMsg && (
          <div className="rounded-lg bg-red-50 p-3 text-sm text-red-600 mt-2">
            {errorMsg}
          </div>
        )}

        {successMsg && (
          <div className="flex items-center gap-2 rounded-lg bg-emerald-50 p-3 text-sm font-medium text-emerald-700 mt-2">
            <CheckCircle2 className="h-4 w-4" />
            {successMsg}
          </div>
        )}

        <button
          type="submit"
          disabled={isSubmitting}
          className="mt-6 flex w-full items-center justify-center rounded-xl bg-primary-600 px-6 py-3.5 text-base font-medium text-white shadow-sm transition-all hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 disabled:opacity-70 disabled:cursor-not-allowed"
        >
          {isSubmitting ? (
            <>
              <Loader2 className="mr-2 h-5 w-5 animate-spin" /> Saving...
            </>
          ) : (
            `Log ${tabs.find(t => t.id === activeTab).label}`
          )}
        </button>
      </form>
    </div>
  );
};

export default CheckInForm;
