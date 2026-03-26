import React from 'react';
import { useSelector } from 'react-redux';
import ProfileForm from '../features/profile/ProfileForm';

export default function ProfilePage() {
    const { data: profile } = useSelector((state) => state.profile);

    const handleSuccess = () => {
        // Optional: show a toast or confirmation
        console.log('Profile saved successfully');
    };

    return (
        <div className="min-h-screen pb-20 px-4 py-6" style={{ background: 'var(--bg-base)' }}>
            <div className="max-w-2xl mx-auto">
                <h1 className="text-xl font-semibold mb-6" style={{ color: 'var(--text-primary)' }}>
                    Profile
                </h1>
                <ProfileForm
                    existingProfile={profile}
                    onSuccess={handleSuccess}
                />
            </div>
        </div>
    );
}