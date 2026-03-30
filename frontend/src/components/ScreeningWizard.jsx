import api from '../services/api';
import PatientSearch from './PatientSearch';
import RiskBadge from './RiskBadge';
import React, { useState, useEffect } from 'react';

export default function ScreeningWizard({ apiBaseUrl = '' }) {
  const [step, setStep] = useState(1);
  const [screeningData, setScreeningData] = useState({
    patient: null,
    consentGiven: false,
    practitionerRole: 'nurse',
    bp: { systolic: '', diastolic: '', classification: null },
    glucose: { include: false, value: '', unit: 'mmol_l', testType: 'random', classification: null },
  });

  const [isClassifying, setIsClassifying] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submissionResult, setSubmissionResult] = useState(null);
  const [error, setError] = useState(null);

  const updateData = (field, value) => {
    setScreeningData(prev => ({ ...prev, [field]: value }));
  };

  const handleNext = () => {
    setError(null);
    setStep(s => s + 1);
  };

  const handleBack = () => {
    setError(null);
    setStep(s => s - 1);
  };

  const resetWizard = () => {
    setStep(1);
    setScreeningData({
      patient: null,
      consentGiven: false,
      practitionerRole: 'nurse',
      bp: { systolic: '', diastolic: '', classification: null },
      glucose: { include: false, value: '', unit: 'mmol_l', testType: 'random', classification: null },
    });
    setSubmissionResult(null);
    setError(null);
  };

  // Step 2: Submit BP for classification via tracking log endpoint (which returns classification)
  // Or just store it locally. Wait, the prompt said: "Submit BP Reading button -> calls POST /api/tracking/log with type 'bp' ... On success: immediately show RiskBadge".
  const handleBPSubmit = async () => {
    try {
      setIsClassifying(true);
      setError(null);

      const sys = parseInt(screeningData.bp.systolic, 10);
      const dia = parseInt(screeningData.bp.diastolic, 10);
      if (isNaN(sys) || isNaN(dia)) throw new Error("Please enter valid numbers for blood pressure.");
      if (sys < 60 || sys > 300) throw new Error("Systolic must be between 60 and 300.");
      if (dia < 30 || dia > 200) throw new Error("Diastolic must be between 30 and 200.");

      const payload = {
        log_type: 'bp',
        systolic: sys,
        diastolic: dia
      };

      const res = await api.post(`/tracking/log`, payload);
      const data = res.data;

      updateData('bp', { ...screeningData.bp, classification: data.bp_classification });
      handleNext();
    } catch (err) {
      setError(err.message);
    } finally {
      setIsClassifying(false);
    }
  };

  // Step 3: Submit Glucose (if included) for classification
  const handleGlucoseSubmit = async () => {
    try {
      if (!screeningData.glucose.include) {
        handleNext();
        return;
      }

      setIsClassifying(true);
      setError(null);

      const val = parseFloat(screeningData.glucose.value);
      if (isNaN(val)) throw new Error("Please enter a valid glucose value.");

      const payload = {
        log_type: 'glucose',
        glucose_value: val,
        glucose_test_type: screeningData.glucose.testType,
        glucose_unit: screeningData.glucose.unit
      };

      const res = await api.post(`/tracking/log`, payload);
      const data = res.data;

      updateData('glucose', { ...screeningData.glucose, classification: data.glucose_classification });
      handleNext();
    } catch (err) {
      setError(err.message);
    } finally {
      setIsClassifying(false);
    }
  };

  // Step 4: Submit Full Screening
  const submitScreening = async () => {
    try {
      setIsSubmitting(true);
      setError(null);

      // Assemble the screening payload
      const payload = {
        patient_id: screeningData.patient.id || screeningData.patient._id,
        bp_systolic: parseInt(screeningData.bp.systolic, 10),
        bp_diastolic: parseInt(screeningData.bp.diastolic, 10),
        practitioner_role: screeningData.practitionerRole,
        consent_given: screeningData.consentGiven,
        notes: ""
      };

      if (screeningData.glucose.include) {
        payload.glucose_value = parseFloat(screeningData.glucose.value);
        payload.glucose_unit = screeningData.glucose.unit;
        payload.glucose_test_type = screeningData.glucose.testType;
      }

      const res = await api.post(`/screening/submit`, payload);

      setSubmissionResult(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Error running the Agent pipeline.');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Run initial submit when arriving at Step 4
  React.useEffect(() => {
    if (step === 4 && !submissionResult && !isSubmitting && !error) {
      submitScreening();
    }
  }, [step]);


  const renderStepIndicator = () => (
    <div className="mb-6 flex justify-between items-center text-sm font-medium"
      style={{ color: 'var(--muted)' }}>
      <span>Step {step} of 4</span>
      <div className="flex space-x-1">
        {[1, 2, 3, 4].map(i => (
          <div key={i} className={"h-2 w-8 rounded-full"} style={{ background: i <= step ? 'var(--color-primary)' : 'var(--bg-elevated)' }} />
        ))}
      </div>
    </div>
  );

  return (
    <div className="w-full max-w-2xl mx-auto p-6 rounded-lg shadow-sm"
      style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-color)' }}>
      {renderStepIndicator()}

      {/* ERROR DISPLAY */}
      {error && (
        <div className="mb-4 bg-red-50 p-3 rounded-md border border-red-200 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* STEP 1: Patient and Consent */}
      {step === 1 && (
        <div className="space-y-6 animate-fadeIn">
          <div>
            <h2 className="text-xl font-semibold" style={{ color: 'var(--text-primary)' }}>Select Patient</h2>
            {!screeningData.patient ? (
              <PatientSearch onPatientSelected={(p) => updateData('patient', p)} apiBaseUrl={apiBaseUrl} />
            ) : (
              <div className="p-4 rounded-md flex justify-between items-center"
                style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-color)' }}>
                <div>
                  <p className="font-medium" style={{ color: 'var(--text-primary)' }}>{screeningData.patient.name}</p>
                  <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>{screeningData.patient.phone || 'No phone'} | Age: {screeningData.patient.age || 'Unknown'}</p>
                </div>
                <button
                  onClick={() => updateData('patient', null)}
                  className="text-sm font-medium hover:underline"
                  style={{ color: 'var(--color-primary)' }}
                >
                  Change
                </button>
              </div>
            )}
          </div>

          <div className="pt-4 border-t" style={{ borderColor: 'var(--border-color)' }}>
            <label className="flex items-start space-x-3 cursor-pointer">
              <input
                type="checkbox"
                checked={screeningData.consentGiven}
                onChange={(e) => updateData('consentGiven', e.target.checked)}
                className="mt-1 h-4 w-4 rounded"
                style={{ borderColor: 'var(--border-color)' }}
              />
              <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                Patient has given verbal consent to have their data recorded in this system.
              </span>
            </label>
          </div>

          <div className="flex justify-end pt-4">
            <button
              onClick={handleNext}
              disabled={!screeningData.patient || !screeningData.consentGiven}
              className="btn-primary px-6 py-2 disabled:opacity-50 disabled:cursor-not-allowed"
              style={{ background: 'var(--color-primary)' }}
            >
              Next Step
            </button>
          </div>
        </div>
      )}

      {/* STEP 2: Blood Pressure */}
      {step === 2 && (
        <div className="space-y-6 animate-fadeIn">
          <h2 className="text-xl font-semibold" style={{ color: 'var(--text-primary)' }}>Measure Blood Pressure</h2>

          <div>
            <label className="block text-sm font-medium mb-1" style={{ color: 'var(--text-primary)' }}>Practitioner Role</label>
            <select
              value={screeningData.practitionerRole}
              onChange={(e) => updateData('practitionerRole', e.target.value)}
              className="input w-full md:w-1/2 p-2"
            >
              <option value="doctor">Doctor</option>
              <option value="nurse">Nurse</option>
              <option value="clinical_officer">Clinical Officer</option>
              <option value="chv">Community Health Volunteer (CHV)</option>
            </select>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1" style={{ color: 'var(--text-primary)' }}>Systolic (mmHg)</label>
              <input
                type="number"
                placeholder="120"
                value={screeningData.bp.systolic}
                onChange={(e) => updateData('bp', { ...screeningData.bp, systolic: e.target.value })}
                className="input w-full p-2"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1" style={{ color: 'var(--text-primary)' }}>Diastolic (mmHg)</label>
              <input
                type="number"
                placeholder="80"
                value={screeningData.bp.diastolic}
                onChange={(e) => updateData('bp', { ...screeningData.bp, diastolic: e.target.value })}
                className="input w-full p-2"
              />
            </div>
          </div>

          {screeningData.bp.classification && (
            <div className="p-4 rounded-md" style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-color)' }}>
              <div className="flex items-center space-x-3">
                <span className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>Classification:</span>
                <RiskBadge category={screeningData.bp.classification.category} label={screeningData.bp.classification.label} />
              </div>

              {['elevated', 'stage_1', 'stage_2', 'crisis'].includes(screeningData.bp.classification.category) && (
                <div className="mt-3 p-3 rounded-md" style={{ background: 'rgba(234, 179, 8, 0.1)' }}>
                  <p className="text-sm font-medium" style={{ color: 'rgb(161, 98, 7)' }}>Please take a second reading after 5 minutes</p>
                </div>
              )}
            </div>
          )}

          <div className="flex justify-between pt-4">
            <button onClick={handleBack} className="btn-secondary px-4 py-2">Back</button>
            <button
              onClick={handleBPSubmit}
              disabled={!screeningData.bp.systolic || !screeningData.bp.diastolic || isClassifying}
              className="btn-primary px-6 py-2 disabled:opacity-50"
            >
              {screeningData.bp.classification ? 'Confirm & Continue' : (isClassifying ? 'Checking...' : 'Check BP')}
            </button>
          </div>
        </div>
      )}

      {/* STEP 3: Blood Glucose */}
      {step === 3 && (
        <div className="space-y-6 animate-fadeIn">
          <h2 className="text-xl font-semibold" style={{ color: 'var(--text-primary)' }}>Measure Blood Glucose (Optional)</h2>

          <label className="flex items-center space-x-3 cursor-pointer">
            <input
              type="checkbox"
              checked={screeningData.glucose.include}
              onChange={(e) => updateData('glucose', { ...screeningData.glucose, include: e.target.checked })}
              className="h-4 w-4 rounded" style={{ accentColor: 'var(--color-primary)' }}
            />
            <span className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>Include glucose reading?</span>
          </label>

          {screeningData.glucose.include && (
            <div className="space-y-4 p-4 rounded-md" style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-color)' }}>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1" style={{ color: 'var(--text-primary)' }}>Value</label>
                  <input
                    type="number"
                    step="0.1"
                    placeholder="5.5"
                    value={screeningData.glucose.value}
                    onChange={(e) => updateData('glucose', { ...screeningData.glucose, value: e.target.value })}
                    className="input w-full p-2"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1" style={{ color: 'var(--text-primary)' }}>Unit</label>
                  <select
                    value={screeningData.glucose.unit}
                    onChange={(e) => updateData('glucose', { ...screeningData.glucose, unit: e.target.value })}
                    className="input w-full p-2"
                  >
                    <option value="mmol_l">mmol/L</option>
                    <option value="mg_dl">mg/dL</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium mb-1" style={{ color: 'var(--text-primary)' }}>Test Type</label>
                <select
                  value={screeningData.glucose.testType}
                  onChange={(e) => updateData('glucose', { ...screeningData.glucose, testType: e.target.value })}
                  className="input w-full md:w-1/2 p-2"
                >
                  <option value="random">Random</option>
                  <option value="fasting">Fasting</option>
                </select>
              </div>

              {screeningData.glucose.classification && (
                <div className="mt-4 flex items-center space-x-3">
                  <span className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>Classification:</span>
                  <RiskBadge category={screeningData.glucose.classification.category} label={screeningData.glucose.classification.label} />
                </div>
              )}
            </div>
          )}

          <div className="flex justify-between pt-4">
            <button onClick={handleBack} className="btn-secondary px-4 py-2">Back</button>
            <button
              onClick={handleGlucoseSubmit}
              disabled={screeningData.glucose.include && !screeningData.glucose.value}
              className="btn-primary px-6 py-2 disabled:opacity-50"
            >
              {screeningData.glucose.include ? (screeningData.glucose.classification ? 'Confirm & Continue' : 'Check Glucose') : 'Skip Glucose'}
            </button>
          </div>
        </div>
      )}

      {/* STEP 4: AI Summary / Submission Result */}
      {step === 4 && (
        <div className="space-y-6 animate-fadeIn min-h-[300px] flex flex-col justify-center">
          {isSubmitting ? (
            <div className="flex flex-col items-center justify-center space-y-4 py-8">
              <svg className="animate-spin h-8 w-8" style={{ color: 'var(--text-primary)' }} fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              <p className="font-medium" style={{ color: 'var(--text-secondary)' }}>Generating screening summary...</p>
            </div>
          ) : submissionResult ? (
            <div className="space-y-6 rounded-md p-6" style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-color)' }}>
              <div className="pb-4" style={{ borderBottom: '1px solid var(--border-color)' }}>
                <h3 className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>{screeningData.patient.name}</h3>
                <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Screening Date: {new Date().toLocaleDateString()}</p>

                <div className="flex gap-2 mt-3">
                  <RiskBadge category={screeningData.bp.classification?.category || 'normal'} label={`BP: ${screeningData.bp.systolic}/${screeningData.bp.diastolic} mmHg`} />
                  {screeningData.glucose.include && (
                    <RiskBadge category={screeningData.glucose.classification?.category || 'normal'} label={`Glucose: ${screeningData.glucose.value} ${screeningData.glucose.unit}`} />
                  )}
                </div>
              </div>

              {/* Splitting the Markdown generated by Agent summary */}
              <div className="text-sm whitespace-pre-wrap leading-relaxed" style={{ color: 'var(--text-primary)' }}>
                <p className="font-semibold mb-2" style={{ color: 'var(--text-primary)' }}>Clinical Summary</p>
                {submissionResult.agent_summary}
              </div>

              {submissionResult.referrals && submissionResult.referrals.length > 0 && (
                <div className="bg-red-50 border border-red-200 p-4 rounded-md">
                  <p className="font-bold text-red-800 mb-2">Referrals and Escalations:</p>
                  <ul className="list-disc pl-5 text-sm text-red-700 space-y-1">
                    {submissionResult.referrals.map((ref, idx) => (
                      <li key={idx}>{ref}</li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="pt-4 flex justify-center mt-6" style={{ borderTop: '1px solid var(--border-color)' }}>
                <button onClick={resetWizard} className="btn-secondary px-6 py-2">
                  Start New Screening
                </button>
              </div>
            </div>
          ) : (
            <div className="text-center py-8">
              {error ? (
                <div className="mt-4 space-y-4">
                  <p className="text-red-600 mb-4">{error}</p>
                  <button onClick={submitScreening} className="btn-primary px-4 py-2">Retry Submission</button>
                  <button onClick={handleBack} className="btn-secondary ml-2 px-4 py-2">Back</button>
                </div>
              ) : (
                <p style={{ color: 'var(--text-muted)' }}>Preparing to submit...</p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
