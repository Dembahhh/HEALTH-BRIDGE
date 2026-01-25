import { useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { updateProfile } from '../features/profile/profileSlice';
import { useNavigate } from 'react-router-dom';

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

    const [currentStep, setCurrentStep] = useState(0);
    const [formData, setFormData] = useState({
        age_band: '18-29',
        sex: 'male',
        family_history_hypertension: false,
        family_history_diabetes: false,
        smoking_status: 'never',
        alcohol_consumption: 'none',
        activity_level: 'sedentary',
    });

    const handleChange = (e) => {
        const { name, value, type, checked } = e.target;
        setFormData((prev) => ({
            ...prev,
            [name]: type === 'checkbox' ? checked : value,
        }));
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

    const { user } = useSelector((state) => state.auth);

    const handleSkip = () => {
        // Mark as skipped in local storage so we don't show it again automatically
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

    const renderStepContent = () => {
        switch (steps[currentStep].id) {
            case 'intro':
                return (
                    <div className="text-center py-8">
                        <div className="mx-auto flex items-center justify-center h-24 w-24 rounded-full bg-blue-100 mb-6">
                            <svg className="h-12 w-12 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.828 14.828a4 4 0 01-5.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                        </div>
                        <p className="text-gray-600 mb-8 max-w-sm mx-auto">
                            We'll ask you a few simple questions to tailor your AI health coach. You can skip this and fill it out later from your dashboard.
                        </p>
                    </div>
                );
            case 'demographics':
                return (
                    <div className="space-y-6 py-4">
                        <div>
                            <label htmlFor="age_band" className="block text-sm font-medium text-gray-700 mb-2">Age Group</label>
                            <select
                                id="age_band"
                                name="age_band"
                                value={formData.age_band}
                                onChange={handleChange}
                                className="block w-full py-3 px-4 border border-gray-300 bg-white rounded-lg shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                            >
                                <option value="18-29">18-29</option>
                                <option value="30-39">30-39</option>
                                <option value="40-49">40-49</option>
                                <option value="50-59">50-59</option>
                                <option value="60+">60+</option>
                            </select>
                        </div>
                        <div>
                            <label htmlFor="sex" className="block text-sm font-medium text-gray-700 mb-2">Sex</label>
                            <select
                                id="sex"
                                name="sex"
                                value={formData.sex}
                                onChange={handleChange}
                                className="block w-full py-3 px-4 border border-gray-300 bg-white rounded-lg shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                            >
                                <option value="male">Male</option>
                                <option value="female">Female</option>
                            </select>
                        </div>
                    </div>
                );
            case 'history':
                return (
                    <div className="space-y-6 py-4">
                        <p className="text-gray-600 mb-4">Select any that apply to your immediate family (parents, siblings):</p>
                        <div className="space-y-4">
                            <label className="flex items-center p-4 border rounded-lg hover:bg-gray-50 cursor-pointer transition-colors">
                                <input
                                    type="checkbox"
                                    name="family_history_hypertension"
                                    checked={formData.family_history_hypertension}
                                    onChange={handleChange}
                                    className="h-5 w-5 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                                />
                                <span className="ml-3 text-gray-900 font-medium">Hypertension (High Blood Pressure)</span>
                            </label>
                            <label className="flex items-center p-4 border rounded-lg hover:bg-gray-50 cursor-pointer transition-colors">
                                <input
                                    type="checkbox"
                                    name="family_history_diabetes"
                                    checked={formData.family_history_diabetes}
                                    onChange={handleChange}
                                    className="h-5 w-5 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                                />
                                <span className="ml-3 text-gray-900 font-medium">Diabetes (Type 1 or 2)</span>
                            </label>
                        </div>
                    </div>
                );
            case 'lifestyle':
                return (
                    <div className="space-y-6 py-4">
                        <div>
                            <label htmlFor="smoking_status" className="block text-sm font-medium text-gray-700 mb-2">Smoking Status</label>
                            <select
                                id="smoking_status"
                                name="smoking_status"
                                value={formData.smoking_status}
                                onChange={handleChange}
                                className="block w-full py-3 px-4 border border-gray-300 bg-white rounded-lg shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                            >
                                <option value="never">Never Smoked</option>
                                <option value="former">Former Smoker</option>
                                <option value="current">Current Smoker</option>
                            </select>
                        </div>
                        <div>
                            <label htmlFor="alcohol_consumption" className="block text-sm font-medium text-gray-700 mb-2">Alcohol Consumption</label>
                            <select
                                id="alcohol_consumption"
                                name="alcohol_consumption"
                                value={formData.alcohol_consumption}
                                onChange={handleChange}
                                className="block w-full py-3 px-4 border border-gray-300 bg-white rounded-lg shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                            >
                                <option value="none">None</option>
                                <option value="occasional">Occasional</option>
                                <option value="regular">Regular</option>
                            </select>
                        </div>
                    </div>
                );
            case 'activity':
                return (
                    <div className="space-y-6 py-4">
                        <div>
                            <label htmlFor="activity_level" className="block text-sm font-medium text-gray-700 mb-2">Activity Level</label>
                            <p className="text-xs text-gray-500 mb-2">How much physical activity do you get?</p>
                            <select
                                id="activity_level"
                                name="activity_level"
                                value={formData.activity_level}
                                onChange={handleChange}
                                className="block w-full py-3 px-4 border border-gray-300 bg-white rounded-lg shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                            >
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
        <div className="min-h-screen bg-gray-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
            <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-xl">
                <div className="bg-white py-8 px-4 shadow-xl sm:rounded-xl sm:px-10 border border-gray-100">

                    {/* Header */}
                    <div className="mb-8">
                        <div className="flex justify-between items-center mb-4">
                            {/* Progress Dots */}
                            <div className="flex space-x-2">
                                {steps.map((_, idx) => (
                                    <div
                                        key={idx}
                                        className={`h-2 w-2 rounded-full transition-colors duration-300 ${idx === currentStep ? 'bg-blue-600 w-4' : (idx < currentStep ? 'bg-blue-400' : 'bg-gray-200')}`}
                                    />
                                ))}
                            </div>

                            <button onClick={handleSkip} className="text-sm text-gray-400 hover:text-gray-600">
                                Skip
                            </button>
                        </div>

                        <h2 className="text-2xl font-bold text-gray-900 transition-all duration-300 ease-in-out">
                            {steps[currentStep].title}
                        </h2>
                        <p className="mt-1 text-sm text-gray-500">
                            {steps[currentStep].description}
                        </p>
                    </div>

                    {/* Content */}
                    <div className="min-h-[200px] transition-all duration-300 ease-in-out">
                        {renderStepContent()}
                    </div>

                    {/* Footer */}
                    <div className="mt-8 flex justify-between pt-6 border-t border-gray-100">
                        <button
                            onClick={handleBack}
                            disabled={currentStep === 0}
                            className={`px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 ${currentStep === 0 ? 'opacity-0 cursor-default' : ''}`}
                        >
                            Back
                        </button>

                        <button
                            onClick={handleNext}
                            disabled={loading}
                            className="inline-flex items-center px-6 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-all"
                        >
                            {loading ? (
                                <span>Saving...</span>
                            ) : (
                                <span>{currentStep === steps.length - 1 ? 'Finish' : 'Next'}</span>
                            )}
                            {currentStep !== steps.length - 1 && !loading && (
                                <svg className="ml-2 -mr-1 h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                                </svg>
                            )}
                        </button>
                    </div>

                </div>

                <p className="text-center text-xs text-gray-400 mt-6">
                    HealthBridge AI • Step {currentStep + 1} of {steps.length}
                </p>
            </div>
        </div>
    );
}
