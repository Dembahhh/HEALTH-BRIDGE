import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import PatientSearch from '../components/PatientSearch';
import PatientHistory from '../components/PatientHistory';

export default function PatientViewPage() {
  const [selectedPatient, setSelectedPatient] = useState(null);
  const navigate = useNavigate();

  return (
    <div className="min-h-screen" style={{ background: 'var(--bg-primary)' }}>
      <div className='max-w-4xl mx-auto px-4 py-8 pb-24'>
        <div className="mb-8 pb-6 border-b" style={{ borderColor: 'var(--border-color)' }}>

          <h1 className="text-2xl font-bold mb-6" style={{ color: 'var(--text-primary)' }}>Patient Lookup</h1>
          <PatientSearch onPatientSelected={(p) => setSelectedPatient(p)} />
        </div>

        <div>
          {selectedPatient ? (
            <div>
              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6 p-4 rounded-lg"
                style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-color)' }}>
                <div>
                  <h2 className="text-xl font-bold" style={{ color: 'var(--text-primary)' }}>{selectedPatient.name}</h2>
                  <div className="flex text-sm space-x-4 mt-1" style={{ color: 'var(--text-secondary)' }}>
                    {selectedPatient.phone && <span>{selectedPatient.phone}</span>}
                    {selectedPatient.age && <span>Age: {selectedPatient.age}</span>}
                    {selectedPatient.sex && <span className="capitalize">{selectedPatient.sex}</span>}
                  </div>
                </div>
                <button
                  onClick={() => navigate('/screening')}
                  className="mt-4 sm:mt-0 inline-flex items-center px-4 py-2 text-white font-medium text-sm rounded-md shadow-sm transition-all hover:scale-105"
                  style={{ background: 'linear-gradient(135deg, var(--color-primary) 0%, var(--color-accent) 100%)' }}
                >
                  Start Screening
                </button>
              </div>

              <PatientHistory patientId={selectedPatient.id || selectedPatient._id} patientName={selectedPatient.name} />
            </div>
          ) : (
            <div className="text-center py-16 rounded-lg border border-dashed"
              style={{ background: 'var(--bg-surface)', borderColor: 'var(--border-color)' }}>
              <h3 className="text-lg font-medium mb-2" style={{ color: 'var(--text-primary)' }}>No Patient Selected</h3>
              <p style={{ color: 'var(--text-secondary)' }}>Search for a patient above to view their health history</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
