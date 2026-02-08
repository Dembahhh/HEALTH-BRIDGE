import { useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { updateProfile } from '../features/profile/profileSlice';
import { useNavigate, Link } from 'react-router-dom';
import ThemeToggle from '../components/ThemeToggle';
import { Sparkles, ChevronRight, ChevronLeft, Check } from 'lucide-react';

const steps = [
    {
        id: 'intro',
        title: 'Welcome to HealthBridge',
        description: "Let's personalize your health journey. This will only take a minute.",
    },
    {
        id: 'demographics',
        title: 'About You',
        description: 'Basic information helps us calculate your baseline.',
    },
    {
        id: 'history',
        title: 'Family History',
        description: 'Understanding your genetics helps us predict risks.',
    },
    {
        id: 'lifestyle',
        title: 'Lifestyle',
        description: 'Your daily habits play a huge role in your health.',
    },
    {
        id: 'activity',
        title: 'Activity Level',
        description: 'How active are you on a typical day?',
    }
];

export default function OnboardingPage() {
    const dispatch = useDispatch();
    const navigate = useNavigate();
    const { loading } = useSelector((state) => state.profile);
    const { user } = useSelector((state) => state.auth);

    const [currentStep, setCurrentStep] = useState(0);
    const [formData, setFormData] = useState({
        age_band: '',
        sex: '',
        family_history_hypertension: false,
        family_history_diabetes: false,
        smoking_status: '',
        alcohol_consumption: '',
        activity_level: '',
    });

    const handleChange = (e) => {
        const { name, value, type, checked } = e.target;
        setFormData((prev) => ({
            ...prev,
            [name]: type === 'checkbox' ? checked : value,
        }));
    };

    const isStepValid = () => {
        switch (steps[currentStep].id) {
            case 'intro':
                return true;
            case 'demographics':
                return formData.age_band !== '' && formData.sex !== '';
            case 'history':
                return true; // Checkboxes are optional
            case 'lifestyle':
                return formData.smoking_status !== '' && formData.alcohol_consumption !== '';
            case 'activity':
                return formData.activity_level !== '';
            default:
                return true;
        }
    };

    const handleNext = () => {
        if (currentStep < steps.length - 1) {
            setCurrentStep(prev => prev + 1);
        } else {
            handleComplete();
        }
    };

    const handleBack = () => {
        if (currentStep > 0) {
            setCurrentStep(prev => prev - 1);
        }
    };

    const handleSkip = () => {
        if (user?.uid) {
            localStorage.setItem(`onboarding_skipped_${user.uid}`, 'true');
        }
        navigate('/dashboard');
    };

    const handleComplete = async () => {
        try {
            await dispatch(updateProfile(formData)).unwrap();
            navigate('/dashboard');
        } catch (err) {
            console.error('Failed to save profile', err);
        }
    };

    const selectStyle = {
        background: 'var(--bg-elevated)',
        border: '1px solid var(--border-color)',
        color: 'var(--text-primary)'
    };

    const renderStepContent = () => {
        switch (steps[currentStep].id) {
            case 'intro':
                return (
                    <div className="text-center py-8 animate-fadeIn">
                        <div className="mx-auto flex items-center justify-center h-24 w-24 rounded-3xl mb-6 animate-pulse-glow"
                            style={{ background: 'linear-gradient(135deg, var(--color-primary) 0%, var(--color-accent) 100%)' }}>
                            <Sparkles className="h-12 w-12 text-white" />
                        </div>
                        <p className="mb-8 max-w-sm mx-auto" style={{ color: 'var(--text-secondary)' }}>
                            We'll ask you a few simple questions to tailor your AI health coach. You can skip this and fill it out later from your dashboard.
                        </p>
                    </div>
                );
            case 'demographics':
                return (
                    <div className="space-y-6 py-4 animate-fadeIn">
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
                                <option value="" disabled>Select your age group</option>
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
                                <option value="" disabled>Select your sex</option>
                                <option value="male">Male</option>
                                <option value="female">Female</option>
                            </select>
                        </div>
                    </div>
                );
            case 'history':
                return (
                    <div className="space-y-4 py-4 animate-fadeIn">
                        <p className="mb-4" style={{ color: 'var(--text-secondary)' }}>
                            Select any that apply to your immediate family:
                        </p>
                        {[
                            { name: 'family_history_hypertension', label: 'Hypertension (High Blood Pressure)', checked: formData.family_history_hypertension },
                            { name: 'family_history_diabetes', label: 'Diabetes (Type 1 or 2)', checked: formData.family_history_diabetes },
                        ].map((item) => (
                            <label
                                key={item.name}
                                className="flex items-center p-4 rounded-xl cursor-pointer transition-all"
                                style={{
                                    background: item.checked ? 'rgba(var(--color-primary-rgb), 0.1)' : 'var(--bg-elevated)',
                                    border: item.checked ? '2px solid var(--color-primary)' : '1px solid var(--border-color)'
                                }}>
                                <input
                                    type="checkbox"
                                    name={item.name}
                                    checked={item.checked}
                                    onChange={handleChange}
                                    className="sr-only"
                                />
                                <div className="w-6 h-6 rounded-lg mr-4 flex items-center justify-center transition-all"
                                    style={{
                                        background: item.checked ? 'var(--color-primary)' : 'var(--bg-surface)',
                                        border: item.checked ? 'none' : '2px solid var(--border-color)'
                                    }}>
                                    {item.checked && <Check className="w-4 h-4 text-white" />}
                                </div>
                                <span className="font-medium" style={{ color: 'var(--text-primary)' }}>{item.label}</span>
                            </label>
                        ))}
                    </div>
                );
            case 'lifestyle':
                return (
                    <div className="space-y-6 py-4 animate-fadeIn">
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
                                <option value="" disabled>Select your smoking status</option>
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
                                <option value="" disabled>Select your alcohol consumption</option>
                                <option value="none">None</option>
                                <option value="occasional">Occasional</option>
                                <option value="regular">Regular</option>
                            </select>
                        </div>
                    </div>
                );
            case 'activity':
                return (
                    <div className="space-y-6 py-4 animate-fadeIn">
                        <div>
                            <label htmlFor="activity_level" className="block text-sm font-medium mb-2" style={{ color: 'var(--text-primary)' }}>
                                Activity Level
                            </label>
                            <p className="text-xs mb-3" style={{ color: 'var(--text-muted)' }}>
                                How much physical activity do you get?
                            </p>
                            <select
                                id="activity_level"
                                name="activity_level"
                                value={formData.activity_level}
                                onChange={handleChange}
                                className="input w-full"
                                style={selectStyle}
                            >
                                <option value="" disabled>Select your activity level</option>
                                <option value="sedentary">Sedentary (Little to no exercise)</option>
                                <option value="light">Light (1-3 days/week)</option>
                                <option value="moderate">Moderate (3-5 days/week)</option>
                                <option value="active">Active (6-7 days/week)</option>
                            </select>
                        </div>
                    </div>
                );
            default:
                return null;
        }
    };

    return (
        <div className="min-h-screen flex flex-col justify-center py-12 px-4 sm:px-6 lg:px-8 relative overflow-hidden"
            style={{ background: 'var(--bg-primary)' }}>

            {/* Background Gradient Orbs */}
            <div className="absolute inset-0 overflow-hidden pointer-events-none">
                <div className="absolute top-20 right-20 w-64 h-64 rounded-full opacity-20"
                    style={{ background: 'radial-gradient(circle, var(--color-primary) 0%, transparent 70%)' }} />
                <div className="absolute bottom-20 left-20 w-80 h-80 rounded-full opacity-15"
                    style={{ background: 'radial-gradient(circle, var(--color-accent) 0%, transparent 70%)' }} />
            </div>

            {/* Header */}
            <div className="absolute top-6 left-6 right-6 flex justify-between items-center">
                <Link to="/" className="flex items-center gap-2">
                    <div className="w-10 h-10 rounded-xl flex items-center justify-center"
                        style={{ background: 'linear-gradient(135deg, var(--color-primary) 0%, var(--color-accent) 100%)' }}>
                        <span className="text-white font-bold text-lg">H</span>
                    </div>
                    <span className="font-bold text-xl hidden sm:block" style={{ color: 'var(--text-primary)' }}>HealthBridge</span>
                </Link>
                <ThemeToggle />
            </div>

            <div className="sm:mx-auto sm:w-full sm:max-w-xl relative z-10">
                {/* Card */}
                <div className="rounded-2xl py-8 px-6 sm:px-10 shadow-2xl"
                    style={{
                        background: 'var(--bg-surface)',
                        border: '1px solid var(--border-color)'
                    }}>

                    {/* Progress Bar */}
                    <div className="mb-8">
                        <div className="flex justify-between items-center mb-4">
                            <div className="flex gap-2">
                                {steps.map((_, idx) => (
                                    <div
                                        key={idx}
                                        className="h-2 rounded-full transition-all duration-300"
                                        style={{
                                            width: idx === currentStep ? '2rem' : '0.5rem',
                                            background: idx <= currentStep ? 'var(--color-primary)' : 'var(--border-color)'
                                        }}
                                    />
                                ))}
                            </div>

                            <button
                                onClick={handleSkip}
                                className="text-sm font-medium transition-colors"
                                style={{ color: 'var(--text-muted)' }}>
                                Skip
                            </button>
                        </div>

                        <h2 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
                            {steps[currentStep].title}
                        </h2>
                        <p className="mt-1 text-sm" style={{ color: 'var(--text-secondary)' }}>
                            {steps[currentStep].description}
                        </p>
                    </div>

                    {/* Content */}
                    <div className="min-h-[200px]">
                        {renderStepContent()}
                    </div>

                    {/* Footer */}
                    <div className="mt-8 flex justify-between pt-6" style={{ borderTop: '1px solid var(--border-color)' }}>
                        <button
                            onClick={handleBack}
                            disabled={currentStep === 0}
                            className={`btn-secondary flex items-center gap-2 ${currentStep === 0 ? 'opacity-0 pointer-events-none' : ''}`}
                        >
                            <ChevronLeft className="w-4 h-4" />
                            Back
                        </button>

                        <button
                            onClick={handleNext}
                            disabled={loading || !isStepValid()}
                            className="btn-primary flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {loading ? (
                                <span className="flex items-center gap-2">
                                    <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                                    </svg>
                                    Saving...
                                </span>
                            ) : (
                                <>
                                    {currentStep === steps.length - 1 ? 'Finish' : 'Next'}
                                    {currentStep !== steps.length - 1 && <ChevronRight className="w-4 h-4" />}
                                </>
                            )}
                        </button>
                    </div>
                </div>

                <p className="text-center text-xs mt-6" style={{ color: 'var(--text-muted)' }}>
                    HealthBridge AI • Step {currentStep + 1} of {steps.length}
                </p>
            </div>
        </div>
    );
}
