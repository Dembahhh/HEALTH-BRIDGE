import { useState, useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { updateProfile } from './profileSlice';

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

    return (
        <form onSubmit={handleSubmit} className="space-y-6 bg-white dark:bg-gray-800 shadow px-4 py-5 sm:rounded-lg sm:p-6 transition-colors duration-200">
            <div className="md:grid md:grid-cols-3 md:gap-6">
                <div className="md:col-span-1">
                    <h3 className="text-lg font-medium leading-6 text-gray-900 dark:text-white">Personal Information</h3>
                    <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">Essential details for your health assessment.</p>
                </div>
                <div className="mt-5 md:mt-0 md:col-span-2 space-y-6">

                    <div className="grid grid-cols-6 gap-6">
                        <div className="col-span-6 sm:col-span-3">
                            <label htmlFor="age_band" className="block text-sm font-medium text-gray-700 dark:text-gray-300">Age Group</label>
                            <select
                                id="age_band"
                                name="age_band"
                                value={formData.age_band}
                                onChange={handleChange}
                                className="mt-1 block w-full py-2 px-3 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 text-gray-900 dark:text-white sm:text-sm"
                            >
                                <option value="18-29">18-29</option>
                                <option value="30-39">30-39</option>
                                <option value="40-49">40-49</option>
                                <option value="50-59">50-59</option>
                                <option value="60+">60+</option>
                            </select>
                        </div>

                        <div className="col-span-6 sm:col-span-3">
                            <label htmlFor="sex" className="block text-sm font-medium text-gray-700 dark:text-gray-300">Sex</label>
                            <select
                                id="sex"
                                name="sex"
                                value={formData.sex}
                                onChange={handleChange}
                                className="mt-1 block w-full py-2 px-3 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 text-gray-900 dark:text-white sm:text-sm"
                            >
                                <option value="male">Male</option>
                                <option value="female">Female</option>
                            </select>
                        </div>
                    </div>

                    <fieldset>
                        <legend className="text-base font-medium text-gray-900 dark:text-white">Family History</legend>
                        <div className="mt-4 space-y-4">
                            <div className="flex items-start">
                                <div className="flex items-center h-5">
                                    <input
                                        id="family_history_hypertension"
                                        name="family_history_hypertension"
                                        type="checkbox"
                                        checked={formData.family_history_hypertension}
                                        onChange={handleChange}
                                        className="focus:ring-indigo-500 h-4 w-4 text-indigo-600 border-gray-300 dark:border-gray-500 rounded bg-white dark:bg-gray-700"
                                    />
                                </div>
                                <div className="ml-3 text-sm">
                                    <label htmlFor="family_history_hypertension" className="font-medium text-gray-700 dark:text-gray-300">Hypertension</label>
                                    <p className="text-gray-500 dark:text-gray-400">Close family members diagnosed with high blood pressure.</p>
                                </div>
                            </div>
                            <div className="flex items-start">
                                <div className="flex items-center h-5">
                                    <input
                                        id="family_history_diabetes"
                                        name="family_history_diabetes"
                                        type="checkbox"
                                        checked={formData.family_history_diabetes}
                                        onChange={handleChange}
                                        className="focus:ring-indigo-500 h-4 w-4 text-indigo-600 border-gray-300 dark:border-gray-500 rounded bg-white dark:bg-gray-700"
                                    />
                                </div>
                                <div className="ml-3 text-sm">
                                    <label htmlFor="family_history_diabetes" className="font-medium text-gray-700 dark:text-gray-300">Diabetes</label>
                                    <p className="text-gray-500 dark:text-gray-400">Close family members diagnosed with diabetes.</p>
                                </div>
                            </div>
                        </div>
                    </fieldset>

                    <div className="grid grid-cols-6 gap-6 pt-4 border-t border-gray-100 dark:border-gray-700">
                        <div className="col-span-6 sm:col-span-3">
                            <label htmlFor="smoking_status" className="block text-sm font-medium text-gray-700 dark:text-gray-300">Smoking Status</label>
                            <select
                                id="smoking_status"
                                name="smoking_status"
                                value={formData.smoking_status}
                                onChange={handleChange}
                                className="mt-1 block w-full py-2 px-3 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 text-gray-900 dark:text-white sm:text-sm"
                            >
                                <option value="never">Never Smoked</option>
                                <option value="former">Former Smoker</option>
                                <option value="current">Current Smoker</option>
                            </select>
                        </div>
                        <div className="col-span-6 sm:col-span-3">
                            <label htmlFor="alcohol_consumption" className="block text-sm font-medium text-gray-700 dark:text-gray-300">Alcohol Consumption</label>
                            <select
                                id="alcohol_consumption"
                                name="alcohol_consumption"
                                value={formData.alcohol_consumption}
                                onChange={handleChange}
                                className="mt-1 block w-full py-2 px-3 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 text-gray-900 dark:text-white sm:text-sm"
                            >
                                <option value="none">None</option>
                                <option value="occasional">Occasional</option>
                                <option value="regular">Regular</option>
                            </select>
                        </div>
                        <div className="col-span-6">
                            <label htmlFor="activity_level" className="block text-sm font-medium text-gray-700 dark:text-gray-300">Activity Level</label>
                            <select
                                id="activity_level"
                                name="activity_level"
                                value={formData.activity_level}
                                onChange={handleChange}
                                className="mt-1 block w-full py-2 px-3 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 text-gray-900 dark:text-white sm:text-sm"
                            >
                                <option value="sedentary">Sedentary (Little to no exercise)</option>
                                <option value="light">Light (1-3 days/week)</option>
                                <option value="moderate">Moderate (3-5 days/week)</option>
                                <option value="active">Active (6-7 days/week)</option>
                            </select>
                        </div>
                    </div>

                </div>
            </div>

            <div className="px-4 py-3 bg-gray-50 dark:bg-gray-700/30 text-right sm:px-6">
                <button
                    type="submit"
                    disabled={loading}
                    className="inline-flex justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 dark:bg-indigo-500 dark:hover:bg-indigo-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                >
                    {loading ? 'Saving...' : 'Save Profile'}
                </button>
            </div>
        </form>
    );
}
