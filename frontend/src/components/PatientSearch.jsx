import React, { useState, useEffect } from 'react';
import api from '../services/api';

export default function PatientSearch({ onPatientSelected, apiBaseUrl = '' }) {
  const [searchQuery, setSearchQuery] = useState('');
  const [results, setResults] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newPatientData, setNewPatientData] = useState({
    name: '',
    phone: '',
    age: '',
    sex: ''
  });
  const [isCreating, setIsCreating] = useState(false);

  // Debounced Search
  useEffect(() => {
    if (searchQuery.trim().length < 2) {
      setResults([]);
      setError('');
      return;
    }

    const timerId = setTimeout(async () => {
      setIsLoading(true);
      setError('');
      try {
        const res = await api.get(`/patients/search?q=${encodeURIComponent(searchQuery.trim())}`);

        const data = res.data;
        setResults(Array.isArray(data) ? data : []);
      } catch (err) {
        setError(err.response?.data?.detail || err.message || 'Error searching patients');
        setResults([]);
      } finally {
        setIsLoading(false);
      }
    }, 250);

    return () => clearTimeout(timerId);
  }, [searchQuery, apiBaseUrl]);

  // Handle Create Patient Submission
  const handleCreateNew = async (e) => {
    e.preventDefault();
    if (!newPatientData.name.trim()) {
      setError('Patient name is required.');
      return;
    }

    setIsCreating(true);
    setError('');

    try {
      const payload = {
        name: newPatientData.name.trim(),
        phone: newPatientData.phone.trim() || undefined,
        age: newPatientData.age ? parseInt(newPatientData.age, 10) : undefined,
        sex: newPatientData.sex || undefined,
      };

      const res = await api.post(`/patients/`, payload);
      const newPatient = res.data;

      // Cleanup UI
      setShowCreateForm(false);
      setSearchQuery('');
      setResults([]);

      // Bubble up the selected (new) patient
      onPatientSelected(newPatient);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Error creating patient');
    } finally {
      setIsCreating(false);
    }
  };

  const handleInputChange = (field, value) => {
    setNewPatientData(prev => ({ ...prev, [field]: value }));
  };

  return (
    <div className="relative w-full max-w-lg">
      <div className="mb-2">
        <label htmlFor="patient-search" className="block text-sm font-medium mb-1" style={{ color: 'var(--text-primary)' }}>
          Search existing patient
        </label>
        <div className="relative">
          <input
            id="patient-search"
            type="text"
            className="input w-full pl-4 pr-10 py-2"
            placeholder="Search by name or phone number..."
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setShowCreateForm(false);
            }}
          />
          {isLoading && (
            <div className="absolute right-3 top-2.5">
              <svg className="animate-spin h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
            </div>
          )}
        </div>
      </div>

      {error && !showCreateForm && (
        <p className="text-sm text-red-600 mb-2">{error}</p>
      )}

      {/* Dropdown Results */}
      {searchQuery.length >= 2 && !showCreateForm && (
        <div className="absolute z-10 w-full shadow-lg rounded-md mt-1 max-h-64 overflow-y-auto"
          style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-color)' }}>
          {results.length > 0 ? (
            <ul className="divide-y divide-gray-200">
              {results.map((patient) => (
                <li
                  key={patient.id || patient._id}
                  className="px-4 py-3 cursor-pointer transition-colors"
                  style={{ borderBottom: '1px solid var(--border-color)' }}
                  onMouseEnter={e => e.currentTarget.style.background = 'var(--bg-elevated)'}
                  onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                  onClick={() => {
                    setSearchQuery('');
                    setResults([]);
                    onPatientSelected(patient);
                  }}
                >
                  <p className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>{patient.name}</p>
                  <div className="flex text-xs mt-1 space-x-3" style={{ color: 'var(--text-secondary)' }}>
                    {patient.phone && <span>{patient.phone}</span>}
                    {patient.age && <span>Age: {patient.age}</span>}
                  </div>
                </li>
              ))}<li className="px-4 py-3 cursor-pointer text-center transition-colors"
                style={{ borderBottom: '1px solid var(--border-color)' }}
                onMouseEnter={e => e.currentTarget.style.background = 'var(--bg-elevated)'}
                onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                onClick={() => setShowCreateForm(true)}>
                <span className="text-sm font-medium" style={{ color: 'var(--color-primary)' }}>Patient not in list? Create new</span>
              </li>
            </ul>
          ) : (
            !isLoading && (
              <div className="px-4 py-6 text-center">
                <p className="text-sm mb-3" style={{ color: 'var(--text-secondary)' }}>No patient found</p>
                <button
                  type="button"
                  className="inline-flex items-center px-4 py-2 text-sm font-medium rounded-md shadow-sm text-white transition-all hover:scale-105"
                  style={{ background: 'linear-gradient(135deg, var(--color-primary) 0%, var(--color-accent) 100%)' }}
                  onClick={() => {
                    setNewPatientData(prev => ({ ...prev, name: searchQuery }));
                    setShowCreateForm(true);
                  }}
                >
                  Create new patient
                </button>
              </div>
            )
          )}
        </div>
      )}

      {/* Inline Create Form */}
      {showCreateForm && (
        <div className="mt-4 p-4 rounded-md" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-color)' }}>
          <h3 className="text-md font-medium mb-4" style={{ color: 'var(--text-primary)' }}>Create New Patient</h3>

          {error && <p className="text-sm text-red-600 mb-3">{error}</p>}

          <form onSubmit={handleCreateNew} className="space-y-4">
            <div>
              <label className="block text-xs font-medium" style={{ color: 'var(--text-primary)' }}>Full Name *</label>
              <input
                type="text"
                required
                className="input mt-1 block w-full sm:text-sm py-2 px-3"
                value={newPatientData.name}
                onChange={(e) => handleInputChange('name', e.target.value)}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium" style={{ color: 'var(--text-primary)' }}>Phone</label>
                <input
                  type="tel"
                  className="input mt-1 block w-full sm:text-sm py-2 px-3"
                  value={newPatientData.phone}
                  onChange={(e) => handleInputChange('phone', e.target.value)}
                />
              </div>

              <div>
                <label className="block text-xs font-medium" style={{ color: 'var(--text-primary)' }}>Age</label>
                <input
                  type="number"
                  min="0"
                  max="120"
                  className="input mt-1 block w-full sm:text-sm py-2 px-3"
                  value={newPatientData.age}
                  onChange={(e) => handleInputChange('age', e.target.value)}
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium" style={{ color: 'var(--text-primary)' }}>Sex</label>
              <select
                className="input mt-1 block w-full sm:text-sm py-2 px-3"
                value={newPatientData.sex}
                onChange={(e) => handleInputChange('sex', e.target.value)}
              > <option value="" disabled>Select sex</option>
                <option value="female">Female</option>
                <option value="male">Male</option>
                <option value="other">Other</option>
              </select>
            </div>

            <div className="flex justify-end space-x-3 pt-2">
              <button
                type="button"
                className="btn-secondary px-3 py-2 text-sm"
                onClick={() => setShowCreateForm(false)}
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isCreating}
                className="btn-primary px-4 py-2 text-sm disabled:opacity-50"
              >
                {isCreating ? 'Saving...' : 'Save & Select'}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
