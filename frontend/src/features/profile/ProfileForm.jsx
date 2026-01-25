import { useState, useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { updateProfile } from './profileSlice';
import { Check } from 'lucide-react';

export default function ProfileForm({ existingProfile, onSuccess }) {
    const dispatch = useDispatch();
    const { loading } = useSelector((state) => state.profile);

    const [formData, setFormData] = useState({
        age_band: '18-29',
        sex: 'male',
        family_history_hypertension: false,
        family_history_diabetes: false,
        smoking_status: 'never',
        alcohol_consumption: 'none',
        activity_level: 'sedentary',
    });

    useEffect(() => {
        if (existingProfile) {
            setFormData({
                age_band: existingProfile.age_band || '18-29',
                sex: existingProfile.sex || 'male',
                family_history_hypertension: existingProfile.family_history_hypertension || false,
                family_history_diabetes: existingProfile.family_history_diabetes || false,
                smoking_status: existingProfile.smoking_status || 'never',
                alcohol_consumption: existingProfile.alcohol_consumption || 'none',
                activity_level: existingProfile.activity_level || 'sedentary',
            });
        }
    }, [existingProfile]);

    const handleChange = (e) => {
        const { name, value, type, checked } = e.target;
        setFormData((prev) => ({
            ...prev,
            [name]: type === 'checkbox' ? checked : value,
        }));
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        try {
            await dispatch(updateProfile(formData)).unwrap();
            if (onSuccess) onSuccess();
        } catch (err) {
            console.error('Failed to save profile:', err);
        }
    };

    const selectStyle = {
        background: 'var(--bg-elevated)',
        border: '1px solid var(--border-color)',
        color: 'var(--text-primary)'
    };

    return (
        <form onSubmit={handleSubmit}
            className="rounded-2xl overflow-hidden"
            style={{
                background: 'var(--bg-surface)',
                border: '1px solid var(--border-color)'
            }}>

            {/* Header */}
            <div className="px-6 py-5" style={{ borderBottom: '1px solid var(--border-color)' }}>
                <h3 className="text-lg font-semibold" style={{ color: 'var(--text-primary)' }}>
                    {existingProfile ? 'Edit Profile' : 'Complete Your Profile'}
                </h3>
                <p className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>
                    Essential details for your health assessment
                </p>
            </div>

            <div className="p-6 space-y-6">
                {/* Demographics */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                        <label htmlFor="age_band" className="block text-sm font-medium mb-2" style={{ color: 'var(--text-primary)' }}>
                            Age Group
                        </label>
                        <select
                            id="age_band"
                            name="age_band"
                            value={formData.age_band}
                            onChange={handleChange}
                            className="input w-full"
                            style={selectStyle}
                        >
                            <option value="18-29">18-29</option>
                            <option value="30-39">30-39</option>
                            <option value="40-49">40-49</option>
                            <option value="50-59">50-59</option>
                            <option value="60+">60+</option>
                        </select>
                    </div>

                    <div>
                        <label htmlFor="sex" className="block text-sm font-medium mb-2" style={{ color: 'var(--text-primary)' }}>
                            Sex
                        </label>
                        <select
                            id="sex"
                            name="sex"
                            value={formData.sex}
                            onChange={handleChange}
                            className="input w-full"
                            style={selectStyle}
                        >
                            <option value="male">Male</option>
                            <option value="female">Female</option>
                        </select>
                    </div>
                </div>

                {/* Family History */}
                <div>
                    <label className="block text-sm font-medium mb-3" style={{ color: 'var(--text-primary)' }}>
                        Family History
                    </label>
                    <div className="space-y-3">
                        {[
                            { name: 'family_history_hypertension', label: 'Hypertension', desc: 'High blood pressure in close family', checked: formData.family_history_hypertension },
                            { name: 'family_history_diabetes', label: 'Diabetes', desc: 'Diabetes in close family', checked: formData.family_history_diabetes },
                        ].map((item) => (
                            <label
                                key={item.name}
                                className="flex items-center p-4 rounded-xl cursor-pointer transition-all"
                                style={{
                                    background: item.checked ? 'rgba(241, 143, 46, 0.1)' : 'var(--bg-elevated)',
                                    border: item.checked ? '2px solid var(--color-primary)' : '1px solid var(--border-color)'
                                }}>
                                <input
                                    type="checkbox"
                                    name={item.name}
                                    checked={item.checked}
                                    onChange={handleChange}
                                    className="sr-only"
                                />
                                <div className="w-6 h-6 rounded-lg mr-4 flex items-center justify-center transition-all flex-shrink-0"
                                    style={{
                                        background: item.checked ? 'var(--color-primary)' : 'var(--bg-surface)',
                                        border: item.checked ? 'none' : '2px solid var(--border-color)'
                                    }}>
                                    {item.checked && <Check className="w-4 h-4 text-white" />}
                                </div>
                                <div>
                                    <span className="font-medium block" style={{ color: 'var(--text-primary)' }}>{item.label}</span>
                                    <span className="text-xs" style={{ color: 'var(--text-muted)' }}>{item.desc}</span>
                                </div>
                            </label>
                        ))}
                    </div>
                </div>

                {/* Lifestyle */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-4" style={{ borderTop: '1px solid var(--border-color)' }}>
                    <div>
                        <label htmlFor="smoking_status" className="block text-sm font-medium mb-2" style={{ color: 'var(--text-primary)' }}>
                            Smoking Status
                        </label>
                        <select
                            id="smoking_status"
                            name="smoking_status"
                            value={formData.smoking_status}
                            onChange={handleChange}
                            className="input w-full"
                            style={selectStyle}
                        >
                            <option value="never">Never Smoked</option>
                            <option value="former">Former Smoker</option>
                            <option value="current">Current Smoker</option>
                        </select>
                    </div>
                    <div>
                        <label htmlFor="alcohol_consumption" className="block text-sm font-medium mb-2" style={{ color: 'var(--text-primary)' }}>
                            Alcohol Consumption
                        </label>
                        <select
                            id="alcohol_consumption"
                            name="alcohol_consumption"
                            value={formData.alcohol_consumption}
                            onChange={handleChange}
                            className="input w-full"
                            style={selectStyle}
                        >
                            <option value="none">None</option>
                            <option value="occasional">Occasional</option>
                            <option value="regular">Regular</option>
                        </select>
                    </div>
                    <div className="sm:col-span-2">
                        <label htmlFor="activity_level" className="block text-sm font-medium mb-2" style={{ color: 'var(--text-primary)' }}>
                            Activity Level
                        </label>
                        <select
                            id="activity_level"
                            name="activity_level"
                            value={formData.activity_level}
                            onChange={handleChange}
                            className="input w-full"
                            style={selectStyle}
                        >
                            <option value="sedentary">Sedentary (Little to no exercise)</option>
                            <option value="light">Light (1-3 days/week)</option>
                            <option value="moderate">Moderate (3-5 days/week)</option>
                            <option value="active">Active (6-7 days/week)</option>
                        </select>
                    </div>
                </div>
            </div>

            {/* Footer */}
            <div className="px-6 py-4 flex justify-end" style={{ background: 'var(--bg-elevated)', borderTop: '1px solid var(--border-color)' }}>
                <button
                    type="submit"
                    disabled={loading}
                    className="btn-primary"
                >
                    {loading ? (
                        <span className="flex items-center gap-2">
                            <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                            </svg>
                            Saving...
                        </span>
                    ) : 'Save Profile'}
                </button>
            </div>
        </form>
    );
}
